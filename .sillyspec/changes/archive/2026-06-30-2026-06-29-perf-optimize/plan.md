---
author: lmr
created_at: 2026-06-30 02:47:34
change: 2026-06-29-perf-optimize
stage: plan
doc_type: plan
plan_level: light
---

# 轻量计划：Phase15 step6 + step7 并发优化

## 来源

引用 brainstorm 结论：Phase15 范围锁定为方案 B，只做 `step6.py` 文章正文提取并发 + `step7.py` LLM 摘要并发；实现方案选方案 A，使用 `ThreadPoolExecutor` 保守线程池；保持 `run_all.sh` CLI、文件接力 Markdown 格式、栏目顺序、HTML/PNG 产物语义、失败 fallback 语义不变。

## 范围

- `step6.py` / extractor：并发化正文提取，保持 `fetch_and_extract()` 签名与返回值不变。
- `step7.py` / summarizer：并发化摘要生成，保持 `parse_1news()`、`parse_2news()`、`llm_summarize()`、`fallback_summarize()` 外部行为不变。
- `.sillyspec/changes/2026-06-29-perf-optimize/*`：本次变更规范、计划和验证记录。

不修改：`step1_3.py`、`step4.py`、`step8.py`、`run_all.sh`、Markdown 文件契约、HTML/PNG 渲染语义。

## Tasks

### Wave 1（并行，无依赖）

- [x] task-01: 为 `step6.py` 新增并发常量与单篇正文提取 worker（覆盖：FR-01, FR-05, D-002@v1, D-004@v1）
- [x] task-03: 为 `step7.py` 新增并发常量与单篇摘要 worker（覆盖：FR-02, FR-05, D-002@v1, D-004@v1）

### Wave 2（依赖 Wave 1）

- [x] task-02: 改造 `step6.py run()` 使用线程池并保持输出顺序与失败占位（覆盖：FR-01, FR-04, D-001@v1, D-003@v1）
- [x] task-04: 改造 `step7.py run()` 使用线程池并保持栏目顺序与 fallback 语义（覆盖：FR-02, FR-04, D-001@v1, D-003@v1）

### Wave 3（依赖 Wave 2）

- [x] task-05: 验证 step6/step7 语法、dry-run、Markdown 契约与失败语义（覆盖：FR-03, FR-04, FR-05）

### Wave 4（依赖 Wave 3）

- [x] task-06: 使用 `perf_profile.py` 记录前后性能对比并写验证结论（覆盖：FR-06, D-001@v1）

## 验收

- AC-01: `python3 -m py_compile step6.py step7.py` 通过。
- AC-02: `python3 step6.py --date YYYY-MM-DD --dry-run` 可运行，预览输出保持输入文章顺序。
- AC-03: `python3 step7.py --date YYYY-MM-DD --dry-run` 可运行，预览输出保持 `COLUMN_ORDER` 栏目顺序。
- AC-04: `2新闻_已审核.md` 保持 `## 【来源】标题` + `正文：...` 格式。
- AC-05: `3新闻_概述.md` 保持栏目标题与摘要段落格式。
- AC-06: 单篇正文失败仍写 `[正文提取失败: ...]`，不阻断其他文章。
- AC-07: 单篇摘要失败仍走 `fallback_summarize()`，不阻断其他文章。
- AC-08: `python3 perf_profile.py --date YYYY-MM-DD --dry-run` 可用于记录 step6/step7 前后耗时对比；外部网络或 LLM 波动需在验证记录中说明。
- AC-09: `run_all.sh` 无需修改即可继续调用 step6 和 step7。

## 覆盖矩阵

| ID | 覆盖任务 | 验收证据 |
|---|---|---|
| D-001@v1 | task-02, task-04, task-06 | AC-02, AC-03, AC-08 |
| D-002@v1 | task-01, task-03 | AC-01, AC-02, AC-03 |
| D-003@v1 | task-02, task-04, task-05 | AC-04, AC-05, AC-09 |
| D-004@v1 | task-01, task-03, task-05 | AC-06, AC-07 |
| FR-01 | task-01, task-02 | AC-02, AC-06 |
| FR-02 | task-03, task-04 | AC-03, AC-07 |
| FR-03 | task-05 | AC-01, AC-09 |
| FR-04 | task-02, task-04, task-05 | AC-04, AC-05 |
| FR-05 | task-01, task-03, task-05 | AC-06, AC-07 |
| FR-06 | task-06 | AC-08 |

## 自检结果

| 检查项 | 结果 |
|---|---|
| plan_level: light | PASS |
| 包含来源、范围、任务列表、验收、覆盖矩阵 | PASS |
| 来源直接引用 brainstorm 结论 | PASS |
| 任务列表清晰且无实现细节 | PASS |
| 任务使用 checkbox 格式 | PASS |
| 验收标准具体可验证 | PASS |
| D-001@v1 至 D-004@v1 全部可追踪 | PASS |
| 无 P0/P1 unresolved blocker | PASS |
| 无 Mermaid、估时、泛泛风险分析 | PASS |
| 无函数签名或代码示例 | PASS |
| plan.md 与 design.md 文件变更清单一致 | PASS |
