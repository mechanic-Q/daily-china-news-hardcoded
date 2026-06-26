---
author: lmr
created_at: 2026-06-24 19:05:00
change: 2025-06-11-llm-console
stage: brainstorm
doc_type: tasks
note: 仅任务名，细节在 plan 阶段展开
---

# Tasks — Daily LLM 配置统一管理

## Phase 1：配置基础设施

### task-01: 编写 `llm.yaml`
- 路径：新增 `/mnt/e/Daily/llm.yaml`
- 覆盖：FR-01, D-001@v1, D-002@v1, D-009@v1, D-011@v1
- 注意：base_url 用占位 + TODO 注释

### task-02: 编写 `llm_client.py`
- 路径：新增 `/mnt/e/Daily/llm_client.py`
- 覆盖：FR-01, FR-02, FR-03, D-007@v1, D-008@v1, D-010@v1
- 含 `load_config` / `get_client` / `call_llm` / `ConfigError` / `LLMCallError`

### task-03: 编写 `requirements.txt`
- 路径：新增 `/mnt/e/Daily/requirements.txt`
- 覆盖：R-03（依赖锁定）
- 内容：openai, aiohttp, Pillow, python-dotenv, PyYAML

### task-04: 追加 `.env` 占位
- 路径：修改 `/mnt/e/Daily/.env`
- 覆盖：D-004@v1
- 加 `NINEROUTER_API_KEY=` 占位（用户后填）

## Phase 2：调用点替换

### task-05: 改造 `step4.py:llm_is_china_related`
- 路径：修改 `/mnt/e/Daily/step4.py`
- 覆盖：FR-04（涉华兜底），D-007@v1
- 删除直接 OpenAI 构造、`MINIMAX_API_KEY` 读取
- 用 `call_llm("china-relevance", ...)` 替代

### task-06: 改造 `step4.py:llm_classify_single`
- 路径：修改 `/mnt/e/Daily/step4.py`
- 覆盖：FR-04（栏目仲裁），D-007@v1
- 删除直接 OpenAI 构造、`ZHIPU_API_KEY` 读取
- 用 `call_llm("column-classify", ...)` 替代

### task-07: 改造 `step7.py:llm_summarize`
- 路径：修改 `/mnt/e/Daily/step7.py`
- 覆盖：FR-05（摘要），D-007@v1，R-08
- 内层 LLM 调用换 `call_llm("summarize", ...)`
- 外层 `for attempt in range(3)` 循环 + `_why_invalid` / `RETRY_PROMPTS` / `failures` 全部保留

## Phase 3：文档与验收

### task-08: 更新 `CLAUDE.md` LLM 章节
- 路径：修改 `/mnt/e/Daily/CLAUDE.md`
- 覆盖：项目知识维护
- 把"LLM 调用点（共 3 处）"章节改成指向 `llm.yaml` + `llm_client.py`

### task-09: 干跑验证（`--dry-run` 测试）
- 覆盖：成功标准 1-3
- 步骤：
  1. `pip install -r requirements.txt`
  2. `python3 step4.py --dry-run --date 2026-06-24` 不报错
  3. `python3 step7.py --dry-run --date 2026-06-24` 不报错
  4. yaml 改 `provider: zhipu`, `model: glm-4-flash` 重测一次

### task-10: 异常路径验证
- 覆盖：成功标准 5-6, FR-01, FR-03
- 步骤：
  1. yaml 写错 `provider: xxx` → 期望 ConfigError
  2. base_url 写错 → 期望看到 traceback 但走 fallback 完成流水线