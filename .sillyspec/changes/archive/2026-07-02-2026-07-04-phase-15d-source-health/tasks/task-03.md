---
id: task-03
title: 在 `monthly_report.py` 增加月度信源健康摘要输出。（覆盖：FR-03）
author: lmr
created_at: 2026-07-02 20:12:36
priority: P0
depends_on: [task-01, task-04]
blocks: []
requirement_ids: [FR-03]
decision_ids: []
allowed_paths:
  - monthly_report.py
goal: >
  monthly_report.py 读取 task-01 写入的 archive/sources_health.jsonl，
  按月聚合每信源运行天数/平均 passed/0 条天数/最差连续低谷，写入月报统计段。
implementation:
  - 在 monthly_report.py 新增 load_source_health(month) 函数，扫描 JSONL 过滤当月记录
  - 在 monthly_report.py 新增 compute_source_health_stats(records) 函数，按 source 分组计算指标：run_days（非重复 date 数）、avg_passed、zero_days（passed==0 天数）、worst_streak（passed<5 最长连续天数）
  - 在 compute_stats() 返回字典或 render_markdown() 中插入健康摘要区块，dry-run 时打印相同内容
acceptance:
  - ./monthly_report.py --month 2026-07 --dry-run 输出中包含每信源运行天数/平均 passed/0 条天数/最差连续低谷
  - sources_health.jsonl 不存在或为空时，脚本不崩溃并给出提示
  - 同一 date+source 有多行记录时以最后一行为准（JSONL 自然覆盖）
verify:
  - python3 -m py_compile monthly_report.py
  - python3 -c "from monthly_report import load_source_health, compute_source_health_stats; h=load_source_health('2026-07'); print(compute_source_health_stats(h))"
constraints:
  - 只改 monthly_report.py，不改 step1_3.py / llm.yaml / run_all.sh
  - 健康摘要为纯文本统计段，不依赖 LLM 调用
  - 无 health JSONL 时 graceful degrade（print 提示 + 跳过）
  - 保持原有 --dry-run / --no-llm 参数行为不变
  - 异常不中断月报主流程（try/except + warning print）
