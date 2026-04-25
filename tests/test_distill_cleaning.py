import importlib.util
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "distill_educreator.py"
SPEC = importlib.util.spec_from_file_location("distill_educreator", SCRIPT_PATH)
distill = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
sys.modules[SPEC.name] = distill
SPEC.loader.exec_module(distill)


class DistillCleaningTests(unittest.TestCase):
    def test_clean_pdf_text_removes_wechat_boilerplate_and_series_index(self) -> None:
        raw_text = """泡泡玛特被做空后，我研究了5次经典做空，发现最像的是特斯拉
1/4
做空比做多更难
做空的理由总体可以分为四类：
一是估值层面，认为估值过高，与基本面不符；
2026年3月8日 20:29 上海原创思想钢印思想钢印
交易策略系列
2026-1-18 2026年，主动跑赢量化？
2026-1-11 同样是牛市，为什么2025年赚钱比2020年难？
更多关于本文的讨论，欢迎加入提问，方法如下
↓↓↓
"""

        cleaned = distill.clean_pdf_text(raw_text)

        self.assertIn("做空比做多更难", cleaned)
        self.assertIn("估值过高", cleaned)
        self.assertNotIn("1/4", cleaned)
        self.assertNotIn("原创思想钢印", cleaned)
        self.assertNotIn("交易策略系列", cleaned)
        self.assertNotIn("主动跑赢量化", cleaned)
        self.assertNotIn("欢迎加入提问", cleaned)

    def test_extract_terms_filters_boilerplate_terms(self) -> None:
        text = """
        喜欢作者 喜欢作者 关注我 长按二维码 公众号 篇原创内容 年度十大影响力用户 私募基金经理 投资需要信仰
        确定性 估值锚 确定性 交易策略 胜率 赔率 仓位 催化剂 路径
        筹码结构 走势关系 贝叶斯 预期差 信息定价
        """

        terms = distill.extract_terms(text)

        for noisy_term in ["喜欢作者", "关注我", "长按二维码", "公众号", "篇原创内容", "投资需要信仰"]:
            self.assertNotIn(noisy_term, terms)
        for signal_term in ["确定性", "估值锚", "胜率", "赔率", "仓位", "催化剂", "筹码结构"]:
            self.assertIn(signal_term, terms)

    def test_extract_terms_filters_series_boilerplate(self) -> None:
        text = """
        行为金融学系列 年四季度 问题 方法 结果 事件 市场 公司 股票 美元 年代
        波动 势能 动能 波动率末日 反身性 锚定效应 认知差 基本面
        """

        terms = distill.extract_terms(text)

        for noisy_term in ["行为金融学系列", "年四季度"]:
            self.assertNotIn(noisy_term, terms)
        for signal_term in ["波动", "势能", "动能", "波动率末日", "反身性", "锚定效应", "认知差", "基本面"]:
            self.assertIn(signal_term, terms)

    def test_rank_topic_terms_prefers_concepts_over_generic_words(self) -> None:
        terms = Counter(
            {
                "理由": 8,
                "最后": 8,
                "导致": 6,
                "方法": 5,
                "投资": 4,
                "市场": 4,
                "效应": 5,
                "最佳策略是什么": 7,
                "如何抓住基本面的核心": 5,
                "做空": 2,
                "波动率末日": 2,
                "反身性": 2,
                "锚定效应": 2,
                "赔率胜率仓位": 1,
            }
        )
        titles = ["索罗斯方法论", "锚定效应", "投资中那些看似简单的事", "市场如何变化", "泡泡玛特被做空后"]

        ranked = [term for term, _frequency, _score in distill.rank_topic_terms(terms, titles, limit=5)]

        for signal_term in ["赔率胜率仓位", "波动率末日", "锚定效应", "反身性", "做空"]:
            self.assertIn(signal_term, ranked)
        self.assertNotIn("理由", ranked)
        self.assertNotIn("最后", ranked)
        self.assertNotIn("导致", ranked)
        self.assertNotIn("方法", ranked)
        self.assertNotIn("投资", ranked)
        self.assertNotIn("市场", ranked)
        self.assertNotIn("效应", ranked)
        self.assertNotIn("最佳策略是什么", ranked)
        self.assertNotIn("如何抓住基本面的核心", ranked)

    def test_generate_readme_md_writes_standalone_skill_index(self) -> None:
        metrics = {"doc_count": 14, "processed_pages": 53, "ocr_pages": 1, "low_text_pages": 0}
        concepts = [{"name": "赔率-胜率-仓位"}, {"name": "确定性与估值锚"}]
        frameworks = [{"name": "赔率-胜率-仓位"}, {"name": "确定性与估值锚"}]

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            distill.generate_readme_md(output_dir, "思想钢印", "sixiang-gangyin-v2-partial-check", metrics, concepts, frameworks)
            text = (output_dir / "README.md").read_text(encoding="utf-8")

        self.assertIn("# 思想钢印 Knowledge Framework", text)
        self.assertIn("SKILL.md", text)
        self.assertIn("references/research/02-topic-clusters.md", text)
        self.assertIn("artifacts/corpus.jsonl", text)
        self.assertIn("validate_generated_skill.py", text)
        self.assertIn("current facts", text)


if __name__ == "__main__":
    unittest.main()
