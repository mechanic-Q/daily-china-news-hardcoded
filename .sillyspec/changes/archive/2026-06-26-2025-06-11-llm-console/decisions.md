---
author: lmr
created_at: 2026-06-24 18:35:00
stage: brainstorm
schema: decisions
---

# 决策记录

## D-001@v1: 9router provider 类型
- type: term
- status: accepted
- source: user
- question: 9router 是公开服务还是私有部署？
- answer: 私有/自建 router，base_url 待用户后补
- normalized_requirement: 代码中 base_url 必须从配置读取，不写死任何 URL（除非临时 placeholder + TODO 标记）
- impacts: [FR-1, llm-config]
- evidence: brainstorm step 6 用户答复

## D-002@v1: "low 模型" 含义
- type: term
- status: accepted
- source: user
- question: "low 模型" 指 9router 自定义档位还是某具体模型名？
- answer: 9router 自定义便宜档位（字符串如 "low" 或 "router-low"），具体值用户后补
- normalized_requirement: model 字符串必须可配置，默认值是 placeholder（"low"），不要硬编码具体模型名
- impacts: [FR-1, llm-config]
- evidence: brainstorm step 6 用户答复

## D-003@v1: 控制台形态
- type: architecture
- status: accepted
- source: user
- question: 是要 YAML 配置 / CLI / TUI / Web UI 哪种？
- answer: YAML/JSON 配置文件，最轻量方案
- normalized_requirement: 本次变更不实现 CLI / TUI / Web UI，仅产出一个可读 YAML 配置 + 加载模块
- impacts: [FR-2, FR-3]
- evidence: brainstorm step 6 用户答复

## D-004@v1: Key 管理策略
- type: compatibility
- status: accepted
- source: user
- question: 切到 9router 后旧 key 怎么处理？
- answer: 新增 NINEROUTER_API_KEY，旧的 MINIMAX_API_KEY / ZHIPU_API_KEY 保留以防回退
- normalized_requirement: .env 同时含 3 个 key；配置文件可指定每个调用点用哪个 provider；删除任一 key 不应导致默认配置加载失败
- impacts: [FR-4, env]
- evidence: brainstorm step 6 用户答复

## D-005@v1: 切换粒度
- type: architecture
- status: accepted
- source: user
- question: 3 处 LLM 调用是同一配置还是各自独立？
- answer: 一个全局默认 + 单点可 override
- normalized_requirement: YAML 结构 `default: {provider, model, ...}` + 可选 `overrides: {<call-site-id>: {...}}`，调用点用稳定 ID 标识（如 china-relevance / column-classify / summarize）
- impacts: [FR-1, FR-5, schema]
- evidence: brainstorm step 6 用户答复

## D-006@v1: 回退机制
- type: compatibility
- status: accepted
- source: user
- question: 旧 provider 保留是手动切回还是运行时自动 fallback？
- answer: yaml 手动切回（改字段），不要运行时自动 fallback
- normalized_requirement: 代码中不实现 try-primary-then-secondary 逻辑；切换 provider 仅靠改 yaml；这简化了实现也避免双倍 LLM 费用
- impacts: [FR-1, NFR-simplicity]
- evidence: brainstorm step 6 用户答复

## D-007@v1: 异常可见性
- type: risk
- status: accepted
- source: user
- question: LLM 失败时仍按现有 except Exception 静默吞掉还是改？
- answer: 额外加 print(traceback) 提高可见性，但仍走 fallback（不重抛）
- normalized_requirement: classifier 和 summarizer 的 LLM 调用 except 块新增 `import traceback; traceback.print_exc()` 或等价 print；fallback 行为不变；保证旧的"流水线不中断"语义
- impacts: [FR-1, classifier, summarizer]
- evidence: brainstorm step 7 用户答复

## D-009@v1: 统一管理（无 vision 预留）
- type: architecture
- status: accepted
- source: user
- question: 3 处 LLM 调用是否要按 profile（text/vision）分组管理？
- answer: 当前 3 处全是纯文本调用，无视觉需求；统一一个全局 provider+model 即可，视觉调用未来真要加再扩 schema
- normalized_requirement: yaml 顶层平铺 `provider` + `model`，不引入 profiles 抽象；call_sites 只记录 temperature/max_tokens/timeout 这类调用点特有参数
- impacts: [FR-1, FR-2, schema]
- evidence: brainstorm step 9 用户答复
- supersedes: D-008@v1 中的 profiles 结构（D-008@v1 的方案 B 仍生效，仅 yaml schema 简化）

## D-010@v1: Key 缺失策略 — 宽松模式
- type: architecture
- priority: P0
- status: accepted
- source: design-grill (X-008, X-010)
- question: load_config 是否校验 api_key_env 环境变量存在？
- answer: 宽松模式。load_config 只检 yaml 格式完整性，不检 key 存在性。call_llm 内部 key 缺失时 os.getenv 返回 None，OpenAI client 构造失败抛异常，call_llm 捕获后打印 traceback 并抛 LLMCallError。上游 except Exception 捕获 → 走 fallback
- normalized_requirement: load_config 不读 os.environ；call_llm 内 os.getenv(api_key_env) 返回 None 时抛 LLMCallError("Missing API key for <provider>: <env_var>")；上游 except 已存在，行为不变
- impacts: [FR-1, llm_client, load_config]
- supersedes: design.md §7.2 中 load_config 校验"api_key_env 对应的环境变量必须存在"的行
- evidence: design-grill X-008/X-010，用户确认宽松

## D-011@v1: Temperature 统一为 0.7
- type: architecture
- priority: P2
- status: accepted
- source: design-grill (X-002)
- question: 迁移时 temperature 按现有值（0.1 / 0 / 0.3）还是统一？
- answer: 统一为 0.7（3 个调用点都用 0.7）
- normalized_requirement: llm.yaml 中 china-relevance/column-classify/summarize 的 temperature 字段全改为 0.7
- impacts: [FR-1, FR-2, llm.yaml call_sites]
- evidence: design-grill X-002，用户确认 0.7

## 剩余风险

1. **base_url + model 字符串占位符**：用户未给，代码先放 placeholder `https://9router.example.com/v1` 和 `"low"`，加 TODO 注释。用户后续填入即可，但若忘记填，运行时会失败，由 D-007 的 traceback 暴露
2. **MiniMax m2.7 历史 known-issue**：本次顺便修正 — 切换到 9router 后 step4.py:86 的涉华兜底改用 9router low，不再需要 MiniMax，旧 model 字符串问题随之消失
3. **无单元测试**：变更后只能 `--dry-run` 验证，需在 verify 阶段补一个最小烟雾测试（直接跑 step4/step7 单步小数据集）