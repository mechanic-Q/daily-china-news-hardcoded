---
id: task-08
title: 新增 tests/test_archive_enrich.py（覆盖：FR-01~FR-06, FR-08, FR-09, D-001@v1~D-005@v1, D-007@v1）
author: lmr
created_at: 2026-06-29 14:36:20
priority: P0
depends_on: [task-06, task-07]
blocks: [task-10]
requirement_ids: [FR-01, FR-02, FR-03, FR-04, FR-05, FR-06, FR-08, FR-09]
decision_ids: [D-001@v1, D-002@v1, D-003@v1, D-004@v1, D-005@v1, D-007@v1]
allowed_paths:
  - tests/test_archive_enrich.py
goal: >
  编写 archive_enrich 单元测试，全部 mock 无真实网络。覆盖正文补全状态机、首图提取与下载、CLI
  路由、dry-run/missing-only/max-seconds 语义、best-effort 异常安全、旧 v1 JSONL 向后兼容。
implementation:
  - 风格同 tests/test_news_archive.py：unittest、sys.path.insert、tempfile、mock
  - mock.patch 替代 step6.fetch_and_extract、urllib 下载，零网络请求
  - make_record(overrides) helper 减少样板代码
  - 测试矩阵：正文成功/失败、禁止 LLM（assert LLM 函数未被调用）、非 top10 image="not_selected"、
    首图成功/not_found/下载失败、dry-run 不写不下载、missing-only 跳过已成功记录、
    max_seconds 超时标记 skipped、best-effort 捕获异常、旧 record 默认 status、
    stats 键完整性、extract_first_image_url 优先级、image_month_dir 路径、should_enrich_*
    边界条件、parse_args 参数组合
acceptance:
  - python3 tests/test_archive_enrich.py 全部通过
  - 零网络请求，全部 mock
  - 覆盖 FR-01~FR-06, FR-08, FR-09 全部验收路径
verify:
  - python3 tests/test_archive_enrich.py
constraints:
  - 不请求任何真实 URL；所有 HTTP/urllib/step6 调用均 mock
  - 不修改 archive_enrich.py、news_archive.py 等源文件
  - 仅使用 unittest + mock + tempfile，无第三方依赖
  - 项目风格：无 type hints
---
