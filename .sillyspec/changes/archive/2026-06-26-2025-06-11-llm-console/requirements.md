---
author: lmr
created_at: 2026-06-24 19:05:00
change: 2025-06-11-llm-console
stage: brainstorm
doc_type: requirements
---

# Requirements — Daily LLM 配置统一管理

## 角色

| 角色 | 说明 |
|------|------|
| 项目维护者（用户 lmr） | 唯一用户。改 yaml 切换 provider，跑 `./run_all.sh` 生成每日报纸 |
| 流水线进程 | `python3 stepN.py` 自动调用 `llm_client.py`，无人工干预 |

## 功能需求

### FR-01: 集中配置加载

**覆盖决策**：D-001@v1, D-002@v1, D-008@v1, D-009@v1, D-010@v1

**Given** 项目根目录存在 `llm.yaml`，含 `provider` / `model` / `providers` / `call_sites` 4 段
**When** 进程首次 `import llm_client` 并调用 `load_config()`
**Then** 返回 dict，第二次调用走 lru_cache 不重读文件

**Given** `llm.yaml` 顶层 `provider` 字段不在 `providers` 段定义
**When** `load_config()` 被调用
**Then** 抛 `ConfigError("provider 'xxx' not defined in providers")`，stderr 含明确信息

**Given** `llm.yaml` 缺少 `call_sites.china-relevance` 段
**When** `load_config()` 被调用
**Then** 抛 `ConfigError("call_site 'china-relevance' missing in llm.yaml")`

**Given** `llm.yaml` 顶层 `provider: 9router` 但 `NINEROUTER_API_KEY` 环境变量未设
**When** `load_config()` 被调用
**Then** 不报错（D-010 宽松校验，key 缺失留到调用时再说）

### FR-02: 客户端工厂

**覆盖决策**：D-005@v1, D-009@v1

**Given** `llm.yaml` 顶层 `provider: 9router`, `model: low`，call_sites.summarize 含 temperature=0.7, max_tokens=300, timeout=30
**When** 调用 `get_client("summarize")`
**Then** 返回 `(OpenAI 实例, "low", {"temperature": 0.7, "max_tokens": 300, "timeout": 30})`，OpenAI 实例的 base_url 是 9router 的

**Given** call_site_id 不在 `call_sites` 段中
**When** 调用 `get_client("unknown-id")`
**Then** 抛 `ConfigError("call_site 'unknown-id' not defined")`

### FR-03: 一站式调用 + 异常可见

**覆盖决策**：D-007@v1, D-010@v1

**Given** `llm.yaml` 配置合法，`NINEROUTER_API_KEY` 已设
**When** 调用 `call_llm("summarize", messages=[{"role": "user", "content": "..."}])`
**Then** 返回 LLM 响应字符串（`response.choices[0].message.content`）

**Given** `NINEROUTER_API_KEY` 未设
**When** 调用 `call_llm("summarize", messages=[...])`
**Then** 抛 `LLMCallError("Missing API key for 9router: NINEROUTER_API_KEY")`，stderr 含 traceback

**Given** 9router base_url 不可达（网络错误）
**When** 调用 `call_llm("summarize", messages=[...])`
**Then** 抛 `LLMCallError`，stderr 含 openai SDK 抛出的具体异常 traceback（D-007）

**Given** 调用者传 override 参数（如 `temperature=0.1`）
**When** 调用 `call_llm("summarize", messages=[...], temperature=0.1)`
**Then** override 优先于 yaml 默认值

### FR-04: step4.py 2 处 LLM 调用替换

**覆盖决策**：D-005@v1, D-007@v1, D-008@v1, D-011@v1

**Given** `step4.py:79-95 llm_is_china_related(title)` 函数
**When** 替换为 `call_llm("china-relevance", messages=[...])`
**Then**
- 不再 `import openai` 或构造 `OpenAI(...)`，仅 `from llm_client import call_llm, LLMCallError`
- 不读 `MINIMAX_API_KEY`（key 由配置层 + call_llm 处理）
- 保留原 prompt 文本和"是/否"解析逻辑
- except 块兜底返回 False（保留现有 fallback 语义）

**Given** `step4.py:209-249 llm_classify_single(articles)` 函数
**When** 替换为 `call_llm("column-classify", messages=[...])`
**Then**
- 不再独立构造 OpenAI client
- 不读 `ZHIPU_API_KEY`
- 保留原 prompt + `<think>` 剥离 + 栏目匹配解析
- except 块兜底跳过该篇（保留现有 fallback）

### FR-05: step7.py 1 处 LLM 调用替换 + 兼容外层重试

**覆盖决策**：D-005@v1, D-007@v1, D-008@v1, D-011@v1, R-08

**Given** `step7.py:150-192 llm_summarize(title, body)` 含 `for attempt in range(3)` 重试循环
**When** 替换内层 `client.chat.completions.create(...)` 为 `call_llm("summarize", messages=[...])`
**Then**
- 外层 `for attempt in range(3)` 循环保留不动
- `_why_invalid` / `RETRY_PROMPTS` / `failures` set 逻辑保留
- `call_llm` 抛 `LLMCallError` 被现有 `except Exception as e` 捕获，打印 `print(f"  ⚠ API 异常: {e}")` 后进入下次 attempt
- 3 次都失败返回 None，上游走 `fallback_summarize`

### FR-06: 切回旧 provider

**覆盖决策**：D-004@v1, D-006@v1

**Given** 当前 yaml 是 `provider: 9router`, `model: low`
**When** 用户手工把 yaml 改为 `provider: zhipu`, `model: glm-4-flash`，确认 `ZHIPU_API_KEY` 在 .env
**Then** 重跑 `./run_all.sh --date 2026-06-24` 全部 step 正常完成；3 处 LLM 调用都用 Zhipu

**Given** 改完 yaml 但旧进程仍在运行
**When** 同一进程内再次调用 `load_config()`
**Then** 走 lru_cache 返回旧值（不会热生效）；新 step 进程才会读到新 yaml（R-07 已记录）

## 非功能需求

- **兼容性**：3 处 LLM 调用的输入/输出契约不变（输入仍是 title/body 字符串，输出仍是 LLM 返回的中文文本），上游 step 无感
- **可回退**：仅改 yaml 一行即可切回 Zhipu/MiniMax（D-006）
- **可测试**：所有验收条件可用 `--dry-run` + 小日期数据集验证（无单元测试框架但可手测）
- **简洁性**：抽象层 < 150 行，调用点改动 ≤ 10 行/处
- **不引入新 SDK**：仅 `openai` + `PyYAML`，两者都是成熟广用包

## 决策覆盖矩阵

| 决策 ID | 覆盖的 FR | 说明 |
|---------|-----------|------|
| D-001@v1 | FR-01 | 9router 私有，base_url 在 yaml 中占位待补 |
| D-002@v1 | FR-01 | "low" 字符串可配置，不硬编码 |
| D-003@v1 | （非目标） | 仅 YAML，不做 CLI/TUI/Web |
| D-004@v1 | FR-06 | 旧 key 保留，应急 provider 可用 |
| D-005@v1 | FR-02, FR-04, FR-05 | call_site 级别参数（temperature/max_tokens/timeout）独立配置 |
| D-006@v1 | FR-06 | 手动切回，无运行时 fallback |
| D-007@v1 | FR-03, FR-04, FR-05 | LLM 异常打 traceback，保留 fallback |
| D-008@v1 | FR-01, FR-02, FR-03 | 抽象层方案 B |
| D-009@v1 | FR-01 | 统一管理，yaml 顶层平铺 |
| D-010@v1 | FR-01, FR-03 | Key 宽松校验 |
| D-011@v1 | FR-02, FR-04, FR-05 | temperature 统一 0.7 |

全部 11 条 D-xxx@v1 都有 FR 覆盖。无遗漏。