---
id: task-07
title: 补充 step6 纯函数回归测试
author: lmr
created_at: 2026-07-03 20:11:30
priority: P1
depends_on: [task-05]
blocks: [task-08]
requirement_ids: [FR-04]
decision_ids: [D-003@v1]
allowed_paths: [tests/test_step6.py]
---

goal: >
  为 step6 的正文清洗和污染检测 helper 补充无网络、无 Chromium 的回归测试。
implementation:
  - 选择 _postprocess_text、_is_contaminated 等纯函数路径。
  - 构造含站点噪声和正常正文的样例。
  - 验证清洗输出和污染判定稳定。
acceptance:
  - python3 -m pytest tests/test_step6.py 通过。
  - 测试不启动 Chromium。
  - 测试不抓取远端页面。
verify:
  - python3 -m pytest tests/test_step6.py
constraints:
  - 不修改 step6.py 业务逻辑。
  - 不测试真实 fetch_and_extract 网络路径。
  - 不要求外部二进制存在。
