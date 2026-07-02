---
author: lmr
created_at: 2026-07-01 18:49:10
schema_version: 1
doc_type: proposal
change_id: 2026-07-03-phase-15c-async-fetch
phase: 15c
depends_on:
  - 2026-07-01-phase-15a-common-lib
status: brainstorm-skeleton
---

# Proposal · Phase 15C · async fetch performance

## 动机

当前 `step1_3.py` 除 HTTP 200 验证外，大部分抓取仍是同步 `urllib`。人民日报版面、CAS 标题抓取、单页面标题 fallback 都是串行网络请求；Chromium fallback 也可能过早触发。完整采集阶段耗时高，且失败重试策略分散。

Phase 15C 目标是在不改变外部运行命令和输出格式的前提下，把采集阶段改为受控并发 + retry，并让静态 HTML 优先，Chromium 作为真正 fallback。

## 关键问题

1. 串行 urllib 请求造成 step1_3 耗时过长。
2. 无统一 retry/backoff，临时网络抖动会导致信源 0 条。
3. 央视/军事等页面可能静态已够用，但当前部分路径直接 Chromium，浪费冷启动时间。

## 变更范围

- `requirements.txt` 新增 `httpx`、`tenacity`
- `step1_3.py` 引入 `httpx.AsyncClient` 与 `asyncio.Semaphore(5)`
- 人民日报版面与正文标题抓取改并发
- CAS 文章标题抓取改并发
- 静态抓取失败或正文不足时才 Chromium fallback
- 采集输出 `0新闻_粗筛.md` 格式不变

## 不在范围内

- 不改正文提取算法（15B）
- 不改 LLM 分类/摘要（15E）
- 不加信源健康持久化（15D）
- 不改 `run_all.sh`

## 成功标准

- `time python3 step1_3.py --date 2026-06-30 --dry-run` 相比 15A 基线降低 ≥40%
- 单信源并发上限 5
- 网络失败自动 retry 3 次（带 backoff + jitter）
- 采集输出格式与旧版一致
