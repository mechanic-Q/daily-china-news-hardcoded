---
author: lmr
created_at: 2026-07-01 18:49:10
schema_version: 1
doc_type: proposal
change_id: 2026-07-04-phase-15d-source-health
phase: 15d
depends_on:
  - 2026-07-01-phase-15a-common-lib
status: brainstorm-skeleton
---

# Proposal · Phase 15D · source health monitoring

## 动机

当前某个信源变成 0 条时，流水线仍继续输出日报，除人工阅读 `0新闻_粗筛.md` 外没有长期健康记录。比如新华社某日 0 条可能是页面结构变了，也可能是当天首页未匹配，系统无法区分临时为空和爬虫失效。

Phase 15D 目标是让信源健康显性化：每次采集记录每个信源的通过/淘汰/耗时/工具，并在连续异常时输出 warning，同时让月报展示近 30 天信源健康概况。

## 关键问题

1. 无历史成功率，无法发现连续退化。
2. 信源失败只存在 stdout，不持久化。
3. 月报没有数据质量/采集覆盖情况。

## 变更范围

- 新增 `archive/sources_health.jsonl`
- `step1_3.py` 每信源采集后 append health record
- pipeline 结束输出 red/yellow banner：连续 3 天 <5 条等规则
- `monthly_report.py` 增加信源健康段
- `monthly_report.py` 顺手改为使用 `llm_client.call_llm("monthly-overview")`
- `llm.yaml` 新增 `call_sites.monthly-overview`

## 不在范围内

- 不改变采集逻辑本身（15C）
- 不引入数据库
- 不改变 `run_all.sh`

## 成功标准

- 每次 `step1_3.py` 运行追加 7 条 health JSONL
- 连续异常能在 stdout 中显示 warning
- `monthly_report.py --month YYYY-MM --dry-run` 可展示信源健康摘要
- `monthly_report.py` 不再直接 `from openai import OpenAI`
