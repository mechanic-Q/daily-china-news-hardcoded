---
author: lmr
created_at: 2026-06-29 21:12:00
schema_version: 1
plan_level: light
change_id: phase-14c-monthly-report
phase: 14C
---

# 轻量计划：Phase 14C 自动月报

## 来源

按 `design.md`（单体方案 A、loader/stats/select/llm/render 分层、4 件套输出）与 `decisions.md`（D-001@v1~D-006@v1）实现。

## 范围

- 新增 `monthly_report.py`（含 CLI、loader、stats、select、llm、render、main）
- 新增 `tests/test_monthly_report.py`（loader/stats/select/render/sanitize/parse_args 单测）
- 更新 `.sillyspec/docs/Daily/modules/_module-map.yaml`（+ `monthly`）
- 新增 `.sillyspec/docs/Daily/modules/monthly.md` 模块卡片
- 不修改：`step1_3.py` / `step4.py` / `step6.py` / `step7.py` / `step8.py` / `run_all.sh` / `news_archive.py` / `archive_enrich.py`

## Tasks

- [x] task-01: `monthly_report.py` 骨架（常量/路径/CLI parse_args/main 编排空壳）（覆盖 FR-01, FR-07, D-001@v1, D-004@v1）
- [x] task-02: 实现 `load_month_jsonl` + `normalize_record`（覆盖 FR-02, FR-08, D-005@v1）
- [x] task-03: 实现 `compute_stats` + `top_keywords`（基于已有 CATEGORY_KEYWORDS 词库）（覆盖 FR-03, D-002@v1, D-006@v1）
- [x] task-04: 实现 `pick_top_per_column` 排序键（覆盖 FR-04, D-002@v1）
- [x] task-05: 实现 `build_grounding_context` + `llm_monthly_overview`（ZHIPU SDK，30s 超时；缺 key 直接降级）（覆盖 FR-05, D-003@v1）
- [x] task-06: 实现 `sanitize_llm_text` + `fallback_overview`（覆盖 FR-05, D-003@v1）
- [x] task-07: 实现 `render_markdown` + `render_html`（独立模板，复用日报双栏感觉）（覆盖 FR-06, D-001@v1）
- [x] task-08: 实现 `render_png`（chromium 60s 超时 + Pillow 裁边）+ 写 `统计.json`（覆盖 FR-06, D-001@v1）
- [x] task-09: 新增 `tests/test_monthly_report.py`（LLM/chromium mock，覆盖 loader/stats/select/sanitize/fallback/render 快照/parse_args/dry-run/上限校验）（覆盖 FR-09, FR-10, D-003@v1）
- [x] task-10: 模块文档：`_module-map.yaml` +monthly + 新增 `modules/monthly.md`；运行 `--dry-run` 与单测确认通过（覆盖 D-004@v1, D-005@v1, D-006@v1）

## 验收

- [x] `python3 tests/test_monthly_report.py` 全部通过，无网络请求（mock LLM 与 chromium）
- [x] `python3 monthly_report.py --month <test> --dry-run` 只打印统计与目标路径，不写任何文件
- [x] 真实月份运行时输出 4 件套到 `archive/monthly/YYYY-MM/`（chromium 缺失时 png 缺、exit 2，其余正常）
- [x] LLM 失败/超时/无 key → fallback_overview 接管，月报中标注"本期使用规则模板"
- [x] 月报代表新闻条目均含 url、source、归档日期；缺 image_path 用占位符
- [x] `--top-per-column` 上限校验 ≤10
- [x] `step1_3 / step4 / step6 / step7 / step8 / run_all.sh / news_archive.py / archive_enrich.py` 零修改
- [x] archive/articles JSONL 和 archive/images 内容零修改

## 覆盖矩阵

| ID | 覆盖任务 | 验收证据 |
|---|---|---|
| D-001@v1 | task-01, task-07, task-08 | 4 件套输出齐全；幂等覆盖 |
| D-002@v1 | task-03, task-04 | 全量统计 + 每栏目 Top N 代表新闻 |
| D-003@v1 | task-05, task-06, task-09 | grounding context + sanitize + fallback + LLM mock 单测 |
| D-004@v1 | task-01, task-10 | 单文件 monthly_report.py + monthly 模块卡片 |
| D-005@v1 | task-02, task-10 | 流水线/archive schema 零修改；模块卡片记录 |
| D-006@v1 | task-03, task-10 | 关键词命中走 CATEGORY_KEYWORDS；无新依赖；模块卡片 concerns 记录 |
