# EduCreator Skill Distiller

**其他语言 / Other Languages:**

[English](README_EN.md)

`educreator-skill` 是一个面向科教、财经、自媒体创作者的离线知识框架蒸馏器。
它受 `[alchaincyf/nuwa-skill](https://github.com/alchaincyf/nuwa-skill)`
启发并改写而成，只以本地离线 PDF 作为语料来源，将创作者文章归纳为可复用的
Cursor knowledge-framework skill。

它的目标不是复制人格、口吻或传记，而是抽取一套可运行的认知系统：创作者反复
解决什么问题、使用哪些概念框架、判断前检查哪些变量、形成哪些决策启发式，以及
这些框架在哪些边界下失效。

### 文件说明

- `SKILL.md`：使用该蒸馏器 skill 的操作协议。
- `scripts/distill_educreator.py`：抽取 PDF 文本、清洗语料噪音，并生成主题簇、
概念卡、框架卡和最终 skill。
- `scripts/validate_generated_skill.py`：校验生成 skill 的必需文件和核心运行规则。
- `references/extraction-framework.md`：概念、主张和框架卡的提取标准。
- `references/skill-template.md`：生成 skill 的结构模板。

### 输出结构

运行结果应当是一个独立的 skill 目录：

```text
<output-dir>/
├── SKILL.md
├── artifacts/
│   └── corpus.jsonl
└── references/
    └── research/
        ├── 01-corpus-index.md
        ├── 02-topic-clusters.md
        ├── 03-core-claims.md
        ├── 04-concept-cards.md
        ├── 05-framework-cards.md
        └── 06-boundaries-and-gaps.md
```

### 从 PDF 运行

```bash
python scripts/distill_educreator.py \
  --pdf-root "<pdf-root>" \
  --output-dir "<generated-skill-dir>" \
  --creator-name "<creator-name>" \
  --case-name "<case-name>" \
  --ocr-mode auto \
  --focus-concepts "<comma-separated concepts>"
```

常用的局部运行参数：

- `--sample-limit N`：按排序后的发现顺序，只处理前 `N` 个 PDF。
- `--max-pages-per-pdf N`：每个 PDF 只读取前 `N` 页。
- `--ocr-mode off`：关闭 OCR，仅做更快的文本层检查。

### 从已有语料重放

当你想复测综合与清洗逻辑，而不想重新读取 PDF 时，可以使用已有输出中的
`corpus.jsonl`：

```bash
python scripts/distill_educreator.py \
  --corpus-jsonl "<existing-output>/artifacts/corpus.jsonl" \
  --output-dir "<new-output-dir>" \
  --creator-name "<creator-name>" \
  --case-name "<case-name>" \
  --sample-limit 20 \
  --focus-concepts "<comma-separated concepts>"
```

重放时仍会对加载的页面记录应用当前文本清洗规则。

### 清洗策略

公众号和 PDF 抽取出的原始文本经常混有正文之外的内容，例如页码、作者元信息、
二维码提示、系列目录和平台样板文案。蒸馏器会在写入 `artifacts/corpus.jsonl`、
提取核心主张或构建主题簇之前清洗这些噪音。

当前过滤目标包括：

- `1/4` 这类页码计数。
- 作者名、来源、署名等重复尾巴。
- `关注我`、`长按二维码`、`公众号` 等订阅和二维码提示。
- `喜欢作者`、`篇原创内容`、`年度十大影响力用户` 等重复简介或页脚文本。
- 文末互动提示和系列目录块。
- 包含已知样板文案，或以常见虚词开头/结尾的主题词。

修改清洗规则后，应检查生成目录中的
`references/research/02-topic-clusters.md` 和 `SKILL.md` 的
`Knowledge System` 部分，确保高频页脚词没有压过真实主题词。

### 校验生成的 Skill

```bash
python scripts/validate_generated_skill.py \
  --output-dir "<generated-skill-dir>" \
  --focus-concepts "<comma-separated concepts>"
```

校验器会检查必需文件、独立输出结构、重点概念覆盖、框架卡深度、运行时事实更新
协议，以及是否避免了嘈杂的可见证据样板。