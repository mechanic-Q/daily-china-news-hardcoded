---
id: task-01
title: 新增 Phase 15E 手工调用计数与输出对比脚本（覆盖：FR-01, FR-02, FR-03, FR-04）
author: lmr
created_at: 2026-07-03 02:51:33
priority: P0
depends_on: []
blocks: [task-06]
requirement_ids: [FR-01, FR-02, FR-03, FR-04]
decision_ids: []
allowed_paths:
  - tests/manual/test_15e_llm_call_count.py
goal: >
  新建手工脚本统计 step4 LLM 调用次数和输出差异，给 15E batching 提供可复验基线。
implementation:
  - 接收 `--date YYYY-MM-DD` 并检查样本 `0新闻_粗筛.md`。
  - 替换 `llm_is_china_related()`、`score_signals()`、`llm_classify_single()` 为计数替身。
  - 调用 `build_classification_result(today)` 并输出调用次数、函数明细、文章数和分类数。
acceptance:
  - 样本存在时输出调用计数，样本缺失时报告缺样本提示。
  - 替身返回固定合法结果，确保调用路径覆盖率。
  - 计数脚本不触发真实 LLM/API 调用，不写流水线产物。
verify:
  - python3 -m py_compile tests/manual/test_15e_llm_call_count.py
  - python3 tests/manual/test_15e_llm_call_count.py --date 2026-06-30
constraints:
  - 不修改生产代码。
  - 替身必须返回 `_validate_signals()` 可接受的结构。
  - 脚本必须兼容新老流水线文件格式。
---
## Acceptance
See frontmatter `acceptance`.
## Verify
See frontmatter `verify`.
