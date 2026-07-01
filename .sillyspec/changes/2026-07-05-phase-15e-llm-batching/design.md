---
author: lmr
created_at: 2026-07-01 18:49:10
schema_version: 1
doc_type: design
change_id: 2026-07-05-phase-15e-llm-batching
phase: 15e
status: brainstorm-skeleton
---

# Design · Phase 15E · LLM batching

## 总体方案

### 1. step4 高置信度免 LLM

在 `score_all_categories(title)` 后计算：
- `best_score >= 6`
- `best_score - second_score >= 3`

满足则直接分栏，不调用 `score_signals`。

### 2. 批量涉华判断

对 `china_llm` 列表按 20 条分批 prompt：要求返回 JSON `{title: true/false}` 或 list of `{index,is_china_related}`。

JSON parse 失败 → fallback 到现有 `llm_is_china_related` 单条函数。

### 3. 批量栏目分类/评分

对需要 LLM 的低置信度标题按 20 条分批：
- 输入 index/title/source
- 输出 index/category/relevance/importance/timeliness（正式 brainstorm 决定是否保留完整 signals）

解析失败 → fallback 到现有 `score_signals` / `llm_classify_single`。

### 4. step7 摘要并发

保留 `llm_summarize(title, body)` 单条 API；新增并发 runner 包装：
- `concurrent.futures.ThreadPoolExecutor(max_workers=3)`
- 或 `asyncio.to_thread`

正式 brainstorm 决策并发上限。

## 文件变更清单

| 操作 | 文件 |
|---|---|
| 修改 | `step4.py` |
| 修改 | `step7.py` |
| 修改 | `llm_client.py`（可选，正式 brainstorm 决策） |
| 新增 | `tests/manual/test_15e_llm_call_count.py` |

## 风险

| 风险 | 应对 |
|---|---|
| 批处理 JSON 格式不稳定 | 严格 prompt + parse fallback 单条 |
| 批量与单条分类略有差异 | 输出对比报告，差异 ≤5% 或人工确认 |
| 并发触发 rate limit | max_workers 限制 + fallback 重试 |

## 待正式 brainstorm 完善

- 批处理输出 schema
- 高置信度阈值是否 6/3 固定
- 摘要并发 worker 数
