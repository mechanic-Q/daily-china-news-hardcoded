---
id: task-01
title: monthly_report.py 骨架（CLI/常量/main 空壳）
author: lmr
created_at: 2026-06-29 21:09:11
priority: P0
depends_on: []
blocks: [task-02, task-03, task-04, task-05, task-06, task-07, task-08, task-09, task-10]
requirement_ids: [FR-01, FR-07]
decision_ids: [D-001@v1, D-004@v1]
allowed_paths: [monthly_report.py]
goal: >
  新增 monthly_report.py 骨架：手写 parse_args、模块常量、COLUMN_ORDER（与 step8 一致）、main 空壳编排，使 --dry-run 可跑通。
implementation:
  - 手写 parse_args 解析 --month/--dry-run/--no-llm/--top-per-column/--max-llm-seconds；缺省 month 用当前 CST 月份
  - 校验 --top-per-column ∈[1,10] 与 --max-llm-seconds ≥1；非法时 print 错误 + sys.exit(1)
  - 定义常量 ARCHIVE_DIR / ARTICLES_DIR / IMAGES_DIR / MONTHLY_DIR / DEFAULT_TOP_PER_COLUMN=3 / DEFAULT_MAX_LLM_SECONDS=30 / LLM_MODEL='glm-4-flash' / LLM_BASE_URL / OVERVIEW_MAX_CHARS=700 / BODY_SNIPPET_CHARS=300 / CST
  - 内联 COLUMN_ORDER（复制 step8 当前 9 项，注释提示同步 step4/step7/step8）
  - main() 调用占位函数链 load_month_jsonl → normalize_record → compute_stats → pick_top_per_column → build_overview → render_markdown → render_html → write_outputs；占位函数 pass/return None
  - `if __name__ == "__main__": main()`
acceptance:
  - python3 monthly_report.py --month 2026-06 --dry-run 无 traceback 且 exit 0
  - --top-per-column 11 / --month bad-format 报错 + exit 1
  - 文件含 COLUMN_ORDER 常量（9 项）和 11 个上述常量
verify:
  - python3 monthly_report.py --month 2026-06 --dry-run
constraints:
  - 不引入 argparse / 第三方 CLI 库
  - 不写 type hints
  - 不 import step4/step7/step8
  - 占位函数仅满足 --dry-run，不实现真实逻辑（留给后续任务）
