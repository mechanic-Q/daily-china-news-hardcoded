---
id: task-05
title: 增加 manual test 文档，覆盖采集写入、dry-run 不污染、banner、月报摘要、LLM client 统一调用。（覆盖：FR-01, FR-02, FR-03, FR-04）
author: lmr
created_at: 2026-07-02 20:12:36
priority: P0
depends_on: [task-02, task-03, task-04]
blocks: []
requirement_ids: [FR-01, FR-02, FR-03, FR-04]
decision_ids: []
allowed_paths:
  - tests/manual/test_15d_source_health.py
goal: >
  为 Phase 15D 四个 FR 提供可手工执行的验收脚本，覆盖采集写入、dry-run 隔离、banner、月报摘要、LLM 统一调用。
implementation:
  - Create tests/manual/test_15d_source_health.py with 6 子测试标志：--test-write / --test-dry-run / --test-banner-zero / --test-banner-streak / --test-monthly / --test-llm-client
  - 每个子测试在 /tmp/ 构造隔离 mock JSONL，不依赖真实数据或网络
  - banner 子测试验证 passed==0 和连续 3 天 passed<5 触发规则
  - --test-llm-client 通过 grep 确认 monthly_report.py 无 direct OpenAI import
acceptance:
  - --help 列出 6 个子测试标志
  - --test-write 字段完整性（date/source/passed/failed/total/tool/elapsed_ms/status/recorded_at）全部校验
  - --test-dry-run 确认 health JSONL 不变，stdout 含 dry-run/would-write
  - --test-banner-* 使用手工构造数据验证 banner 规则
  - --test-monthly 验证月报 stats 字段（运行天数/平均 passed/0 条天数/最差低谷）
  - --test-llm-client 确认 call_llm 存在且 llm.yaml 含 monthly-overview
  - python3 -m py_compile tests/manual/test_15d_source_health.py 通过
verify:
  - python3 -m py_compile tests/manual/test_15d_source_health.py
  - python3 tests/manual/test_15d_source_health.py --help
  - python3 tests/manual/test_15d_source_health.py --test-write
  - python3 tests/manual/test_15d_source_health.py --test-dry-run
  - python3 tests/manual/test_15d_source_health.py --test-banner-zero
  - python3 tests/manual/test_15d_source_health.py --test-banner-streak
  - python3 tests/manual/test_15d_source_health.py --test-monthly
  - python3 tests/manual/test_15d_source_health.py --test-llm-client
constraints:
  - 不修改现有代码，不引入新依赖（仅用 stdlib）
  - 不执行真实网络请求；子测试独立可单独运行
  - 模拟数据在 /tmp/ 下操作，不污染 project 目录
