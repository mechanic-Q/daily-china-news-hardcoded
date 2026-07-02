---
id: task-02
title: 在 `step1_3.py` 完成非 dry-run 写入、dry-run would-write 输出、异常 warning banner。（覆盖：FR-01, FR-02）
author: lmr
created_at: 2026-07-02 20:12:36
priority: P0
depends_on: [task-01]
blocks: []
requirement_ids: [FR-01, FR-02]
decision_ids: []
allowed_paths:
  - step1_3.py
goal: >
  在 step1_3.py 主循环中，每信源采集完成后写入 health JSONL（非
  dry-run），dry-run 只输出 would-write，并在 passed==0 或连续 3 天
  passed<5 时输出 warning banner。
implementation:
  - main() 循环每个 source 采集后构造 health record（date, source, passed, failed, total, tool, elapsed_ms, status, recorded_at）
  - 非 dry-run 以 append 模式写入 archive/sources_health.jsonl，写入异常只 warning 不中断 pipeline
  - dry-run 不写文件，stdout 打印 would-write 提示 + 被跳过的 JSON 行
  - 写入前读取最近 7 天同 source health 记录，判断是否触发 warning banner
  - banner 条件: 当天 passed==0 或连续 3 天 passed<5，以醒目标记输出到 stderr
acceptance:
  - 非 dry-run 运行后 archive/sources_health.jsonl 追加每信源 JSONL 记录，字段完整且不含无效值
  - dry-run 不追加 health JSONL，stdout 显示 would-write 行
  - 当天 passed==0 时 stderr 输出 warning banner
  - 连续 3 天 passed<5 时 stderr 输出 warning banner
  - health JSONL 写入异常只 warning 不中断，后续信源继续处理
verify:
  - python3 -m py_compile step1_3.py
  - python3 step1_3.py --date 2026-06-30 --dry-run 2>&1 | head -20
constraints:
  - 不改写现有采集/验证逻辑（brownfield 兼容）
  - 不引入新的外部依赖
  - health record 的 recorded_at 用 ISO 8601 含时区
  - JSONL 路径: daily.common.BASE_DIR / "archive" / "sources_health.jsonl"
  - health 写入失败仅 warning，不抛出异常
