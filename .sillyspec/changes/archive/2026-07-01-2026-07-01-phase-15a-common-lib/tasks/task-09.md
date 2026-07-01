---
id: task-09
title: 执行全局回归验证
author: lmr
created_at: 2026-07-01 19:08:31
priority: P0
depends_on: [task-02, task-03, task-04, task-05, task-06, task-07, task-08]
blocks: []
requirement_ids: [FR-01, FR-02, FR-03, FR-04, FR-05, FR-06, FR-07]
decision_ids: [D-001@v1, D-002@v1, D-003@v1, D-004@v1, D-005@v1]
allowed_paths:
  - .sillyspec/changes/2026-07-01-phase-15a-common-lib/verify-result.md
goal: >
  对 Phase 15A 执行 import、env、重复定义、兼容层、pytest 和 dry-run 回归验证。
implementation:
  - 执行 daily.common 与 daily.http import smoke。
  - 执行 DAILY_OUTPUT_DIR 覆盖断言和 rg 重复定义检查。
  - 执行 pytest 全量与 dry-run 回归，记录 verify-result.md。
acceptance:
  - V-01 至 V-12 通过或记录环境阻塞原因。
  - python3 -m pytest tests/ 通过。
  - re-export 检查 step6、monthly_report、news_archive 通过。
verify:
  - python3 -m pytest tests/
  - ./run_all.sh --date 2026-06-30 --dry-run
constraints:
  - local.yaml 未配置 test/lint/build，使用 design.md 验收命令。
  - 验证任务不改业务源码。
---
## Acceptance
- 见 frontmatter acceptance。
## Verify
- 见 frontmatter verify。
