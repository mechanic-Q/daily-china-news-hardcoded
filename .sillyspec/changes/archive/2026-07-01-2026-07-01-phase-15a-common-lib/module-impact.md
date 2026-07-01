---
author: lmr
created_at: 2026-07-01 21:20:00
schema_version: 1
doc_type: module-impact
change_id: 2026-07-01-phase-15a-common-lib
---

# Module Impact — Phase 15A common lib

## File Change Matrix

| File | Module | Impact Type | Summary | needs_review |
|------|--------|-------------|---------|-------------|
| daily/__init__.py | — (new) | 新增 | Package entry point | false |
| daily/common.py | — (new) | 新增 | Shared constants, path, date, source detection | false |
| daily/http.py | — (new) | 新增 | HTTP/Chromium helpers | false |
| step1_3.py | collector | 调用关系变更 | Imports from daily.common/daily.http instead of local defs | false |
| step4.py | classifier | 调用关系变更 | Imports COLUMN_ORDER/detect_source/BASE_DIR from daily.common | false |
| step6.py | extractor | 调用关系变更 | Imports from daily.common/daily.http with re-export | false |
| step7.py | summarizer | 调用关系变更 | Imports BASE_DIR/COLUMN_ORDER/parse_args from daily.common | false |
| step8.py | renderer | 调用关系变更 | Imports BASE_DIR/COLUMN_ORDER/WEEKDAYS/parse_args from daily.common | false |
| news_archive.py | archiver | 调用关系变更 | Imports BASE_DIR/CST/detect_source; infer_source shim | false |
| archive_enrich.py | archiver | 调用关系变更 | Imports CST/SSL_CTX from daily | false |
| monthly_report.py | monthly | 调用关系变更 | Imports BASE_DIR/COLUMN_ORDER/CST; special parse_args preserved | false |
| perf_profile.py | profiler | 调用关系变更 | Imports BASE_DIR from daily.common | false |
| .env.example | — | 新增 | DAILY_OUTPUT_DIR example | false |
| tests/manual/__init__.py | — | 新增 | Test package | false |
| tests/manual/test_15a_diff_smoke.py | — | 新增 | Manual smoke diff script | false |

## Unmatched Files

None — all changed files in the git diff map to known modules.

## Module Dependency Impact

| Module | depends_on | Affected by Phase 15A | Notes |
|--------|-----------|----------------------|-------|
| collector | — | Yes | Import path changed |
| classifier | collector | Yes | Import path changed |
| extractor | classifier | Yes | Import + re-export |
| summarizer | extractor | Yes | Import path changed |
| renderer | summarizer | Yes | Import path changed |
| archiver | extractor | Yes | Import path changed + shim |
| monthly | archiver, llm-client | Yes | Import path changed |
| profiler | — | Yes | Import path changed |
| llm-client | — | No | Unchanged |
| orchestrator | all | No | run_all.sh unchanged |

## Conclusion

Phase 15A is a pure refactor affecting import paths only. No logic, schema, or API changes. All 8 source modules plus profiler use the new daily/ package. Runnable behavior is unchanged.
