## Project Reference

See: `.planning/PROJECT.md` (updated 2026-05-16)

**Core value:** 从多个中国新闻信源自动、确定性地采集当日新闻
**Current focus:** v1.1 Quality Fix — 正文提取乱码修复 + 左右栏平衡改进

## Status

active

## Last Activity

2026-05-17: Phase 7 execution complete — 左右栏平衡改进 (1 plan, 3 tasks, E2E passed)
2026-05-17: Phase 6 shipped — PR #3 merged (正文提取修复, 9/10 E2E)

## Current Position

Phase 7 execution complete — 左右栏平衡改进（视觉权重穷举），待verify/ship

## Key Decisions

- Python 3: 已有代码全部 Python
- MiniMax M2.7: 摘要生成 LLM API（OpenAI SDK 兼容）
- .env + dotenv: API key 管理（非硬编码）
- 7 信源: 已验证稳定
- 保持平面脚本结构（不重构为包）
- **分支策略（自Phase 6起）**: 每个 phase 的 discuss 阶段开头创建 feature 分支 `phase-NN-name`，所有 plan/execute/verify 的 commits 在该分支上进行，ship 时 push + gh pr create → merge
