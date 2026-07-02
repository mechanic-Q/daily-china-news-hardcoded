---
id: task-01
title: 定义并接入 health JSONL 记录范围，覆盖采集结果字段与 best-effort 写入策略。（覆盖：FR-01）
author: lmr
created_at: 2026-07-02 20:12:36
priority: P0
depends_on: []
blocks: []
requirement_ids:
  - FR-01
decision_ids: []
allowed_paths:
  - step1_3.py
goal: >
  为每个信源定义结构化的健康记录（HealthRecord），包含通过数/淘汰数/总数/耗时/工具/状态/记录时间，
  并在 step1_3.py 每个信源处理完成后 best-effort 追加写入 archive/sources_health.jsonl，失败不中断流水线。
implementation:
  - 在 step1_3.py 顶部定义 HealthRecord dataclass 或 TypedDict，字段：date/source/passed/failed/total/tool/elapsed_ms/status/recorded_at
  - 定义 HEALTH_FILE = BASE_DIR / "archive" / "sources_health.jsonl"，确保 archive 目录存在
  - 实现 write_health_record(record, dry_run=False) — 接收 dict，序列化 JSON 追加一行。dry_run 时只打印 would-write，不写文件
  - 实现 best-effort 策略：写入异常只 logging.warning，不 raise；文件路径不存在时自动创建父目录
  - 主循环中每个 source 完成后构造 HealthRecord，调用 write_health_record。status 根据 passed > 0 判定 "ok"/"failed"
  - 耗时以毫秒为单位（int），recorded_at 使用 CST 时区的 ISO-8601 时间戳
acceptance:
  - step1_3.py 中存在 HealthRecord 定义，字段与 design.md JSON schema 一致（date/source/passed/failed/total/tool/elapsed_ms/status/recorded_at）
  - 每个信源处理完成后（含 0 条和异常分支）都调用 write_health_record
  - archive/sources_health.jsonl 的每行是合法的 JSON，含所有必填字段
  - dry-run 时不追加 JSONL 文件，stdout 含 "would-write health" 提示
  - 若写入失败（权限/磁盘），流水线不中断，print warning 后继续
verify:
  - python3 -m py_compile step1_3.py
  - python3 step1_3.py --date 2026-07-01 --dry-run 2>&1 | rg -q "would-write health"
constraints:
  - 只改 step1_3.py，不改其他文件
  - health 写入失败仅 warning，不 raise，不阻塞主流程
  - elapsed_ms 用 int(time.time() - t0) * 1000 计算，CST 时间戳
  - 不引入新依赖（只用标准库 json/datetime/logging）
  - archive/ 目录自动创建，不假设已存在
  - 已存在 decisions.md（本 change 无），无需标注 D-xxx
