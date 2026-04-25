# EduCreator Extraction Framework

## 1. What To Extract

For education/self-media creators, the target is a reusable knowledge system, not a biography.

Extract four layers:
1. **Problem domains**: recurring questions the creator tries to answer.
2. **Named concepts**: terms, metaphors, diagrams, formulas, and title-born frameworks.
3. **Core claims**: repeated judgments with conditions and counterexamples.
4. **Framework cards**: operational models that can be applied to new cases.

## 2. Named Concept Detection

High-signal concept sources:
- PDF/article titles.
- Section headings and numbered lists.
- Quoted terms such as `“筹码结构”`.
- Phrases around `框架`, `模型`, `方法`, `四象限`, `三角`, `公式`, `系统`, `逻辑`.
- User-supplied focus concepts.

Title-born frameworks can pass even with low exact repetition. A creator often introduces a framework in one flagship article and reuses its variables later without repeating the exact title.

Score each concept:
- **Title signal**: appears in a title or heading.
- **Corpus signal**: appears in multiple documents or pages.
- **Variable signal**: has associated variables, axes, steps, or tradeoffs.
- **Generative signal**: helps answer new questions.
- **Distinctiveness**: not a generic topic label.

Promote concepts with strong title signal plus variable/generative signal, even if corpus frequency is modest.

## 3. Core Claim Screening

Score candidate claims from 1-5 on:
- Repetition across documents.
- Coverage across topic clusters.
- Actionability.
- Falsifiability and boundary clarity.
- Relationship to named concepts.

Do not rely only on exact repeated sentences. Merge paraphrases that express the same claim.

## 4. Framework Card Requirements

Each framework card must include:
- **Problem type**: when to use it.
- **Core variables**: the dimensions the creator watches.
- **Variable relationships**: how variables trade off or update each other.
- **Judgment logic**: 3-5 steps for applying the framework.
- **Action implications**: what changes in the user's decision.
- **Failure boundary**: conditions where the framework misleads.
- **Internal references**: local source pointers kept for traceability.

Reject generic cards that only say:
- define object and time window
- identify variables
- give base case and alternatives

Those are scaffolds, not distilled frameworks.

## 5. Runtime Research Protocol

Generated skills must separate:
- **Framework facts**: extracted from the local corpus.
- **Current facts**: gathered at answer time with web/current search when allowed.

For fact-sensitive questions, derive research dimensions from the framework cards. Example for an investment creator:
- current business facts
- expectation gap
- price/volume or chip structure
- valuation and odds
- catalyst path
- counter-scenario

## 6. Validation Gates

A generated skill fails validation if:
- It depends on another skill's `runs/` directory.
- It lacks an Agentic Protocol for current facts.
- Focus concepts are absent without being marked weak.
- Framework cards lack variables or judgment logic.
- The output only contains generic topic labels.
- Normal answer instructions force noisy evidence boilerplate.
