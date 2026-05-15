# Phase 4: 摘要生成 - Context

**Gathered:** 2026-05-16
**Status:** Ready for planning

<domain>
## Phase Boundary

从 `2新闻_已审核.md` 读取已提取正文的新闻，调用 LLM API 逐条生成 2-3 句摘要，输出 `3新闻_概述.md`，供后续 Phase 5 报纸渲染使用。

不包含 JSON 生成、HTML 渲染、PNG 截图（移至 Phase 5）。
</domain>

<decisions>
## Implementation Decisions

### D-01: LLM API 方案
- 使用 MiniMax M2.7 API，通过 `openai` Python SDK 调用（已安装 v2.36.0）
- API base_url: `https://api.minimax.chat/v1`
- API key: 环境变量 `MINIMAX_API_KEY`

### D-02: 摘要范围
- 仅对 step4 精选的 10-16 条新闻生成摘要，跳过被淘汰的
- 逐条单独调用，非批量

### D-03: 输出格式
- 保留 `3新闻_概述.md` 中间文件
- 格式与原 SKILL.md Step 7 一致：`## 栏目名` + `### 标题` + 摘要段落
- 按 8 栏目分组（世界性科研突破/农业/扶贫/能源/医疗/科技/材料/军事）

### D-04: 数据流
- 从 `1新闻_链接.md` 读取栏目分类（类别归属）
- 从 `2新闻_已审核.md` 读取正文内容
- 按标题匹配合并

### D-05: 架构
- 独立脚本 `step7.py`，不合并进 step6.py
- `--date`、`--dry-run` 参数与 step1_3/step4/step6 一致

### the agent's Discretion
- MiniMax 模型名称（使用 "minimax-m2.7"）
- API 超时 / 重试参数
- 标题匹配的容差策略
- 摘要 prompt 的具体措辞
- API 失败时的回退策略（规则截取）
</decisions>

<canonical_refs>
## Canonical References

### 上游数据
- `/mnt/e/Daily/step6.py` — 正文提取脚本，产出 2新闻_已审核.md
- `/mnt/e/Daily/step4.py` — 分类筛选脚本，产出 1新闻_链接.md

### 原 skill 参考
- `/home/lmr/.hermes/skills/productivity/daily-china-news/SKILL.md` — Step 7 摘要生成参考（LLM 逐条总结逻辑）
- `/home/lmr/.hermes/skills/productivity/daily-china-news/scripts/step7_summarize.py` — 原摘要脚本

### 输出格式参考
- `/home/lmr/.hermes/skills/productivity/daily-china-news/SKILL.md` — 3新闻_概述.md 格式规范（##栏目 + ###标题 + 段落）
</canonical_refs>

<deferred>
## Deferred Ideas
- JSON 生成 — Phase 5
- HTML 渲染 — Phase 5
- PNG 截图 — Phase 5
</deferred>

---

*Phase: 04-summary-gen*
*Context gathered: 2026-05-16*
