---
author: lmr
created_at: 2026-06-27 13:37:38
change: 2026-06-27-perf-profile
stage: brainstorm
doc_type: decisions
---

# Decisions — Phase 12 性能量化

## D-001@v1: 外部 profiler + run_all 内置计时

- type: architecture
- priority: P1
- status: accepted
- source: user
- question: Phase 12 量化方式是只做外部脚本、只改 run_all，还是两者都做？
- answer: C：两者都做。
- normalized_requirement: 新增外部 `perf_profile.py` 生成结构化报告，同时修改 `run_all.sh` 输出每步耗时和总耗时。
- impacts: [FR-01, FR-02, FR-03, task-profiler, task-run-all-timing]
- evidence: 用户回答：“c”

## D-002@v1: 默认 step 级，低侵入补充子阶段线索

- type: boundary
- priority: P1
- status: accepted
- source: user
- question: 性能量化粒度是否需要深度记录 LLM/Chromium/网络抓取等子阶段？
- answer: C：默认 step 级，能低侵入就加子阶段。
- normalized_requirement: Phase 12 以 step 级耗时为基线，避免大改业务脚本；可利用 stdout/stderr 和现有输出补充低侵入线索。
- impacts: [FR-01, FR-04, task-profiler]
- evidence: 用户回答：“c”

## D-003@v1: Phase 12 只量化不优化

- type: boundary
- priority: P1
- status: accepted
- source: user
- question: 本 phase 是否直接做提速？
- answer: 不做优化；先量化再优化。
- normalized_requirement: 不并发化、不重构、不改栏目评分；只建立性能报告和慢点定位。
- impacts: [FR-04, FR-05, non-goals]
- evidence: 用户前序确认：“先量化再优化我同意”

## D-004@v1: 选择方案 A

- type: architecture
- priority: P2
- status: accepted
- source: user
- question: 采用外部 profiler 为主、深度插桩，还是只改 run_all？
- answer: 采用方案 A。
- normalized_requirement: 新增 `perf_profile.py` 为主，`run_all.sh` 只做轻量计时；拒绝深度插桩和只改 run_all。
- impacts: [FR-01, FR-02, FR-03, implementation-plan]
- evidence: 用户回答：“a”
