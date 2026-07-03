---
id: task-06
title: 运行 Phase 15E 验收检查，记录 LLM 调用次数、输出差异和 fallback 行为（覆盖：全部）
author: lmr
created_at: 2026-07-03 02:51:33
priority: P0
depends_on: [task-01, task-02, task-03, task-04, task-05]
blocks: []
requirement_ids: [FR-01, FR-02, FR-03, FR-04, FR-05]
decision_ids: []
allowed_paths:
  - .sillyspec/changes/2026-07-05-phase-15e-llm-batching/verify-result.md
goal: >
  验证 15E 是否达到调用次数、输出差异、batch fallback 和 step7 顺序契约。
implementation:
  - 运行 py_compile 和调用计数脚本，记录结果。
  - 对比 2026-06-30 样本输出差异，列出需要人工确认的差异。
  - 模拟 batch JSON 失败并记录 fallback 证据。
  - 写入 `verify-result.md`。
acceptance:
  - step4 LLM 调用次数 `<=30` 或报告未达标原因。
  - 输出差异 `<=5%` 或列出差异供人工确认。
  - batch JSON 失败回退单条，step7 单条失败回退且顺序一致。
verify:
  - python3 -m py_compile step4.py step7.py llm_client.py
  - python3 tests/manual/test_15e_llm_call_count.py --date 2026-06-30
constraints:
  - 样本缺失时记录缺样本，不合成 pass。
  - API key 缺失记录为环境问题，不标记伪通过。
  - diff 用 dry-run，不改已生成发布文件。
---
## Acceptance
See frontmatter `acceptance`.
## Verify
See frontmatter `verify`.
