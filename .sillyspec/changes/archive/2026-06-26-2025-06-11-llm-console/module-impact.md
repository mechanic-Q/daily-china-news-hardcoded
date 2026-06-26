---
author: lmr
created_at: 2026-06-26 22:30:00
change: 2025-06-11-llm-console
---

# 模块影响分析 — LLM 配置统一管理

## 影响矩阵

| 模块 | 影响类型 | 相关文件 | 更新内容摘要 | needs_review |
|------|----------|----------|-------------|-------------|
| llm-client（新增） | 新增 | llm_client.py | 新增 load_config/get_client/call_llm 抽象层 | false |
| llm-client（新增） | 新增 | llm.yaml | 新增 LLM 统一配置（provider/model/providers/call_sites） | false |
| llm-client（新增） | 新增 | requirements.txt | 新增 PyYAML 依赖 | false |
| classifier | 调用关系变更 | step4.py | llm_is_china_related + llm_classify_single 改用 call_llm | false |
| summarizer | 调用关系变更 | step7.py | llm_summarize 改用 call_llm | false |
| —（项目文档） | 文档变更 | CLAUDE.md | LLM 调用点章节更新，指向 llm.yaml + llm_client.py | false |

## 未匹配文件
- .env — 环境变量文件，全局配置

## 影响说明
1. **新增 llm-client 模块**：新建模块，不影响现有模块结构。
2. **classifier 模块**：LLM 调用方式从直接构造 OpenAI client 改为 call_llm，接口签名简化。业务逻辑（涉华三级回退、关键词加权、8栏目分类）不变。
3. **summarizer 模块**：LLM 调用方式从直接构造 OpenAI client 改为 call_llm，重试循环 + fallback_summarize 保留。
4. 模块间数据流（文件接力）不变。

## 建议操作
- 在 _module-map.yaml 中注册新模块 `llm-client`
- 更新已标记 needs_review 的 classifier/summarizer 状态（本轮已修复 LLM 调用点）
