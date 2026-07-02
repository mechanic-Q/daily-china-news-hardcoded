---
author: lmr
created_at: 2026-07-02 20:11:50
schema_version: 1
doc_type: plan
change_id: 2026-07-04-phase-15d-source-health
phase: 15d
plan_level: light
---

# 轻量计划：Phase 15D source health monitoring

## 来源

直接引用 brainstorm 结论：Phase 15D 目标是让信源健康显性化；每次采集记录每个信源的通过/淘汰/耗时/工具，并在连续异常时输出 warning，同时让月报展示近 30 天信源健康概况。

## 范围

- `step1_3.py`：记录每信源 health JSONL，并输出异常 warning banner。
- `monthly_report.py`：读取 health JSONL，展示月度信源健康摘要，并统一使用 `llm_client.call_llm("monthly-overview", ...)`。
- `llm.yaml`：新增 `monthly-overview` call site。
- `tests/manual/test_15d_source_health.py`：记录手工验收入口与样例验证步骤。

## Tasks

### Wave 1

- [x] task-01: 定义并接入 health JSONL 记录范围，覆盖采集结果字段与 best-effort 写入策略。（覆盖：FR-01）
- [x] task-04: 将 `monthly_report.py` 的 overview LLM 调用迁移到 `llm_client.call_llm("monthly-overview", ...)`，并补齐 `llm.yaml` 配置。（覆盖：FR-04）

### Wave 2

- [x] task-02: 在 `step1_3.py` 完成非 dry-run 写入、dry-run would-write 输出、异常 warning banner。（覆盖：FR-01, FR-02）
- [x] task-03: 在 `monthly_report.py` 增加月度信源健康摘要输出。（覆盖：FR-03）

### Wave 3

- [x] task-05: 增加 manual test 文档，覆盖采集写入、dry-run 不污染、banner、月报摘要、LLM client 统一调用。（覆盖：FR-01, FR-02, FR-03, FR-04）

## 验收

- AC-01: 非 dry-run 运行 `step1_3.py --date YYYY-MM-DD` 后，`archive/sources_health.jsonl` 追加每信源 JSONL 记录，字段包含 date/source/passed/failed/total/tool/elapsed_ms/status/recorded_at。
- AC-02: dry-run 运行 `step1_3.py --date YYYY-MM-DD --dry-run` 不追加 health JSONL，只输出 would-write 信息。
- AC-03: 当天某信源 `passed == 0` 或最近 3 天连续 `passed < 5` 时，`step1_3.py` stdout 显示 warning banner。
- AC-04: `monthly_report.py --month YYYY-MM --dry-run` 输出每信源运行天数、平均 passed、0 条天数、最差连续低谷。
- AC-05: `monthly_report.py` 不再直接 `from openai import OpenAI` 生成 overview，overview 通过 `llm_client.call_llm("monthly-overview", ...)` 调用。
- AC-06: `llm.yaml` 包含 `monthly-overview` call site。
- AC-07: 变更不改变 `run_all.sh` 编排，不改变原有采集过滤逻辑。
