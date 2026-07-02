---
author: lmr
created_at: 2026-07-01 18:49:10
schema_version: 1
doc_type: requirements
change_id: 2026-07-04-phase-15d-source-health
phase: 15d
status: brainstorm-skeleton
---

# Requirements · Phase 15D · source health monitoring

## 角色

| 角色 | 说明 |
|---|---|
| 运行者 | 运行每日采集并看到 warning |
| 维护者 | 通过 health JSONL 发现信源退化 |
| 月报读者 | 在月报看到信源覆盖情况 |

## 功能需求

### FR-01: 记录每信源健康数据

Given `step1_3.py` 处理一个信源完成  
When 非 dry-run 模式  
Then append 一条 JSONL 到 `archive/sources_health.jsonl`

### FR-02: 异常信源 warning

Given 某信源当天通过条数为 0 或连续 3 天低于阈值  
When `step1_3.py` 汇总输出  
Then stdout 显示 warning banner

### FR-03: 月报包含信源健康

Given 某月存在 health JSONL 记录  
When `monthly_report.py --month YYYY-MM` 运行  
Then 月报统计包含每信源运行天数、平均通过数、0 条天数

### FR-04: monthly_report 使用 llm_client

Given `llm.yaml` 配有 `monthly-overview` call site  
When 月报生成 LLM overview  
Then 通过 `llm_client.call_llm("monthly-overview", ...)` 调用

## 非功能需求

- 不改变日报主流程
- health 写入失败不得中断 pipeline（best effort）
- dry-run 默认不污染 health 数据（待正式确认）
