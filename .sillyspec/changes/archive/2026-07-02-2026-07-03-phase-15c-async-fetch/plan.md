---
author: lmr
created_at: 2026-07-02 14:35:15
schema_version: 1
doc_type: plan
change_id: 2026-07-03-phase-15c-async-fetch
plan_level: light
---

# 轻量计划：Phase 15C · async fetch performance

## 来源

来自 design.md：在 step1_3.py 内部新增受控并发（httpx.AsyncClient + Semaphore(5) + tenacity retry），改造 CAS/RMRB 批量抓取，实现 static-first Chromium fallback。保持 0新闻_粗筛.md 格式、SOURCES/fetcher 签名、run_all.sh 不变。

## 范围

- `requirements.txt`：新增 `httpx`、`tenacity`
- `step1_3.py` / collector 模块：受控并发批量 HTTP + static-first fallback
- `tests/manual/test_15c_step1_timing.py`：手动 timing baseline

## Wave 1
- [x] task-01: 新增 httpx/tenacity 依赖声明到 requirements.txt（覆盖：FR-01, FR-02, D-001@v1）

## Wave 2
- [x] task-02: 新增 timing baseline 手动脚本 tests/manual/test_15c_step1_timing.py（覆盖：FR-04, D-004@v1）

## Wave 3
- [x] task-03: 在 step1_3.py 中实现 _async_fetch_many helper（httpx + Semaphore(5) + tenacity retry 3 次）（覆盖：FR-01, FR-02, D-001@v1, D-002@v1, D-003@v1）

## Wave 4
- [x] task-04: 改造 fetch_cas 和 fetch_rmrb 使用 _async_fetch_many 并发抓取标题（覆盖：FR-01, D-001@v1, D-002@v1）

## Wave 5
- [x] task-05: 实现 static-first Chromium fallback（修改 fetch_home_html 等，静态空/短才 fallback）（覆盖：FR-03, D-001@v1）

## Wave 6
- [x] task-06: 验证：py_compile + dry-run 格式对比 + timing 对比（覆盖：全部）

## 验收

- AC-01: `python3 -c "import httpx; import tenacity"` 成功。
- AC-02: timing baseline 脚本可运行，输出 15A 与 15C 耗时对比。
- AC-03: `python3 step1_3.py --date YYYY-MM-DD --dry-run` 输出仍含 `## {name}（通过N条 / 淘汰N条 / 汇总N条 → 状态）`、`工具:`、`- [{date}] title | url ✅`、`（淘汰）` 格式。
- AC-04: SOURCES 列表结构、各 fetch_* 函数签名、run_all.sh 无变更。
- AC-05: fetch_cas/fetch_rmrb 内部 HTTP 请求并发 ≤5。

## 覆盖矩阵

| ID | 覆盖任务 | 验收证据 |
|---|---|---|
| D-001@v1 | task-01, task-03, task-04, task-05, task-06 | AC-01, AC-03, AC-04 |
| D-002@v1 | task-03, task-04 | AC-01 |
| D-003@v1 | task-03, task-06 | AC-03 |
| D-004@v1 | task-02, task-06 | AC-02 |

## 自检

- [x] plan_level: light
- [x] 有来源、范围、任务列表、验收标准
- [x] 来源直接引用已有文档
- [x] 任务使用 checkbox 格式
- [x] 验收标准具体可验证
- [x] D-001@v1 到 D-004@v1 在覆盖矩阵中可追踪
- [x] 无 Mermaid/估时/风险分析/实现细节
- [x] 与 design.md 文件变更清单一致
