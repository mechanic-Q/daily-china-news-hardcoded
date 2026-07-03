---
id: task-02
title: 为 LLM 调用失败路径加入脱敏日志与错误文案
author: lmr
created_at: 2026-07-03 20:11:30
priority: P0
depends_on: [task-01]
blocks: [task-03, task-08]
requirement_ids: [FR-02]
decision_ids: [D-001@v1, D-002@v1]
allowed_paths: [llm_client.py, daily_logging.py]
---

goal: >
  让 call_llm 失败时记录安全摘要并抛出不含敏感上下文的 LLMCallError。
implementation:
  - 移除 call_llm 中的 traceback.print_exc 路径。
  - 记录 call_site_id、异常类型、status_code、error_code。
  - 保持 call_llm 签名和 LLMCallError 控制流。
acceptance:
  - 异常日志不包含 API key 或 Authorization。
  - step4、step7、monthly_report 调用点无需修改。
  - LLMCallError 文案不拼接完整异常对象。
verify:
  - python3 -m pytest tests/test_llm_client.py
constraints:
  - 不改真实 LLM provider 配置。
  - 不吞掉原异常链。
  - 不记录 request headers。
