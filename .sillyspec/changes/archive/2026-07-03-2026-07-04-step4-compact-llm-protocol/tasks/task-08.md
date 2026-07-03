---
id: task-08
title: 运行测试套件和 2026-07-03 dry-run 验收
author: lmr
created_at: 2026-07-04 00:38:17
priority: P0
depends_on: [task-07]
blocks: []
requirement_ids: [FR-01, FR-02, FR-03, FR-04, FR-05, FR-06]
decision_ids: [D-001@v1, D-002@v1, D-003@v1, D-004@v1]
allowed_paths: [step4.py, llm_client.py, llm.yaml, tests/test_step4.py, tests/test_llm_client.py, news_archive.py, monthly_report.py]
---
## goal
Run full test suite and 2026-07-03 dry-run after all tasks land.
## implementation
Execute pytest and step4 dry-run — no source changes.
## acceptance
All tests pass. Dry-run completes without empty LLM response.
Non-keyword-fallback signals appear in dry-run log.
Archive/monthly files unmodified.
## verify
python3 -m pytest tests/ -v
python3 step4.py --date 2026-07-03 --dry-run
## constraints
No source modifications. Failures block ship. Confirm archive/monthly unchanged.
