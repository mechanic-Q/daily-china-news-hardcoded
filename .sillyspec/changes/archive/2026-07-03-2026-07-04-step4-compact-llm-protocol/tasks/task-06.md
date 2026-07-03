---
id: task-06
title: 为 low 调用注入 reasoning 和输出预算
author: lmr
created_at: 2026-07-04 00:38:17
priority: P0
depends_on:
  - task-03
blocks:
  - task-07
requirement_ids:
  - FR-04
decision_ids:
  - D-004@v1
allowed_paths:
  - step4.py
  - llm.yaml
  - tests/test_step4.py
  - tests/test_llm_client.py
---

## goal

compact protocol call sites send reasoning_effort none and max_tokens 262144 for low model.

## implementation

Add reasoning_effort=none and max_tokens=262144 to compact protocol call_llm invocations for low model. Wire through extra_body parameter support.

## acceptance

integration test confirms reasoning_effort=none is sent. max_tokens 262144 applied without truncation.

## verify

python3 -m pytest tests/test_llm_client.py tests/test_step4.py -v

## constraints

do not alter unrelated call sites; do not change scoring algorithms; keep provider secrets out of logs.
