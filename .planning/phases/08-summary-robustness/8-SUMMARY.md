# Plan 1: 过滤摘要健壮性 — Summary

**Completed:** 2026-05-17
**Files modified:** step4.py, step7.py

## What was built

### Key changes

| Function | File | Change |
|----------|------|--------|
| `is_quality_news()` | step4.py | 增加 EXCLUDE_NEGATIVE 检查 |
| `is_china_related(title)` | step4.py | 新增 — 80+ CHINA_KEYWORDS 涉华检测 |
| `is_china_source(url)` | step4.py | 新增 — 中国官方信源域名白名单 |
| `llm_is_china_related(title)` | step4.py | 新增 — LLM二次确认（D-01双重过滤） |
| `classify()` 扶贫关键词 | step4.py | 去掉"乡村振兴"/"新就业形态"，新增"精准扶贫"/"易地搬迁" |
| `llm_summarize()` | step7.py | 精简prompt + is_valid_summary检测 + 回退 |
| `is_valid_summary(summary, body)` | step7.py | 新增 — 长度/截断/原文片段检测 |

### E2E results (2026-05-17 data)

- ✅ step4: 194条→103条移除→91条→10条精选
- ✅ step7: 4/5 API成功，摘要精简（64-117字）
- ✅ step8: HTML+PNG 正常生成（5栏目，左右平衡）

### Requirements covered

- SUM-01: 摘要结果质量验证（is_valid_summary）✅
- SUM-02: 长正文截断保护（不设硬上限，通过 prompt 精简）✅
- SUM-03: 无效摘要回退（llm_summarize 返回 None 触发 fallback）✅
