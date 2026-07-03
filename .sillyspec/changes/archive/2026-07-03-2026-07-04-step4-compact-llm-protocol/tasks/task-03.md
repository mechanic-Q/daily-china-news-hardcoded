---
id: task-03
title: 增强 llm_client 空 content 诊断
author: lmr
created_at: 2026-07-04 00:38:17
priority: P0
depends_on: []
blocks: [task-06]
requirement_ids: [FR-05]
decision_ids: [D-004@v1]
allowed_paths:
  - llm_client.py
  - tests/test_llm_client.py
---

## goal

fail fast on empty message.content with finish_reason/content_len/reasoning_len diagnostics

## implementation

in call_llm(), before returning resp.choices[0].message.content, check if content is None or empty string. when empty, log finish_reason, len(content or ''), len(reasoning_content or '') at error level, then raise LLMCallError with finish_reason baked into message

## acceptance

AC-05: empty message.content raises LLMCallError, log includes finish_reason/content_len/reasoning_len

## verify

python3 -m pytest tests/test_llm_client.py -v

## constraints

no secret logging, preserve existing API/key errors, no hardcoded call-site policy here
