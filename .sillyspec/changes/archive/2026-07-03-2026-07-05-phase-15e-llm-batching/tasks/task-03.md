---
id: task-03
title: 在 `step4.py` 增加批量涉华判断，并保留现有单条 fallback（覆盖：FR-02, FR-04）
author: lmr
created_at: 2026-07-03 02:51:33
priority: P0
depends_on: []
blocks: [task-06]
requirement_ids: [FR-02, FR-04]
decision_ids: []
allowed_paths:
  - step4.py
goal: >
  用批量涉华判断替换 `china_llm` 逐条 LLM 循环，失败时回退现有单条函数。
implementation:
  - 增加 JSON 清洗、分批 helper 和 `llm_is_china_related_batch(articles)`。
  - Prompt 使用 index-based JSON，校验 index 范围和 bool 类型。
  - batch 解析失败、缺项或类型错误时，该批次逐条调用 `llm_is_china_related()`。
acceptance:
  - 有效 batch 以每 20 条一次 LLM 调用返回涉华列表。
  - 无效 batch 回退单条涉华判断。
  - `classified`、`selected` 和 `1新闻_链接.md` 格式不变。
verify:
  - python3 -m py_compile step4.py
  - python3 tests/manual/test_15e_llm_call_count.py --date 2026-06-30
constraints:
  - 必须使用 index-based JSON，不用标题作 key。
  - 不新增 CLI 参数或运行步骤。
  - 不改变非 LLM 涉华关键词/信源判断。
---
## Acceptance
See frontmatter `acceptance`.
## Verify
See frontmatter `verify`.
