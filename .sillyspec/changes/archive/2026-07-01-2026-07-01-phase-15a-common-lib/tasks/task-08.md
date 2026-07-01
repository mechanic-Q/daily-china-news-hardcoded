---
id: task-08
title: 新增手动 diff smoke 脚本
author: lmr
created_at: 2026-07-01 19:08:31
priority: P1
depends_on: [task-02, task-03, task-04, task-05, task-06]
blocks: [task-09]
requirement_ids: [FR-07]
decision_ids: []
allowed_paths:
  - tests/manual/__init__.py
  - tests/manual/test_15a_diff_smoke.py
goal: >
  提供手动 dry-run baseline/diff 脚本，辅助确认 Phase 15A 重构前后关键输出不漂移。
implementation:
  - 新建 tests/manual/__init__.py。
  - 新建 test_15a_diff_smoke.py，支持 --baseline、--diff、--date、--baseline-file。
  - 调用 ./run_all.sh --date DATE --dry-run 并提取关键行统一 diff。
acceptance:
  - --baseline 可生成 baseline 文件。
  - --diff 无差异时 exit 0。
  - 有差异时输出差异计数并 exit 1。
verify:
  - python3 tests/manual/test_15a_diff_smoke.py --help
  - python3 tests/manual/test_15a_diff_smoke.py --baseline --date 2026-06-30
constraints:
  - 脚本不依赖 pytest。
  - 不修改 run_all.sh 或 step 输出。
---
## Acceptance
- 见 frontmatter acceptance。
## Verify
- 见 frontmatter verify。
