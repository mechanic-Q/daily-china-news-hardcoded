---
id: task-02
author: lmr
created_at: 2026-07-02 14:35:30
priority: P0
depends_on: []
blocks: []
requirement_ids: [FR-04]
decision_ids: [D-004@v1]
allowed_paths: [tests/manual/test_15c_step1_timing.py]
status: pending
---

## Goal

Create `tests/manual/test_15c_step1_timing.py` to measure per-source elapsed wall-clock time of `step1_3.py --dry-run`, providing a repeatable timing baseline to compare 15A (sync) vs 15C (async) performance.

## Implementation

- Script runs `python3 step1_3.py --date 2026-06-30 --dry-run` via `subprocess`, capturing stdout/stderr and measuring total wall-clock time.
- Parses the per-source summary lines (passed/eliminated/total) from dry-run output to extract per-source timing via `time` module wrapping or log-timestamp heuristics.
- Outputs a formatted table: source name | elapsed seconds | article count, plus a grand-total row.
- Exits with code 0 on success; prints clear error and exits 1 if `step1_3.py` not found, dry-run fails, or output cannot be parsed.

## Acceptance

- [x] Running `python3 tests/manual/test_15c_step1_timing.py` produces a per-source timing table with plausible elapsed times.
- [x] Script exits 0 and prints no unexpected stderr.
- [x] Running twice within 60 seconds on the same date yields total times within 20% (demonstrating measurement stability).

## Verify

```bash
python3 tests/manual/test_15c_step1_timing.py
```

## Constraints

- Only file allowed to create/modify: `tests/manual/test_15c_step1_timing.py`
- No production code changes (step1_3.py, requirements.txt, run_all.sh, etc.)
- Script is not added to `run_all.sh` — manual-only timing tool
