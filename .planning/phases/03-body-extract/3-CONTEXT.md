# Phase 3: 正文提取 - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning

<domain>
## Phase Boundary

从 `1新闻_链接.md` 读取已分类的新闻条目，从对应 URL 提取正文内容，输出 `2新闻_已审核.md`。

</domain>

<decisions>
## Implementation Decisions

### D-01: 信源分流
- 静态源（新华社/人民日报/中科院）→ urllib 直接 HTTP 请求
- 央视系（央视新闻/央视军事）→ chromium --dump-dom 逐条提取
- 参考消息 → urllib + 关键词定位法（搜索"据…报道"截取至"责任编辑"前）
- 中核集团 → chromium --dump-dom（CF 保护）

### D-02: 5 层策略链
1. `<div class="TRS_Editor">` — 人民日报/中科院/新华社标准容器
2. `<article>` / `<div class="article-content/content/detail/main-content">` — 通用容器
3. 参考消息关键词定位法 — 从"据…报道"到"责任编辑"
4. 所有 `<p>` 标签兜底 — 过滤 `< 20` 字段落
5. 央视 chromium 长段提取 — chromium 获取完整 DOM 后提取 `>30` 字段落，过滤干扰词（copyright/icp/登录/央视网/二维码）

### D-03: 正文长度
- 无上限，全文保留

### D-04: 输出格式
- `2新闻_已审核.md`，格式：
  ```
  ## 【信源】标题
  来源：信源  发布时间：日期
  正文：正文内容
  ```
- 无 URL 残留

### D-05: 架构
- 独立脚本 `step6.py`，不合并
- `--date`、`--dry-run` 参数与 step1_3/step4 一致
- 从零重写，不引用旧 step6.py

### the agent's Discretion
- chromium --virtual-time-budget 超时值
- 央视干扰词的精确排除列表
- `<p>` 标签过滤的最小长度阈值

</decisions>

<canonical_refs>
## Canonical References

### 参考实现
- `/home/lmr/.hermes/skills/productivity/daily-china-news/scripts/step56_fetch_body.py` — 正文提取策略参考（88行）
- `/home/lmr/.hermes/skills/productivity/daily-china-news/scripts/step6_extract_body.py` — Step6 正文提取
- `/home/lmr/.hermes/skills/productivity/daily-china-news/references/cctv-extraction-workaround.md` — CCTV 正文提取问题

### 上游
- `/mnt/e/Daily/step4.py` — Phase 2 产出格式参考

</canonical_refs>

<deferred>
## Deferred Ideas
- 摘要生成 — Phase 4
- 报纸渲染 — Phase 5
</deferred>

---

*Phase: 03-body-extract*
*Context gathered: 2026-05-15*
