---
plan_level: light
author: lmr
created_at: 2026-06-24 19:25:00
change: 2025-06-11-llm-console
---

# 轻量计划：Daily LLM 配置统一管理

## 来源

见 brainstorm 阶段产出：
- `proposal.md` — 动机 + 范围 + 6 条成功标准
- `design.md` — 12 节完整设计 + Grill 修订
- `requirements.md` — 6 个 FR + 11 条 D 覆盖矩阵
- `decisions.md` — 11 条 D-xxx@v1（D-001 ~ D-011，全 accepted）

## 范围

涉及 7 个文件：

| 操作 | 路径 | 来源任务 |
|------|------|---------|
| 新增 | `/mnt/e/Daily/llm.yaml` | task-01 |
| 新增 | `/mnt/e/Daily/llm_client.py` | task-02 |
| 新增 | `/mnt/e/Daily/requirements.txt` | task-03 |
| 修改 | `/mnt/e/Daily/.env` | task-04 |
| 修改 | `/mnt/e/Daily/step4.py` | task-05, task-06 |
| 修改 | `/mnt/e/Daily/step7.py` | task-07 |
| 修改 | `/mnt/e/Daily/CLAUDE.md` | task-08 |

涉及 3 个模块：**新增 llm-client** + **classifier** (step4) + **summarizer** (step7)

## Tasks

- [x] task-01: 编写 llm.yaml 配置（覆盖：FR-01, D-001@v1, D-002@v1, D-009@v1, D-011@v1）
- [x] task-02: 编写 llm_client.py 抽象层（覆盖：FR-01, FR-02, FR-03, D-005@v1, D-007@v1, D-008@v1, D-010@v1）
- [x] task-03: 编写 requirements.txt（覆盖：R-03 依赖锁定）
- [x] task-04: 追加 .env 新增 NINEROUTER_API_KEY 占位（覆盖：D-004@v1）
- [x] task-05: 改造 step4.py:llm_is_china_related 为 call_llm("china-relevance", ...)（覆盖：FR-04, D-007@v1）
- [x] task-06: 改造 step4.py:llm_classify_single 为 call_llm("column-classify", ...)（覆盖：FR-04, D-007@v1）
- [x] task-07: 改造 step7.py:llm_summarize 内层为 call_llm("summarize", ...)，保留外层重试循环（覆盖：FR-05, D-007@v1, R-08）
- [x] task-08: 更新 CLAUDE.md 的 LLM 调用点章节，指向 llm.yaml + llm_client.py（覆盖：项目知识维护）
- [x] task-09: 干跑验证 step4/step7 --dry-run 通过；切回 zhipu 重测通过（覆盖：成功标准 1-4, FR-06）
- [x] task-10: 异常路径验证 — 错配置抛 ConfigError；错 base_url 走 fallback 见 traceback（覆盖：成功标准 5-6, FR-01, FR-03, D-006@v1, D-003@v1）

## Wave 分组

### Wave 1（基础设施，无依赖 → 可并行）
- [x] task-01: 编写 llm.yaml 配置
- [x] task-03: 编写 requirements.txt
- [x] task-04: 追加 .env 新增 NINEROUTER_API_KEY 占位

### Wave 2（依赖 W1）
- [x] task-02: 编写 llm_client.py 抽象层

### Wave 3（依赖 W2 → 可并行）
- [x] task-05: 改造 step4.py:llm_is_china_related 为 call_llm("china-relevance", ...)
- [x] task-07: 改造 step7.py:llm_summarize 内层为 call_llm("summarize", ...)
- [x] task-08: 更新 CLAUDE.md 的 LLM 调用点章节

### Wave 4（依赖 W3 task-05，同文件 step4.py 需序列化）
- [x] task-06: 改造 step4.py:llm_classify_single 为 call_llm("column-classify", ...)

### Wave 5（依赖 W1~W4 全部完成）
- [x] task-09: 干跑验证 step4/step7 --dry-run 通过；切回 zhipu 重测

### Wave 6（依赖 W5）
- [x] task-10: 异常路径验证

## 关键路径

task-01 → task-02 → task-05 → task-06 → task-09 → task-10（6 Wave，最长链，决定最短交付周期）

## 执行顺序

W1(task-01/03/04 并行) → W2(task-02) → W3(task-05/07/08 并行) → W4(task-06) → W5(task-09) → W6(task-10)

## 验收

- [x] AC-01: `cat /mnt/e/Daily/llm.yaml` 输出含 provider/model/providers/call_sites 4 段，3 个 call_sites 全部 temperature=0.7
- [x] AC-02: `pip install -r /mnt/e/Daily/requirements.txt` 不报错
- [x] AC-03: `cd /mnt/e/Daily && python3 step4.py --dry-run --date 2026-06-25` 不抛异常，产出 1新闻_链接.md
- [x] AC-04: `cd /mnt/e/Daily && python3 step7.py --dry-run --date 2026-06-25` 不抛异常，产出 3新闻_概述.md
- [x] AC-05: 改 llm.yaml 顶层 `provider: zhipu`, `model: glm-4-flash` 重跑 step4 → 也成功
- [x] AC-06: 改 llm.yaml 顶层 `provider: xxx`（不存在 provider）重跑 → 启动时抛 ConfigError，stderr 含 "provider 'xxx' not defined"
- [x] AC-07: 改 llm.yaml 中 9router base_url 为不可达 URL 重跑 → step4/step7 看到 traceback 输出但 call_llm 抛 LLMCallError（step7 fallback 触发）
- [x] AC-08: step4.py / step7.py 中不再含 `from openai import OpenAI` / `OpenAI(base_url=...)` / `MINIMAX_API_KEY` / `ZHIPU_API_KEY` 等字面量（grep 验证）
- [x] AC-09: step7.py 中 `for attempt in range(3)` 重试循环 + `_why_invalid` + `RETRY_PROMPTS` + `fallback_summarize` 全部存在（业务逻辑保留）
- [x] AC-10: CLAUDE.md "LLM 调用点" 章节包含 llm.yaml 和 llm_client.py 的描述

## 覆盖矩阵

| ID | 覆盖任务 | 验收证据 |
|----|---------|---------|
| D-001@v1 | task-01 | AC-01 (yaml 含 9router base_url + TODO) |
| D-002@v1 | task-01 | AC-01 (yaml model: low) |
| D-003@v1 | task-10 | AC-06 (无 CLI，仅 YAML 错误反馈) |
| D-004@v1 | task-04 | AC-05 (旧 key 应急切回成功) |
| D-005@v1 | task-01, task-02 | AC-01 (call_sites 段 + get_client 返回 kwargs) |
| D-006@v1 | task-09 | AC-05 (yaml 手动切回，无运行时 fallback) |
| D-007@v1 | task-02, task-05, task-06, task-07 | AC-07 (traceback 可见) |
| D-008@v1 | task-02 | AC-08 (llm_client.py 抽象层存在) |
| D-009@v1 | task-01 | AC-01 (yaml 顶层平铺无 profiles) |
| D-010@v1 | task-02 | AC-07 (key 缺失走 fallback 不启动报错) |
| D-011@v1 | task-01 | AC-01 (temperature=0.7) |