---
id: task-04
title: 实现正文补全状态机（覆盖：FR-01, FR-02, D-001@v1, D-002@v1）
author: lmr
created_at: 2026-06-29 14:36:20
priority: P0
depends_on: [task-03]
blocks: [task-06, task-08]
requirement_ids: [FR-01, FR-02]
decision_ids: [D-001@v1, D-002@v1]
allowed_paths:
  - archive_enrich.py
  - tests/test_archive_enrich.py
goal: >
  实现正文补全状态机，确保 body 只来自 step6.fetch_and_extract，失败只写状态和错误。
implementation:
  - 实现 should_enrich_body(record, missing_only)
  - 实现 enrich_body(record)，调用 step6.fetch_and_extract(url, title)
  - 成功写 body/body_status/body_extracted_at/body_source_url
  - 失败写 body_status=failed/body_error，不写 fake body
  - 成功 archive_status=body-enriched，失败 archive_status=body-failed
acceptance:
  - missing/failed 状态需要补全，extracted/skipped 状态按 missing_only 跳过
  - fetch_and_extract 成功时 body_status=extracted 且 body 为原始提取正文
  - fetch_and_extract 失败时不写 body，body_error 记录原因
  - 不调用任何 LLM 接口或摘要逻辑
verify:
  - python3 tests/test_archive_enrich.py
constraints:
  - 不修改 step6.fetch_and_extract 契约
  - 禁止生成、润色、改写、补写正文
  - 不新增第三方依赖，不写 type hints
---
