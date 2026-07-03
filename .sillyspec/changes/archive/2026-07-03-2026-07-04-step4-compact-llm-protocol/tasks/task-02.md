---
id: task-02
title: 新增栏目评分矩阵 parser 与单元测试
author: lmr
created_at: 2026-07-04 00:38:17
priority: P0
depends_on: []
blocks:
  - task-05
requirement_ids:
  - FR-02
  - FR-03
decision_ids:
  - D-003@v1
allowed_paths:
  - step4.py
  - tests/test_step4.py
---

## goal

add matrix parser that restores old signals dict

## implementation

- step4.py: `_parse_score_matrix(raw, expected_count)` — split rows, validate `index|r1..r9|importance|timeliness`, map relevance columns via COLUMN_ORDER, return `list[dict]`
- malformed rows, out-of-range values, wrong column count, duplicate index raise ValueError for caller fallback

## acceptance

returns `{"relevance": {col: score}, "importance": int, "timeliness": int}` consumable by `aggregate_scores` / `assign_category` without changes; rejects missing rows, dup index, col count != 9, values outside [0,10]

## verify

python3 -m pytest tests/test_step4.py -k matrix -v

## constraints

- no changes to COLUMN_ORDER, aggregate_scores, assign_category, archive/monthly
