# 每日新中国硬编码采集项目

## What This Is

将原 daily-china-news Hermes skill（AI 驱动新闻采集流程）改造成确定性 Python 脚本。从7个中国权威信源自动采集当日新闻，通过三淘汰验证输出标准格式候选新闻列表。

## Core Value

从多个中国新闻信源自动、确定性地采集当日新闻，消除 AI 驱动采集的不确定性。

## Requirements

### Validated

- ✓ Step 1+2（日期确认 + 工作目录创建）
- ✓ Step 3（7 信源采集 + 三淘汰验证）
- ✓ 7/7 信源工具链全通（181条/日）
- ✓ `--dry-run` / `--date` 参数

### Active

- [ ] 保存代码到 git 仓库
- [ ] 注册远程仓库并推送
- [ ] Phase 2：性能优化与 bug 修复
- [ ] Phase 3：分类筛选
- [ ] Phase 4：正文提取
- [ ] Phase 5：摘要生成
- [ ] Phase 6：报纸渲染

### Out of Scope

- UI/前端界面 — 纯 CLI 工具
- 实时推送 — 按需执行
- 多语言支持 — 仅中文新闻

## Context

原始 skill：`/home/lmr/.hermes/skills/productivity/daily-china-news/`
参考脚本：`fetch_9src.py`、`classify_and_filter.py`
依赖：`/snap/bin/chromium`、Python 3、`aiohttp`

## Constraints

- **环境**: Linux WSL，依赖 chromium v147
- **网络**: 需访问中国新闻网站
- **LLM**: Step 5 摘要生成是唯一需要 LLM 的步骤

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python 3 | 现有代码全部 Python | ✓ Good |
| chromium --dump-dom | JS 渲染站已验证可用 | ✓ Good |
| aiohttp 并发验证 | 53条 URL 0.5s | ✓ Good |
| 7 信源版 | 非 9 信源，已验证稳定 | ✓ Good |

---

*Last updated: 2026-05-15 after initialization*
