---
author: lmr
created_at: 2026-07-03 19:59:01
schema_version: 1
doc_type: decisions
change_id: 2026-07-07-phase-15g-engineering
phase: 15g
status: confirmed
---

# Decisions · Phase 15G · Engineering Hardening

## D-001@v1: 使用标准库 logging

- type: architecture
- status: accepted
- source: user
- question: Phase 15G 日志是否接受新增依赖？
- answer: 使用标准库 logging，不引入 loguru。
- normalized_requirement: 日志实现必须零新增依赖，同时提供日志级别和持久化能力。
- impacts: [FR-01, design:Wave-1, task-logging, verify-logging]
- evidence: Step 6 用户回答「标准库 logging」
- priority: P1

## D-002@v1: 采用方案A最小工程护栏

- type: architecture
- status: accepted
- source: user
- question: Phase 15G 在三种实现方案中选哪一种？
- answer: 选择方案A：最小工程护栏。
- normalized_requirement: 实现 logging、LLM 脱敏、archive migration、关键测试和 CI；不全量替换所有 print，不扩大为全 pipeline 日志标准化。
- impacts: [design:总体方案, task-logging, task-llm-redaction, task-archive-migration, task-ci]
- evidence: Step 8 用户回答「方案A」
- priority: P1

## D-003@v1: CI 排除 manual tests 与 Chromium 依赖

- type: boundary
- status: accepted
- source: docs
- question: GitHub Actions CI 应覆盖哪些测试？
- answer: CI 运行 `python3 -m pytest tests/`，但测试设计避免真实网络、LLM、Chromium；`tests/manual/` 不作为 CI 目标。
- normalized_requirement: CI 必须可在无 API key、无 Chromium 的环境稳定运行。
- impacts: [FR-04, design:Wave-3, task-ci, verify-ci]
- evidence: requirements.md FR-04 与非功能需求；local.yaml test_strategy=skip；Step 9 用户确认设计
- priority: P1

## D-004@v1: Archive migration 在读取时执行

- type: compatibility
- status: accepted
- source: code
- question: 旧 archive record 如何升级到当前 schema？
- answer: 在 `news_archive.load_month_records` 读取 JSONL 时调用 `migrate_record(record)`，内存中补齐默认字段；写回仍保持 JSONL。
- normalized_requirement: 旧记录无需手工改文件即可被当前代码读取，后续写回时自然保存为当前 schema。
- impacts: [FR-03, design:Wave-2, task-archive-migration, verify-archive-migration]
- evidence: news_archive.py `SCHEMA_VERSION = 2`、`build_record`、`load_month_records`; Step 9 用户确认设计
- priority: P1
