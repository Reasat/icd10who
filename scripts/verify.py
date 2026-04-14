#!/usr/bin/env python3
"""Structural checks on produced LinkML YAML for ICD10WHO."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

import yaml


def load_doc(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify ICD10WHO LinkML YAML structure")
    parser.add_argument("--yaml", type=Path, required=True, help="Path to produced YAML")
    parser.add_argument(
        "--expected-version",
        type=str,
        default=None,
        help="If set, document version must match this string",
    )
    args = parser.parse_args()

    if not args.yaml.exists():
        print(f"FAIL: file not found: {args.yaml}", file=sys.stderr)
        return 1

    doc = load_doc(args.yaml)
    title = doc.get("title")
    version = doc.get("version")
    terms = doc.get("terms") or []

    errors: list[str] = []
    if not title or not str(title).strip():
        errors.append("missing or empty title")
    if not version or not str(version).strip():
        errors.append("missing or empty version")
    if args.expected_version is not None and str(version) != args.expected_version:
        errors.append(
            f"version mismatch: expected {args.expected_version!r}, got {version!r}"
        )

    ids = [t.get("id") for t in terms]
    id_counts = Counter(ids)
    dupes = [i for i, c in id_counts.items() if c > 1 and i is not None]
    if dupes:
        errors.append(f"duplicate term IDs (sample): {dupes[:10]}")

    known = {i for i in ids if i}
    broken_parents: list[tuple[str, str]] = []
    missing_labels: list[str] = []

    for t in terms:
        tid = t.get("id")
        if tid is None or not str(tid).strip():
            errors.append("term with missing id")
            continue
        lab = t.get("label")
        if lab is None or not str(lab).strip():
            missing_labels.append(str(tid))
        for p in t.get("parents") or []:
            if p not in known:
                broken_parents.append((str(tid), str(p)))

    if missing_labels:
        errors.append(f"terms missing non-empty label (sample): {missing_labels[:10]}")
    if broken_parents:
        errors.append(
            f"broken parent refs (first 10): {broken_parents[:10]} (total {len(broken_parents)})"
        )

    term_count = len(terms)
    unique_ids = len(known)

    if errors:
        print("FAIL", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        n_broken = len(broken_parents)
        print(
            f"Summary: terms={term_count}, unique_ids={unique_ids}, "
            f"broken_parent_refs={n_broken}",
            file=sys.stderr,
        )
        return 1

    print(
        f"PASS: terms={term_count}, unique_ids={unique_ids}, broken_parent_refs=0",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
