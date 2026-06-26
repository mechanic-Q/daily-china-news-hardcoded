---
schema_version: 1
doc_type: module-card
module_id: llm-client
author: lmr
created_at: 2026-06-26 22:30:00
---

# llm-client

## 定位
- 负责：LLM 配置加载、客户端工厂、一站式 call_llm 封装
- 不负责：业务逻辑（classifier/summarizer 职责）、信源采集（collector）、正文提取（extractor）

## 契约摘要
- 输入：`llm.yaml` 配置文件（手工维护）
- 输出：`call_llm(call_site_id, messages)` → str（LLM 返回文本）
- `load_config()` → Dict（配置缓存，lru_cache）
- `get_client(call_site_id)` → (OpenAI client, model, kwargs)
- 校验：ConfigError（结构性问题）、LLMCallError（运行时错误）

## 关键逻辑
- YAML 4 段结构：provider / model / providers / call_sites
- provider 切换：改顶层 provider + model 二字段即可，不改代码
- api_key_env → os.environ.get()，缺失不阻塞启动（D-010）
- 自定义 base_url，兼容 OpenAI SDK 协议

## 注意事项
- ConfigError 在 step 启动时抛出，不追溯
- LLMCallError 带 traceback，上游用 fallback 处理
- `load_config()` 使用 lru_cache，修改 yaml 需重启进程

## 人工备注

<!-- MANUAL_NOTES_START -->

<!-- MANUAL_NOTES_END -->
