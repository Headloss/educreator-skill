# EduCreator Generated Skill Template

Use this structure when generating a knowledge-framework skill.

```markdown
---
name: [case-name]-knowledge-framework
description: |
  [Creator/topic] knowledge-framework skill distilled from a local corpus.
  Use for [trigger terms], framework application, strategy judgment, and decision review.
---

# [Creator/topic] · Knowledge Framework Skill

## Activation

Use this skill when the user asks to:
- summarize [creator/topic]'s knowledge system
- apply [creator/topic]'s frameworks to a decision
- analyze a market/company/event through [creator/topic]'s lens
- review whether a judgment followed the framework

## Answer Workflow

### Step 1: Classify The Question

| Type | Signal | Action |
|---|---|---|
| Framework summary | asks for体系/框架/观点 | use local distilled models |
| Application | asks how to judge or decide | select 1-2 framework cards |
| Current factual analysis | mentions current company/market/event/news | research current facts first |
| Boundary case | outside corpus or unsupported domain | state uncertainty and limits |

### Step 2: Runtime Research For Current Facts

When the question depends on current facts, use web/current search before judging.

Research dimensions derived from this creator's frameworks:
[research-dimensions]

### Step 3: Apply The Framework

Answer with:
1. conclusion first
2. selected framework and why
3. stepwise reasoning
4. action implication or decision options
5. boundary, counter-scenario, confidence

Do not display source-file details by default. Surface them only if the user asks for evidence, uncertainty depends on a source, or the answer is a validation/debugging task.

## Knowledge System

[topic-map]

## Named Concepts

[concept-cards]

## Framework Cards

[framework-cards]

## Decision Heuristics

[heuristics]

## Anti-Patterns

[anti-patterns]

## Boundaries And Confidence

[boundaries]

## Local Reference Index

This skill is standalone. Supporting files live inside this skill directory:
- `references/research/01-corpus-index.md`
- `references/research/02-topic-clusters.md`
- `references/research/03-core-claims.md`
- `references/research/04-concept-cards.md`
- `references/research/05-framework-cards.md`
- `references/research/06-boundaries-and-gaps.md`
- `artifacts/corpus.jsonl`
```
