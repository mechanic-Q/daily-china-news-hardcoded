---
id: task-02
title: 迁移 collector 到公共包
author: lmr
created_at: 2026-07-01 19:08:31
priority: P0
depends_on: [task-01]
blocks: [task-08, task-09]
requirement_ids: [FR-02, FR-04, FR-05, FR-07]
decision_ids: [D-002@v1, D-003@v1]
allowed_paths:
  - step1_3.py
goal: >
  让 step1_3.py 复用 daily.common 与 daily.http，同时保持采集 CLI 和输出行为不变。
implementation:
  - 用 daily.common.BASE_DIR 与 parse_common_args 替换本地定义。
  - 用 daily.http.CHROMIUM、ssl_ctx、fetch_html_static、chromium_dom 替换重复定义。
  - 显式保留 step1_3 旧 timeout 与 budget。
acceptance:
  - step1_3.py 不再定义重复 helper。
  - python3 -c "import step1_3" 无异常。
  - step1_3 dry-run 可运行。
verify:
  - python3 -c "import step1_3"
  - python3 step1_3.py --date 2026-06-30 --dry-run
constraints:
  - 不改 7 信源列表和 URL 规则。
  - 不改 run_all.sh 调用语义。
---
## Acceptance
- 见 frontmatter acceptance。
## Verify
- 见 frontmatter verify。
