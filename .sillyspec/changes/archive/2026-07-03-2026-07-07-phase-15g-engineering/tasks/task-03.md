---
id: task-03
title: 增加 LLM 脱敏回归测试
author: lmr
created_at: 2026-07-03 20:11:30
priority: P0
depends_on: [task-02]
blocks: [task-06, task-08]
requirement_ids: [FR-02]
decision_ids: [D-001@v1, D-002@v1]
allowed_paths: [tests/test_llm_client.py]
---

goal: >
  用单元测试锁定 LLM 异常脱敏行为，避免后续回归泄露敏感值。
implementation:
  - 模拟 client.chat.completions.create 抛出含假密钥的异常。
  - 捕获日志和 LLMCallError 文案。
  - 断言 fake API key 与 Authorization 均未出现。
acceptance:
  - 测试不读取 .env。
  - 测试不发起真实 LLM 或网络请求。
  - 失败路径仍抛出 LLMCallError。
verify:
  - python3 -m pytest tests/test_llm_client.py
constraints:
  - 只覆盖脱敏行为。
  - 假密钥必须是测试内硬编码假值。
  - 不修改生产调用点。
