---
id: task-01
title: 新建 daily 公共包
author: lmr
created_at: 2026-07-01 19:08:31
priority: P0
depends_on: []
blocks: [task-02, task-03, task-04, task-05, task-06, task-07]
requirement_ids: [FR-01, FR-02, FR-03, FR-05, FR-06]
decision_ids: [D-001@v1, D-002@v1, D-003@v1, D-004@v1]
allowed_paths:
  - daily/__init__.py
  - daily/common.py
  - daily/http.py
goal: >
  建立 daily 公共包，集中共享路径、栏目、时区、参数解析、信源识别和 HTTP/Chromium helper。
implementation:
  - 新建 daily 包入口。
  - 在 daily/common.py 放共享常量和 parse_common_args、detect_source、workdir。
  - 在 daily/http.py 放 CHROMIUM、ssl_ctx、fetch_html_static、chromium_dom、_preprocess_html。
acceptance:
  - daily.common 与 daily.http 可 import。
  - DAILY_OUTPUT_DIR 覆盖 BASE_DIR 生效。
  - detect_source 对 news.cn 返回 新华社。
verify:
  - python3 -c "from daily.common import BASE_DIR; from daily.http import chromium_dom"
constraints:
  - 不使用 argparse。
  - 不修改 run_all.sh 或业务脚本。
---
## Acceptance
- 见 frontmatter acceptance。
## Verify
- 见 frontmatter verify。
