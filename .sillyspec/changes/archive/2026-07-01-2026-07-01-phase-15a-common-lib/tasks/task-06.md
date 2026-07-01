---
id: task-06
title: 迁移 archive news monthly 兼容层
author: lmr
created_at: 2026-07-01 19:08:31
priority: P0
depends_on: [task-01, task-04]
blocks: [task-08, task-09]
requirement_ids: [FR-02, FR-03, FR-06]
decision_ids: [D-003@v1, D-004@v1, D-005@v1]
allowed_paths:
  - news_archive.py
  - archive_enrich.py
  - monthly_report.py
goal: >
  让归档、归档增强和月报复用公共路径、时区、栏目和 SSL context，同时保留旧导入与特殊参数兼容。
implementation:
  - news_archive.py 导入 BASE_DIR、CST、detect_source 并保留 infer_source shim。
  - archive_enrich.py 用 daily.common.CST 与 daily.http.ssl_ctx as SSL_CTX。
  - monthly_report.py 用 BASE_DIR、CST、COLUMN_ORDER 派生路径。
acceptance:
  - infer_source、monthly_report.COLUMN_ORDER、archive_enrich.SSL_CTX 兼容导入可用。
  - archive/monthly 特殊 parse_args 保留。
  - 兼容三件套 pytest 通过。
verify:
  - python3 -m pytest tests/test_news_archive.py tests/test_monthly_report.py tests/test_archive_enrich.py -x
constraints:
  - 不改 archive JSONL schema。
  - 不改月报渲染和 LLM 逻辑。
---
## Acceptance
- 见 frontmatter acceptance。
## Verify
- 见 frontmatter verify。
