---
author: lmr
created_at: 2026-06-24 18:30:00
stage: brainstorm
---

# 用户需求确认记录

## 回答汇总

1. **9router 类型**：私有/自建 router，base_url 待补
2. **low 模型含义**：9router 自定义便宜档位（字符串如 "low" 或 "router-low"）
3. **控制台形态**：YAML/JSON 配置文件，不要 Web UI / CLI 工具 / TUI
4. **API key 策略**：新增 `NINEROUTER_API_KEY`，旧的 `MINIMAX_API_KEY` / `ZHIPU_API_KEY` 保留
5. **切换粒度**：一个默认配置 + 单个调用点可 override（推荐）
6. **回退机制**：yaml 手动切回（改 provider 字段），不要运行时自动 fallback

## 设计约束

- 最轻量方案：纯 YAML 配置文件，不改代码即可换 provider
- 3 处 LLM 调用统一到一个抽象层
- config 默认指向 9router low，但保留 Zhipu/MiniMax 作为可选 provider
- 代码不用 import 新 SDK（沿用 openai SDK + base_url 模式）