---
author: lmr
created_at: 2026-07-01 18:49:10
schema_version: 1
doc_type: proposal
change_id: 2026-07-05-phase-15e-llm-batching
phase: 15e
depends_on:
  - 2026-07-01-phase-15a-common-lib
status: brainstorm-skeleton
---

# Proposal · Phase 15E · LLM batching

## 动机

当前 `step4.py` 和 `step7.py` 的 LLM 调用以单条新闻为单位串行执行。分类阶段可能对 100+ 候选逐条 `score_signals` / `llm_is_china_related`，摘要阶段 10 条逐条调用并 sleep。该设计简单但成本高、耗时长。

Phase 15E 目标是在保持输出语义和运行步骤不变的前提下，把明显高置信度条目从 LLM 路径剥离，并把剩余低置信度条目做批处理，减少调用次数。

## 关键问题

1. `step4` LLM 调用次数 O(N)，最坏可达数百次。
2. 高置信度关键词命中的标题仍可能走 LLM，浪费 token。
3. `step7` 10 条摘要完全串行，存在天然并发空间。

## 变更范围

- `step4.py` 增加高置信度关键词直通规则
- `step4.py` 增加批量涉华判断 / 批量栏目评分或分类
- `step4.py` 保留单条 fallback
- `step7.py` 摘要调用并发化（具体用线程池还是 async wrapper 待正式 brainstorm）
- `llm_client.py` 如需增加 `call_llm_batch` / async wrapper，正式设计时确认

## 不在范围内

- 不改栏目定义（Phase 13 已处理）
- 不改正文提取（15B）
- 不改采集（15C）
- 不改变输出文件结构

## 成功标准

- `step4` LLM 调用次数 ≤30（以单日 2026-06-30 为基准）
- 分类结果与 15A baseline 差异 ≤5%（或人工确认差异合理）
- `step7` 摘要总耗时下降
- 批处理 JSON 解析失败时能 fallback 到单条调用
