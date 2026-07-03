---
author: lmr
created_at: 2026-07-03 14:44:13
schema_version: 1
doc_type: decisions
change_id: 2026-07-06-phase-15f-image-quality
phase: 15f
status: design-confirmed
---

# Decisions · Phase 15F · disable automatic image collection

## D-001@v1: 禁用范围限定为 step4 自动图片收集

- type: boundary
- status: accepted
- source: user + code
- question: 禁用图片收集是否同时关闭正文增强和直接 CLI？
- answer: 否。只禁用 `step4.py` 自动流程中的图片收集；正文增强继续；`archive_enrich.py` 直接 CLI 默认行为保持兼容。
- normalized_requirement: `step4.py` 调用归档增强时不触发图片 URL 提取、图片下载或本地图片写入；正文 `fetch_and_extract()` 仍可执行。
- impacts: [FR-01, FR-02, FR-03, T-01, T-02, T-03]
- evidence: 用户确认“改 plan 方向”与“确认设计”；`step4.py:646-648`；`archive_enrich.py:229-325`
- priority: P1

## D-002@v1: 使用参数开关方案

- type: architecture
- status: superseded
- source: user
- question: 用哪种实现方式禁用自动图片收集？
- answer: 选择方案 A：在 `archive_enrich` 调用链增加 `enrich_image=True` 参数，`step4.py` 传 `False`。
- normalized_requirement: 新参数默认 `True` 保持兼容，只有 `step4.py` 自动入口显式传 `False`。
- impacts: [FR-01, FR-02, FR-03, T-01, T-02, T-03]
- evidence: 用户选择“方案A”
- priority: P1

## D-002@v2: 使用 include_images 参数开关

- type: architecture
- priority: P1
- status: accepted
- supersedes: D-002@v1
- source: design-grill
- question: `enrich_image` 参数名会遮蔽同名函数 `enrich_image()`，默认图片路径是否会崩溃？
- answer: 会有风险；参数名改为 `include_images`，保留方案 A 的参数开关设计。
- normalized_requirement: `archive_enrich` 调用链使用 `include_images=True` 默认参数；`step4.py` 自动入口传 `include_images=False`；函数 `enrich_image()` 名称保持不变。
- impacts: [FR-01, FR-02, FR-03, T-01, T-02, T-03]
- evidence: Design Grill cross-check X-003；`archive_enrich.py:267-269`
