---
id: task-06
title: 补充 step4 纯函数回归测试
author: lmr
created_at: 2026-07-03 20:11:30
priority: P1
depends_on: [task-03]
blocks: [task-08]
requirement_ids: [FR-04]
decision_ids: [D-003@v1]
allowed_paths: [tests/test_step4.py]
---

goal: >
  为 step4 的解析、过滤或打分纯函数补充 CI 可运行的无外部依赖测试。
implementation:
  - 选择不触发 LLM 的 helper 或解析路径。
  - 构造最小输入覆盖正向和边界样例。
  - 保持测试数据内联且可读。
acceptance:
  - python3 -m pytest tests/test_step4.py 通过。
  - 测试不读取 API key。
  - 测试不访问网络或真实 LLM。
verify:
  - python3 -m pytest tests/test_step4.py
constraints:
  - 不修改 step4.py 业务逻辑。
  - 不覆盖 batch LLM 集成路径。
  - 不需要 Chromium。
