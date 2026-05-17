## Project Reference

See: `.planning/PROJECT.md` (updated 2026-05-16)

**Core value:** 从多个中国新闻信源自动、确定性地采集当日新闻
**Current focus:** 全管道完成 — Phase 1-5 全部 complete

## Status

active

## Last Activity

2026-05-17: Phase 5 executed — step8.py + run_all.sh (2/2 plans)

## Current Position

Phase: 5（报纸渲染）— Complete. UAT 10/10 passed. step8.py 可产出 HTML+PNG，run_all.sh 可串联全管道。

## Key Decisions

- Python 3: 已有代码全部 Python
- MiniMax M2.7: 摘要生成 LLM API（OpenAI SDK 兼容）
- .env + dotenv: API key 管理（非硬编码）
- 7 信源: 已验证稳定
