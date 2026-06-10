#!/usr/bin/env python3
"""Compare two seed annotation JSON files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

"""

python compare_annotation_jsons.py seed_annotations.json seed_annotation_gpt_gpt-5.4-mini.json

"""


ANNOTATIONS_DIR = "annotations"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare matched word-pair decisions between two annotation JSON files."
    )
    parser.add_argument(
        "human_json",
        help="Human annotation JSON path, or filename inside annotations/.",
    )
    parser.add_argument(
        "gpt_json",
        help="GPT annotation JSON path, or filename inside annotations/.",
    )
    return parser.parse_args()


def resolve_annotation_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.exists():
        return path

    script_dir = Path(__file__).resolve().parent
    annotations_path = script_dir / ANNOTATIONS_DIR / raw_path
    if annotations_path.exists():
        return annotations_path

    script_relative = script_dir / raw_path
    if script_relative.exists():
        return script_relative

    return path


def annotation_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(row["source_lang"]),
        str(row["target_lang"]),
        str(row["source_word"]),
        str(row["target_word"]),
    )


def load_annotations(path: Path) -> tuple[dict[tuple[str, str, str, str], bool], int]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    annotations = data.get("annotations")
    if not isinstance(annotations, list):
        raise ValueError(f"Unexpected annotation file format: {path}")

    rows: dict[tuple[str, str, str, str], bool] = {}
    duplicates = 0
    for row in annotations:
        if not isinstance(row, dict):
            continue
        key = annotation_key(row)
        decision = row.get("human_is_valid")
        if not isinstance(decision, bool):
            continue
        if key in rows:
            duplicates += 1
        rows[key] = decision
    return rows, duplicates


def pct(part: int, total: int) -> str:
    if total == 0:
        return "n/a"
    return f"{part / total * 100:.2f}%"


def main() -> int:
    args = parse_args()
    human_path = resolve_annotation_path(args.human_json)
    gpt_path = resolve_annotation_path(args.gpt_json)
    if not human_path.exists():
        raise FileNotFoundError(f"Human annotation JSON not found: {human_path}")
    if not gpt_path.exists():
        raise FileNotFoundError(f"GPT annotation JSON not found: {gpt_path}")

    human, human_duplicates = load_annotations(human_path)
    gpt, gpt_duplicates = load_annotations(gpt_path)

    human_keys = set(human)
    gpt_keys = set(gpt)
    matched_keys = human_keys & gpt_keys
    human_only = human_keys - gpt_keys
    gpt_only = gpt_keys - human_keys

    agree = sum(1 for key in matched_keys if human[key] == gpt[key])
    disagree = len(matched_keys) - agree
    all_words_match = not human_only and not gpt_only

    print(f"Human file: {human_path}")
    print(f"GPT file:   {gpt_path}")
    print()
    print(f"Human annotations: {len(human)}")
    print(f"GPT annotations:   {len(gpt)}")
    print(f"Matched word pairs: {len(matched_keys)}")
    print(f"Human-only word pairs: {len(human_only)}")
    print(f"GPT-only word pairs:   {len(gpt_only)}")
    print(f"All word pairs match: {'yes' if all_words_match else 'no'}")
    if human_duplicates or gpt_duplicates:
        print(f"Duplicate rows ignored: human={human_duplicates}, gpt={gpt_duplicates}")
    print()
    print(f"Agreements on matched pairs: {agree}/{len(matched_keys)} ({pct(agree, len(matched_keys))})")
    print(
        f"Disagreements on matched pairs: "
        f"{disagree}/{len(matched_keys)} ({pct(disagree, len(matched_keys))})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
