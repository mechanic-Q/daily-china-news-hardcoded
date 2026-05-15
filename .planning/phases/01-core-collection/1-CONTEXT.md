# Phase 1: 基础采集与优化 - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning

<domain>
## Phase Boundary

从 7 个中国信源自动采集当日新闻，通过确定性 Python 代码替代原 AI 驱动的 Hermes skill，完成 Step 1-3 硬编码化和代码优化。

</domain>

<decisions>
## Implementation Decisions

### D-01: Python 3 + chromium --dump-dom
- 原 Hermes skill 的 AI 驱动采集存在不确定性（LLM 可能编造 URL/标题）
- 改用 Python 3 正则从真实 DOM 提取，确保数据来源可靠
- JS 渲染站（央视系、新华社）用 chromium --dump-dom

### D-02: 验证简化为仅 HTTP 200
- 原三淘汰（HTTP 200 + 标题匹配 + 日期核对）是为防止 LLM 编造
- Python 正则从真实 DOM 提取 URL，不存在编造风险
- 保留 aiohttp 并发 HTTP 200 检查（192 条 0.5 秒）
- 去掉 chromium 逐条验证（从 ~10 分钟缩短至 ~1 分钟）

### D-03: 7 信源最终版
- 非原 9 信源版本，已验证稳定的 7 个
- 新华社、参考消息、央视新闻、央视军事、中科院、中核集团、人民日报

### D-04: 中核集团三级降级链
- ① chromium --dump-dom cnnc.com.cn（Cloudflare 页面）
- ② cnnpn.cn 聚合站（CF 绕过）
- ③ 标注技术不可达

### D-05: aiohttp 并发
- 静态源验证使用 aiohttp 并发请求
- 192 条 URL 验证耗时 < 1 秒

### D-06: SOURCES 元组重构
- 统一采集函数返回格式，消除 `if name == "中核集团"` 特殊分支
- 所有信源共用单一 `verify_http()` 验证函数

### the agent's Discretion
- 各信源采集工具的 `--virtual-time-budget` 超时参数
- 新闻质量排除列表（节气/文艺等）在 Phase 2 实施

</decisions>

<canonical_refs>
## Canonical References

### 原始 skill
- `/home/lmr/.hermes/skills/productivity/daily-china-news/SKILL.md` — 原始 AI skill 完整参考
- `/home/lmr/.hermes/skills/productivity/daily-china-news/references/date-formats.md` — 各信源 URL 日期格式

### 参考实现
- `/home/lmr/.hermes/skills/productivity/daily-china-news/scripts/fetch_9src.py` — 采集模板参考
- `/home/lmr/.hermes/skills/productivity/daily-china-news/references/aiohttp-concurrency-pattern.md` — aiohttp 并发模式

### 交付代码
- `/mnt/e/Daily/step1_3.py` — 最终产出

</canonical_refs>

<deferred>
## Deferred Ideas

- 分类筛选 — Phase 2
- 正文提取 — Phase 3
- 报纸渲染 — Phase 4
- 新闻质量排除列表 — Phase 2

</deferred>

---

*Phase: 01-core-collection*
*Context gathered: 2026-05-15*
