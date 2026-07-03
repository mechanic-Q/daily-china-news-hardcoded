---
author: lmr
created_at: 2026-07-03 12:56:09 +0800
phase: phase-15e-llm-batching
stage: verify
change_id: 2026-07-05-phase-15e-llm-batching
---

# 验证报告

## 结论

PASS WITH NOTES

Phase 15E 的核心实现已完成并通过本轮静态检查、任务验收、语法检查、现有 pytest、mock 批量成功路径探针和 fallback 探针。保留两条 notes：

- `tests/manual/test_15e_llm_call_count.py` 的 mock 覆盖不完整，只 patch `llm_client.call_llm`，未 patch `step4.call_llm`，因此脚本原始输出中的 `call_llm 4 次` 不是完整 batch 成功路径计数。
- 缺真实 API key，无法生成真实 `step4.py --dry-run` 新输出与 15A baseline 做百分比 diff；本报告用 mock 探针验证调用次数与 fallback 行为。

风险等级为 `unit-sufficient`，不触发 integration-critical / deployment-critical 风险门控，因此 `PASS WITH NOTES` 不降级为 FAIL。

## 任务完成度

| Task | 结果 | 证据 |
|---|---|---|
| task-01 调用计数脚本 | PASS WITH NOTES | `tests/manual/test_15e_llm_call_count.py` 存在，缺样本提示存在，mock 计数可运行；mock 未覆盖 `step4.call_llm` 记为 note |
| task-02 高置信度关键词直通 | PASS | `HIGH_CONFIDENCE_MIN_SCORE = 6`、`HIGH_CONFIDENCE_MARGIN = 3`、`high_confidence_keyword_category()`、`keyword-high-confidence` |
| task-03 批量涉华判断 | PASS | `LLM_BATCH_SIZE = 20`、`llm_is_china_related_batch()`、index JSON 校验、batch 失败回退单条 |
| task-04 批量栏目评分 | PASS | `score_signals_batch()`、`llm-batch` 标记、`_validate_signals()` 校验、单条/关键词 fallback |
| task-05 step7 并发异常回退 | PASS | `ThreadPoolExecutor` + `as_completed`，`future.result()` 外层 try/except，异常条目 `fallback_summarize()` |
| task-06 验收报告 | PASS | 本文件已写入，包含调用次数、fallback、测试和风险结论 |

完成率：6/6。

## 设计一致性

| 设计要求 | 结果 | 证据 |
|---|---|---|
| 高置信关键词直通阈值 6/3 | PASS | `step4.py:28-29`, `step4.py:278-287`, `step4.py:477-484` |
| 批量涉华判断按 20 条分批 | PASS | `step4.py:31`, `step4.py:121-170` |
| 批量 JSON 使用 index，不用 title 作 key | PASS | `step4.py:130-132`, `step4.py:146-156` |
| 批量涉华失败回退单条 | PASS | `step4.py:162-170` |
| 批量栏目评分按 20 条分批 | PASS | `step4.py:401-449` |
| 批量评分复用 `_validate_signals()` | PASS | `step4.py:435-440` |
| 批量评分失败回退单条/关键词 | PASS | `step4.py:500-534` |
| `step7.py` 保持 index 顺序 | PASS | `step7.py:205-221` |
| `step7.py` 单 worker 异常不影响整步 | PASS | `step7.py:208-216` |
| 输出 Markdown 契约不变 | PASS | 未修改 `write_output()` / `3新闻_概述.md` 格式写入逻辑 |
| 不新增运行步骤 | PASS | 保留现有 `step4.py` / `step7.py` CLI；新增手工验证脚本不在生产流水线 |

偏差：`design.md` 文件变更清单列出 `llm_client.py` 为“修改/默认不修改”，实际未修改。非阻断文档表述偏差。

## 探针结果

- 未实现标记扫描：PASS，变更文件无 `尚未实现|TODO|FIXME|HACK|XXX` 命中。
- 关键词覆盖：PASS，`高置信`、`批量`、`涉华`、`栏目评分`、`fallback`、`并发`、`顺序` 均在 `step4.py`、`step7.py` 或测试脚本中有实现证据。
- 测试覆盖：PASS WITH NOTES，存在手工验证脚本与现有 pytest；缺专门覆盖 `column-score` batch 成功路径的持久化测试，已用 inline 探针补验证。
- 决策追踪覆盖：N/A，无 `decisions.md`。
- API Contract Parity：N/A，无 `.sillyspec/.runtime/contract-artifacts/`，项目无 `backend/` + `frontend/` 结构。

## 决策追踪矩阵

无 `decisions.md`，N/A。

## 测试结果

| 命令 | 结果 | 说明 |
|---|---|---|
| `python3 -m py_compile step4.py step7.py llm_client.py tests/manual/test_15e_llm_call_count.py` | PASS | 无输出，语法通过 |
| `pytest tests/test_archive_enrich.py tests/test_monthly_report.py tests/test_news_archive.py` | PASS | 75 passed |
| `python3 tests/manual/test_15e_llm_call_count.py --date 2026-06-30` | PASS WITH NOTES | exit 0；输出 fallback tracebacks，原因是 mock 未 patch `step4.call_llm`，不是生产路径结论 |
| inline batch success probe | PASS | 同时 patch `step4.call_llm` 与 `llm_client.call_llm`，结果 `china-relevance=4`、`column-score=7`、`total_call_llm=11`、`selected=10` |

补充探针输出：

```json
{"counts":{"china-relevance":4,"column-score":7},"total_call_llm":11,"classified_total":127,"selected_total":10,"non_empty_columns":1}
```

`total_call_llm=11 <= 30`，满足 Phase 15E 调用次数目标。

## 技术债务

- 0 个新增 TODO/FIXME/HACK/XXX。
- Warning：`tests/manual/test_15e_llm_call_count.py` 应后续修正 mock，同时 patch `step4.call_llm`，否则 `column-score` batch 成功路径计数不完整。
- Warning：真实 API key 缺失导致无法验证真实模型输出差异百分比。

## 变更风险等级

`change_risk_profile: unit-sufficient`

判定依据：本变更只修改本地 Python 流水线脚本与手工验证脚本，不涉及 API contract、DTO/client contract、daemon/backend 跨进程、session/lease/run 状态机、部署启动路径。无需 Runtime Evidence 门控。

## Runtime Evidence

N/A。风险等级为 `unit-sufficient`，不要求 daemon/backend/session 真实集成证据。

## 代码审查

总体评价：实现与 design.md 主体一致，fallback 边界完整，输出契约保持不变。

问题列表：

- P2 warning：计数脚本 mock 覆盖不完整，见“技术债务”。建议在后续修复脚本，使 `column-score` batch 成功路径无需 inline 探针即可稳定验证。
- P2 warning：真实 API diff 未验证。建议在配置真实 API key 后运行 `step4.py --date 2026-06-30 --dry-run` 并对比 `1新闻_链接.md` 分类差异。
- P2 warning：`score_signals_batch()` 失败时打印完整 traceback，mock/无 key 环境输出噪声较大；生产可接受但后续可改为摘要日志。

## 下一步

可进入归档：

```bash
sillyspec run archive --change "2026-07-05-phase-15e-llm-batching"
```
