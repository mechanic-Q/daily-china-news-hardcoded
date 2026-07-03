---
id: task-01
title: 建立标准库 logging 基础入口
author: lmr
created_at: 2026-07-03 20:11:30
priority: P0
depends_on: []
blocks: [task-02, task-03]
requirement_ids: [FR-01]
decision_ids: [D-001@v1, D-002@v1]
allowed_paths: [daily_logging.py]
---

goal: >
  提供零新增依赖的 Daily logging 入口，让工程模块可写 stdout 与持久化日志。
implementation:
  - 新增 daily_logging.py，封装标准库 logging 配置。
  - 默认使用 INFO，可由 DAILY_LOG_LEVEL 覆盖。
  - 配置 stdout handler 和可失败降级的 file handler。
acceptance:
  - setup_logging 可重复调用且不重复添加 handler。
  - 不安装 loguru 或新增 logging 依赖。
  - 日志文件创建失败时 stdout 仍可用。
verify:
  - python3 -m pytest tests/test_llm_client.py
constraints:
  - 不修改 run_all.sh 或用户运行命令。
  - 不替换全 pipeline 的 print。
  - 文件 handler 错误不得阻断流水线。