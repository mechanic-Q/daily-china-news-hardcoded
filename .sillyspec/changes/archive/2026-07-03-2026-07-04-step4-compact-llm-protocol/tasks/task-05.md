---
id: task-05
title: 切换栏目评分 batch/单条 fallback 到矩阵协议
author: lmr
created_at: 2026-07-04 00:38:17
priority: P0
depends_on:
  - task-02
blocks:
  - task-07
requirement_ids:
  - FR-02
  - FR-03
decision_ids:
  - D-001@v1
  - D-003@v1
allowed_paths:
  - step4.py
  - tests/test_step4.py
---

## goal

Use matrix protocol for score_signals_batch() and score_signals(), restoring old signals dict structure consumed by aggregate_scores() and assign_category().

## implementation

score_signals_batch(): collate articles → compact prompt with matrix instructions → _parse_score_matrix() → signals per article. score_signals() single-article fallback also uses one-row matrix prompt + _parse_score_matrix() instead of JSON prompt. On parse failure fall back to keyword-based scoring (unchanged _score_by_keywords()). Update score_source to reflect matrix vs fallback origin. Add unit tests for batch round-trip and fallback triggering.

## acceptance

Matrix parser rejects malformed output (wrong row count, duplicate index, !=9 columns, values outside 0-10). Parser output matches old signals dict structure. Dry-run produces non-null signals and non-keyword-fallback score_source for non-high-confidence-keyword candidates.

## verify

python3 -m pytest tests/test_step4.py -k score -v

## constraints

Do not change aggregate_scores(), assign_category(), priority_score(), or archive/monthly structures. Malformed matrix input falls back to keyword scoring.
