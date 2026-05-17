# Plan 1: 过滤摘要健壮性 — Summary

**Completed:** 2026-05-17
**Files modified:** step4.py, step7.py

## What was built

### Key changes

| Function | File | Change |
|----------|------|--------|
| `is_quality_news()` | step4.py | 增加 EXCLUDE_NEGATIVE 检查 + is_china_related() 涉华检测 |
| `is_china_related(title)` | step4.py | 新增 — 去噪后检查 CHINA_KEYWORDS 是否涉华 |
| `classify()` 扶贫关键词 | step4.py | 去掉"乡村振兴"/"新就业形态"，新增"精准扶贫"/"易地搬迁" |
| `is_valid_summary(summary, body)` | step7.py | 新增 — 检测长度/截断/原文片段 |
| `llm_summarize()` | step7.py | 精简 prompt + 无效摘要触发回退 |

### E2E results (2026-05-17 data)

- ✅ step4: 194条→52条→5条精选（纯外国/负面已过滤，扶贫无泛匹配）
- ✅ step7: 摘要83字/2句话，无截断
- ✅ step8: HTML+PNG 正常生成

### Requirements covered

- SUM-01: 摘要结果质量验证（is_valid_summary）✅
- SUM-02: 长正文截断保护（不设硬上限，通过 prompt 精简）✅
- SUM-03: 无效摘要回退（llm_summarize 返回 None 触发 fallback）✅
