---
id: task-05
title: static-first Chromium fallback
author: lmr
created_at: 2026-07-02 14:35:30
priority: P0
depends_on:
  - task-03
blocks:
  - task-06
requirement_ids:
  - FR-03
decision_ids:
  - D-001@v1
allowed_paths:
  - step1_3.py
---

## Goal

Modify `fetch_home_html` so it tries `fetch_html_static` first and only falls back to `chromium_dom` when static HTML is empty, too short (<500 chars), or lacks key selectors. Affects fetchers that route through `fetch_home_html`: xinhuanet, cctv_news, cctv_military, cnnc_chromium. `fetch_cas` and `fetch_rmrb` call `fetch_html_static` directly and are unchanged by this task.

## Implementation

1. Add `_is_static_sufficient(html: str, required_selectors: list[str] = []) -> bool` helper: returns `False` if html is empty, stripped length < 500, or any required selector regex is missing.
2. Modify `fetch_home_html(url, required_selectors=[])` signature: call `fetch_html_static` first → check `_is_static_sufficient(result, required_selectors)` → if sufficient, return result; otherwise fall back to `chromium_dom(url)`.
3. Update callers in `fetch_xinhuanet`, `fetch_cctv_news`, `fetch_cctv_military`: pass source-specific required selectors (e.g. `news.cn` anchor pattern, `.shtml` link presence) to `fetch_home_html`.
4. Keep `fetch_cas` and `fetch_rmrb` on direct `fetch_html_static` — static-only is correct for cas.cn / paper.people.com.cn.

## Acceptance

- [x] `fetch_xinhuanet` with `--dry-run` returns ≥1 article when static HTML is sufficient (no chromium subprocess launched).
- [x] `fetch_cctv_news` with `--dry-run` behaves identically to current output when static HTML is sufficient.
- [x] When static HTML is blocked/empty, `fetch_home_html` falls back to `chromium_dom` and output matches current behavior.

## Verification

```bash
python3 -m py_compile step1_3.py
```

## Constraints

- Keep all fetcher signatures `def fetch_*(today) -> list[dict{url, title}]` unchanged.
- Keep `needs_chromium` logic in other modules (daily/http.py, step6, step7) untouched.
- `fetch_cas` and `fetch_rmrb` must NOT call `chromium_dom` — they remain static-only.
