# Phase 6: 正文提取修复 - Context

**Gathered:** 2026-05-17
**Status:** Ready for planning

<domain>
## Phase Boundary

修复 step6.py 的正文提取策略链，消除提取结果中的污染（JS代码、CSS样式、HTML实体未解码、视频播放器UI文字、导航垃圾），改进提取健壮性。不改动现有策略链的流程结构，只增强清洗和验证。

不包含：左右栏平衡改进（Phase 7）、summary生成（Phase 4）、新信源接入。

</domain>

<decisions>
## Implementation Decisions

### D-01: 清洗层级 — 两层都做
- **提取前预处理**：剥离所有`<script>...</script>`和`<style>...</style>`块后再进入策略链
- **提取后后处理**：调用`html.unescape()`解码HTML实体（`&ldquo;`→`"`、`&mdash;`→`—`、`&nbsp;`→空格等）
- **提取后清理**：剥离视频播放器标记（`[!--begin:htmlVideoCode--]...[!--end:htmlVideoCode--]`）和播放器UI文字（具体模式由agent决定）

### D-02: 人民日报专用策略 — 并入现有层2
- 在层2的通用div搜索列表新增`<div id="ozoom">`pattern
- 最小改动，不新增代码路径或URL分流逻辑

### D-03: 验证回退 — 清理+重试
- 提取→污染检测→不通过→清理HTML后重提取→再验证→仍不通过→标记`[正文提取失败: 未找到正文区域]`
- 污染检测用模式匹配：CSS规则模式（`{`、`font-family`、`margin`、`padding`）、JS代码模式（`var `、`function(`、`$(`）、导航垃圾（`日报`、`周报`、`杂志`等）
- 具体检测阈值和模式列表由agent决定

### D-04: 内容去重
- 在`extract_body()`返回前检测并去除连续重复的段落
- 避免LLM调用浪费在重复内容上

### the agent's Discretion
- 视频标记和播放器UI文字的具体清理正则
- 污染检测的具体pattern列表和阈值
- `<p>`标签聚合时的噪声过滤词表更新

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 要修复的代码
- `step6.py` — Phase 6 要修改的目标脚本（正文提取+5层策略链）

### 信源页面结构（污染来源分析）
- 参考消息 JS 混入：页面内嵌`<script>`块通过关键词定位法被捕获
- 央视新闻 HTML实体 + 视频标记：`[!--begin:htmlVideoCode--]` + `&ldquo;`等未解码
- 人民日报 CSS/导航污染：`#ozoom`内容区未匹配，退到整页`<p>`聚合

### 参考数据（5月17日污染样本）
- `/mnt/e/每日新中国/2026-05-17/2新闻_已审核.md` — 污染后的正文提取结果

### 上游决策
- `.planning/phases/03-body-extract/3-CONTEXT.md` — Phase 3 D-01（信源分流）、D-02（5层策略链）、D-04（输出格式）
- `.planning/milestones/v1.1-REQUIREMENTS.md` — v1.1 需求追踪表（EXT-01 到 EXT-05）

</canonical_refs>

<code_context>
## Existing Code Insights

### 被修复的代码
- `step6.py` 的 `extract_body()` 函数 — 5层策略链的入口，需要在第一行执行前做HTML预处理
- `step6.py` 的 `fetch_and_extract()` — 在调用`extract_body()`返回后添加后处理（实体解码、视频标记清理、去重）
- `step6.py` 的 `needs_chromium()` — 信源分流逻辑，不需要修改

### Established Patterns
- CLI参数：所有step脚本统一`--date YYYY-MM-DD` + `--dry-run`
- 数据路径：`/mnt/e/每日新中国/{date}/`
- 5层策略链的失败回退顺序（TRS_Editor → 通用容器 → 关键词 → `<p>`兜底 → chromium）

### Integration Points
- 输入：`/mnt/e/每日新中国/{date}/1新闻_链接.md`（step4.py产出）
- 输出：`/mnt/e/每日新中国/{date}/2新闻_已审核.md`（step7.py的输入）
- 输出格式不变，不改变下游脚本

</code_context>

<specifics>
## Specific Ideas

- 预处理应在`extract_body()`函数内部进行，对传入的html字符串先strip script/style block
- 后处理（实体解码、视频标记清理）放在`fetch_and_extract()`中`extract_body()`返回之后
- 避免修改现有策略链的搜索顺序——只增强，不重排
- 去重逻辑：按`。`或`\n`分割成段落，检测连续相同段落后只保留一份

</specifics>

<deferred>
## Deferred Ideas

- 左右栏平衡改进 — Phase 7
- LLM报纸概述替换auto-concatenation — 后续milestone
- 代码质量（logging/config/utils提取）— 后续milestone

</deferred>

---

*Phase: 06-fix-body-extract*
*Context gathered: 2026-05-17*
