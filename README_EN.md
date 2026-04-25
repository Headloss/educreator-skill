# EduCreator Skill Distiller

**Other Languages:**

[中文](README.md)

`educreator-skill` is an offline knowledge-framework distiller for education,
science/technology, finance, and self-media creators. It is inspired by and
rewritten from `[alchaincyf/nuwa-skill](https://github.com/alchaincyf/nuwa-skill)`,
using only local offline PDFs as the source corpus to turn creator archives into
reusable Cursor knowledge-framework skills.

Its goal is not to copy a persona, tone, or biography. It extracts a runnable
cognitive system: what problems the creator repeatedly solves, which concepts
and frameworks they use, which variables they inspect before judging, what
decision heuristics follow, and where those frameworks fail.

### Files

- `SKILL.md`: operating protocol for using this distiller skill.
- `scripts/distill_educreator.py`: extracts PDF text, cleans corpus noise,
builds topic clusters, concept cards, framework cards, and the generated skill.
- `scripts/validate_generated_skill.py`: validates required generated skill
files and core runtime rules.
- `references/extraction-framework.md`: extraction criteria for concepts,
claims, and framework cards.
- `references/skill-template.md`: generated skill structure.

### Output Structure

Run output should be a standalone skill directory:

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

### Run From PDFs

```bash
python scripts/distill_educreator.py \
  --pdf-root "<pdf-root>" \
  --output-dir "<generated-skill-dir>" \
  --creator-name "<creator-name>" \
  --case-name "<case-name>" \
  --ocr-mode auto \
  --focus-concepts "<comma-separated concepts>"
```

Useful partial-run flags:

- `--sample-limit N`: only process the first `N` PDFs after sorted discovery.
- `--max-pages-per-pdf N`: only read the first `N` pages per PDF.
- `--ocr-mode off`: skip OCR for faster text-layer-only checks.

### Replay From Existing Corpus

Use this when you want to retest synthesis and cleaning without reading PDFs
again:

```bash
python scripts/distill_educreator.py \
  --corpus-jsonl "<existing-output>/artifacts/corpus.jsonl" \
  --output-dir "<new-output-dir>" \
  --creator-name "<creator-name>" \
  --case-name "<case-name>" \
  --sample-limit 20 \
  --focus-concepts "<comma-separated concepts>"
```

Replay still applies the current text cleaning rules to loaded page records.

### Cleaning Strategy

Raw WeChat/PDF extraction often mixes article body with page numbers, author
metadata, QR-code prompts, series indexes, and platform boilerplate. The
distiller cleans these before writing `artifacts/corpus.jsonl`, extracting
claims, or building topic clusters.

Current filters target:

- Page counters such as `1/4`.
- Repeated author, source, or byline tails.
- Subscription and QR prompts such as `关注我`, `长按二维码`, and `公众号`.
- Repeated profile/footer text such as `喜欢作者`, `篇原创内容`, and
`年度十大影响力用户`.
- End-of-article discussion prompts and series index blocks.
- Topic terms that contain known boilerplate substrings or begin/end with
common function words.

After changes to cleaning rules, inspect
`references/research/02-topic-clusters.md` and the `Knowledge System` section in
generated `SKILL.md`. High-frequency footer phrases should not outrank real
topic terms.

### Validate Generated Skill

```bash
python scripts/validate_generated_skill.py \
  --output-dir "<generated-skill-dir>" \
  --focus-concepts "<comma-separated concepts>"
```

The validator checks required files, standalone output, focus concept presence,
framework card depth, runtime current-fact protocol, and absence of noisy
visible evidence boilerplate.