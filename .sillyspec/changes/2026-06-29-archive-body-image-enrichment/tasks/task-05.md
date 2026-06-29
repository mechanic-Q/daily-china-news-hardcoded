---
id: task-05
title: 实现首图提取与下载（覆盖：FR-03, FR-04, FR-08, D-003@v1, D-007@v1）
author: lmr
created_at: 2026-06-29 14:36:20
priority: P1
depends_on: [task-03]
blocks: [task-06, task-08]
requirement_ids: [FR-03, FR-04, FR-08]
decision_ids: [D-003@v1, D-007@v1]
allowed_paths:
  - archive_enrich.py
  - tests/test_archive_enrich.py
goal: >
  仅为 top10 record 提取首图 URL 并下载本地，同时保持 step6.fetch_and_extract 返回契约不变。
implementation:
  - 实现 should_enrich_image(record, missing_only)
  - 实现 fetch_html_for_image(record)，单独抓 HTML
  - 实现 extract_first_image_url，按 og:image/twitter:image/img 顺序查找
  - 实现 download_image，保存到 archive/images/YYYY-MM/<article_id>.<ext>
  - 实现 enrich_image，返回 image_url/image_path/image_status/image_error
acceptance:
  - 非 top10 record 写 image_status=not_selected 且不下载
  - top10 成功时写 image_url、image_path、image_status=downloaded
  - 无图写 not_found，下载失败写 failed 和 image_error
  - dry-run 不下载图片
verify:
  - python3 tests/test_archive_enrich.py
constraints:
  - 不改变 step6.fetch_and_extract 签名或返回值
  - 只抓首图，不抓多图
  - 图片失败不影响正文状态，不 raise 到上层
---
