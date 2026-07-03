---
id: task-05
title: 增加 archive migration 回归测试
author: lmr
created_at: 2026-07-03 20:11:30
priority: P0
depends_on: [task-04]
blocks: [task-08]
requirement_ids: [FR-03]
decision_ids: [D-004@v1]
allowed_paths: [tests/test_news_archive.py]
---

goal: >
  用回归测试证明旧 archive record 可在读取时迁移并保持 JSONL 兼容。
implementation:
  - 用 tmp_path 写入缺 schema_version 的旧 record。
  - 调用 load_month_records 验证迁移结果。
  - 覆盖默认字段和原始字段保留。
acceptance:
  - 测试不写真实 archive 目录。
  - 旧记录读取后 schema_version 为当前值。
  - 默认状态字段表达 missing 或 metadata-only。
verify:
  - python3 -m pytest tests/test_news_archive.py
constraints:
  - 不依赖网络、LLM 或 Chromium。
  - 不改变已有 archive 测试语义。
  - 使用 tmp_path 隔离文件 I/O。
