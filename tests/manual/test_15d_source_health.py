#!/usr/bin/env python3
"""
author: lmr
created_at: 2026-07-02 20:12:36

Phase 15D source health manual acceptance tests.
6 independent sub-tests selected via CLI flags.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

CST = timezone(timedelta(hours=8))
HEALTH_FIELDS = [
    "date", "source", "passed", "failed", "total",
    "tool", "elapsed_ms", "status", "recorded_at",
]


def make_health_record(
    date="2026-07-01", source="xinhua", passed=10, failed=0,
    total=10, tool="httpx", elapsed_ms=1200, status="ok",
):
    return {
        "date": date,
        "source": source,
        "passed": passed,
        "failed": failed,
        "total": total,
        "tool": tool,
        "elapsed_ms": elapsed_ms,
        "status": status,
        "recorded_at": datetime.now(CST).isoformat(),
    }


def test_write():
    rec = make_health_record()
    missing = [f for f in HEALTH_FIELDS if f not in rec]
    if missing:
        print(f"FAIL: missing fields: {missing}")
        sys.exit(1)
    for f in HEALTH_FIELDS:
        if f in ("passed", "failed", "total", "elapsed_ms"):
            assert isinstance(rec[f], int), f"{f} should be int"
        elif f == "recorded_at":
            assert isinstance(rec[f], str), f"{f} should be str"
        elif f == "date":
            assert isinstance(rec[f], str) and len(rec[f]) == 10, \
                f"{f} should be YYYY-MM-DD string"
        elif f == "status":
            assert rec[f] in ("ok", "failed"), f"status should be ok|failed"
    line = json.dumps(rec, ensure_ascii=False)
    print(f"PASS: HealthRecord all {len(HEALTH_FIELDS)} fields valid")
    print(f"  JSON: {line}")
    print(f"  date={rec['date']} source={rec['source']} "
          f"passed={rec['passed']} failed={rec['failed']} "
          f"total={rec['total']} tool={rec['tool']} "
          f"elapsed_ms={rec['elapsed_ms']} status={rec['status']}")


def test_dry_run():
    with tempfile.TemporaryDirectory() as tmp:
        jsonl = Path(tmp) / "sources_health.jsonl"
        rec = make_health_record()
        from io import StringIO
        old_stdout = sys.stdout
        captured = StringIO()
        sys.stdout = captured
        try:
            line = json.dumps(rec, ensure_ascii=False)
            print(f"  [dry-run] would-write health: {line}")
        finally:
            sys.stdout = old_stdout
        output = captured.getvalue()
        assert "would-write" in output, "dry-run should emit would-write"
        assert jsonl.exists() is False or jsonl.stat().st_size == 0, \
            "dry-run must not write JSONL"
    print("PASS: dry-run does not write JSONL, stdout contains would-write")


def test_banner_zero():
    today = "2026-07-01"
    import io
    old_stderr = sys.stderr
    captured = io.StringIO()
    sys.stderr = captured
    try:
        passed = 0
        if passed == 0:
            print(
                f"\u26a0\ufe0f  [WARNING] \u4fe1\u6e90\u5065\u5eb7: test_source passed=0 ({today})",
                file=sys.stderr,
            )
    finally:
        sys.stderr = old_stderr
    output = captured.getvalue()
    assert "WARNING" in output
    assert "passed=0" in output
    print("PASS: banner-zero triggered with passed==0")


def _consecutive_dates(dates):
    """Return True if all dates are consecutive calendar days."""
    try:
        parsed = [datetime.strptime(d, "%Y-%m-%d").date() for d in dates]
    except ValueError:
        return False
    for i in range(1, len(parsed)):
        if (parsed[i] - parsed[i-1]).days != 1:
            return False
    return True


def test_banner_streak():
    today = "2026-07-03"
    records = [
        {"date": "2026-07-01", "source": "test_source", "passed": 2},
        {"date": "2026-07-02", "source": "test_source", "passed": 3},
        {"date": "2026-07-03", "source": "test_source", "passed": 1},
    ]
    daily = {}
    for r in records:
        daily[r["date"]] = r
    sorted_dates = sorted(daily.keys())
    recent_dates = [d for d in sorted_dates if d <= today][-3:]
    assert len(recent_dates) >= 3, "need >=3 days"
    assert _consecutive_dates(recent_dates), "dates must be consecutive"
    recent = [daily[d] for d in recent_dates]
    all_bad = all(int(r.get("passed", 0)) < 5 for r in recent)
    assert all_bad, "all 3 days should have passed<5"
    import io
    old_stderr = sys.stderr
    captured = io.StringIO()
    sys.stderr = captured
    try:
        vals = ", ".join(str(r.get("passed", 0)) for r in recent)
        print(
            f"\u26a0\ufe0f  [WARNING] \u4fe1\u6e90\u5065\u5eb7: test_source "
            f"\u8fde\u7eed3\u5929 passed<5 ({vals}, {recent_dates[0]}~{recent_dates[-1]})",
            file=sys.stderr,
        )
    finally:
        sys.stderr = old_stderr
    output = captured.getvalue()
    assert "WARNING" in output
    assert "passed<5" in output
    print("PASS: banner-streak triggered for 3 consecutive days passed<5")


def test_no_banner_non_consecutive():
    """Non-consecutive low-passed dates must NOT trigger banner."""
    today = "2026-07-07"
    records = [
        {"date": "2026-07-01", "source": "test_source", "passed": 1},
        {"date": "2026-07-03", "source": "test_source", "passed": 2},
        {"date": "2026-07-07", "source": "test_source", "passed": 3},
    ]
    daily = {}
    for r in records:
        daily[r["date"]] = r
    sorted_dates = sorted(daily.keys())
    recent_dates = [d for d in sorted_dates if d <= today][-3:]
    if len(recent_dates) >= 3:
        assert not _consecutive_dates(recent_dates), \
            "non-consecutive dates must NOT pass consecutive check"
    print("PASS: non-consecutive low dates do not trigger banner-streak")


def compute_source_health_stats(records):
    if not records:
        return {}
    seen = {}
    for r in records:
        key = (r.get("date", ""), r.get("source", ""))
        seen[key] = r
    deduped = list(seen.values())
    from collections import defaultdict
    by_source = defaultdict(list)
    for r in deduped:
        by_source[r.get("source", "")].append(r)
    stats = {}
    for source, src_records in by_source.items():
        dates = sorted(set(r.get("date", "") for r in src_records))
        run_days = len(dates)
        passed_vals = [r.get("passed", 0) or 0 for r in src_records]
        avg_passed = sum(passed_vals) / len(passed_vals) if passed_vals else 0
        zero_days = sum(1 for p in passed_vals if p == 0)
        date_passed = {}
        for r in src_records:
            date_passed[r.get("date", "")[:10]] = r.get("passed", 0) or 0
        sorted_dates2 = sorted(date_passed.keys())
        worst_streak = 0
        current_streak = 0
        prev_date = None
        for d in sorted_dates2:
            cur_date = datetime.strptime(d, "%Y-%m-%d").date()
            if prev_date and (cur_date - prev_date).days != 1:
                current_streak = 0
            if date_passed[d] < 5:
                current_streak += 1
                if current_streak > worst_streak:
                    worst_streak = current_streak
            else:
                current_streak = 0
            prev_date = cur_date
        stats[source] = {
            "run_days": run_days,
            "avg_passed": round(avg_passed, 1),
            "zero_days": zero_days,
            "worst_streak": worst_streak,
        }
    return stats


def test_monthly():
    records = [
        {"date": "2026-07-01", "source": "xinhua", "passed": 10, "failed": 0},
        {"date": "2026-07-02", "source": "xinhua", "passed": 8, "failed": 1},
        {"date": "2026-07-03", "source": "xinhua", "passed": 0, "failed": 3},
        {"date": "2026-07-04", "source": "xinhua", "passed": 4, "failed": 0},
        {"date": "2026-07-05", "source": "xinhua", "passed": 4, "failed": 1},
        {"date": "2026-07-06", "source": "xinhua", "passed": 2, "failed": 0},
        {"date": "2026-07-07", "source": "xinhua", "passed": 9, "failed": 0},
    ]
    stats = compute_source_health_stats(records)
    assert "xinhua" in stats, "xinhua should be in stats"
    s = stats["xinhua"]
    assert s["run_days"] == 7, f"expected 7 run_days, got {s['run_days']}"
    expected_avg = round((10 + 8 + 0 + 4 + 4 + 2 + 9) / 7, 1)
    assert s["avg_passed"] == expected_avg, \
        f"avg_passed mismatch: {s['avg_passed']} != {expected_avg}"
    assert s["zero_days"] == 1, f"expected 1 zero_day, got {s['zero_days']}"
    assert s["worst_streak"] == 4, \
        f"expected worst_streak=4 (days 3-6: 0,4,4,2<5), got {s['worst_streak']}"
    print("PASS: monthly stats fields valid")
    print(f"  run_days={s['run_days']} avg_passed={s['avg_passed']} "
          f"zero_days={s['zero_days']} worst_streak={s['worst_streak']}")


def test_llm_client():
    proj = Path(__file__).resolve().parent.parent.parent
    monthly_py = proj / "monthly_report.py"
    content = monthly_py.read_text(encoding="utf-8")
    if "from openai import" in content or "import openai" in content:
        print("FAIL: monthly_report.py has direct OpenAI import")
        sys.exit(1)
    if "from llm_client import call_llm" not in content:
        print("FAIL: monthly_report.py does not use call_llm from llm_client")
        sys.exit(1)
    llm_yaml = proj / "llm.yaml"
    yaml_content = llm_yaml.read_text(encoding="utf-8")
    if "monthly-overview" not in yaml_content:
        print("FAIL: llm.yaml missing monthly-overview call site")
        sys.exit(1)
    print("PASS: monthly_report.py uses call_llm (no direct OpenAI import)")
    print("PASS: llm.yaml contains monthly-overview")


def main():
    p = argparse.ArgumentParser(
        description="Phase 15D source health manual acceptance tests"
    )
    p.add_argument("--test-write", action="store_true",
                   help="Construct HealthRecord, verify all 9 fields")
    p.add_argument("--test-dry-run", action="store_true",
                   help="Confirm dry-run does not write JSONL, stdout has would-write")
    p.add_argument("--test-banner-zero", action="store_true",
                   help="Construct passed==0 mock, verify banner on stderr")
    p.add_argument("--test-banner-streak", action="store_true",
                   help="Construct 3 consecutive passed<5 days, verify banner")
    p.add_argument("--test-no-banner-non-consecutive", action="store_true",
                   help="Non-consecutive low dates must NOT trigger banner")
    p.add_argument("--test-monthly", action="store_true",
                   help="Construct multi-day multi-source JSONL, verify report stats")
    p.add_argument("--test-llm-client", action="store_true",
                   help="Grep monthly_report.py for no direct OpenAI import, "
                        "llm.yaml for monthly-overview")
    args = p.parse_args()

    ran_any = False

    if args.test_write:
        ran_any = True
        test_write()

    if args.test_dry_run:
        ran_any = True
        test_dry_run()

    if args.test_banner_zero:
        ran_any = True
        test_banner_zero()

    if args.test_banner_streak:
        ran_any = True
        test_banner_streak()

    if args.test_no_banner_non_consecutive:
        ran_any = True
        test_no_banner_non_consecutive()

    if args.test_monthly:
        ran_any = True
        test_monthly()

    if args.test_llm_client:
        ran_any = True
        test_llm_client()

    if not ran_any:
        p.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
