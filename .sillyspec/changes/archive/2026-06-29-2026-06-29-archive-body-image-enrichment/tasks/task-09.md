---
id: task-09
title: 扩展 tests/test_news_archive.py（覆盖：FR-07, FR-09, D-006@v1）
author: lmr
created_at: 2026-06-29 14:36:20
priority: P0
depends_on: [task-02]
blocks: [task-10]
requirement_ids: [FR-07, FR-09]
decision_ids: [D-006@v1]
allowed_paths:
  - tests/test_news_archive.py
goal: >
  扩展 news_archive 测试，证明 schema v2 兼容旧记录且 14A upsert 不覆盖 14B 字段。
implementation:
  - 增加 build_record 生成 schema_version=2 的断言
  - 增加 load_month_records 读取旧 v1 record 的兼容测试
  - 增加 archive_articles 保留 body/body_status 的 upsert 测试
  - 增加 archive_articles 保留 image_url/image_path 的 upsert 测试
acceptance:
  - 旧 v1 JSONL 无 body/image 字段时可正常加载
  - build_record 返回 schema_version=2
  - 同 URL upsert 后 title/score 可更新但 body* 字段保留
  - 同 URL upsert 后 image* 字段保留
verify:
  - python3 tests/test_news_archive.py
constraints:
  - 不新增外部依赖
  - 使用 tempfile 与 mock.patch 隔离 ARTICLES_DIR
  - 不测试 archive_enrich 行为，该部分由 task-08 覆盖
---
