---
author: lmr
created_at: 2026-07-01 18:49:10
schema_version: 1
doc_type: design
change_id: 2026-07-04-phase-15d-source-health
phase: 15d
status: brainstorm-skeleton
---

# Design · Phase 15D · source health monitoring

## 目标/背景/问题描述

Phase 15D 目标是让信源健康状态从一次性 stdout 变成可追踪的历史数据。当前某个信源变成 0 条时，流水线仍继续输出日报，异常只存在运行日志或 `0新闻_粗筛.md` 中，缺少跨天记录，维护者无法快速判断是单日无新闻、页面结构变化，还是采集链路失效。

本变更要达成：

- 每次采集记录每个信源的通过数、淘汰数、总数、耗时、工具和状态。
- 当天 0 条或连续异常时，在采集输出中显示 warning banner。
- 月报展示近 30 天信源健康摘要，让数据质量和采集覆盖情况可见。
- `monthly_report.py` 统一走 `llm_client.call_llm("monthly-overview", ...)`，不再手写 OpenAI client。

不改变采集逻辑本身，不引入数据库，不改变 `run_all.sh` 编排。

## 决策/方案选择

| 决策 | 方案 | 理由 | 取舍 |
|---|---|---|---|
| 健康数据存储 | 追加写入 `daily.common.BASE_DIR / "archive" / "sources_health.jsonl"` | JSONL 易追加、易按月扫描，符合当前文件型流水线 | 不做数据库查询能力；月级体量可接受 |
| 写入时机 | `step1_3.py` 每个 source 处理完成后 append 一行 | 最贴近采集结果，避免 pipeline 后段失败导致健康数据缺失 | 单个信源异常需 best effort 捕获 |
| dry-run 行为 | dry-run 不写 health，只打印 would-write | 避免预览污染历史健康数据 | dry-run 不能用于生成真实健康样本 |
| 写入失败策略 | health 写入失败只 warning，不中断 pipeline | 健康监控不能影响日报主产物 | 极端情况下健康数据缺口需要人工查看 stdout |
| warning 阈值 | 当天 `passed == 0` 或最近 3 天连续 `passed < 5` | 覆盖硬失败和连续退化，规则简单可解释 | 阈值暂不配置化，后续有需求再提取配置 |
| 月报统计 | 按月输出运行天数、平均 passed、0 条天数、最差连续低谷 | 对应维护者判断信源覆盖质量所需指标 | 不做图表，只输出文本摘要 |
| LLM client 统一 | `monthly_report.py` 使用 `llm_client.call_llm("monthly-overview", ...)`，`llm.yaml` 新增 call site | 和 Phase 15A common lib 对齐，避免散落 provider 配置 | 需要确认现有 `llm_client` 调用签名后改造 |

## 总体方案

### 1. 数据文件

`daily.common.BASE_DIR / "archive" / "sources_health.jsonl"`

每行 JSON：

```json
{
  "date": "2026-07-04",
  "source": "新华社",
  "passed": 0,
  "failed": 0,
  "total": 0,
  "tool": "urllib 首页 + chromium 降级",
  "elapsed_ms": 1234,
  "status": "failed",
  "recorded_at": "2026-07-04T08:00:00+08:00"
}
```

### 2. 写入时机

`step1_3.py` 每个 source 处理完成后 append 一行。dry-run 是否写入需正式 brainstorm 决策；初稿建议 dry-run 不写，只打印 would-write。

### 3. Banner 规则

读取最近 7 天同 source 记录：
- 连续 3 天 `passed < 5` → warning
- 当天 `passed == 0` → warning

### 4. 月报集成

`monthly_report.py` 读取 health JSONL，按月计算：
- 每信源运行天数
- 平均 passed
- 0 条天数
- 最差连续低谷

### 5. LLM client 统一

新增 `llm.yaml` call site：

```yaml
monthly-overview:
  max_tokens: 1200
  temperature: 0.7
  timeout: 30
```

`monthly_report.py` 用 `call_llm("monthly-overview", ...)` 替代手写 OpenAI client。

## 文件变更清单

| 操作 | 文件 |
|---|---|
| 修改 | `step1_3.py` |
| 修改 | `monthly_report.py` |
| 修改 | `llm.yaml` |
| 新增 | `tests/manual/test_15d_source_health.py` |

## 风险

| 风险 | 应对 |
|---|---|
| health JSONL 无限增长 | 月级体量小，15G 可考虑 rotate；本 change 不做 |
| dry-run 写入污染数据 | 初稿建议 dry-run 不写 |
| monthly_report 依赖 llm_client 后 provider 变化 | 这是目标，统一配置 |

## 待正式 brainstorm 完善

- dry-run 是否写 health
- health status 枚举
- banner 阈值是否 `<5` 固定还是配置化
