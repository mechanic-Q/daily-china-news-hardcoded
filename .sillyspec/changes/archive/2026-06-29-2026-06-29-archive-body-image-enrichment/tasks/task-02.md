---
id: task-02
title: 14A upsert 保留 14B enrichment 字段（覆盖：FR-07, D-006@v1）
author: lmr
created_at: 2026-06-29 14:36:20
priority: P0
depends_on: [task-01]
blocks: [task-09]
requirement_ids: [FR-07]
decision_ids: [D-006@v1]
allowed_paths:
  - news_archive.py
  - tests/test_news_archive.py
goal: >
  修改 14A archive_articles upsert 合并逻辑，保留已有 14B body/image 字段，避免重跑归档降级记录。
implementation:
  - 在 existing[rid] 已存在时合并新旧 record
  - 新 record 更新 title/category/score/signals/updated_at 等 14A 字段
  - 旧 record 的 body* 与 image* 字段必须保留
  - 已 enriched 的 archive_status 不得降级为 metadata-only
acceptance:
  - 同 URL upsert 后 body/body_status/body_source_url 仍存在
  - 同 URL upsert 后 image_url/image_path/image_status 仍存在
  - title/score/signals/updated_at 仍可更新
  - 新记录仍使用 14A 默认字段
verify:
  - python3 tests/test_news_archive.py
constraints:
  - archive_articles 函数签名不变
  - 不新增依赖，不写 type hints
  - 只改 news_archive.py 与相关测试
---
