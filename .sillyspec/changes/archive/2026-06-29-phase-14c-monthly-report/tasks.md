---
author: lmr
created_at: 2026-06-29 21:05:00
schema_version: 1
doc_type: tasks
change_id: phase-14c-monthly-report
phase: 14C
---

# Phase 14C 任务清单 — 自动月报

## Wave 1 — Loader & Stats（数据层）

- task-01: 新增 `monthly_report.py` 骨架：CLI 解析 + 常量定义 + main 编排空壳（覆盖 FR-01, FR-07, D-001@v1, D-004@v1）
- task-02: 实现 `load_month_jsonl` + `normalize_record`（覆盖 FR-02, D-005@v1）
- task-03: 实现 `compute_stats` + `top_keywords`（覆盖 FR-03, D-006@v1）

## Wave 2 — Select & LLM（内容生成层）

- task-04: 实现 `pick_top_per_column` 排序键（覆盖 FR-04, D-002@v1）
- task-05: 实现 `build_grounding_context` + `llm_monthly_overview`（带超时）（覆盖 FR-05, D-003@v1）
- task-06: 实现 `sanitize_llm_text` + `fallback_overview`（覆盖 FR-05, R-01, R-05）

## Wave 3 — Render（输出层）

- task-07: 实现 `render_markdown`（覆盖 FR-06）
- task-08: 实现 `render_html` 独立模板（覆盖 FR-06, R-03）
- task-09: 实现 `render_png`（chromium 截图 + Pillow 裁边，60s 超时）+ `统计.json` 写入（覆盖 FR-06, R-03）

## Wave 4 — Tests & Module Docs（验收）

- task-10: 新增 `tests/test_monthly_report.py` 单元测试（覆盖 FR-09，LLM mock）
- task-11: 模块索引 + 卡片更新 `_module-map.yaml` + 新增 `modules/monthly.md`（覆盖 D-004@v1）
- task-12: 运行验证：单测、`--dry-run`、真实月（如有 archive 数据）（覆盖 FR-01~FR-10）
