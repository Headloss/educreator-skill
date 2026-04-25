#!/usr/bin/env python
"""Validate a generated EduCreator knowledge-framework skill."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import List, Sequence, Tuple


REQUIRED_RESEARCH_FILES = [
    "01-corpus-index.md",
    "02-topic-clusters.md",
    "03-core-claims.md",
    "04-concept-cards.md",
    "05-framework-cards.md",
    "06-boundaries-and-gaps.md",
]


def normalize_key(text: str) -> str:
    text = re.sub(r"[和与]", "", text)
    return re.sub(r"[\s,，。；;：:、_\\/\-—\"'“”‘’《》<>（）()]+", "", text).lower()


def parse_focus_concepts(raw: str) -> List[str]:
    if not raw.strip():
        return []
    return [p.strip() for p in re.split(r"[,，;；|]", raw) if p.strip()]


def check(condition: bool, name: str, detail: str, results: List[Tuple[bool, str, str]]) -> None:
    results.append((condition, name, detail))


def contains_focus(text: str, concept: str) -> bool:
    norm_text = normalize_key(text)
    norm_concept = normalize_key(concept)
    return norm_concept in norm_text


def validate(output_dir: Path, focus_concepts: Sequence[str]) -> Tuple[bool, List[Tuple[bool, str, str]]]:
    results: List[Tuple[bool, str, str]] = []
    skill_md = output_dir / "SKILL.md"
    research_dir = output_dir / "references" / "research"
    corpus_jsonl = output_dir / "artifacts" / "corpus.jsonl"

    check(skill_md.exists(), "skill-md", "SKILL.md exists", results)
    check(research_dir.exists(), "research-dir", "references/research exists", results)
    check(corpus_jsonl.exists(), "corpus-jsonl", "artifacts/corpus.jsonl exists", results)

    text = skill_md.read_text(encoding="utf-8") if skill_md.exists() else ""
    concept_text = ""
    framework_text = ""
    if (research_dir / "04-concept-cards.md").exists():
        concept_text = (research_dir / "04-concept-cards.md").read_text(encoding="utf-8")
    if (research_dir / "05-framework-cards.md").exists():
        framework_text = (research_dir / "05-framework-cards.md").read_text(encoding="utf-8")

    for filename in REQUIRED_RESEARCH_FILES:
        check((research_dir / filename).exists(), f"research-{filename}", f"{filename} exists", results)

    forbidden_patterns = [
        "educreator-skill/runs",
        "educreator-skill\\runs",
        "offline-educreator-skill/runs",
        "offline-educreator-skill\\runs",
    ]
    check(
        not any(pattern in text for pattern in forbidden_patterns),
        "standalone",
        "No external distiller runs directory reference",
        results,
    )

    check(
        "Runtime Research For Current Facts" in text and "web/current search" in text,
        "runtime-protocol",
        "Agentic Protocol requires current-fact research",
        results,
    )
    check(
        "Do not display source-file details by default" in text,
        "no-noisy-evidence",
        "Normal answers avoid noisy source boilerplate",
        results,
    )
    check(
        "证据：PDF + 页码" not in text,
        "forbidden-evidence-line",
        "Forbidden visible evidence line is absent",
        results,
    )

    combined = "\n".join([text, concept_text, framework_text])
    for concept in focus_concepts:
        check(
            contains_focus(combined, concept),
            f"focus-{concept}",
            f"Focus concept present: {concept}",
            results,
        )

    framework_count = len(re.findall(r"^## Card \d+:", framework_text, flags=re.MULTILINE))
    check(framework_count >= 3, "framework-count", f"Framework cards >= 3 (found {framework_count})", results)
    check(
        "Core variables:" in framework_text and "Variable relationship:" in framework_text and "Judgment logic:" in framework_text,
        "framework-depth",
        "Framework cards include variables, relationships, and judgment logic",
        results,
    )

    if corpus_jsonl.exists():
        rows = 0
        with corpus_jsonl.open("r", encoding="utf-8") as f:
            for line in f:
                json.loads(line)
                rows += 1
                if rows >= 1:
                    break
        check(rows > 0, "corpus-readable", "corpus.jsonl is valid JSONL", results)

    ok = all(success for success, _, _ in results)
    return ok, results


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate generated EduCreator skill")
    p.add_argument("--output-dir", required=True, help="Generated skill directory")
    p.add_argument("--focus-concepts", default="", help="Comma-separated concepts expected in output")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    ok, results = validate(Path(args.output_dir).expanduser().resolve(), parse_focus_concepts(args.focus_concepts))
    for success, name, detail in results:
        status = "PASS" if success else "FAIL"
        print(f"[{status}] {name}: {detail}")
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
