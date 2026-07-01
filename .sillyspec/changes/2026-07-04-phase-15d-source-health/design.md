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
