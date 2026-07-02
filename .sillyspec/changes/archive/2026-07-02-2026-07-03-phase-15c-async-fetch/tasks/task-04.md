---
id: task-04
author: lmr
created_at: 2026-07-02 14:35:30
priority: P0
depends_on:
  - task-03
blocks:
  - task-06
requirement_ids:
  - FR-01
  - FR-02
decision_ids:
  - D-001@v1
  - D-002@v1
allowed_paths:
  - step1_3.py
---

# Task-04: 改造 fetch_cas 和 fetch_rmrb 使用 _async_fetch_many

## Goal

Replace serial per-URL `fetch_html_static` + `fetch_title` calls in `fetch_cas` and `fetch_rmrb` with `_async_fetch_many` batch calls. Fetcher signatures and output format unchanged.

## Implementation

1. `fetch_cas` — collect all deduplicated article URLs from CAS home page into a list; call `_async_fetch_many(urls)`; zip results with URLs, pass each HTML to `fetch_title`, append non-empty results.
2. `fetch_rmrb` — collect all layout board URLs (node_01-09), batch via `_async_fetch_many`; from each returned HTML parse content URLs; collect all content URLs into second batch via `_async_fetch_many`; extract titles with `fetch_title`.
3. `None` entries from `_async_fetch_many` treated as fetch failures (skip, same as current `try/except` behavior).
4. No new imports needed (task-03 already added `httpx`, `tenacity`, `asyncio`).

## Acceptance

- [x] No serial `fetch_html_static` per-article calls remain in `fetch_cas` or `fetch_rmrb` — all bulk fetches go through `_async_fetch_many`.
- [x] Output list format matches original: `[{"url": str, "title": str}, ...]`, same order guarantees as serial version.
- [x] `python3 -m py_compile step1_3.py` passes.

## Verify

```bash
python3 -m py_compile step1_3.py
```

## Constraints

- Keep `fetch_cas(today)` and `fetch_rmrb(today)` signatures.
- Keep output format identical to pre-change.
- Do not modify any other fetcher or `SOURCES`.
