---
author: lmr
created_at: 2026-06-24 18:40:00
stage: brainstorm
---

# 方案选择

## D-008@v1: 实现架构方案
- type: architecture
- status: accepted
- source: user
- question: 2 种方案选哪个（A 极简 / B 抽象层 / C 抽象层+CLI）？
- answer: 方案 B + 未来预留 vision profile
- normalized_requirement: 新增 llm_client.py 抽象层 + llm.yaml 用 profiles/call_sites 结构，未来视觉调用只需加 profile 条目
- impacts: [FR-1..FR-5, llm-client, llm-config]
- evidence: brainstorm step 8 用户选择

## YAML schema 结构（已确认）
```yaml
profiles:
  text:
    provider: 9router      # provider 名字，映射到 providers 段
    model: low              # 具体 model 字符串
  # vision:                # 未来预留
  #   provider: ...
  #   model: ...

providers:
  9router:
    base_url: https://9router.example.com/v1  # placeholder
    api_key_env: NINEROUTER_API_KEY
  zhipu:
    base_url: https://open.bigmodel.cn/api/paas/v4/
    api_key_env: ZHIPU_API_KEY
  minimax:
    base_url: https://api.minimax.chat/v1
    api_key_env: MINIMAX_API_KEY

call_sites:
  china-relevance:
    profile: text
    temperature: 0
    max_tokens: 10
    timeout: 15
  column-classify:
    profile: text
    temperature: 0
    max_tokens: 10
    timeout: 15
  summarize:
    profile: text
    temperature: 0.3
    max_tokens: 300
    timeout: 30
```