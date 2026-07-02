---
author: lmr
created_at: 2026-07-02 23:27:00
schema_version: 1
doc_type: module-impact
change_id: 2026-07-04-phase-15d-source-health
phase: 15d
---

# Module Impact · Phase 15D · source health monitoring

> 注：`.sillyspec/docs/Daily/modules/_module-map.yaml` 不存在，建议运行 `sillyspec run scan` 生成模块映射。
> 以下为未匹配文件的直接变更清单。

## 真实变更（git diff HEAD~1）

| 文件 | 操作 | 说明 |
|---|---|---|
| `step1_3.py` | 修改 | 新增 `HealthRecord`、`HEALTH_FILE`、`write_health_record()`、`_read_recent_health()`、`_emit_health_warnings()`；三处采集分支接入 |
| `monthly_report.py` | 修改 | 新增 `load_source_health()`、`compute_source_health_stats()`；月报渲染信源健康区块；LLM client 迁移至 `call_llm` |
| `llm.yaml` | 修改 | 新增 `monthly-overview` call site |
| `tests/manual/test_15d_source_health.py` | 新增 | 8 项 manual 子测试覆盖全部验收条件 |

## 未匹配文件

| 文件 | 影响类型 | 更新内容摘要 | needs_review |
|------|----------|-------------|-------------|
| `step1_3.py` | 逻辑变更 | 每 source 采集后写入 health JSONL；输出 passed==0 / 连续 3 天 <5 warning banner | false |
| `monthly_report.py` | 逻辑变更 + 接口变更 | 新增信源健康摘要月度统计；overview 用 `call_llm` 替代直接 OpenAI | false |
| `llm.yaml` | 配置变更 | 新增 `monthly-overview` 配置块 | false |
| `tests/manual/test_15d_source_health.py` | 新增 | 8 项 manual acceptance tests | false |

## 依赖关系

- `step1_3.py` → `daily.common.BASE_DIR`（已有依赖，未变更）
- `monthly_report.py` → `llm_client.call_llm`（Phase 15A 新增）
- 无跨模块循环依赖
