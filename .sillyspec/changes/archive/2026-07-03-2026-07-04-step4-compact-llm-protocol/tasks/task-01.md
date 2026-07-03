---
id: task-01
title: 新增涉华位串 parser 与单元测试
author: lmr
created_at: 2026-07-04 00:38:17
priority: P0
depends_on: []
blocks: [task-04]
requirement_ids: [FR-01]
decision_ids: [D-001@v1]
allowed_paths: [step4.py, tests/test_step4.py]
---

## goal

Add pure bitstring parser returning list[bool].

## implementation

Parse "101101" -> [True, False, True, True, False, True].
Reject non-binary chars with ValueError.
One pure function, no state.

## acceptance

Parser exists in step4.py under a private bitstring parser function.
Tests cover empty, valid, invalid inputs.

## verify

```
python3 -m pytest tests/test_step4.py -k bitstring -v
```

## constraints

No algorithm changes beyond parser. No new deps. No llm/yaml/archive changes.
