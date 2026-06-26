---
author: lmr
created_at: 2026-06-27 03:06:00
change: 2026-06-27-user-manual-summary-bar
stage: brainstorm
doc_type: decisions
---

# Decisions — 用户手册与顶部总摘要栏移除

## D-001@v1: 删除顶部全局摘要栏

- type: boundary
- status: accepted
- source: user
- question: 大标题下方的所有新闻总和栏目是否保留？
- answer: 不保留；用户明确表示不要这个栏目。
- normalized_requirement: step8 输出 HTML 中不得包含大标题下方的全局摘要栏；标题后直接进入栏目正文。
- impacts: [FR-01, task-remove-summary-bar, verify-no-summary-dom]
- evidence: 用户原始需求：“大标题的下边所有新闻的一个总和这块我不想要了”；Step 9 用户确认设计。
- priority: P1

## D-002@v1: 用户手册覆盖全范围

- type: scope
- status: accepted
- source: user
- question: USER_MANUAL.md 需要覆盖哪些内容？
- answer: 全都要。
- normalized_requirement: 手册必须覆盖项目整体功能、run_all/各 step 用法、sillyspec 阶段命令、time 计时方法、常见故障排查、后续 Phase 12/13/14 路线。
- impacts: [FR-02, FR-03, task-user-manual, verify-manual-sections]
- evidence: 用户回答：“全都要”。
- priority: P1

## D-003@v1: 拆分后续性能与栏目算法 phase

- type: architecture
- status: accepted
- source: user
- question: 三个议题是否打包到一个变更？
- answer: 拆成多个独立变更；本次只做手册和删 summary 栏，性能先量化再优化，栏目算法完全重做另起 phase。
- normalized_requirement: Phase 11 不实现性能量化、性能优化或栏目评分算法重做；只在手册中记录后续路线。
- impacts: [FR-04, non-goals, task-user-manual-roadmap]
- evidence: 用户回答：“q1:b ... 先量化再优化我同意 ... q3:完全重做 ... q4:用原样计数保持一致”。
- priority: P1

## D-004@v1: 选择最小变更方案 A

- type: architecture
- status: accepted
- source: user
- question: 采用最小删除、配置开关，还是多文档拆分？
- answer: 采用方案 A：最小变更。
- normalized_requirement: 删除 summary 栏并新增单文件 USER_MANUAL.md；不新增 summary 开关，不新增多文档目录。
- impacts: [FR-01, FR-02, implementation-plan]
- evidence: 用户回答：“a”。
- priority: P2
