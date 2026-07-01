---
id: task-04
title: 迁移 extractor 到公共包
author: lmr
created_at: 2026-07-01 19:08:31
priority: P0
depends_on: [task-01]
blocks: [task-06, task-08, task-09]
requirement_ids: [FR-02, FR-04, FR-05, FR-07]
decision_ids: [D-001@v1, D-002@v1]
allowed_paths:
  - step6.py
goal: >
  让 step6.py 复用公共路径、参数解析和 HTTP helper，同时保留 archive_enrich 依赖的 re-export 名称。
implementation:
  - 用 daily.common.BASE_DIR 与 parse_common_args 替换本地定义。
  - 用 daily.http.fetch_html_static、chromium_dom、ssl_ctx、_preprocess_html 替换本地定义。
  - 保留 step6 顶层导入名和正文提取业务逻辑。
acceptance:
  - step6.py 不再定义重复 helper。
  - step6.fetch_html_static 与 step6.chromium_dom 仍存在。
  - tests/test_archive_enrich.py 通过。
verify:
  - python3 -c "import step6; assert hasattr(step6,'fetch_html_static')"
  - python3 -m pytest tests/test_archive_enrich.py -x
constraints:
  - 不改正文提取算法。
  - 不改 archive_enrich import 路径。
---
## Acceptance
- 见 frontmatter acceptance。
## Verify
- 见 frontmatter verify。
