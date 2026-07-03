---
author: lmr
created_at: 2026-07-01 18:49:10
schema_version: 1
doc_type: requirements
change_id: 2026-07-07-phase-15g-engineering
phase: 15g
status: brainstorm-skeleton
---

# Requirements · Phase 15G · engineering hardening

## 角色

| 角色 | 说明 |
|---|---|
| 维护者 | 查看日志、排查异常、升级 schema |
| 测试者 | 运行 pytest / CI |
| 运行者 | 依旧通过原命令运行 pipeline |

## 功能需求

### FR-01: 日志分级与持久化

Given pipeline 运行  
When 有 info/warn/error 事件  
Then 输出到 stdout，同时可持久化到日志文件（具体工具正式确认）

### FR-02: LLM 异常脱敏

Given LLM API 调用失败  
When `call_llm` 捕获异常  
Then 日志不包含 API key 或 Authorization header

### FR-03: Archive schema migration

Given archive JSONL 中存在旧 schema record  
When load records  
Then 通过 `migrate_record` 补齐默认字段并升级 schema_version

### FR-04: CI 运行单元测试

Given push/PR 触发 GitHub Actions  
When workflow 执行  
Then 安装依赖并运行 `python3 -m pytest tests/`

## 非功能需求

- 不跑 manual tests in CI
- 不依赖 Chromium 的测试进入 CI
- 不改用户运行步骤
