---
id: task-01
title: 为 archive_enrich 调用链增加 include_images 图片开关
author: lmr
created_at: 2026-07-03 14:47:33
priority: P0
depends_on: []
blocks: [task-02, task-03]
requirement_ids: [FR-01, FR-02, FR-03]
decision_ids: [D-001@v1, D-002@v2]
allowed_paths:
  - archive_enrich.py
goal: >
  给 archive_enrich 调用链增加 include_images 参数，False 时跳过图片分支但保留正文增强和默认兼容。
implementation:
  - enrich_records 增加 include_images=True 参数。
  - include_images=False 时跳过图片预算、should_enrich_image、enrich_image 和图片统计。
  - enrich_archive/enrich_archive_best_effort 透传 include_images，并在 False 时不打印图片统计行。
acceptance:
  - include_images=False 时不调用 enrich_image 但仍执行正文增强。
  - 默认不传 include_images 时图片分支仍执行。
verify:
  - python3 -m unittest discover -s tests -p 'test_archive_enrich.py' -v
constraints:
  - 默认 include_images=True，未配置新功能时行为不变。
  - 不改 JSONL schema、image_status 状态或 enrich_image() 名称。
---
## Acceptance
- See frontmatter acceptance.
## Verify
- See frontmatter verify.
