---
author: lmr
created_at: 2026-07-01 18:49:10
schema_version: 1
doc_type: proposal
change_id: 2026-07-07-phase-15g-engineering
phase: 15g
depends_on:
  - 2026-07-01-phase-15a-common-lib
  - 2026-07-02-phase-15b-trafilatura-body
  - 2026-07-03-phase-15c-async-fetch
  - 2026-07-04-phase-15d-source-health
  - 2026-07-05-phase-15e-llm-batching
  - 2026-07-06-phase-15f-image-quality
status: brainstorm-skeleton
---

# Proposal · Phase 15G · engineering hardening

## 动机

Phase 15A–15F 会完成结构整理、正文提取替换、采集加速、健康监控、LLM 批处理与图片质量提升。最后需要一个工程化收尾 change，把日志、测试、schema migration、错误脱敏与 CI 补齐，避免优化后缺少长期维护护栏。

## 关键问题

1. 仍以 `print` 为主，无持久化日志和日志级别。
2. `llm_client.py` 使用 `traceback.print_exc()`，潜在泄露 API 错误上下文。
3. archive schema 只有 `SCHEMA_VERSION`，没有显式 migration。
4. 缺少 CI，测试靠人工。

## 变更范围

- 引入 `loguru`（正式 brainstorm 确认）或标准库 logging
- `llm_client.call_llm` 异常脱敏
- `news_archive.migrate_record(r)` 显式 schema migration
- 扩充单测：step4/step6/archive/monthly
- 新增 `.github/workflows/test.yml`

## 不在范围内

- 不再改业务算法（前面 change 已完成）
- 不改运行命令
- 不做数据库化

## 成功标准

- pytest 在 CI 绿
- LLM 异常日志不包含 API key/Authorization header
- 旧 archive 记录可显式 migrate 到当前 schema
- 日志文件可轮转或至少按月写入
