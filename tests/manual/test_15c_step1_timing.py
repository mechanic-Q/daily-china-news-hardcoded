#!/usr/bin/env python3
"""Baseline timing: measure per-source wall-clock for step1_3.py --dry-run."""

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path


SOURCE_ORDER = [
    "新华社", "参考消息", "央视新闻", "央视军事",
    "中科院", "中核集团", "人民日报",
]

BASELINE_FILE = Path(__file__).resolve().parent / ".timing-baseline.json"


def parse_step1_3_output(stdout: str) -> list[dict]:
    """Parse per-source article counts and elapsed times from step1_3.py dry-run output."""
    results = []

    for line in stdout.splitlines():
        # [1/7] 新华社... → 12条 (3.2s)
        m = re.match(
            r'^\[\d+/7\]\s*(.+?)\.\.\.\s*→\s*(\d+)条\s*(?:\((\d+\.?\d*)s\))?',
            line
        )
        if m:
            current_name = m.group(1).strip()
            found = int(m.group(2))
            elapsed_s = float(m.group(3)) if m.group(3) else 0.0
            results.append({
                "name": current_name, "found": found,
                "passed": 0, "failed": 0, "elapsed_s": elapsed_s,
            })
            continue

        # ✅12 / ❌3
        m = re.match(r'\s*✅(\d+)\s*/\s*❌(\d+)', line)
        if m and results:
            results[-1]["passed"] = int(m.group(1))
            results[-1]["failed"] = int(m.group(2))

    return results


def load_baseline() -> dict | None:
    if BASELINE_FILE.exists():
        try:
            return json.loads(BASELINE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return None
    return None


def save_baseline(sources: list[dict], total_elapsed: float, date: str):
    data = {
        "date": date,
        "total_seconds": total_elapsed,
        "sources": sources,
    }
    BASELINE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"baseline_saved: {BASELINE_FILE}")


def format_table(sources: list[dict]):
    lines = []
    lines.append(f"{'Source':<12} {'Found':>6} {'Passed':>6} {'Failed':>6} {'Elapsed':>8}")
    lines.append("-" * 40)
    for s in sources:
        lines.append(
            f"{s['name']:<12} {s['found']:>6} {s['passed']:>6} "
            f"{s['failed']:>6} {s.get('elapsed_s', 0):>7.1f}s"
        )
    lines.append("-" * 40)
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description="Phase 15C step1_3 baseline timing")
    p.add_argument("--date", default="2026-06-30", help="collection date (YYYY-MM-DD)")
    p.add_argument("--script", default="step1_3.py", help="path to step1_3.py")
    p.add_argument("--compare", action="store_true", help="compare against saved baseline")
    p.add_argument("--save", action="store_true", help="save results as new baseline")
    args = p.parse_args()

    script = args.script
    date = args.date

    print(f"Baseline timing: {script} --date {date} --dry-run\n")

    t0 = time.time()
    result = subprocess.run(
        [sys.executable, script, "--date", date, "--dry-run"],
        capture_output=True, text=True, timeout=600,
    )
    wall_elapsed = time.time() - t0

    if result.returncode != 0:
        print(f"ERROR: step1_3.py exited with code {result.returncode}")
        print(result.stderr[:2000])
        sys.exit(1)

    stdout = result.stdout
    stderr = result.stderr

    sources = parse_step1_3_output(stdout)
    total_articles = sum(s["found"] for s in sources)
    total_elapsed = sum(s.get("elapsed_s", 0) for s in sources)

    print(format_table(sources))
    print(f"{'TOTAL':<12} {total_articles:>6} {'':>6} {'':>6} {total_elapsed:>7.1f}s")
    print()

    print(f"baseline_name: step1_3 --date {date} --dry-run")
    print(f"total_seconds: {wall_elapsed:.2f}")
    print(f"exit_code: {result.returncode}")
    print()

    if args.compare:
        prev = load_baseline()
        if prev:
            delta = wall_elapsed - prev["total_seconds"]
            pct = (delta / prev["total_seconds"]) * 100 if prev["total_seconds"] > 0 else 0
            print(f"vs baseline ({prev.get('date', '?')}): Δ={delta:+.2f}s ({pct:+.1f}%)")
            if pct <= -40:
                print("PERFORMANCE GOAL: >=40% improvement — MET")
            elif delta < 0:
                print(f"PERFORMANCE GOAL: improvement of {abs(pct):.1f}%, <40% target")
            else:
                print(f"PERFORMANCE GOAL: {abs(pct):.1f}% regression from baseline")
        else:
            print("No saved baseline for comparison. Use --save to create one.")
    elif args.save:
        save_baseline(sources, wall_elapsed, date)
    else:
        print("Tip: use --save to record baseline, --compare to check against saved baseline.")

    if stderr:
        print(f"stderr ({len(stderr)} chars):")
        print(stderr[:1000])

    sys.exit(0)


if __name__ == "__main__":
    main()
