---
id: task-05
title: 验证 `step7.py` 摘要并发契约，必要时补强单条失败回退（覆盖：FR-05）
author: lmr
created_at: 2026-07-03 02:51:33
priority: P0
depends_on: []
blocks: [task-06]
requirement_ids: [FR-05]
decision_ids: []
allowed_paths:
  - step7.py
goal: >
  确认并发摘要按原始顺序写回，且单条 worker 异常不影响整步输出。
implementation:
  - 检查 `as_completed` 收集处是否会因单个 future 异常中断。
  - 必要时补异常保护，异常条目使用 `fallback_summarize()` 并标记 fallback。
  - 保持 `STEP7_MAX_WORKERS = 3`、worker 签名和按 index 回填顺序。
acceptance:
  - 单条 worker 异常不阻塞其他 future。
  - 异常条目使用规则回退摘要。
  - `3新闻_概述.md` 栏目和标题结构不变。
verify:
  - python3 -m py_compile step7.py
  - python3 step7.py --date 2026-06-30 --dry-run
constraints:
  - 输出顺序严格按 `enumerate(matched)` 原始顺序。
  - 不新增依赖、不改 `llm_client.py`。
  - dry-run 仍可能需要 API key；缺失时记录环境问题。
---
## Acceptance
See frontmatter `acceptance`.
## Verify
See frontmatter `verify`.
