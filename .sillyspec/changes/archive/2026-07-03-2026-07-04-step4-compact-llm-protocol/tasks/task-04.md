---
id: task-04
title: 切换涉华 batch 到位串协议并保留 fallback
author: lmr
created_at: 2026-07-04 00:38:17
priority: P0
depends_on:
  - task-01
blocks:
  - task-07
requirement_ids:
  - FR-01
decision_ids:
  - D-001@v1
  - D-002@v1
allowed_paths:
  - step4.py
  - tests/test_step4.py
---
## goal
replace china batch JSON prompt/parser with bitstring protocol while preserving fallback
## implementation
1. modify `llm_is_china_related_batch()` prompt to require bitstring output
2. parse with `_parse_china_bitstring()`; success returns `list[bool]`
3. parse failure falls back to per-item loop, logs `china-bitstring-fallback`
4. unit tests for parse path, fallback trigger, score_source marking
## acceptance
- AC-01: valid bitstring maps correctly to per-item results
- AC-02: invalid bitstring triggers per-item fallback with log marker
- AC-03: aggregate_scores / assign_category input unchanged
## verify
python3 -m pytest tests/test_step4.py -k china -v
## constraints
- no algorithm/category/archive changes
- invalid bitstring triggers existing fallback path, never crashes pipeline
