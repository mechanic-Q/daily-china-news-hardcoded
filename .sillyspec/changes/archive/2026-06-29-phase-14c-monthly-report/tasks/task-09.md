---
id: task-09
title: tests/test_monthly_report.py
author: lmr
created_at: 2026-06-29 21:09:11
priority: P0
depends_on: [task-02, task-03, task-04, task-05, task-06, task-07, task-08]
blocks: [task-10]
requirement_ids: [FR-09, FR-10]
decision_ids: [D-003@v1, D-005@v1]
allowed_paths: [tests/test_monthly_report.py]
goal: >
  unittest 覆盖 monthly_report 核心函数与 dry-run；LLM 与 chromium 全 mock，零网络零外部进程。
implementation:
  - 用例覆盖：
    - parse_args（默认月、合法 month、--top-per-column 11 → SystemExit、--max-llm-seconds 0 → SystemExit）
    - load_month_jsonl（文件缺失 → SystemExit；坏行跳过；正常解析）
    - normalize_record（默认值，原 record 不变）
    - compute_stats（字段完整、by_column 倒序、coverage 计数）
    - top_keywords（CATEGORY_KEYWORDS 命中计数）
    - pick_top_per_column（排序键 4 级 + COLUMN_ORDER 顺序）
    - build_grounding_context（含所有 picks article_id；不含外部 id）
    - llm_monthly_overview（mock 缺 key/异常/成功；超时路径 mock 时钟）
    - sanitize_llm_text（合法/非授权 id/占位符/英文超阈值）
    - fallback_overview（含 ⚠ 标注、≤700 字）
    - render_markdown/html（含 url、source、date、栏目顺序）
    - render_png（mock subprocess + PIL，缺 chromium 路径返回 False）
    - write_outputs（tmpdir 验四件套；dry_run 不写文件）
  - 使用 unittest.mock 替换 openai client、subprocess.run、PIL.Image
  - 使用 tempfile.TemporaryDirectory monkeypatch ARTICLES_DIR / MONTHLY_DIR
acceptance:
  - python3 tests/test_monthly_report.py 全绿
  - 测试中无真实网络/无 chromium 调用
  - 不写入真实 archive 路径
verify:
  - python3 tests/test_monthly_report.py
constraints:
  - 不修改 archive/articles
  - 不发起网络请求
  - 不依赖外部 chromium
  - 不引入 pytest（沿用项目 unittest 风格）
