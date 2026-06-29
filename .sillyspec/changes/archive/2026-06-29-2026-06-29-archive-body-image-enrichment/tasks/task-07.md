---
id: task-07
title: step4 接入 archive_enrich best-effort（覆盖：FR-06, D-005@v1）
author: lmr
created_at: 2026-06-29 14:36:20
priority: P0
depends_on: [task-06]
blocks: [task-08, task-10]
requirement_ids: [FR-06]
decision_ids: [D-005@v1]
allowed_paths:
  - step4.py
  - tests/test_archive_enrich.py
goal: >
  step4.run() 在 14A archive_articles_best_effort 调用之后追加
  archive_enrich.enrich_archive_best_effort 调用，实现全量归档文章正文补全与 top10 首图下载。
  调用必须 best-effort 不阻断：失败只打印 warning，不 raise，不影响 1新闻_链接.md 写入与主流程返回。
  run_all.sh 不做任何修改。
implementation:
  - 在 step4.py run() 末尾 archive_articles_best_effort 调用之后，追加 try/except 块：
    try: 导入 archive_enrich，调用 enrich_archive_best_effort(today_str, selected, dry_run=dry_run)；
    except Exception: print(f"⚠ 归档正文/首图补全失败: {e}", file=sys.stderr)
  - enrich_archive_best_effort 内部已有异常捕获，step4 的 try/except 作为防御式外层保障
  - 不改变 step4 已有逻辑：1新闻_链接.md 写入、classified/selected 构建、14A 归档均保持原样
  - 不修改 run_all.sh
acceptance:
  - step4 --dry-run 不触发实际正文抓取和图片下载（dry_run 透传给 enrich_archive_best_effort）
  - archive_enrich 模块不存在或 import 失败时，step4 正常完成，打印 warning
  - enrich_archive_best_effort 内部抛异常时，step4 正常完成，不中断日报
  - step4 正常运行时（非 dry-run），归档 JSONL 的 body/image 字段被补充
verify:
  - python3 tests/test_archive_enrich.py
constraints:
  - 只修改 step4.py，不修改 news_archive.py、run_all.sh、1新闻_链接.md 等
  - 遵循最佳-effort 模式：try/except 仅用于防御，具体异常处理由 enrich_archive_best_effort 负责
  - 不引入新依赖
---
