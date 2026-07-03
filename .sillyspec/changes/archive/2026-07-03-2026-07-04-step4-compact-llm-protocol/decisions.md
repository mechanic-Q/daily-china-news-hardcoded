---
author: lmr
created_at: 2026-07-04 00:23:08
---

# Decisions: Step4 Compact LLM Protocol

## D-001@v1: 紧凑协议为 Step4 主路径

- type: architecture
- status: accepted
- source: user
- question: Step4 应继续使用高 token JSON，还是改为非 JSON 紧凑协议？
- answer: 选择紧凑协议优先。涉华使用位串，栏目评分使用矩阵；JSON 仅作为 fallback/debug。
- normalized_requirement: `llm_is_china_related_batch()` 和 `score_signals_batch()` 的主 LLM prompt 使用紧凑协议，成功解析后进入现有分类流程。
- impacts: [FR-compact-china, FR-compact-score, verify-dry-run]
- evidence: 用户选择“方案A”；设计确认“确认”。
- priority: P0

## D-002@v1: 不改评分算法和上下游结构

- type: boundary
- status: accepted
- source: user
- question: 紧凑协议是否可以改变最终算法或月报/归档结构？
- answer: 不可以。安全边界是不改算法、不改不相关结构、不破坏上下游。
- normalized_requirement: 不修改 `aggregate_scores()`、`assign_category()`、`priority_score()` 的算法语义；不修改 `news_archive.py` 和 `monthly_report.py` 依赖的数据字段。
- impacts: [FR-compat-signals, FR-no-archive-schema-change, verify-monthly-safe]
- evidence: 用户要求“安全边界：不要改算法，不相关的结构”。
- priority: P0

## D-003@v1: parser 必须还原旧 signals 结构

- type: compatibility
- status: accepted
- source: code
- question: 非 JSON 输出如何与现有 Step4、归档、月报衔接？
- answer: 紧凑输出只存在于 LLM I/O 层，parser 负责还原旧 `signals` dict。
- normalized_requirement: parser 输出必须为 `{"relevance": {COLUMN_ORDER[i]: score}, "importance": n, "timeliness": n}`，使后续 `aggregate_scores()` 和 `assign_category()` 无需改动。
- impacts: [FR-parse-score-matrix, verify-signals-non-null]
- evidence: 现有 `step4.aggregate_scores()` 和 `news_archive.build_record()` 使用 `signals` 字段。
- priority: P0

## D-004@v1: low 模型禁 reasoning 并使用 256k 输出上限

- type: feasibility
- status: accepted
- source: user+probe
- question: 是否只靠紧凑协议，还是也要在程序内为 `low` 使用大输出预算？
- answer: 程序内对 `low` 使用 `reasoning_effort="none"` 和 `max_tokens=262144`。1m context 由 `model: low` 的模型能力提供；Chat Completions 侧没有独立 context window 参数需要设置。
- normalized_requirement: `low` 模型调用必须透传 `reasoning_effort="none"`，并将输出上限配置/覆盖为 262144；空 content 时记录 `finish_reason/content_len/reasoning_len` 并抛出 `LLMCallError`。
- impacts: [FR-low-budget, FR-empty-content-diagnostics, verify-low-max-tokens]
- evidence: 用户要求“程序内对low改用1m上下文256k输出”；探针确认 9router 接受 `max_tokens=262144` 且 `reasoning_effort=none` 生效。
- priority: P0
