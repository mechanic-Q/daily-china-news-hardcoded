# 每日新中国硬编码采集项目

## What This Is

从7个中国权威信源自动采集当日新闻的确定性 Python 管道，覆盖采集→分类→正文→摘要→报纸渲染全流程。输出可视化 PNG 报纸。

## Core Value

从多个中国新闻信源自动、确定性地采集当日新闻，消除 AI 驱动采集的不确定性。

## Requirements

### Validated

- ✓ Step 1+2（日期确认 + 工作目录创建）— v1.0
- ✓ Step 3（7 信源采集 + 三淘汰验证）— v1.0
- ✓ 7/7 信源工具链全通（181条/日）— v1.0
- ✓ `--dry-run` / `--date` 参数 — v1.0
- ✓ 8栏目分类 + 涉华过滤（step4.py）— v1.0
- ✓ 5层策略链正文提取（step6.py）— v1.0
- ✓ MiniMax M2.7 LLM 逐条摘要（step7.py）— v1.0
- ✓ 报纸渲染 HTML+PNG（step8.py）— v1.0
- ✓ run_all.sh 全管道串联 — v1.0

### Active

（暂无 — 等待下一 milestone 规划）

### Out of Scope

- UI/前端界面 — 纯 CLI 工具
- 实时推送 — 按需执行
- 多语言支持 — 仅中文新闻

## Context

Shipped v1.0 with 1,645 LOC Python across 6 scripts.
Pipeline: `run_all.sh → step1_3 → step4 → step6 → step7 → step8 → PNG`
Tech stack: Python 3, aiohttp, MiniMax M2.7 (LLM), chromium Headless, Pillow
Total phases: 5, plans: 7, UAT: all passed
Milestone timeline: 2026-05-15 → 2026-05-17 (3 days)
Git commits: 20, files changed: 444

Known tech debt:
- Summary text auto-concatenated from individual article key points
- chromium path hardcoded at `/snap/bin/chromium`
- Chinese ordinal issue numbers in filenames

## Constraints

- **环境**: Linux WSL，依赖 chromium v147
- **网络**: 需访问中国新闻网站
- **LLM**: Summary generation 是唯一需要 LLM 的步骤

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python 3 | 现有代码全部 Python | ✓ Good |
| chromium --dump-dom | JS 渲染站已验证可用 | ✓ Good |
| aiohttp 并发验证 | 53条 URL 0.5s | ✓ Good |
| 7 信源版 | 非 9 信源，已验证稳定 | ✓ Good |
| MiniMax M2.7 | OpenAI SDK 兼容，支持中文 | ✓ Good |
| step8.py 独立全流程 | 不依赖 render_newspaper.py | ✓ Good |
| 贪心双栏平衡 | 按内容长度动态分配左右栏 | ✓ Good |
| run_all.sh 串联 | 无参数默认今天日期 | ✓ Good |

---

*Last updated: 2026-05-17 after v1.0 milestone*
