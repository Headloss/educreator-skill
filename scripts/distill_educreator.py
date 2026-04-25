#!/usr/bin/env python
"""
Distill an education/self-media creator corpus into a standalone Cursor skill.

Inputs:
- PDF root, or an existing corpus.jsonl for replay/testing.

Outputs inside --output-dir:
- SKILL.md
- references/research/*.md
- artifacts/corpus.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover - dependency checked at runtime
    PdfReader = None  # type: ignore

try:
    import numpy as np
    import pypdfium2 as pdfium
    from rapidocr_onnxruntime import RapidOCR

    OCR_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    OCR_AVAILABLE = False


STOPWORDS = {
    "我们",
    "你们",
    "他们",
    "这个",
    "那个",
    "因为",
    "所以",
    "如果",
    "但是",
    "以及",
    "一个",
    "可以",
    "就是",
    "对于",
    "需要",
    "还是",
    "已经",
    "很多",
    "什么",
    "如何",
    "为什么",
    "当然",
    "比如",
    "不过",
    "事实上",
    "那么",
    "第一",
    "第二",
    "年的",
    "钢印",
    "思想钢印",
    "原创思想钢印",
    "原创思想钢印思想钢印",
    "上海原创思想钢印思想",
    "喜欢作者",
    "关注我",
    "长按二维码",
    "公众号",
    "篇原创内容",
    "年度十大影响力用户",
    "私募基金经理",
    "投资需要信仰",
    "把知识变成财富",
    "最好的地方就是股市",
    "实际上",
    "等等",
    "到了",
    "以上",
    "左右",
    "的人",
    "的公司",
    "我在",
    "的年",
    "本文",
    "系列",
}

BOILERPLATE_SUBSTRINGS = {
    "喜欢作者",
    "关注我",
    "长按二维码",
    "二维码",
    "公众号",
    "篇原创内容",
    "年度十大影响力用户",
    "私募基金经理",
    "投资需要信仰",
    "把知识变成财富",
    "最好的地方就是股市",
    "雪球",
    "原创思想钢印",
    "上海原创思想钢印",
    "更多关于本文的讨论",
    "欢迎加入提问",
    "方法如下",
}

BOILERPLATE_LINE_PATTERNS = [
    re.compile(r"^\d+\s*/\s*\d+$"),
    re.compile(r"^[↓↑]+$"),
    re.compile(r"^[-—_=]{2,}$"),
    re.compile(r"^\d{4}[-/年]\d{1,2}[-/月]\d{1,2}.*$"),
    re.compile(r"^[\u4e00-\u9fff]{2,8}系列$"),
]

TERM_PREFIX_STOP_CHARS = tuple("的了和与在从把被是有对及并但而或让用这那我你他它其个年月日")
TERM_SUFFIX_STOP_CHARS = tuple("的了和与在从把被是有对及并但而或到")

DOMAIN_ANCHORS = {
    "估值",
    "波动",
    "风险",
    "胜率",
    "赔率",
    "仓位",
    "筹码",
    "催化剂",
    "预期",
    "确定性",
    "反身性",
    "边际",
    "概率",
    "定价",
    "现金流",
    "基本面",
    "认知差",
    "做空",
    "做多",
    "量化",
}

CONCEPT_MARKERS = {
    "模型",
    "框架",
    "结构",
    "效应",
    "策略",
    "逻辑",
    "悖论",
    "三角",
    "四象限",
    "体系",
    "机制",
    "路径",
}

QUESTION_PHRASE_MARKERS = {
    "什么",
    "如何",
    "为什么",
    "到底",
    "还是",
    "是否",
    "怎么",
    "一文说清",
}

CLAIM_HINTS = [
    "本质",
    "关键",
    "核心",
    "不是",
    "要",
    "应当",
    "必须",
    "逻辑",
    "框架",
    "模型",
    "方法",
    "判断",
    "风险",
    "预期",
    "分歧",
    "边际",
    "概率",
]

CONCEPT_ALIASES: Dict[str, List[str]] = {
    "交易不可能三角": ["交易的不可能三角", "不可能三角形", "不可能三角"],
    "信息定价四象限": ["信息定价四象限", "定价四象限", "四象限"],
    "赔率-胜率-仓位": ["赔率胜率仓位", "赔率-胜率-仓位", "胜率", "赔率", "仓位"],
    "贝叶斯预期差": ["贝叶斯预期差", "贝叶斯", "预期差", "概率判断"],
    "筹码结构与走势关系": ["筹码结构和走势关系", "筹码结构与走势关系", "筹码结构", "上涨力度"],
    "确定性与估值锚": ["确定性", "估值锚", "现金流确定性"],
    "催化剂路径": ["催化剂", "利空催化剂", "利好催化剂"],
    "边际变化": ["边际变化", "边际思维", "边际改善"],
}

FRAMEWORK_TEMPLATES: Dict[str, Dict[str, object]] = {
    "交易不可能三角": {
        "problem": "判断一种交易方法是否自洽，尤其是高收益、高胜率、高容量是否被同时许诺。",
        "variables": ["收益率", "胜率", "机会容量/交易频率"],
        "relationship": "三者通常不能同时最大化。提高收益率往往要牺牲胜率或容量；追求高胜率常常压低赔率；扩大容量会稀释边际收益。",
        "logic": [
            "先识别策略承诺的是哪两个角。",
            "追问第三个角被谁承担成本。",
            "检查收益来自基本面、估值修复、流动性还是对手盘失误。",
            "若三角同时完美，优先怀疑样本期、容量或尾部风险。",
        ],
        "action": "把策略拆成可验证变量，避免被高收益叙事直接带走。",
        "boundary": "极端牛市或流动性单边阶段会短暂掩盖三角约束。",
    },
    "赔率-胜率-仓位": {
        "problem": "决定买不买、买多少、何时加减仓。",
        "variables": ["胜率", "赔率", "仓位"],
        "relationship": "胜率决定判断成功概率，赔率决定盈亏比，仓位决定暴露强度。重仓机会通常来自胜率和赔率同时改善。",
        "logic": [
            "先判断胜率来自确定性、信息优势还是情绪错杀。",
            "再估算赔率：上行空间、下行损失和时间成本。",
            "用仓位表达不确定性，而不是用观点强度替代风险控制。",
            "胜率或赔率只有一个改善时，优先小仓位或等待拐点。",
        ],
        "action": "把观点转换成仓位，而不是把仓位建立在情绪上。",
        "boundary": "流动性断裂、基本面突变、估值锚失效时，原有赔率估算会失真。",
    },
    "贝叶斯预期差": {
        "problem": "判断新信息是否真的改变投资结论，还是只改变叙事。",
        "variables": ["先验判断", "新增证据", "市场一致预期", "边际修正幅度"],
        "relationship": "新信息的价值不在绝对好坏，而在它相对先验和市场预期改变了多少概率。",
        "logic": [
            "列出原来的先验假设和市场共识。",
            "判断新信息是强化、削弱还是推翻先验。",
            "比较自己的概率修正和市场价格修正谁更大。",
            "只有概率修正大于价格修正，才形成可交易的预期差。",
        ],
        "action": "把消息解读从好坏判断改为概率更新。",
        "boundary": "信息不可验证、样本过少或价格已充分反应时，预期差可能不存在。",
    },
    "信息定价四象限": {
        "problem": "判断一条信息是否值得行动。",
        "variables": ["信息重要性", "市场知晓度", "定价程度", "可验证性"],
        "relationship": "重要但未充分定价的信息最有价值；广泛知晓且已定价的信息只提供解释，不提供优势。",
        "logic": [
            "判断信息是否影响现金流、估值锚、风险偏好或催化剂。",
            "判断市场是否已经广泛讨论。",
            "观察价格是否已经反映该信息。",
            "只在重要、可验证、未充分定价的象限寻找机会。",
        ],
        "action": "把信息筛选从新闻刺激改为定价判断。",
        "boundary": "市场流动性极差或信息真假难辨时，象限判断容易误判。",
    },
    "筹码结构与走势关系": {
        "problem": "解释为什么基本面相似的标的走势力度不同。",
        "variables": ["持仓成本", "浮盈浮亏", "换手", "对手盘", "趋势反馈"],
        "relationship": "筹码结构影响上涨阻力和下跌压力；走势又会反过来改变筹码分布和投资者心理。",
        "logic": [
            "识别主要持有人处于浮盈、浮亏还是成本附近。",
            "观察换手是否消化了上方压力或形成新成本区。",
            "区分基本面驱动上涨和筹码真空推动上涨。",
            "把走势当作筹码结构变化的结果和输入，而不是直接等同于基本面。",
        ],
        "action": "用筹码结构解释交易节奏，避免只靠基本面线性外推。",
        "boundary": "公开数据不足、突发基本面变化或极端情绪行情会削弱筹码解释力。",
    },
    "确定性与估值锚": {
        "problem": "判断长期持有逻辑和估值是否稳固。",
        "variables": ["现金流确定性", "增长持续性", "估值锚", "外生变量"],
        "relationship": "确定性越强，估值锚越稳定；外生变量越强，历史确定性越容易失效。",
        "logic": [
            "先看现金流和商业模式是否能穿越周期。",
            "再判断增长和竞争格局是否支持估值锚。",
            "识别外生变量是否正在改变原有确定性。",
            "用确定性强弱决定持有期限和仓位上限。",
        ],
        "action": "把长期持有建立在可复核的确定性上，而不是故事稳定感上。",
        "boundary": "政策、技术替代、需求突变会让历史确定性失效。",
    },
    "催化剂路径": {
        "problem": "判断观点如何转化为价格变化。",
        "variables": ["观点", "催化剂", "时间成本", "对手盘心理"],
        "relationship": "没有催化剂的正确观点可能长期无法兑现，甚至被时间成本吞噬。",
        "logic": [
            "区分长期正确和可交易正确。",
            "寻找能迫使市场重定价的事件。",
            "评估催化剂发生概率和时间窗口。",
            "没有催化剂时降低仓位或拉长评估周期。",
        ],
        "action": "把观点落到可触发重定价的路径上。",
        "boundary": "慢变量改善和长期复利型资产可能不依赖明确短期催化剂。",
    },
    "边际变化": {
        "problem": "判断市场为何对好消息或坏消息反应反常。",
        "variables": ["事实水平", "边际方向", "一致预期", "价格位置"],
        "relationship": "价格常常反映边际变化而非静态好坏；坏中变好可能上涨，好中变差可能下跌。",
        "logic": [
            "分清事实绝对水平和边际变化方向。",
            "比较边际变化与市场原有预期。",
            "检查价格是否已经提前反应。",
            "用边际变化解释预期差，而不是用静态好坏解释涨跌。",
        ],
        "action": "把分析焦点从好坏切到变化率和预期差。",
        "boundary": "趋势末端和流动性冲击阶段，价格可能短期脱离边际基本面。",
    },
}

TEMPLATE_ORDER = [
    "赔率-胜率-仓位",
    "交易不可能三角",
    "贝叶斯预期差",
    "信息定价四象限",
    "筹码结构与走势关系",
    "确定性与估值锚",
    "催化剂路径",
    "边际变化",
]


@dataclass
class PageRecord:
    page: int
    text: str
    source: str


@dataclass
class DocRecord:
    rel_path: str
    category: str
    title: str
    pages_total: int
    pages_processed: int
    ocr_pages: int
    chars: int
    date_hint: str
    page_records: List[PageRecord]


def normalize_text(text: str) -> str:
    text = text.replace("\u3000", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_pdf_text(text: str) -> str:
    text = normalize_text(text)
    cleaned_lines: List[str] = []
    skipping_series_index = False

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = re.sub(r"\d{4}年\d{1,2}月\d{1,2}日\s+\d{1,2}:\d{2}\s+上海原创思想钢印思想钢印.*$", "", line).strip()
        line = re.sub(r"上海原创思想钢印思想钢印.*$", "", line).strip()
        if not line:
            continue
        if any(pattern.match(line) for pattern in BOILERPLATE_LINE_PATTERNS):
            skipping_series_index = line.endswith("系列")
            continue
        if skipping_series_index and re.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+", line):
            continue
        skipping_series_index = False
        if any(marker in line for marker in ("更多关于本文的讨论", "欢迎加入提问", "方法如下")):
            break
        if any(marker in line for marker in BOILERPLATE_SUBSTRINGS):
            continue
        cleaned_lines.append(line)

    return normalize_text("\n".join(cleaned_lines))


def normalize_key(text: str) -> str:
    return re.sub(r"[\s,，。；;：:、_\\/\-—\"'“”‘’《》<>（）()]+", "", text).lower()


def split_sentences(text: str) -> List[str]:
    parts = re.split(r"[。！？!?；;\n]+", text)
    return [p.strip() for p in parts if p.strip()]


def detect_date_hint(text: str) -> str:
    m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", text)
    if m:
        y, mo, d = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    m = re.search(r"\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b", text)
    if m:
        y, mo, d = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    return ""


def title_from_rel_path(rel_path: str) -> str:
    stem = Path(rel_path).stem
    stem = re.sub(r"^\d+[_ -]*", "", stem)
    return stem.strip()


def category_from_rel_path(rel_path: str) -> str:
    parts = re.split(r"[\\/]", rel_path)
    return parts[0] if len(parts) > 1 else "corpus"


def is_topic_term(term: str) -> bool:
    term = term.strip()
    if len(term) < 2 or len(term) > 10:
        return False
    normalized = normalize_key(term)
    if not normalized:
        return False
    if term in STOPWORDS or normalized in {normalize_key(w) for w in STOPWORDS}:
        return False
    if any(normalize_key(marker) in normalized for marker in BOILERPLATE_SUBSTRINGS):
        return False
    if term.endswith("系列") or "系列之" in term:
        return False
    if term.startswith(TERM_PREFIX_STOP_CHARS) or term.endswith(TERM_SUFFIX_STOP_CHARS):
        return False
    if re.fullmatch(r"[一二三四五六七八九十]+", term):
        return False
    return True


def extract_terms(text: str) -> Counter:
    words = re.findall(r"[\u4e00-\u9fff]{2,10}", clean_pdf_text(text))
    c = Counter()
    for w in words:
        if not is_topic_term(w):
            continue
        c[w] += 1
    return c


def score_topic_term(term: str, frequency: int, title_hits: int = 0) -> float:
    normalized = normalize_key(term)
    is_bare_marker = term in CONCEPT_MARKERS
    anchor_hits = sum(1 for anchor in DOMAIN_ANCHORS if normalize_key(anchor) in normalized)
    marker_hits = 0 if is_bare_marker else sum(1 for marker in CONCEPT_MARKERS if normalize_key(marker) in normalized)
    effective_title_hits = title_hits if len(term) >= 4 or anchor_hits or marker_hits else 0

    score = min(frequency, 4)
    score += min(anchor_hits, 3) * 2
    score += min(marker_hits, 2) * 2
    score += min(effective_title_hits, 2) * 3

    if 4 <= len(term) <= 8:
        score += 1
    if len(term) <= 2 and not anchor_hits and not marker_hits and not effective_title_hits:
        score -= 6
    if len(term) == 3 and not anchor_hits and not marker_hits and not effective_title_hits:
        score -= 3
    if not anchor_hits and not marker_hits and not effective_title_hits and frequency <= 2:
        score -= 2
    if any(marker in term for marker in QUESTION_PHRASE_MARKERS):
        score -= 8

    return float(score)


def rank_topic_terms(
    terms: Counter,
    titles: Sequence[str],
    limit: int,
) -> List[Tuple[str, int, float]]:
    title_text = "\n".join(titles)
    ranked: List[Tuple[str, int, float]] = []
    for term, frequency in terms.items():
        title_hits = title_text.count(term)
        score = score_topic_term(term, int(frequency), title_hits)
        if score < 4:
            continue
        ranked.append((term, int(frequency), score))
    ranked.sort(key=lambda row: (-row[2], -row[1], -len(row[0]), row[0]))
    return ranked[:limit]


def sentence_score(sentence: str) -> int:
    score = 0
    if 18 <= len(sentence) <= 180:
        score += 2
    score += sum(1 for k in CLAIM_HINTS if k in sentence)
    if any(k in sentence for k in ("不是", "而是", "只有", "关键在于", "本质上")):
        score += 2
    return score


def init_ocr_engine() -> Optional["RapidOCR"]:
    if not OCR_AVAILABLE:
        return None
    try:
        return RapidOCR()
    except Exception:
        return None


def ocr_page(ocr_engine: "RapidOCR", pdf_doc: "pdfium.PdfDocument", page_idx: int) -> str:
    page = pdf_doc[page_idx]
    pil_image = page.render(scale=2.0).to_pil()
    result, _ = ocr_engine(np.asarray(pil_image))
    texts: List[str] = []
    if not result:
        return ""
    for item in result:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            txt = item[1]
            if isinstance(txt, str):
                texts.append(txt)
            elif isinstance(txt, (list, tuple)) and txt:
                texts.append(str(txt[0]))
        else:
            texts.append(str(item))
    return normalize_text("\n".join(texts))


def extract_pdf_doc(
    pdf_path: Path,
    pdf_root: Path,
    ocr_mode: str,
    max_pages_per_pdf: int,
    min_chars_before_ocr: int,
    ocr_engine: Optional["RapidOCR"],
) -> DocRecord:
    if PdfReader is None:
        raise RuntimeError("pypdf is required for PDF extraction")

    rel_path = str(pdf_path.relative_to(pdf_root))
    reader = PdfReader(str(pdf_path))
    pages_total = len(reader.pages)
    pages_to_read = pages_total if max_pages_per_pdf <= 0 else min(pages_total, max_pages_per_pdf)

    pdf_doc = None
    if ocr_mode != "off" and ocr_engine is not None:
        try:
            pdf_doc = pdfium.PdfDocument(str(pdf_path))
        except Exception:
            pdf_doc = None

    page_records: List[PageRecord] = []
    ocr_pages = 0
    date_hint = ""

    for i in range(pages_to_read):
        txt = normalize_text(reader.pages[i].extract_text() or "")
        source = "text"
        should_ocr = ocr_mode == "force" or (
            ocr_mode == "auto" and len(txt) < min_chars_before_ocr
        )
        if should_ocr and ocr_engine is not None and pdf_doc is not None:
            ocr_txt = ocr_page(ocr_engine, pdf_doc, i)
            if ocr_txt:
                txt = normalize_text(f"{txt}\n{ocr_txt}" if txt else ocr_txt)
                source = "mixed" if source == "text" and txt else "ocr"
                ocr_pages += 1
        if txt and not date_hint:
            date_hint = detect_date_hint(txt)
        txt = clean_pdf_text(txt)
        page_records.append(PageRecord(page=i + 1, text=txt, source=source))

    return DocRecord(
        rel_path=rel_path,
        category=category_from_rel_path(rel_path),
        title=title_from_rel_path(rel_path),
        pages_total=pages_total,
        pages_processed=pages_to_read,
        ocr_pages=ocr_pages,
        chars=sum(len(p.text) for p in page_records),
        date_hint=date_hint,
        page_records=page_records,
    )


def load_docs_from_pdfs(args: argparse.Namespace) -> List[DocRecord]:
    pdf_root = Path(args.pdf_root).expanduser().resolve()
    if not pdf_root.exists():
        raise FileNotFoundError(f"PDF root does not exist: {pdf_root}")
    pdfs = sorted(pdf_root.rglob("*.pdf"))
    if args.sample_limit > 0:
        pdfs = pdfs[: args.sample_limit]
    if not pdfs:
        raise RuntimeError(f"No PDFs found under: {pdf_root}")

    ocr_engine = init_ocr_engine() if args.ocr_mode != "off" else None
    if args.ocr_mode != "off" and ocr_engine is None:
        print("[WARN] OCR requested but engine is unavailable; using text layer only.")

    docs: List[DocRecord] = []
    for idx, pdf_path in enumerate(pdfs, start=1):
        docs.append(
            extract_pdf_doc(
                pdf_path=pdf_path,
                pdf_root=pdf_root,
                ocr_mode=args.ocr_mode,
                max_pages_per_pdf=args.max_pages_per_pdf,
                min_chars_before_ocr=args.min_chars_before_ocr,
                ocr_engine=ocr_engine,
            )
        )
        if idx % 25 == 0 or idx == len(pdfs):
            print(f"[INFO] processed {idx}/{len(pdfs)} PDFs")
    return docs


def load_docs_from_corpus_jsonl(corpus_path: Path, sample_limit: int) -> List[DocRecord]:
    grouped: Dict[str, List[PageRecord]] = defaultdict(list)
    sources: Dict[str, Counter] = defaultdict(Counter)
    with corpus_path.open("r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            rel_path = row["file"]
            grouped[rel_path].append(
                PageRecord(
                    page=int(row.get("page", 0)),
                    text=clean_pdf_text(row.get("text", "")),
                    source=row.get("source", "text"),
                )
            )
            sources[rel_path][row.get("source", "text")] += 1

    items = sorted(grouped.items(), key=lambda x: x[0])
    if sample_limit > 0:
        items = items[:sample_limit]

    docs: List[DocRecord] = []
    for rel_path, pages in items:
        pages.sort(key=lambda p: p.page)
        text = "\n".join(p.text for p in pages)
        docs.append(
            DocRecord(
                rel_path=rel_path,
                category=category_from_rel_path(rel_path),
                title=title_from_rel_path(rel_path),
                pages_total=max((p.page for p in pages), default=0),
                pages_processed=len(pages),
                ocr_pages=sources[rel_path]["ocr"] + sources[rel_path]["mixed"],
                chars=len(text),
                date_hint=detect_date_hint(text),
                page_records=pages,
            )
        )
    return docs


def write_corpus_jsonl(output_dir: Path, docs: Sequence[DocRecord]) -> None:
    artifacts = output_dir / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    with (artifacts / "corpus.jsonl").open("w", encoding="utf-8") as f:
        for d in docs:
            for p in d.page_records:
                f.write(
                    json.dumps(
                        {
                            "file": d.rel_path,
                            "category": d.category,
                            "page": p.page,
                            "source": p.source,
                            "text": p.text,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )


def parse_focus_concepts(raw: str) -> List[str]:
    if not raw.strip():
        return []
    return [p.strip() for p in re.split(r"[,，;；|]", raw) if p.strip()]


def alias_map(focus_concepts: Sequence[str]) -> Dict[str, List[str]]:
    aliases = {k: list(v) for k, v in CONCEPT_ALIASES.items()}
    for concept in focus_concepts:
        matched = False
        norm = normalize_key(concept)
        for canonical, vals in aliases.items():
            if norm == normalize_key(canonical) or any(norm == normalize_key(v) for v in vals):
                if concept not in vals:
                    vals.insert(0, concept)
                matched = True
                break
        if not matched:
            aliases[concept] = [concept]
    return aliases


def text_contains_alias(text: str, aliases: Sequence[str]) -> bool:
    norm_text = normalize_key(text)
    return any(normalize_key(alias) in norm_text for alias in aliases)


def nearby_title_concepts(title: str) -> List[str]:
    found: List[str] = []
    triggers = "不可能三角|四象限|贝叶斯|预期差|筹码结构|赔率|胜率|仓位|催化剂|边际变化|确定性|估值锚"
    for m in re.finditer(rf"[\u4e00-\u9fffA-Za-z0-9“”《》、\-]{{0,8}}(?:{triggers})[\u4e00-\u9fffA-Za-z0-9“”《》、\-]{{0,10}}", title):
        value = re.sub(r"^[一二三四五六七八九十0-9、：:，,]+", "", m.group(0)).strip("“”《》 ")
        if 2 <= len(value) <= 24:
            found.append(value)
    return found


def collect_concepts(
    docs: Sequence[DocRecord], focus_concepts: Sequence[str]
) -> Tuple[List[Dict[str, object]], List[str]]:
    aliases = alias_map(focus_concepts)
    concept_hits: Dict[str, Dict[str, object]] = {
        name: {"title_hits": [], "contexts": [], "aliases": vals} for name, vals in aliases.items()
    }

    for d in docs:
        for title_concept in nearby_title_concepts(d.title):
            if title_concept not in concept_hits:
                concept_hits[title_concept] = {
                    "title_hits": [],
                    "contexts": [],
                    "aliases": [title_concept],
                }

        for name, data in concept_hits.items():
            vals = data["aliases"]  # type: ignore[assignment]
            if text_contains_alias(d.title, vals):  # type: ignore[arg-type]
                data["title_hits"].append((d.rel_path, d.title))  # type: ignore[index]

        for p in d.page_records:
            if not p.text:
                continue
            for name, data in concept_hits.items():
                vals = data["aliases"]  # type: ignore[assignment]
                if not text_contains_alias(p.text, vals):  # type: ignore[arg-type]
                    continue
                contexts = data["contexts"]  # type: ignore[assignment]
                if len(contexts) >= 12:
                    continue
                sentence = next(
                    (s for s in split_sentences(p.text) if text_contains_alias(s, vals)),  # type: ignore[arg-type]
                    p.text[:140],
                )
                contexts.append((d.rel_path, p.page, sentence[:180]))

    cards: List[Dict[str, object]] = []
    for name, data in concept_hits.items():
        title_hits = data["title_hits"]  # type: ignore[assignment]
        contexts = data["contexts"]  # type: ignore[assignment]
        if not title_hits and not contexts:
            continue
        score = len(title_hits) * 3 + min(len(contexts), 8)
        if name in FRAMEWORK_TEMPLATES:
            score += 4
        cards.append(
            {
                "name": name,
                "aliases": data["aliases"],
                "score": score,
                "title_hits": title_hits[:6],
                "contexts": contexts[:8],
                "is_focus": any(normalize_key(name) == normalize_key(f) for f in focus_concepts)
                or any(
                    normalize_key(f) in [normalize_key(a) for a in data["aliases"]]  # type: ignore[index]
                    for f in focus_concepts
                ),
            }
        )
    cards.sort(key=lambda c: int(c["score"]), reverse=True)

    missing_focus = []
    for focus in focus_concepts:
        focus_norm = normalize_key(focus)
        found = False
        for card in cards:
            values = [str(card["name"])] + [str(v) for v in card.get("aliases", [])]
            value_norms = [normalize_key(v) for v in values]
            if any(focus_norm == v or focus_norm in v or v in focus_norm for v in value_norms):
                found = True
                break
        if not found:
            missing_focus.append(focus)
    return cards, missing_focus


def extract_core_claims(docs: Sequence[DocRecord]) -> List[Dict[str, object]]:
    claim_map: Dict[str, Dict[str, object]] = {}
    for d in docs:
        for p in d.page_records:
            for sentence in split_sentences(p.text):
                if sentence_score(sentence) < 4:
                    continue
                key = normalize_key(sentence[:90])
                if key not in claim_map:
                    claim_map[key] = {"text": sentence[:180], "evidence": []}
                evidence = claim_map[key]["evidence"]  # type: ignore[assignment]
                if len(evidence) < 6:
                    evidence.append((d.rel_path, p.page))

    rows = []
    for item in claim_map.values():
        evidence = item["evidence"]  # type: ignore[assignment]
        if len(evidence) >= 2:
            rows.append({"text": item["text"], "frequency": len(evidence), "evidence": evidence})
    rows.sort(key=lambda r: int(r["frequency"]), reverse=True)
    return rows[:80]


def build_framework_cards(concepts: Sequence[Dict[str, object]]) -> List[Dict[str, object]]:
    def resolve_template_key(concept: Dict[str, object]) -> Optional[str]:
        name = str(concept["name"])
        aliases = [str(a) for a in concept.get("aliases", [])]
        if name in FRAMEWORK_TEMPLATES:
            return name
        for key, vals in CONCEPT_ALIASES.items():
            candidates = [name] + aliases
            if any(candidate == key or candidate in vals for candidate in candidates):
                return key
        return None

    def is_junk_concept(name: str) -> bool:
        return name.startswith(("的", "了", "和", "与")) or len(name) < 3

    templated: List[Tuple[int, Dict[str, object], str]] = []
    generic: List[Dict[str, object]] = []
    for concept in concepts:
        key = resolve_template_key(concept)
        if key:
            order = TEMPLATE_ORDER.index(key) if key in TEMPLATE_ORDER else len(TEMPLATE_ORDER)
            templated.append((order, concept, key))
        else:
            generic.append(concept)

    ordered: List[Tuple[Dict[str, object], Optional[str]]] = []
    seen: set[str] = set()
    for _, concept, key in sorted(templated, key=lambda x: (x[0], -int(x[1]["score"]))):
        if key in seen:
            continue
        seen.add(key)
        ordered.append((concept, key))
    for concept in generic:
        if int(concept["score"]) >= 12 and not is_junk_concept(str(concept["name"])):
            ordered.append((concept, None))

    cards: List[Dict[str, object]] = []
    for concept, template_key in ordered:
        name = str(concept["name"])
        output_name = template_key or name
        template = FRAMEWORK_TEMPLATES.get(output_name)
        if template is None:
            template = {
                "problem": f"处理与“{name}”相关的判断问题。",
                "variables": ["对象", "条件", "变化方向"],
                "relationship": "先确认概念的适用条件，再判断变量变化是否足以改变结论。",
                "logic": [
                    "定义问题对象和时间窗口。",
                    "找出该概念关联的关键变量。",
                    "判断变量之间是否存在 tradeoff 或边际变化。",
                    "给出结论、反例和止错条件。",
                ],
                "action": "把抽象概念转化为可检查的判断步骤。",
                "boundary": "语料只提供概念线索、变量关系不足时，应降低置信度。",
            }

        cards.append(
            {
                "name": output_name,
                "problem": template["problem"],
                "variables": template["variables"],
                "relationship": template["relationship"],
                "logic": template["logic"],
                "action": template["action"],
                "boundary": template["boundary"],
                "references": concept.get("contexts", [])[:5],
            }
        )
        if len(cards) >= 10:
            break
    return cards


def build_topic_clusters(docs: Sequence[DocRecord]) -> Dict[str, Counter]:
    clusters: Dict[str, Counter] = defaultdict(Counter)
    for d in docs:
        text = "\n".join(p.text for p in d.page_records)
        clusters[d.category].update(extract_terms(text))
    return clusters


def format_refs(refs: Iterable[Tuple[str, int, str]]) -> str:
    parts = []
    for ref in refs:
        if len(ref) == 3:
            f, p, _ = ref
        else:
            f, p = ref[:2]  # type: ignore[misc]
        parts.append(f"`{f}` p.{p}")
    return "；".join(parts) if parts else "No local reference captured."


def write_reports(
    output_dir: Path,
    docs: Sequence[DocRecord],
    concepts: Sequence[Dict[str, object]],
    missing_focus: Sequence[str],
    claims: Sequence[Dict[str, object]],
    frameworks: Sequence[Dict[str, object]],
) -> Dict[str, int]:
    research_dir = output_dir / "references" / "research"
    research_dir.mkdir(parents=True, exist_ok=True)

    total_pages = sum(d.pages_processed for d in docs)
    total_ocr_pages = sum(d.ocr_pages for d in docs)
    low_text_pages = sum(1 for d in docs for p in d.page_records if len(p.text) < 40)

    lines = [
        "# 01 Corpus Index",
        "",
        f"- Total docs: {len(docs)}",
        f"- Processed pages: {total_pages}",
        f"- OCR pages: {total_ocr_pages}",
        f"- Low-text pages: {low_text_pages}",
        "",
        "| File | Category | Pages(total/used) | Chars | OCR pages | Date hint |",
        "|---|---|---:|---:|---:|---|",
    ]
    for d in docs:
        lines.append(
            f"| `{d.rel_path}` | {d.category} | {d.pages_total}/{d.pages_processed} | {d.chars} | {d.ocr_pages} | {d.date_hint or '-'} |"
        )
    (research_dir / "01-corpus-index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    clusters = build_topic_clusters(docs)
    titles_by_category: Dict[str, List[str]] = defaultdict(list)
    for d in docs:
        titles_by_category[d.category].append(d.title)
    lines = ["# 02 Topic Clusters", ""]
    for category, terms in sorted(clusters.items(), key=lambda x: x[0]):
        top_terms = rank_topic_terms(terms, titles_by_category.get(category, []), 24)
        lines.append(f"## {category}")
        lines.append("- Top terms: " + " / ".join(f"{k}({v})" for k, v, _ in top_terms))
        lines.append("")
    (research_dir / "02-topic-clusters.md").write_text("\n".join(lines), encoding="utf-8")

    lines = ["# 03 Core Claims", ""]
    if not claims:
        lines.append("- No repeated claims extracted; review corpus quality.")
    for idx, claim in enumerate(claims, start=1):
        lines.append(f"{idx}. {claim['text']}")
        lines.append(f"   - Frequency: {claim['frequency']}")
        lines.append(f"   - Internal refs: {format_refs(claim['evidence'])}")
    (research_dir / "03-core-claims.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    lines = ["# 04 Concept Cards", ""]
    if missing_focus:
        lines.append("## Missing Or Weak Focus Concepts")
        for concept in missing_focus:
            lines.append(f"- {concept}")
        lines.append("")
    for concept in concepts:
        lines.append(f"## {concept['name']}")
        lines.append(f"- Score: {concept['score']}")
        if concept.get("title_hits"):
            lines.append("- Title signals:")
            for rel_path, title in concept["title_hits"]:  # type: ignore[index]
                lines.append(f"  - `{rel_path}`: {title}")
        if concept.get("contexts"):
            lines.append("- Context signals:")
            for rel_path, page, sentence in concept["contexts"]:  # type: ignore[index]
                lines.append(f"  - `{rel_path}` p.{page}: {sentence}")
        lines.append("")
    (research_dir / "04-concept-cards.md").write_text("\n".join(lines), encoding="utf-8")

    lines = ["# 05 Framework Cards", ""]
    for idx, card in enumerate(frameworks, start=1):
        lines.append(f"## Card {idx}: {card['name']}")
        lines.append(f"- Problem type: {card['problem']}")
        lines.append("- Core variables: " + " / ".join(str(v) for v in card["variables"]))
        lines.append(f"- Variable relationship: {card['relationship']}")
        lines.append("- Judgment logic:")
        for step_idx, step in enumerate(card["logic"], start=1):
            lines.append(f"  {step_idx}. {step}")
        lines.append(f"- Action implication: {card['action']}")
        lines.append(f"- Failure boundary: {card['boundary']}")
        lines.append(f"- Internal refs: {format_refs(card.get('references', []))}")
        lines.append("")
    (research_dir / "05-framework-cards.md").write_text("\n".join(lines), encoding="utf-8")

    lines = [
        "# 06 Boundaries And Gaps",
        "",
        f"- Docs processed: {len(docs)}",
        f"- Pages processed: {total_pages}",
        f"- OCR pages: {total_ocr_pages}",
        f"- Low-text pages: {low_text_pages}",
        f"- OCR engine available: {OCR_AVAILABLE}",
        f"- Missing or weak focus concepts: {', '.join(missing_focus) if missing_focus else 'None'}",
        "",
        "## Known Limits",
        "- Local corpus defines the extracted framework; it may not cover all public writings.",
        "- OCR can miss chart/layout meaning.",
        "- Title-derived frameworks need human review if supporting contexts are sparse.",
        "- Runtime web research updates current facts, not the distilled historical corpus.",
    ]
    (research_dir / "06-boundaries-and-gaps.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "doc_count": len(docs),
        "processed_pages": total_pages,
        "ocr_pages": total_ocr_pages,
        "low_text_pages": low_text_pages,
        "cluster_count": len(clusters),
        "claim_count": len(claims),
        "concept_count": len(concepts),
        "framework_count": len(frameworks),
        "missing_focus_count": len(missing_focus),
    }


def bullet_list(items: Sequence[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def format_concepts_for_skill(concepts: Sequence[Dict[str, object]]) -> str:
    def is_template_concept(concept: Dict[str, object]) -> bool:
        name = str(concept["name"])
        aliases = [str(a) for a in concept.get("aliases", [])]
        return name in FRAMEWORK_TEMPLATES or any(
            name == key or name in vals or any(alias in vals for alias in aliases)
            for key, vals in CONCEPT_ALIASES.items()
        )

    def is_clean_generic(concept: Dict[str, object]) -> bool:
        name = str(concept["name"])
        return int(concept["score"]) >= 12 and not name.startswith(("的", "了", "和", "与"))

    def concept_priority(concept: Dict[str, object]) -> Tuple[int, int]:
        return (0 if is_template_concept(concept) else 1, -int(concept["score"]))

    lines: List[str] = []
    selected = [
        concept
        for concept in sorted(concepts, key=concept_priority)
        if is_template_concept(concept) or is_clean_generic(concept)
    ][:10]
    for concept in selected:
        contexts = concept.get("contexts", [])
        source_hint = "title signal" if concept.get("title_hits") else "corpus signal"
        lines.append(f"### {concept['name']}")
        lines.append(f"- Role: high-signal named concept captured from {source_hint}.")
        if contexts:
            sample = contexts[0][2]  # type: ignore[index]
            lines.append(f"- Corpus clue: {sample}")
        lines.append("")
    return "\n".join(lines).strip()


def format_frameworks_for_skill(frameworks: Sequence[Dict[str, object]]) -> str:
    lines: List[str] = []
    for idx, card in enumerate(frameworks, start=1):
        lines.append(f"### {idx}. {card['name']}")
        lines.append(f"- Use when: {card['problem']}")
        lines.append("- Variables: " + " / ".join(str(v) for v in card["variables"]))
        lines.append(f"- Relationship: {card['relationship']}")
        lines.append("- How to apply:")
        for step_idx, step in enumerate(card["logic"], start=1):
            lines.append(f"  {step_idx}. {step}")
        lines.append(f"- Decision implication: {card['action']}")
        lines.append(f"- Boundary: {card['boundary']}")
        lines.append("")
    return "\n".join(lines).strip()


def format_topic_map(clusters: Dict[str, Counter]) -> str:
    lines: List[str] = []
    for category, terms in sorted(clusters.items(), key=lambda x: x[0]):
        top = " / ".join(k for k, _, _ in rank_topic_terms(terms, [], 8))
        lines.append(f"- **{category}**: {top}")
    return "\n".join(lines)


def research_dimensions(frameworks: Sequence[Dict[str, object]]) -> str:
    framework_names = {str(f["name"]) for f in frameworks}
    dims = [
        "1. Establish current facts: company, industry, policy, event timeline, and latest available data.",
        "2. Compare market expectation with new facts: what was already priced, what is genuinely incremental.",
    ]
    if "筹码结构与走势关系" in framework_names:
        dims.append("3. Inspect price/volume and chip-structure clues: cost zones, turnover, trapped holders, and trend feedback.")
    if "赔率-胜率-仓位" in framework_names:
        dims.append("4. Estimate odds, win rate, and position implication instead of giving a binary view.")
    if "催化剂路径" in framework_names:
        dims.append("5. Identify catalyst path, timing, and whether the view can be converted into price action.")
    if "贝叶斯预期差" in framework_names or "边际变化" in framework_names:
        dims.append("6. Update priors with new evidence and separate static quality from marginal change.")
    dims.append("7. Build a counter-scenario and mark where the framework would fail.")
    return "\n".join(f"- {d}" for d in dims)


def generate_skill_md(
    output_dir: Path,
    creator_name: str,
    case_name: str,
    metrics: Dict[str, int],
    concepts: Sequence[Dict[str, object]],
    frameworks: Sequence[Dict[str, object]],
    clusters: Dict[str, Counter],
) -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    trigger_names = "、".join(str(c["name"]) for c in concepts[:5]) or creator_name
    text = f"""---
name: {case_name}-knowledge-framework
description: |
  {creator_name} knowledge-framework skill distilled from a local creator corpus.
  Use for {creator_name}体系、{creator_name}框架、{trigger_names}、策略判断、决策复盘、当前事实结合框架分析。
---

# {creator_name} · Knowledge Framework Skill

## Activation

Use this skill when the user asks to:
- summarize {creator_name}'s knowledge system
- apply {creator_name}'s frameworks to a decision
- analyze a market, company, industry, or event through this framework
- review whether a judgment followed the framework

## Answer Workflow

### Step 1: Classify The Question

| Type | Signal | Action |
|---|---|---|
| Framework summary | asks for 体系 / 框架 / 观点 | use the local distilled models |
| Application | asks how to judge or decide | select 1-2 framework cards |
| Current factual analysis | mentions current company / market / event / news | research current facts first |
| Boundary case | outside corpus or unsupported domain | state uncertainty and limits |

### Step 2: Runtime Research For Current Facts

When the question depends on current facts, use web/current search before judging. Do not infer current market facts from the historical corpus.

Research dimensions derived from this creator's frameworks:

{research_dimensions(frameworks)}

### Step 3: Apply The Framework

Answer with:
1. conclusion first
2. selected framework and why
3. stepwise reasoning
4. action implication or decision options
5. boundary, counter-scenario, and confidence

Do not display source-file details by default. Surface them only if the user asks for evidence, uncertainty depends on a source, or the answer is a validation/debugging task.

## Knowledge System

{format_topic_map(clusters)}

## Named Concepts

{format_concepts_for_skill(concepts)}

## Framework Cards

{format_frameworks_for_skill(frameworks)}

## Decision Heuristics

- If a view has no catalyst path, treat it as a long-duration hypothesis rather than an immediate action.
- If price reaction and facts diverge, separate static fact quality from marginal expectation change.
- If only one of odds or win rate improves, express uncertainty through smaller position sizing.
- If a framework promises all variables at once, look for the hidden cost or boundary condition.

## Anti-Patterns

- Treating a correct long-term view as automatically tradable now.
- Explaining every price move with fundamentals while ignoring expectation and chip structure.
- Using static good/bad labels instead of probability updates.
- Letting a framework override missing current facts.

## Boundaries And Confidence

- Corpus scope: {metrics['doc_count']} documents and {metrics['processed_pages']} processed pages.
- Distillation date: {today}.
- OCR pages: {metrics['ocr_pages']}; low-text pages: {metrics['low_text_pages']}.
- This skill captures reusable frameworks from the available corpus, not every possible view by {creator_name}.
- For current markets, companies, policies, or events, web/current research is required before applying the frameworks.

## Local Reference Index

This skill is standalone. Supporting files live inside this skill directory:
- `references/research/01-corpus-index.md`
- `references/research/02-topic-clusters.md`
- `references/research/03-core-claims.md`
- `references/research/04-concept-cards.md`
- `references/research/05-framework-cards.md`
- `references/research/06-boundaries-and-gaps.md`
- `artifacts/corpus.jsonl`
"""
    (output_dir / "SKILL.md").write_text(text, encoding="utf-8")


def generate_readme_md(
    output_dir: Path,
    creator_name: str,
    case_name: str,
    metrics: Dict[str, int],
    concepts: Sequence[Dict[str, object]],
    frameworks: Sequence[Dict[str, object]],
) -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    concept_names = [str(c["name"]) for c in concepts[:8]]
    framework_names = [str(f["name"]) for f in frameworks[:8]]
    concept_text = ", ".join(concept_names) if concept_names else "No concepts captured"
    framework_text = ", ".join(framework_names) if framework_names else "No framework cards captured"

    text = f"""# {creator_name} Knowledge Framework

This is a standalone Cursor skill generated by `educreator-skill`.

## Skill Summary

- Skill name: `{case_name}-knowledge-framework`
- Creator/topic: {creator_name}
- Distillation date: {today}
- Documents processed: {metrics.get('doc_count', 0)}
- Pages processed: {metrics.get('processed_pages', 0)}
- OCR pages: {metrics.get('ocr_pages', 0)}
- Low-text pages: {metrics.get('low_text_pages', 0)}

## How To Use

Use `SKILL.md` when you want to:

- summarize {creator_name}'s knowledge system
- apply the distilled frameworks to a decision
- analyze a market, company, industry, or event through this framework
- review whether a judgment followed the framework

For current facts about companies, markets, policies, or events, research current facts first. Do not infer current facts from the historical corpus.

## Captured Signals

- Named concepts: {concept_text}
- Framework cards: {framework_text}

## Local File Index

- `SKILL.md`: runnable skill instructions
- `references/research/01-corpus-index.md`: processed document index and extraction coverage
- `references/research/02-topic-clusters.md`: scored topic clusters
- `references/research/03-core-claims.md`: repeated claim candidates
- `references/research/04-concept-cards.md`: named concept evidence
- `references/research/05-framework-cards.md`: operational framework cards
- `references/research/06-boundaries-and-gaps.md`: coverage limits and weak areas
- `artifacts/corpus.jsonl`: cleaned page-level corpus records

## Validation

Run:

```bash
python <educreator-skill>/scripts/validate_generated_skill.py --output-dir "<this-skill-dir>"
```

Add `--focus-concepts "<comma-separated concepts>"` when validating expected concepts.

## Boundaries

- The local corpus defines this skill's framework coverage.
- OCR and PDF text extraction can miss charts, layout-dependent meaning, or low-quality scans.
- Topic clusters are scored candidates, not proof that a term is central.
- Runtime current facts must be researched before applying the frameworks to live situations.
"""
    (output_dir / "README.md").write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Distill creator corpus into a standalone knowledge-framework skill")
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument("--pdf-root", help="Root directory containing PDFs")
    source.add_argument("--corpus-jsonl", help="Existing corpus.jsonl to replay")
    p.add_argument("--output-dir", required=True, help="Generated skill directory")
    p.add_argument("--creator-name", required=True, help="Creator/topic display name")
    p.add_argument("--case-name", required=True, help="Generated skill slug without suffix")
    p.add_argument("--focus-concepts", default="", help="Comma-separated concepts that must be checked")
    p.add_argument("--ocr-mode", choices=["off", "auto", "force"], default="auto")
    p.add_argument("--max-pages-per-pdf", type=int, default=0, help="0 means all pages")
    p.add_argument("--min-chars-before-ocr", type=int, default=100)
    p.add_argument("--sample-limit", type=int, default=0, help="Only process first N documents")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.pdf_root:
        docs = load_docs_from_pdfs(args)
    else:
        docs = load_docs_from_corpus_jsonl(Path(args.corpus_jsonl).expanduser().resolve(), args.sample_limit)
    if not docs:
        raise RuntimeError("No documents loaded")

    focus_concepts = parse_focus_concepts(args.focus_concepts)
    write_corpus_jsonl(output_dir, docs)
    concepts, missing_focus = collect_concepts(docs, focus_concepts)
    claims = extract_core_claims(docs)
    frameworks = build_framework_cards(concepts)
    metrics = write_reports(output_dir, docs, concepts, missing_focus, claims, frameworks)
    clusters = build_topic_clusters(docs)
    generate_skill_md(output_dir, args.creator_name, args.case_name, metrics, concepts, frameworks, clusters)
    generate_readme_md(output_dir, args.creator_name, args.case_name, metrics, concepts, frameworks)

    print("[DONE] EduCreator distillation finished")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    if missing_focus:
        print("[WARN] Missing or weak focus concepts: " + ", ".join(missing_focus))


if __name__ == "__main__":
    main()
