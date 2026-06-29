---
id: task-01
title: news_archive schema v2 与 IMAGES_DIR（覆盖：FR-09, D-006@v1）
author: lmr
created_at: 2026-06-29 14:36:20
priority: P0
depends_on: []
blocks: [task-02, task-03]
requirement_ids: [FR-09]
decision_ids: [D-006@v1]
allowed_paths:
  - news_archive.py
goal: >
  SCHEMA_VERSION 升至 2，新增 IMAGES_DIR 常量并导出，为 archive JSONL v2 与增强流水线建立基础路径与版本常量。
implementation:
  - SCHEMA_VERSION 从 1 升至 2
  - 新增 IMAGES_DIR = ARCHIVE_DIR / "images"
  - 添加 __all__ 导出 SCHEMA_VERSION、IMAGES_DIR、BASE_DIR、ARCHIVE_DIR、ARTICLES_DIR 等公共常量
  - 检查 module-level 用途，确保 IMAGES_DIR 被 module 级引用覆盖；如仅在此模块定义路径常量，无需额外导出声明
  - 维护向后兼容：load_month_records 对不含 14B 字段的旧 JSONL 不做强制校验
acceptance:
  - news_archive.SCHEMA_VERSION == 2
  - news_archive.IMAGES_DIR 指向 /mnt/e/每日新中国/archive/images
  - load_month_records 读取旧 v1 JSONL 不报错、不丢弃记录
  - 测试中 import news_archive 可获取全部新增常量
verify:
  - python3 tests/test_news_archive.py
constraints:
  - 不改动 JSONL 文件格式、不修改已有 record 字段结构
  - load_month_records 不做 14B 字段 key 强制存在性校验
  - 不新增第三方依赖；常量命名风格与现有 BASE_DIR/ARCHIVE_DIR/ARTICLES_DIR 一致
---
