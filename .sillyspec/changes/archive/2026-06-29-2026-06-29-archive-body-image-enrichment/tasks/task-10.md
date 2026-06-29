---
id: task-10
title: 运行验证命令（覆盖：FR-01~FR-09）
author: lmr
created_at: 2026-06-29 14:36:20
priority: P0
depends_on: [task-08, task-09]
blocks: []
requirement_ids: [FR-01, FR-02, FR-03, FR-04, FR-05, FR-06, FR-07, FR-08, FR-09]
decision_ids: [D-001@v1, D-002@v1, D-003@v1, D-004@v1, D-005@v1, D-006@v1, D-007@v1]
allowed_paths:
  - tests/test_archive_enrich.py
  - tests/test_news_archive.py
  - archive_enrich.py
goal: >
  运行全部测试套件和一次真实 dry-run，验证 Phase 14B 实现完整通过最终验收。
  重点确认：单测全部绿色、dry-run 不写 JSONL 不下载图片、正文提取和首图补全状态机正确。
implementation:
  - python3 tests/test_news_archive.py —— schema v2 兼容 + upsert 保留 14B 字段（15 条以内用例，几秒跑完）
  - python3 tests/test_archive_enrich.py —— 全部 mock 无网络；textTestRunner 输出 ...OK
  - python3 archive_enrich.py --date 2026-06-29 --dry-run —— 输出统计行，不修改 JSONL 不创建图片文件
  - 检查 dry-run 输出：统计字段完整（total/body_ok/body_failed/image_ok/not_selected/skipped 等）
  - 检查图片目录无新文件写入
acceptance:
  - tests/test_news_archive.py 全部通过，无 FAIL/ERROR
  - tests/test_archive_enrich.py 全部通过，零网络请求
  - archive_enrich.py --dry-run 输出合理统计，不写 JSONL，不下载图片到 archive/images/
  - FR-02（禁 LLM）在 dry-run 中不触发任何 LLM API 调用
verify:
  - python3 tests/test_news_archive.py
  - python3 tests/test_archive_enrich.py
  - python3 archive_enrich.py --date 2026-06-29 --dry-run
constraints:
  - 不修改任何源文件或测试文件
  - 只在项目根目录执行
  - dry-run 必须以退出码 0 完成，stderr 无异常回溯
---
