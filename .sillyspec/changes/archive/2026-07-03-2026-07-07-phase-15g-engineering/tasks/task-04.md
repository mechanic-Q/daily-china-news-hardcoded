---
id: task-04
title: 增加 archive record schema migration
author: lmr
created_at: 2026-07-03 20:11:30
priority: P0
depends_on: []
blocks: [task-05, task-08]
requirement_ids: [FR-03]
decision_ids: [D-004@v1]
allowed_paths: [news_archive.py]
---

goal: >
  在读取 archive JSONL 时把旧记录迁移到当前 schema，保持历史数据可用。
implementation:
  - 新增 migrate_record(record) 并返回升级后的副本。
  - 为缺失字段填入 safe defaults。
  - 在 load_month_records 读取每行后调用 migration。
acceptance:
  - 缺 schema_version 的记录升级到 SCHEMA_VERSION。
  - normalized_url、selected_in_top10、状态字段被补齐。
  - write_month_records 仍输出 JSONL。
verify:
  - python3 -m pytest tests/test_news_archive.py
constraints:
  - 不修改输入 dict。
  - 缺失正文或图片状态不得伪装成功。
  - 不改变 archive 文件目录结构。
