---
author: lmr
created_at: 2026-06-24 19:05:00
change: 2025-06-11-llm-console
stage: brainstorm
doc_type: proposal
---

# Proposal — Daily 项目 LLM 调用统一管理

## 动机

把 Daily 项目中 3 处分散的 LLM 调用集中到一个 YAML 配置文件 + 一个 `llm_client.py` 抽象层，统一切换到 9router low 模型。让"哪个调用点用哪个模型"一眼可见、一键可切。

## 关键问题

为什么现有方案不够：

1. **配置分散且硬编码**：`step4.py:86-88` 用 MiniMax `minimax-m2.7`，`step4.py:225` 和 `step7.py:159` 用 Zhipu `glm-4-flash`，model 字符串、base_url、api_key 名称全部硬编码在调用点。切换 provider 要逐文件改 5+ 处常量。

2. **配置不可视**：当前要回答"摘要用什么模型"必须 grep 源码。无法快速看清"调用点 → provider/model"映射关系。

3. **失败黑盒**：3 处都用宽泛 `except Exception` 静默吞掉异常，运行时 LLM 调用失败的原因（key 错、网络断、model id 无效）无任何可见性。known-issue：`minimax-m2.7` 长期可能是无效 model id，但被静默无人发现。

## 变更范围

- 新增 `llm.yaml` —— LLM 配置单一真相
- 新增 `llm_client.py` —— 加载 + 校验 + 客户端工厂（load_config / get_client / call_llm 三函数）
- 新增 `requirements.txt` —— 锁定 Python 依赖
- 修改 `step4.py` 2 处 LLM 调用 → 改为 `call_llm("china-relevance", ...)` / `call_llm("column-classify", ...)`
- 修改 `step7.py` 1 处 LLM 调用 → 改为 `call_llm("summarize", ...)`，保留外层重试循环
- 修改 `.env`：追加 `NINEROUTER_API_KEY` 占位
- 修改 `CLAUDE.md` 的 LLM 调用点章节

## 不在范围内

- ❌ 不实现 CLI / TUI / Web UI 控制台（D-003 用户明确「只要 YAML」）
- ❌ 不实现运行时主备自动 fallback（D-006，简化实现）
- ❌ 不动 `step1_3.py` / `step6.py` / `step8.py` / `run_all.sh`（无 LLM 调用）
- ❌ 不重构 `_why_invalid` / `RETRY_PROMPTS` / `fallback_summarize` 算法
- ❌ 不引入 vision profile 预留结构（D-009，未来真要加再扩 schema）
- ❌ 不修复 BASE_DIR 硬编码（独立 known-issue，不打包）
- ❌ 不引入新 SDK（沿用 openai SDK + base_url 模式）

## 成功标准（可验证）

1. **配置可读**：`cat llm.yaml` 能一眼看到当前 provider / model / 3 个 call_sites 配置
2. **依赖完整**：`pip install -r requirements.txt` 不报错
3. **流水线跑通**：`python3 step4.py --dry-run --date 2026-06-24` 和 `python3 step7.py --dry-run --date 2026-06-24` 都不报错
4. **应急切回可用**：改 `llm.yaml` 顶层 `provider: zhipu`, `model: glm-4-flash` 重跑 step4 / step7 也成功
5. **异常可见**：故意写错 9router base_url → 控制台能看到 traceback + 走 fallback 完成流水线
6. **配置错误抛错**：故意把 yaml 顶层 `provider` 改成不存在的 `xxx` → 启动时抛 ConfigError，明确指出问题