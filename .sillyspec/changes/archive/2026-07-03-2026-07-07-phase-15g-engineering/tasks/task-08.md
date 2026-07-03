---
id: task-08
title: 新增 GitHub Actions 单元测试 CI
author: lmr
created_at: 2026-07-03 20:11:30
priority: P0
depends_on: [task-03, task-05, task-06, task-07]
blocks: []
requirement_ids: [FR-04]
decision_ids: [D-003@v1]
allowed_paths: [.github/workflows/test.yml]
---

goal: >
  新增 GitHub Actions，让非 manual 单元测试在 push 和 PR 上自动运行。
implementation:
  - 创建 .github/workflows/test.yml。
  - 使用 Python 3.12 并安装 requirements.txt。
  - 执行 python3 -m pytest tests/。
acceptance:
  - workflow 包含 push 和 pull_request 触发。
  - CI 不运行 tests/manual。
  - CI 不要求 API key 或 Chromium。
verify:
  - python3 -m pytest tests/
constraints:
  - 不新增额外 CI 服务。
  - 不修改 local.yaml。
  - 保持用户本地运行命令不变。
