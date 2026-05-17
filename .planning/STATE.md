## Project Reference

See: `.planning/PROJECT.md` (updated 2026-05-16)

**Core value:** 从多个中国新闻信源自动、确定性地采集当日新闻
**Current focus:** v1.1 Quality Fix — 正文提取乱码修复 + 左右栏平衡 + 摘要健壮性

## Status

active

## Last Activity

2026-05-17: Phase 8 execution complete — 过滤摘要健壮性 (step4+step7, E2E passed)
2026-05-17: Phase 7 shipped — PR #4 merged (纯字数权重, WGT-01修复, UAT 5/5)
2026-05-17: Phase 6 shipped — PR #3 merged (正文提取修复, 9/10 E2E)

## Current Position

Phase 8 execution complete — 过滤摘要健壮性 (step4+step7)
Phase 7 shipped — PR #4 merged
Phase 8 UAT pending

## Key Decisions

- Python 3: 已有代码全部 Python
- MiniMax M2.7: 摘要生成 LLM API（OpenAI SDK 兼容）
- .env + dotenv: API key 管理（非硬编码）
- 7 信源: 已验证稳定
- 保持平面脚本结构（不重构为包）
- **分支策略（自Phase 6起）**: 每个 phase 的 discuss 阶段开头创建 feature 分支 `phase-NN-name`，所有 plan/execute/verify 的 commits 在该分支上进行，ship 时 push + gh pr create → merge
