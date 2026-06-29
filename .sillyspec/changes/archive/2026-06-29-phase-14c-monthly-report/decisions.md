---
author: lmr
created_at: 2026-06-29 21:00:00
schema_version: 1
doc_type: decisions
change_id: phase-14c-monthly-report
phase: 14C
---

# 决策记录 — Phase 14C

## D-001@v1: 月报交付格式
- type: boundary
- status: accepted
- source: user (对话式探索第 1 轮)
- question: 月报核心交付物？
- answer: B+C — Markdown + HTML/PNG 可发布月报 + 统计/趋势数据报告
- normalized_requirement: 每期月报输出 4 件套（月报.md, 月报.html, 月报.png, 统计.json）
- impacts: §5.4, §7

## D-002@v1: 月报数据选择范围
- type: boundary
- status: accepted
- source: user (对话式探索第 2 轮)
- question: 统计范围和正文展示范围？
- answer: B — 全量 archive 做统计，月报正文只展示代表新闻
- normalized_requirement: compute_stats 遍历全部 record；render 只展示 pick_top_per_column
- impacts: §5.6, §5.7

## D-003@v1: LLM 文案政策
- type: boundary
- status: accepted
- source: user (对话式探索第 3 轮)
- question: 月报文案是否允许 LLM？
- answer: A — 允许，但必须 grounded 于 archive 真实内容 + 保留来源链接 + 防幻觉约束
- normalized_requirement: LLM prompt 必须包含 grounding context；输出后 sanitize；失败 fallback；代表新闻必须附 url
- impacts: §5.5, R-01

## D-004@v1: 实现架构方案
- type: architecture
- status: accepted
- source: user (Step 8 方案选择)
- question: 单体还是分层？
- answer: 方案 A — 单体文件 monthly_report.py，内部分层函数
- normalized_requirement: 单文件 + 6 组函数（loader/stats/select/llm/render/main）；不建 monthly/ 包
- impacts: §5.1, §7

## D-005@v1: 兼容范围
- type: boundary
- status: accepted
- source: design 自审
- question: 是否修改现有流水线？
- answer: 不改 step1_3/4/6/7/8/run_all.sh/news_archive.py/archive_enrich.py；不改变 archive schema
- normalized_requirement: 新增 monthly_report.py + tests，零修改既有文件
- impacts: §3, §6

## D-006@v1: 外部依赖限制
- type: constraint
- status: accepted
- source: design 自审
- question: 是否可引入 jieba/pandas/duckdb/sqlite？
- answer: 全部不引入。关键词统计复用已有 CATEGORY_KEYWORDS 词库
- normalized_requirement: top_keywords 基于现有词库，不 install 任何新包
- impacts: §5.7, R-04