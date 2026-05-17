# Phase 7: 左右栏平衡改进 - Context

**Gathered:** 2026-05-17
**Status:** Ready for planning

<domain>
## Phase Boundary

改进 step8.py 的 `balance_columns()` 函数，用视觉权重估算替代纯字符计数贪心分配，使左右两栏的渲染高度更接近平衡。

不包含：CSS 样式修改（Phase 5）、布局结构重做、新信源接入、正文提取/摘要生成相关改动。

</domain>

<decisions>
## Implementation Decisions

### 权重公式设计
- **D-01:** 标定公式，非直接移植原始 skill。当前 step8.py 的数据结构（heading + items[title+summary]）与原始 skill（body + bullets）不同，公式重新标定：
  - `weight = 4.5(卡片固定开销) + Σ(1.2 + text_len/90 per item)`
  - `4.5` 覆盖 section-card 的 border-top + padding-top + margin-bottom + heading
  - `1.2` 覆盖每个 `<li>` 的 margin-bottom + `::before` bullet 空间
  - `text_len/90` 估算文本行数贡献（24px font, line-height 1.73, 约 21 字/行 → 90 字符 ≈ 4 行）

### 分配算法
- **D-02:** 穷举最优。8 个栏目 = 2^8 = 256 种组合，枚举所有分配方案找到差值最小的分配。代码复杂度可控，保证最优解。

### 栏目拆分策略
- **D-03:** 不拆分。同一个 heading 下的所有文章作为一个整体分配，保持视觉一致性。穷举在 8 个不可拆分组的情况下已足够。

### the agent's Discretion
- 公式中的具体系数（4.5、1.2、90）可以在 plan 阶段微调
- 穷举算法的实现风格（位掩码枚举 vs 递归回溯）
- 是否需要为空的列分配做特殊处理

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 要修改的代码
- `step8.py` — Phase 7 要修改的目标脚本，`balance_columns()` 函数（第 132-155 行）
- `/home/lmr/.hermes/profiles/glm51/skills/productivity/newspaper-brief/scripts/render_newspaper.py` — 原始 skill 的 `estimate_section_weight()` 函数（第 206-212 行），参考其权重公式思路

### 上游决策
- `.planning/milestones/v1.1-REQUIREMENTS.md` — v1.1 需求追踪表（BAL-01, BAL-02）
- `.planning/phases/05-render-newspaper/5-CONTEXT.md` — Phase 5 的 CSS 布局决策

### 参考数据
- `/mnt/e/每日新中国/2026-05-17/3新闻_概述.md` — step8 的输入数据，测试平衡效果

</canonical_refs>

<code_context>
## Existing Code Insights

### 被修改的代码
- `step8.py:132-155` — `balance_columns()`：当前用 `len(heading)+len(title)+len(summary)` 计算字符数，贪心分配左右栏
- `step8.py:176-366` — `build_html()`：输出 HTML 使用 grid 双栏布局（`grid-template-columns: 1fr 2px 1fr`）

### Established Patterns
- Phase 5 的 CSS 固定参数：section-card 标题 32px、`<li>` 24px font `line-height: 1.73`、margin-bottom 10px、bullet 12px 圆点
- 8 栏目固定顺序（`COLUMN_ORDER`）

### Integration Points
- 输入：`3新闻_概述.md`（step7.py 产出）
- 输出：左右栏分组的栏目列表 → `build_html()`
- 输出格式不变（相同的 data structure），只改分配逻辑

</code_context>

<specifics>
## Specific Ideas

- 原始 skill 的 `estimate_section_weight()` 用 `2.8 + len(body)/140` 做基础权重，每 bullet 加 `1.2 + len(bullet)/90`。当前 step8 的结构不同于 bullets，但文本密度和行数估算的思路可以直接沿用
- 穷举用位掩码：0 左 1 右，从 0 遍历到 2^n-1，记录每个 mask 的左右差值

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-column-balance*
*Context gathered: 2026-05-17*
