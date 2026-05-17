## Project Reference

See: `.planning/PROJECT.md` (updated 2026-05-16)

**Core value:** 从多个中国新闻信源自动、确定性地采集当日新闻
**Current focus:** v1.1 Quality Fix — 正文提取乱码修复 + 左右栏平衡改进

## Status

active

## Last Activity

2026-05-17: Phase 6 executed — 正文提取修复 (5 tasks, 8/10 E2E passed)

## Current Position

Phase 6 complete — 正文提取修复（8/10 E2E passed, all quality checks ✅），待Phase 7

## Key Decisions

- Python 3: 已有代码全部 Python
- MiniMax M2.7: 摘要生成 LLM API（OpenAI SDK 兼容）
- .env + dotenv: API key 管理（非硬编码）
- 7 信源: 已验证稳定
- 保持平面脚本结构（不重构为包）
