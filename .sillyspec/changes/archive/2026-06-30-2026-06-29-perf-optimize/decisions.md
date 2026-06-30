---
author: lmr
created_at: 2026-06-30 01:24:39
change: 2026-06-29-perf-optimize
doc_type: decisions
---

# Phase15 决策台账

## D-001@v1: Phase15 范围只做 step6 + step7 并发

- type: scope
- status: accepted
- source: user
- question: Phase15 性能优化范围怎么定？
- answer: 采用 B：仅 `step6.py` 文章正文提取并发 + `step7.py` LLM 摘要并发。
- normalized_requirement: 本期不做 `step1_3.py` 信源并发，不做 chromium 进程复用，不改 `step4.py` 和 `step8.py`；只优化 `step6.py` 与 `step7.py` 的文章级串行等待。
- impacts: [FR-01, FR-02, FR-03, implementation-plan]
- evidence: 用户在恢复流程中选择「按 B 继续」。
- priority: P0

## D-002@v1: 实现方案采用 ThreadPoolExecutor 保守并发

- type: architecture
- status: accepted
- source: user
- question: step6/step7 并发用哪种实现方案？
- answer: 选择方案A：保守线程池。
- normalized_requirement: 使用标准库 `concurrent.futures.ThreadPoolExecutor` 包裹现有同步函数；不引入 asyncio 重构、子进程分片或新第三方依赖。
- impacts: [FR-01, FR-02, implementation-plan]
- evidence: 用户在方案选择中选择「方案A」。
- priority: P0

## D-003@v1: 保持文件接力与产物语义不变

- type: compatibility
- status: accepted
- source: design-confirmation
- question: 性能优化是否允许改变 CLI、Markdown 文件或报纸产物？
- answer: 不允许。
- normalized_requirement: `run_all.sh` CLI、step 输入输出文件名、Markdown 格式、栏目顺序、HTML/PNG 产物语义保持不变。
- impacts: [FR-03, FR-04, acceptance]
- evidence: 用户确认分段设计方案；设计摘要明确不改产物语义。
- priority: P0

## D-004@v1: 并发上限保守默认，失败按单篇处理

- type: reliability
- status: accepted
- source: design-confirmation
- question: 如何控制并发风险？
- answer: `step6` 和 `step7` 分别设保守并发上限；单篇失败不阻断全局。
- normalized_requirement: `step6.py` 默认建议 4 worker；`step7.py` 默认建议 3 worker。正文失败写错误占位，摘要失败走 `fallback_summarize()`，主流程继续输出完整文件。
- impacts: [FR-01, FR-02, FR-05, risk-register]
- evidence: 用户确认设计方案；设计摘要明确保守并发、fallback 和不阻断全局。
- priority: P1
