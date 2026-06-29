---
id: task-02
title: load_month_jsonl + normalize_record
author: lmr
created_at: 2026-06-29 21:09:11
priority: P0
depends_on: [task-01]
blocks: [task-03, task-04, task-09]
requirement_ids: [FR-02, FR-08]
decision_ids: [D-005@v1]
allowed_paths: [monthly_report.py]
goal: >
  实现归档 JSONL 读取与字段默认化，仅读不写，schema 缺失字段透明补齐。
implementation:
  - load_month_jsonl(month) 计算 ARTICLES_DIR / f"{month}.jsonl" 路径
  - 文件不存在时 print "❌ archive 缺失: <path>" 并 sys.exit(1)
  - 逐行 strip + json.loads；解析失败 print warning 并跳过该行
  - 返回 list[record]（顺序保持原文件顺序）
  - normalize_record(rec) 返回新 dict（dict(rec)），不修改入参
  - 默认值：body_status='missing'、body=''、image_status='missing'、image_path=''、image_url=''、archive_status='metadata-only'、selected_in_top10=False、aggregate_score=0、archived_at=''、source=''、column=''、url=''、title=''
acceptance:
  - 缺失 JSONL → sys.exit(1)
  - 单条 JSON 损坏不阻断其余行
  - schema v2 字段缺失被补默认值，不修改原 record
  - 不写回 archive
verify:
  - 单测：mock 空目录 → sys.exit(1)
  - 单测：tmpdir 写入两行 JSONL（一行坏） → 仅返回 1 条
constraints:
  - 只读 archive，不修改/不删除
  - 不引入第三方库
  - 不调用 LLM/chromium
