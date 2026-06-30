---
author: lmr
created_at: 2026-06-30 01:29:41
change: 2026-06-29-perf-optimize
doc_type: proposal
---

# Proposal

## 动机

Daily 当前流水线已具备采集、分类、正文提取、摘要和渲染能力，但 Phase 12 性能量化显示主要耗时集中在 `step6.py` 正文提取和 `step7.py` 摘要生成。两者都按文章逐条串行执行，而每篇文章之间没有数据依赖，适合做低风险的文章级并发。

本变更目标是在不改变日报产物语义的前提下，缩短 `step6 + step7` 总耗时。

## 关键问题

### 1. step6 正文提取串行等待

`step6.py` 对 `1新闻_链接.md` 中的文章逐条调用 `fetch_and_extract()`。正文抓取主要等待网络、HTML 解析和部分 chromium 子进程，串行执行会把每篇等待时间累加。

### 2. step7 LLM 摘要串行等待

`step7.py` 对每篇文章逐条调用 `llm_summarize()`，单篇内部最多 3 次重试，还在成功项之间 sleep。文章之间没有共享状态，串行调用导致 LLM 网络等待累加。

### 3. 不能牺牲稳定产物

下游 `step8.py` 依赖 `3新闻_概述.md` 栏目顺序和 Markdown 格式；`run_all.sh` 依赖每个 step 的 CLI 和退出语义。本期必须把性能优化限制在内部实现，不改变文件接力契约。

## 变更范围

- 修改 `step6.py`：在 `run()` 中使用 `ThreadPoolExecutor` 并发执行单篇正文提取。
- 修改 `step7.py`：在 `run()` 中使用 `ThreadPoolExecutor` 并发执行单篇摘要生成。
- 新增保守并发上限常量：`STEP6_MAX_WORKERS`、`STEP7_MAX_WORKERS`。
- 新增单篇 worker helper，用 index 保持输出顺序。
- 保留现有失败语义：正文失败写错误占位，摘要失败走规则 fallback。
- 用 `perf_profile.py`、单步 dry-run、语法检查验证变更。

## 不在范围内（显式清单）

- 不优化 `step1_3.py` 信源抓取。
- 不做 chromium 进程复用。
- 不修改 `step4.py` 栏目算法或 LLM 分类逻辑。
- 不修改 `step8.py` HTML/PNG 渲染。
- 不修改 `run_all.sh` CLI、step 顺序或退出语义。
- 不引入 asyncio 重构、Playwright、Selenium 或新第三方依赖。
- 不改变 `1新闻_链接.md`、`2新闻_已审核.md`、`3新闻_概述.md` 格式。

## 成功标准（可验证）

- `python3 -m py_compile step6.py step7.py` 通过。
- `python3 step6.py --date YYYY-MM-DD --dry-run` 可运行，输出仍按原文章顺序展示。
- `python3 step7.py --date YYYY-MM-DD --dry-run` 可运行，输出仍按 `COLUMN_ORDER` 分栏目。
- `2新闻_已审核.md` 与 `3新闻_概述.md` 的 Markdown 契约不变。
- 单篇正文失败不阻断全局，仍写 `[正文提取失败: ...]`。
- 单篇摘要失败不阻断全局，仍走 `fallback_summarize()`。
- `python3 perf_profile.py --date YYYY-MM-DD --dry-run` 可用于对比，`step6 + step7` 耗时应明显低于串行基线；若外部网络/LLM 波动，应在验证记录中说明。
