#!/usr/bin/env python3
"""Golden regression: compare fetch_and_extract output against archived body."""

import argparse
import difflib
import json
import sys

from step6 import fetch_and_extract


def load_records(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main():
    p = argparse.ArgumentParser(description="Phase 15B body extraction golden regression")
    p.add_argument("--file", default="tests/fixtures/body_golden.jsonl",
                   help="path to golden JSONL file")
    args = p.parse_args()

    records = load_records(args.file)
    total = len(records)
    if total == 0:
        print("No records loaded")
        sys.exit(0)

    ratios = []
    details = []  # (idx, source, url, old_body, new_body_or_None, failure_reason_or_None)

    for i, rec in enumerate(records, 1):
        source = rec.get("source", "?")
        title = rec["title"]
        url = rec["url"]
        old_body = rec["old_body"]

        body, err = fetch_and_extract(url, title)

        if body is None:
            ratio_val = 0.0
            ratios.append(ratio_val)
            details.append((i, source, url, old_body, None, err or "extraction returned None"))
            status = "\u274c FAIL"
        else:
            ratio_val = difflib.SequenceMatcher(None, old_body, body).ratio()
            ratios.append(ratio_val)
            if ratio_val < 0.85:
                details.append((i, source, url, old_body, body, None))
            status = "\u2705 PASS" if ratio_val >= 0.85 else "\u26a0\ufe0f  LOW"

        print(f"[{i}/{total}] [{source}] ratio={ratio_val:.4f} {status}")

    passed = sum(1 for r in ratios if r >= 0.85)
    avg = sum(ratios) / len(ratios) if ratios else 0.0
    print()
    print(f"Summary: {passed}/{total} passed, avg ratio={avg:.4f}")

    if details:
        print()
        for idx, source, url, old_body, new_body, failure_reason in details:
            header = f"[{idx}/{total}] {source} \u2014 {url}"
            print(header)
            print("-" * len(header))
            if failure_reason:
                print(f"Failure: {failure_reason}")
            else:
                diff = difflib.unified_diff(
                    old_body.splitlines(),
                    new_body.splitlines(),
                    fromfile="old_body",
                    tofile="new_body",
                    lineterm="",
                    n=3,
                )
                for dline in diff:
                    print(dline)
            print()

    sys.exit(0)


if __name__ == "__main__":
    main()
