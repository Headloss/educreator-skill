---
name: educreator-skill
description: Distills education/self-media creators from local corpora into standalone knowledge-framework skills. Use for 知识框架蒸馏, 自媒体作者蒸馏, 公众号PDF蒸馏, educreator-skill, 思想框架提炼, or when turning creator archives into reusable Agent Skills.
---

# EduCreator Skill

## Core Principle

EduCreator is Nuwa for knowledge creators.

It does not copy a persona. It extracts a runnable cognitive system:
- What problems does this creator repeatedly solve?
- What named concepts and frameworks do they use?
- What variables do they inspect before judging?
- What decision heuristics fall out of those frameworks?
- Where do those frameworks fail?
- When answering current factual questions, what must be researched first?

Local corpus is the canonical source for framework extraction. Web/current search is allowed at runtime for facts that change.

## Activation

Use this skill when the user asks to:
- distill a self-media creator, newsletter author, educator, analyst, or topic archive
- build a standalone knowledge-framework skill from PDFs/articles/transcripts
- improve an existing `offline-educreator-skill` style workflow
- generate a Nuwa-like skill without persona roleplay

## Phase 0: Confirm Scope

Before implementation, confirm:
1. Creator/topic name and intended generated skill name.
2. Input corpus path and material type: PDFs, transcripts, articles, or mixed.
3. OCR mode: `auto` by default.
4. Runtime mode: local-only framework extraction, with web research allowed for current facts unless the user forbids it.
5. Focus concepts the user expects to capture. If the user provides none, infer candidates from titles, headings, quoted terms, and repeated concepts.
6. Output location. Default: `~/.cursor/skills/<case-name>-knowledge-framework/`.

If the corpus is private or the user explicitly says local-only, do not add web supplementation during distillation. Still generate runtime rules that say current facts require user-provided facts or an explicit web-search permission.

## Phase 0.5: Standalone Directory

Create the generated skill directly as a standalone skill:

```text
~/.cursor/skills/<case-name>-knowledge-framework/
├── SKILL.md
├── references/
│   └── research/
│       ├── 01-corpus-index.md
│       ├── 02-topic-clusters.md
│       ├── 03-core-claims.md
│       ├── 04-concept-cards.md
│       ├── 05-framework-cards.md
│       └── 06-boundaries-and-gaps.md
└── artifacts/
    └── corpus.jsonl
```

Never leave the generated skill dependent on `educreator-skill/runs/`, `offline-educreator-skill/runs/`, or any external working directory.

## Phase 1: Corpus Extraction

Use `scripts/distill_educreator.py`:

```bash
python scripts/distill_educreator.py \
  --pdf-root "<pdf-root>" \
  --output-dir "<generated-skill-dir>" \
  --creator-name "<creator-name>" \
  --case-name "<case-name>" \
  --ocr-mode auto \
  --focus-concepts "<comma-separated concepts>"
```

Extraction rules:
- Prefer text layer extraction.
- Use OCR when text is too short and OCR is available.
- Preserve page-level source records in `artifacts/corpus.jsonl`.
- Track coverage, low-text pages, OCR pages, title-derived concepts, and focus-concept hits.

## Phase 1.5: Corpus Checkpoint

Pause and report:
- discovered documents vs processed documents
- processed pages and low-text pages
- OCR availability/intervention
- top title-derived concepts
- missing focus concepts

If document coverage is below 80%, fix extraction before synthesis.

## Phase 2: Nuwa-Style Synthesis

Read `references/extraction-framework.md` before synthesis.

Synthesize in this order:
1. Topic map: long-running problem domains.
2. Named concepts: terms, metaphors, and title-born frameworks.
3. Core claims: repeated, falsifiable judgments.
4. Framework cards: variables, variable relationships, judgment logic, action implications, and failure boundaries.
5. Decision heuristics: concise if/then rules.
6. Anti-patterns: what the creator repeatedly warns against.
7. Runtime research protocol: what facts must be checked before applying the frameworks to current questions.

Do not collapse distinctive concepts into generic labels. For example, prefer `赔率-胜率-仓位` over `风险判断框架` when the corpus supports the former.

## Phase 2.5: Synthesis Checkpoint

Before generating the final skill, show:
- selected knowledge map
- selected named concepts
- selected framework cards
- missing or weak focus concepts
- runtime research dimensions
- boundaries and confidence

Continue only after user approval or after clearly noting any user-approved omissions.

## Phase 3: Skill Construction

Use `references/skill-template.md`.

The generated `SKILL.md` must include:
- activation rules
- answer workflow / Agentic Protocol
- knowledge system overview
- named concepts
- framework cards
- decision heuristics
- anti-patterns and boundaries
- reference index pointing to local files inside the generated skill

Normal answers should not show a default line like `证据：PDF + 页码`. Keep evidence traceability internal, and surface source details only when the user asks, when uncertainty matters, or during validation/debugging.

## Phase 4: Validation

Run `scripts/validate_generated_skill.py` on the output directory.

Validation must check:
- `SKILL.md`, `references/research/`, and `artifacts/corpus.jsonl` exist inside the generated skill.
- No dependency on another skill's `runs/` directory.
- Required focus concepts are present or explicitly marked weak.
- Framework cards include variables and judgment logic.
- Agentic Protocol requires web/current research for fact-sensitive questions.
- Normal answer rules avoid noisy evidence boilerplate.

Minimum live tests:
1. Summary test: summarize the creator's knowledge system.
2. Application test: apply a framework card to a new scenario.
3. Boundary test: answer a question outside the corpus scope.
4. Runtime facts test: for current markets/companies/events, research current facts before applying the framework.
5. Standalone test: generated skill can work from its own directory only.

## Phase 5: Refinement

After validation, optionally run two independent reviews:
- Skill optimizer: workflow clarity, failure gates, runtime usability.
- Skill creator: trigger quality, progressive disclosure, missing domain knowledge.

Apply only improvements that make the generated skill more executable. Do not add roleplay or unrelated biography unless the corpus and user goal require it.

## Boundaries

- Local corpus defines the extracted framework; it may not represent the creator's entire thinking.
- OCR can miss charts and layout-dependent meaning.
- Web search at runtime updates facts, not the historical corpus.
- Framework frequency is not truth. Always preserve boundaries and counter-scenarios.
