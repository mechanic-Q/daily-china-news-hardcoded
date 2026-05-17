# Phase 5: 报纸渲染 - Context

**Gathered:** 2026-05-17
**Status:** Ready for planning

<domain>
## Phase Boundary

从 `3新闻_概述.md`（step7.py 产出）生成可视化报纸，包含三个子步骤：
1. 解析 Markdown → 构造 JSON payload
2. 渲染 1080px 双栏报纸 HTML（内联 CSS）
3. chromium headless 截图 + Pillow 裁白边 → PNG

附加交付：`run_all.sh` 串联全管道（step1_3 → step4 → step6 → step7 → step8），支持 `--date YYYY-MM-DD` 参数。

不包含：新闻采集、分类、正文提取、摘要生成（Phase 1-4 已完成）。
</domain>

<decisions>
## Implementation Decisions

### D-01: 架构 — step8.py 独立全流程
- 写一个 `step8.py` 完成全部：解析 `3新闻_概述.md` → 构造 JSON → 渲染 HTML → 截图 PNG
- 不调用 `render_newspaper.py`，但从其提取设计思路（双栏布局、报头、CSS 样式）
- 与管道风格一致：`--date`、`--dry-run` 参数

### D-02: 浏览器截图方案
- 使用系统已有的 chromium（step6.py 已在用）
- headless 模式截图：`--headless=new --disable-gpu --force-device-scale-factor=2`
- 窗口尺寸：宽度 1080px（匹配 HTML 报纸宽度），高度给超长值（如 10000px）后 Pillow 裁白边
- Pillow 裁白边逻辑沿用 render_newspaper.py 的 `crop_bottom_whitespace`

### D-03: 报头信息
- 报纸名称：`紫音简报`
- 期号：从 2026-04-19 起算，第 N 天 = 第 N 期（中文序数：第一期、第二期...）
- 日期格式：`YYYY年M月D日 星期X`
- 页脚：沿用原 skill（`Mobile Brief` 印章）

### D-04: 8 栏→双栏布局 — 动态平衡
- 不固定分配，按每栏目实际内容长度（摘要字数）动态分配到左/右栏
- 目标：左右栏高度尽量接近
- 分配算法：贪心策略（按栏目顺序，每次把当前栏目放到总高度较短的栏）

### D-05: HTML 视觉风格
- 沿用 render_newspaper.py 的报纸风格
- 1080px 宽、`#f6f1e6` 仿纸背景、`#141414` 墨色文字、`#c0392b` 朱砂红点缀
- 双栏 grid 布局 + 2px 分隔线
- 内联 CSS（不依赖外部样式表）
- 字体栈：Microsoft YaHei / PingFang SC / Noto Sans CJK SC

### D-06: 全管道串联脚本
- 写 `run_all.sh`，按序调用 step1_3.py → step4.py → step6.py → step7.py → step8.py
- 参数：`--date YYYY-MM-DD`（必填），`--dry-run`（可选）
- 某步失败（exit code ≠ 0）则停止执行
- `--date` 传递给每一步

### the agent's Discretion
- JSON payload 的具体字段命名（参考 render_newspaper.py 的 `columns` 结构）
- Markdown→JSON 的解析细节（标题匹配、空栏目处理、弯引号规范化）
- 动态平衡算法的具体实现（贪心/DP）
- CSS 细节（字号、行高、间距）——沿用原 skill 即可
- `--dry-run` 在 step8 中的具体行为（生成 HTML 但不截图？还是只打印预览？）
- Pillow 裁白边的 padding 参数
- step8.py 的具体行数预估和函数拆分
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 核心参考实现
- `/home/lmr/.hermes/profiles/glm51/skills/productivity/newspaper-brief/scripts/render_newspaper.py` — 报纸渲染参考实现（820行），含 JSON 规范化、HTML 模板、截图逻辑。MUST READ — 提取设计思路但不要直接调用

### 上游数据
- `/mnt/e/Daily/step7.py` — 摘要生成脚本，产出 `3新闻_概述.md`（Phase 5 的输入）
- `/mnt/e/Daily/step6.py` — 正文提取脚本（使用 chromium 的参考）
- `/mnt/e/Daily/step4.py` — 分类筛选脚本

### 输入格式规范
- `/home/lmr/.hermes/skills/productivity/daily-china-news/SKILL.md` — Step 7 定义了 `3新闻_概述.md` 格式（##栏目 + ###标题 + 摘要）

### Phase 4 决策上下文
- `/mnt/e/Daily/.planning/phases/04-summary-gen/4-CONTEXT.md` — D-03 锁定了输出格式，D-05 锁定了独立脚本架构
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **chromium headless**: step6.py 已在 PATH 上使用 `chromium --dump-dom`，step8 截图可复用同一 binary
- **Pillow**: render_newspaper.py 中 `crop_bottom_whitespace` 可直接移植
- **render_newspaper.py 的 build_html()**: 1080px 双栏报纸 HTML 模板，可提取 CSS 和结构

### Established Patterns
- **CLI 参数**: 所有 step 脚本统一使用 `--date YYYY-MM-DD` + `--dry-run`，parse_args() 模式一致
- **数据路径**: `/mnt/e/每日新中国/{date}/` 目录结构，`{N}新闻_{描述}.md` 文件命名
- **文件编码**: 所有中间文件 UTF-8

### Integration Points
- **输入**: `/mnt/e/每日新中国/{date}/3新闻_概述.md`（step7.py 产出）
- **输出**: `/mnt/e/每日新中国/{date}/4新闻_报纸.html` + `4新闻_报纸.png`
- **run_all.sh**: 放在 `/mnt/e/Daily/run_all.sh`，调用同目录下的 step 脚本
</code_context>

<specifics>
## Specific Ideas

- 截图方案：按 HTML 实际尺寸截图，不需要额外缩放。2x scale factor 确保 PNG 清晰
- 测试策略：先用手工构造的 `3新闻_概述.md` 测试 step8 基本功能，再跑完整管道做端到端回归
- `run_all.sh --date` 控制采集哪天的新闻，日期参数传递给每一步
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope
</deferred>

---

*Phase: 05-newspaper-render*
*Context gathered: 2026-05-17*
