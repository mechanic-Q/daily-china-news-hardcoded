---
author: lmr
created_at: 2026-07-04 00:23:08
---

# Proposal

## 动机

修复 Step4 在 9router `model: low` 下的 LLM 空响应与栏目评分失效问题。当前 `china-relevance` 和 `column-score` 使用冗长 JSON 输出，`low` 模型会把 token 消耗在 `reasoning_content`，导致 `message.content` 为空或截断。结果是 2026-07-03 当日归档全部退化为 `keyword-fallback`，`signals=null`，相关性、重要性、时效性评分没有真正生效。

## 关键问题

1. 现有 JSON 协议输出过长：每条评分重复 9 个 emoji 栏目 key，batch 越大越容易截断。
2. 现有 `llm_client.call_llm()` 只返回 `message.content`，对空 content 缺少结构化诊断，解析层只能看到 `empty LLM response`。
3. 现有 fallback 保住了流程不中断，但掩盖了 LLM 评分整体失效，导致最终精选长期退化为关键词兜底。

## 变更范围

1. Step4 涉华 batch 主路径改为位串协议：每位对应输入 batch 的一条标题。
2. Step4 栏目评分主路径改为矩阵协议：`index|9 relevance|importance|timeliness`。
3. parser 严格校验紧凑输出，并还原现有 `signals` dict。
4. `low` 模型调用传入 `reasoning_effort="none"`，并使用 `max_tokens=262144` 输出上限。
5. `llm_client` 对空 content fail-fast，并记录 `finish_reason/content_len/reasoning_len`。
6. 增加 parser、LLM 空响应诊断、batch mock 端到端测试。

## 不在范围内（显式清单）

- 不修改 `aggregate_scores()`、`assign_category()`、`priority_score()` 的算法语义。
- 不修改 `COLUMN_ORDER` 或栏目定义。
- 不修改 `news_archive.py`、`monthly_report.py` 数据结构。
- 不迁移历史归档记录。
- 不重写 step1/step6/step7/step8 流水线。

## 成功标准（可验证）

- `tests/test_step4.py` 覆盖位串 parser、矩阵 parser、signals 还原。
- `tests/test_llm_client.py` 覆盖空 content 诊断与 `LLMCallError`。
- mock batch 端到端测试证明紧凑协议能进入现有 `aggregate_scores()` / `assign_category()` 流程。
- `python3 step4.py --date 2026-07-03 --dry-run` 不再出现 `empty LLM response`。
- dry-run 中 Step4 对非高置信关键词候选能产出非空 `signals`，`score_source` 不再全部是 `keyword-fallback`。
