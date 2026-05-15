## Project Reference

See: `.planning/PROJECT.md` (updated 2026-05-16)

**Core value:** 从多个中国新闻信源自动、确定性地采集当日新闻
**Current focus:** 摘要生成（Phase 4）

## Status

active

## Last Activity

2026-05-16: Phase 4 shipped — PR #1 created

## Current Position

Phase: 4 shipped — PR #1 open (https://github.com/mechanic-Q/daily-china-news-hardcoded/pull/1)
Next: Phase 5（报纸渲染）— JSON 生成 + HTML 渲染 + PNG 截图

## Key Decisions

- Python 3: 已有代码全部 Python
- MiniMax M2.7: 摘要生成 LLM API（OpenAI SDK 兼容）
- .env + dotenv: API key 管理（非硬编码）
- 7 信源: 已验证稳定
