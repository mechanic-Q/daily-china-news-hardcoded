---
author: lmr
created_at: 2026-07-01 18:49:10
schema_version: 1
doc_type: design
change_id: 2026-07-03-phase-15c-async-fetch
phase: 15c
status: brainstorm-skeleton
---

# Design · Phase 15C · async fetch performance

## 总体方案

- 保持 `SOURCES` 与各信源 fetcher 对外返回结构不变：`list[dict{url,title}]`
- 内部新增 async HTTP layer：`httpx.AsyncClient(verify=False, timeout=...)`
- 每信源内部并发上限 `Semaphore(5)`
- 对失败请求使用 `tenacity` retry 3 次，指数退避 + jitter
- 对需要 Chromium 的路径采用 static-first 策略：先 `fetch_html_static`，若空/过短/缺关键 selector 再 `chromium_dom`

## 文件变更清单

| 操作 | 文件 |
|---|---|
| 修改 | `requirements.txt` |
| 修改 | `step1_3.py` |
| 修改 | `daily/http.py`（如需 async helper，正式 brainstorm 确认） |
| 新增 | `tests/manual/test_15c_step1_timing.py` |

## 兼容策略

- CLI 不变：`python3 step1_3.py --date YYYY-MM-DD [--dry-run]`
- `0新闻_粗筛.md` Markdown 格式不变
- 若 async fetcher 异常，单信源失败不影响其他信源（沿用现有 try/except）

## 风险

| 风险 | 应对 |
|---|---|
| 并发请求导致被限流 | Semaphore(5) + User-Agent + backoff |
| 输出顺序因并发改变 | 在写出前按原发现顺序稳定排序或保留 gather 输入顺序 |
| httpx 与 urllib 行为差异 | 先只改批量标题抓取路径；信源入口逐步迁移 |

## 待正式 brainstorm 完善

- async helper 放 `daily/http.py` 还是留 `step1_3.py`
- 输出顺序稳定策略
- timing baseline 采集方法
