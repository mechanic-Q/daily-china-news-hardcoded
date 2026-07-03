---
id: task-02
title: 在 `step4.py` 增加高置信度关键词直通，跳过明显无须 LLM 的栏目评分（覆盖：FR-01）
author: lmr
created_at: 2026-07-03 02:51:33
priority: P0
depends_on: []
blocks: [task-04, task-06]
requirement_ids: [FR-01]
decision_ids: []
allowed_paths:
  - step4.py
goal: >
  对关键词高分且领先明显的标题直接分栏，避免无必要的 `score_signals()` LLM 调用。
implementation:
  - 新增高置信阈值常量，复用 `score_all_categories(title)`。
  - 新增直通判断 helper：`best_score >= 6` 且 `margin >= 3` 时返回栏目。
  - 分类循环命中直通时写入现有 article 字段并跳过 `score_signals()`。
acceptance:
  - 高置信文章不调 `score_signals()`，标记 `keyword-high-confidence`。
  - 低置信文章不受影响。
  - `1新闻_链接.md` 格式与 15A baseline 一致。
verify:
  - python3 -m py_compile step4.py
  - python3 tests/manual/test_15e_llm_call_count.py --date 2026-06-30
constraints:
  - 不改变 `COLUMN_ORDER`、`1新闻_链接.md` 结构、`--date`/`--dry-run` CLI。
  - 不改变 `score_signals()` 失败后的关键词 fallback 与 `llm_classify_single()` 路径。
  - 直通优先级公式沿用现有关键词 fallback 公式。
---
## Acceptance
See frontmatter `acceptance`.
## Verify
See frontmatter `verify`.
