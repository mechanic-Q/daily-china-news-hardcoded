---
author: lmr
created_at: 2026-07-01 18:49:10
schema_version: 1
doc_type: design
change_id: 2026-07-07-phase-15g-engineering
phase: 15g
status: brainstorm-skeleton
---

# Design · Phase 15G · engineering hardening

## 总体方案

### 1. Logging

候选方案：
- A: `loguru`，低配置成本，rotation 简单
- B: 标准库 `logging`，零新增依赖但配置较繁

初稿推荐 A，但正式 brainstorm 需确认是否接受新增依赖。

### 2. LLM 异常脱敏

`llm_client.call_llm` 不再直接 `traceback.print_exc()`。改为捕获 OpenAI SDK 异常，输出：
- call_site_id
- exception class
- status_code / error code（若有）
- 不输出 request headers / api key / Authorization

### 3. Schema migration

`news_archive.migrate_record(record)`：
- 缺 `schema_version` → 视为 v1
- 补 `body_status`、`image_status`、`archive_status`、`selected_in_top10` 等默认字段
- 写回 `schema_version = SCHEMA_VERSION`

### 4. CI

`.github/workflows/test.yml`：
- setup Python 3.12
- pip install requirements
- pytest tests/

## 文件变更清单

| 操作 | 文件 |
|---|---|
| 修改 | `requirements.txt`（如采用 loguru） |
| 修改 | `llm_client.py` |
| 修改 | `news_archive.py` |
| 新增 | `.github/workflows/test.yml` |
| 新增/修改 | `tests/*.py` |

## 风险

| 风险 | 应对 |
|---|---|
| CI 环境无 Chromium | 单元测试避免依赖真实 Chromium；E2E 留 manual |
| loguru 新依赖争议 | 正式 brainstorm 可选标准库 logging |
| 脱敏后 debug 信息不足 | 保留 exception class/status/code 与 call_site_id |

## 待正式 brainstorm 完善

- loguru vs stdlib logging
- migration 字段清单
- CI 是否跑 manual tests（初稿：不跑）
