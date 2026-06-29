---
id: task-10
title: 模块文档同步 + 联调
author: lmr
created_at: 2026-06-29 21:09:11
priority: P1
depends_on: [task-09]
blocks: []
requirement_ids: [FR-01, FR-06, FR-09, FR-10]
decision_ids: [D-004@v1, D-005@v1, D-006@v1]
allowed_paths:
  - .sillyspec/docs/Daily/modules/_module-map.yaml
  - .sillyspec/docs/Daily/modules/monthly.md
goal: >
  在模块索引和模块卡片中登记新增 monthly 模块；运行单测与 --dry-run 进行最终联调。
implementation:
  - _module-map.yaml 新增 monthly 模块条目：
    - paths=[monthly_report.py]
    - tags=[monthly, report, archive, llm]
    - aliases=[月报]
    - entrypoints=["python3 monthly_report.py --month YYYY-MM ..."]
    - main_symbols=[parse_args, load_month_jsonl, compute_stats, pick_top_per_column, llm_monthly_overview, sanitize_llm_text, fallback_overview, render_markdown, render_html, render_png, write_outputs, main]
    - depends_on=[archiver, llm-client]
    - used_by=[]
    - needs_review=false
    - concerns 含 R-04（关键词词库统计偏差） R-06（top_per_column 上限） R-07（不进 run_all.sh）
  - archiver.used_by 追加 monthly
  - 更新 _module-map.yaml 顶部 generated_at 至当前时间
  - 新增 modules/monthly.md 模块卡片（定位 / 契约摘要 / 关键逻辑 / 注意事项 / 人工备注 + MANUAL_NOTES 占位）
  - 运行 python3 tests/test_monthly_report.py 与 python3 monthly_report.py --month 2026-06 --dry-run
acceptance:
  - _module-map.yaml 包含 monthly 模块且 archiver.used_by 已更新
  - modules/monthly.md 存在且有 MANUAL_NOTES_START/END 标记
  - 单测全绿；--dry-run 不写文件
verify:
  - python3 tests/test_monthly_report.py
  - python3 monthly_report.py --month 2026-06 --dry-run
constraints:
  - 不修改 archiver/extractor/renderer 等其他模块卡片
  - 不改 run_all.sh
  - 不向 orchestrator.depends_on 追加 monthly
