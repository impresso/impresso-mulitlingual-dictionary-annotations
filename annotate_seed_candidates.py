#!/usr/bin/env python3
"""Terminal annotator for 1-to-1 pivot seed candidates."""

from __future__ import annotations

import argparse
import json
import random
import sys
import termios
import tty
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_CANDIDATES = "pivot_seed_candidates_1to1_clustered_500x4.jsonl"
DEFAULT_OUTPUT = "annotations/seed_annotations.json"
DEFAULT_SEED = 13


"""

python annotate_seed_candidates.py

"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Annotate seed candidates with single-key t/f/s controls."
    )
    parser.add_argument(
        "--candidates",
        default=DEFAULT_CANDIDATES,
        help=f"Candidate JSONL path. Default: {DEFAULT_CANDIDATES}",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Random seed for sampling unannotated rows. Default: {DEFAULT_SEED}",
    )
    parser.add_argument(
        "--output-json",
        default=DEFAULT_OUTPUT,
        help=f"Shared annotation JSON output. Default: {DEFAULT_OUTPUT}",
    )
    return parser.parse_args()


def resolve_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.exists():
        return path
    script_relative = Path(__file__).resolve().parent / raw_path
    if script_relative.exists():
        return script_relative
    return path


def candidate_key(row: dict[str, Any]) -> str:
    return "\t".join(
        [
            str(row["source_lang"]),
            str(row["target_lang"]),
            str(row["source_word"]),
            str(row["target_word"]),
        ]
    )


def load_candidates(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            for key in ("pair", "source_lang", "target_lang", "source_word", "target_word"):
                if key not in row:
                    raise ValueError(f"Missing {key!r} in {path}:{line_no}")
            rows.append(row)
    return rows


def empty_annotation_file(candidates_path: Path) -> dict[str, Any]:
    now = datetime.now().isoformat(timespec="seconds")
    return {
        "candidate_file": str(candidates_path),
        "created_at": now,
        "updated_at": now,
        "annotations": [],
    }


def load_annotation_file(path: Path, candidates_path: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_annotation_file(candidates_path)

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or not isinstance(data.get("annotations"), list):
        raise ValueError(f"Unexpected annotation file format: {path}")
    return data


def annotated_keys(data: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for row in data.get("annotations", []):
        try:
            keys.add(candidate_key(row))
        except KeyError:
            continue
    return keys


def annotated_counts_by_pair(data: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    seen: set[str] = set()
    for row in data.get("annotations", []):
        try:
            key = candidate_key(row)
            pair = str(row["pair"])
        except KeyError:
            continue
        if key in seen:
            continue
        seen.add(key)
        counts[pair] = counts.get(pair, 0) + 1
    return counts


def candidate_counts_by_pair(candidates: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in candidates:
        pair = str(row["pair"])
        counts[pair] = counts.get(pair, 0) + 1
    return counts


def unannotated_counts_by_pair(candidates: list[dict[str, Any]], done: set[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in candidates:
        if candidate_key(row) in done:
            continue
        pair = str(row["pair"])
        counts[pair] = counts.get(pair, 0) + 1
    return counts


def print_current_counts(
    pairs: list[str],
    candidate_counts: dict[str, int],
    existing_counts: dict[str, int],
    unannotated_counts: dict[str, int],
) -> None:
    print()
    print("Current shared annotation counts:")
    for pair in pairs:
        print(
            f"  {pair}: annotated={existing_counts.get(pair, 0)}, "
            f"remaining={unannotated_counts.get(pair, 0)}, "
            f"candidate_total={candidate_counts.get(pair, 0)}"
        )
    print()


def ask_new_counts(
    pairs: list[str],
    existing_counts: dict[str, int],
    unannotated_counts: dict[str, int],
) -> dict[str, int]:
    requested: dict[str, int] = {}
    for pair in pairs:
        remaining = unannotated_counts.get(pair, 0)
        if remaining <= 0:
            print(f"{pair}: no unannotated candidates left; skipping.")
            continue

        while True:
            raw = input(
                f"How many NEW annotations for {pair}? "
                f"(current total: {existing_counts.get(pair, 0)}, "
                f"remaining: {remaining}; enter 0 if you do not know/want to annotate this language): "
            ).strip()
            try:
                value = int(raw)
            except ValueError:
                print("Please enter a non-negative integer.")
                continue
            if value < 0:
                print("Please enter 0 or a positive integer.")
                continue
            if value == 0:
                requested[pair] = 0
                break
            if value > remaining:
                print(f"Only {remaining} unannotated candidates remain for {pair}.")
                continue
            requested[pair] = value
            break

    return requested


def sample_unannotated(
    candidates: list[dict[str, Any]],
    done: set[str],
    requested_new_by_pair: dict[str, int],
    seed: int,
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    by_pair: dict[str, list[dict[str, Any]]] = {}
    for row in candidates:
        if candidate_key(row) in done:
            continue
        by_pair.setdefault(str(row["pair"]), []).append(row)

    selected: list[dict[str, Any]] = []
    reserves_by_pair: dict[str, list[dict[str, Any]]] = {}
    for pair, rows in sorted(by_pair.items()):
        needed = requested_new_by_pair.get(pair, 0)
        if needed == 0:
            reserves_by_pair[pair] = []
            continue
        rng = random.Random(f"{seed}:{pair}:{len(done)}")
        rows = list(rows)
        rng.shuffle(rows)
        selected.extend(rows[:needed])
        reserves_by_pair[pair] = rows[needed:]

    return selected, reserves_by_pair


def write_annotations(path: Path, data: dict[str, Any]) -> None:
    data["updated_at"] = datetime.now().isoformat(timespec="seconds")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    tmp_path.replace(path)


def remove_annotation_for_candidate(data: dict[str, Any], candidate: dict[str, Any]) -> None:
    key = candidate_key(candidate)
    annotations = data.get("annotations", [])
    for idx in range(len(annotations) - 1, -1, -1):
        if candidate_key(annotations[idx]) == key:
            del annotations[idx]
            return


def get_single_key() -> str:
    if not sys.stdin.isatty():
        return input().strip().lower()[:1]

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        return sys.stdin.read(1).lower()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def clear_screen() -> None:
    print("\033[2J\033[H", end="")


def print_table(
    row: dict[str, Any],
    index: int,
    total: int,
    output_path: Path,
    message: str = "",
) -> None:
    pair = str(row["pair"])
    left_label = f"{row['source_lang']} word"
    right_label = f"{row['target_lang']} word"
    left = str(row["source_word"])
    right = str(row["target_word"])

    width_left = max(len(left_label), len(left), 12)
    width_right = max(len(right_label), len(right), 12)
    border = f"+{'-' * (width_left + 2)}+{'-' * (width_right + 2)}+"

    clear_screen()
    print(f"Annotation {index}/{total}    pair: {pair}")
    print(f"Saving to: {output_path}")
    print()
    print(border)
    print(f"| {left_label:<{width_left}} | {right_label:<{width_right}} |")
    print(border)
    print(f"| {left:<{width_left}} | {right:<{width_right}} |")
    print(border)
    print()
    print("Press:  t = true    f = false    s = skip    b = back    q = quit")
    if message:
        print()
        print(message)


def print_instructions() -> None:
    clear_screen()
    print("Seed Pair Annotation")
    print()
    print("Judge whether the target word is a valid translation of the source word.")
    print()
    print("Keys:")
    print("  t  mark as true/correct")
    print("  f  mark as false/incorrect")
    print("  s  skip if you do not know the word or are very unsure")
    print("  b  go back to the previous pair and change your answer")
    print("  q  quit; progress is saved")
    print()
    print("Please judge the meaning, not surface details:")
    print("  - ignore capitalization")
    print("  - ignore OCR/spelling errors in either word if the intended word is clear")
    print("  - ignore singular/plural differences if the meaning is otherwise correct")
    print("  - mark false if a word is in the wrong language")
    print("  - mark false if the source word has multiple commonly used meanings")
    print()
    print("If a word has several often-used meanings, mark it as false immediately,")
    print("even if the shown translation is correct for one of those meanings.")
    print()
    print("If you know both words and the translation is only sort of correct,")
    print("but not really correct, mark it as false.")
    print()
    print("Press any key to start.")
    get_single_key()


def annotation_row(candidate: dict[str, Any], is_valid: bool) -> dict[str, Any]:
    return {
        "pair": candidate["pair"],
        "source_lang": candidate["source_lang"],
        "target_lang": candidate["target_lang"],
        "source_word": candidate["source_word"],
        "target_word": candidate["target_word"],
        "human_is_valid": is_valid,
        "sample_id": candidate.get("sample_id"),
        "annotated_at": datetime.now().isoformat(timespec="seconds"),
    }


def main() -> int:
    args = parse_args()

    candidates_path = resolve_path(args.candidates)
    if not candidates_path.exists():
        raise FileNotFoundError(f"Candidate file not found: {candidates_path}")

    output_path = Path(args.output_json)
    if not output_path.is_absolute():
        output_path = Path(__file__).resolve().parent / output_path

    candidates = load_candidates(candidates_path)
    if not candidates:
        print("No candidates found.")
        return 0

    annotation_data = load_annotation_file(output_path, candidates_path)
    done = annotated_keys(annotation_data)
    existing_counts = annotated_counts_by_pair(annotation_data)
    candidate_counts = candidate_counts_by_pair(candidates)
    unannotated_counts = unannotated_counts_by_pair(candidates, done)
    active_pairs = sorted(candidate_counts)

    print(f"Loaded {len(candidates)} candidates.")
    print(f"{len(done)} candidates are already annotated in the shared file.")
    print_current_counts(
        pairs=active_pairs,
        candidate_counts=candidate_counts,
        existing_counts=existing_counts,
        unannotated_counts=unannotated_counts,
    )

    requested_new_by_pair = ask_new_counts(active_pairs, existing_counts, unannotated_counts)
    selected, reserves_by_pair = sample_unannotated(
        candidates, done, requested_new_by_pair, args.seed
    )

    if not selected:
        print("No new annotations requested.")
        return 0

    print(
        f"Starting {len(selected)} new annotations: "
        + ", ".join(f"{pair}={count}" for pair, count in sorted(requested_new_by_pair.items()))
    )
    print_instructions()

    total = len(selected)
    idx = 0
    skipped_count = 0
    message = ""
    while idx < total:
        candidate = selected[idx]
        while True:
            print_table(candidate, idx + 1, total, output_path, message)
            message = ""
            key = get_single_key()
            if key == "q":
                print("\nStopped. Progress saved.")
                return 0
            if key == "s":
                pair = str(candidate["pair"])
                replacements = reserves_by_pair.get(pair, [])
                if not replacements:
                    message = (
                        f"No replacement candidates left for {pair}. "
                        "Please mark this pair, go back, or quit."
                    )
                    break
                selected[idx] = replacements.pop(0)
                skipped_count += 1
                message = "Skipped. Showing a replacement candidate."
                break
            if key == "b":
                if idx == 0:
                    continue
                idx -= 1
                remove_annotation_for_candidate(annotation_data, selected[idx])
                write_annotations(output_path, annotation_data)
                break
            if key in {"t", "f"}:
                remove_annotation_for_candidate(annotation_data, candidate)
                is_valid = key == "t"
                annotation_data["annotations"].append(
                    annotation_row(candidate, is_valid)
                )
                write_annotations(output_path, annotation_data)
                idx += 1
                break

    clear_screen()
    print(f"Done. Wrote {len(annotation_data['annotations'])} total annotations to:")
    print(output_path)
    if skipped_count:
        print(f"Skipped {skipped_count} candidates during this run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
