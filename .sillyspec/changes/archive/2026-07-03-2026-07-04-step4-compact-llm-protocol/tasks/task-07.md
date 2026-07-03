---
id: task-07
title: 增加 mock batch 端到端兼容测试
author: lmr
created_at: 2026-07-04 00:38:17
priority: P0
depends_on: [task-04, task-05, task-06]
blocks: [task-08]
requirement_ids: [FR-01, FR-02, FR-03, FR-06]
decision_ids: [D-001@v1, D-002@v1, D-003@v1]
allowed_paths:
  - tests/test_step4.py
  - news_archive.py
---

## goal

mock bitstring and matrix responses through step4 and archive compatibility.

## implementation

Add `TestBatchE2E` in `tests/test_step4.py`. Four tests: (1) `test_china_bitstring_batch` — mock `call_llm` returning `"101"`, verify china-relevance filter. (2) `test_score_matrix_batch` — mock 2-row matrix, verify `score_signals_batch` outputs dicts with `relevance/importance/timeliness`. (3) `test_e2e_signals_flow` — mock both calls, `build_classification_result` yields non-empty `signals` and non-`keyword-fallback` `score_source`. (4) `test_archive_compatibility` — feed result to `news_archive.build_record`, confirm `signals/category/priority/selected_in_top10/score_source` survive.

## acceptance

- bitstring mock proves china filter correct (FR-01)
- matrix mock proves score output consumed by existing algorithms (FR-02, FR-03)
- e2e mock proves `score_source != keyword-fallback` (FR-03)
- archive mock proves `build_record` field completeness (FR-06)

## verify

python3 -m pytest tests/test_step4.py -v

## constraints

- no production code changes in this task
- no new deps; only `unittest.mock`
- cover non-keyword-fallback `score_source`
