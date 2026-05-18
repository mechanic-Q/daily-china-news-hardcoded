## Project Reference

See: `.planning/PROJECT.md` (updated 2026-05-16)

**Core value:** 从多个中国新闻信源自动、确定性地采集当日新闻
**Current focus:** v1.1 Quality Fix — 正文提取乱码修复 + 左右栏平衡 + 摘要健壮性

## Status

active

## Last Activity

2026-05-18: Phase 9 shipped — PR #6 merged (智能分类 C+D混合, UAT 8/8)
2026-05-18: Phase 8 shipped — PR #5 merged (过滤摘要健壮性, UAT 10/10)

## Current Position

Phase 9 shipped — PR #6 merged (智能分类 C+D混合, UAT 8/8)
v1.1 Quality Fix complete (Phases 6-9)

## Key Decisions

- Python 3: 已有代码全部 Python
- MiniMax M2.7: 摘要生成 LLM API（OpenAI SDK 兼容）
- .env + dotenv: API key 管理（非硬编码）
- 7 信源: 已验证稳定
- 保持平面脚本结构（不重构为包）
- **分支策略（自Phase 6起）**: 每个 phase 的 discuss 阶段开头创建 feature 分支 `phase-NN-name`，所有 plan/execute/verify 的 commits 在该分支上进行，ship 时 push + gh pr create → merge
