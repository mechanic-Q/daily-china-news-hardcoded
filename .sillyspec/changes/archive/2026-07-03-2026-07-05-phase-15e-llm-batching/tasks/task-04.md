---
id: task-04
title: 在 `step4.py` 增加批量栏目评分，并保留现有单条评分与关键词 fallback（覆盖：FR-03, FR-04）
author: lmr
created_at: 2026-07-03 02:51:33
priority: P0
depends_on: [task-02]
blocks: [task-06]
requirement_ids: [FR-03, FR-04]
decision_ids: []
allowed_paths:
  - step4.py
goal: >
  对未命中高置信直通的文章批量执行栏目评分，保持单条评分和关键词 fallback。
implementation:
  - 新增 `score_signals_batch(articles)`，按 20 条分批请求 `column-score`。
  - Prompt 返回 index、完整 `COLUMN_ORDER` relevance、importance 和 timeliness。
  - 每条结果复用 `_validate_signals()`，无效条目回退 `score_signals()` 再走关键词路径。
acceptance:
  - 批量评分命中时标记 `llm-batch` 并写入 signals。
  - JSON 缺项或校验失败条目回退单条/关键词路径。
  - 2026-06-30 样本 step4 LLM 调用次数 `<=30` 或报告原因。
verify:
  - python3 -m py_compile step4.py
  - python3 tests/manual/test_15e_llm_call_count.py --date 2026-06-30
constraints:
  - `_validate_signals()` 语义不变。
  - 每条 relevance 覆盖全部 `COLUMN_ORDER`。
  - 不修改 `llm.yaml`，除非执行中确认必须。
---
## Acceptance
See frontmatter `acceptance`.
## Verify
See frontmatter `verify`.
