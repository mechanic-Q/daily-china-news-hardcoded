---
author: lmr
created_at: 2026-07-01 18:49:10
schema_version: 1
doc_type: requirements
change_id: 2026-07-05-phase-15e-llm-batching
phase: 15e
status: brainstorm-skeleton
---

# Requirements · Phase 15E · LLM batching

## 角色

| 角色 | 说明 |
|---|---|
| 运行者 | 执行分类/摘要流水线 |
| 维护者 | 调整分类阈值与 fallback |
| 测试者 | 比较 LLM 调用次数与输出差异 |

## 功能需求

### FR-01: 高置信度关键词直通

Given 标题关键词得分高且领先第二名足够多  
When `step4.py` 分类  
Then 不调用 LLM，直接分配栏目

### FR-02: 批量涉华判断

Given 多条来源可信但标题未命中涉华关键词  
When 需要 LLM 判断涉华  
Then 按批次调用 LLM 并解析 JSON

### FR-03: 批量栏目判断

Given 多条低置信度标题需要 LLM 分类  
When `step4.py` 进入 LLM 路径  
Then 批量调用 LLM，并为每条返回分类/评分信号

### FR-04: 批处理失败 fallback

Given 批处理 LLM 返回 JSON 解析失败或缺项  
When `step4.py` 处理该批次  
Then fallback 到现有单条分类逻辑

### FR-05: 摘要并发

Given 10 条新闻需要摘要  
When `step7.py` 生成摘要  
Then 并发执行多个 `llm_summarize`，并保持输出顺序与 `1新闻_链接.md` 一致

## 非功能需求

- `step4` 单日 LLM 调用次数 ≤30
- 分类输出差异 ≤5% 或人工确认可接受
- 无新增运行步骤
