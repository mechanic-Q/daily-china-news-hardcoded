# Phase 2: 分类筛选 - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning

<domain>
## Phase Boundary

从 `0新闻_粗筛.md` 读取 step1_3.py 采集的原始新闻数据，经质量过滤 → 8栏目分类 → 优先级排序 → 精选输出 `1新闻_链接.md`。

</domain>

<decisions>
## Implementation Decisions

### D-01: 8 栏目定义
- 🔬 世界性科研突破、🌾 农业、🤝 扶贫、⚡ 能源、🏥 医疗、🚀 科技、🧱 材料、🎖️ 军事
- 原 "🔬科研" 改为 "🔬世界性科研突破"，强调全球级而非国内日常科研

### D-02: 每栏目上限策略
- 延续原 skill 策略：每栏目先取最高优先级 1 条，总条数不足 10 条时按全局优先级补满
- 上限 10-16 条

### D-03: 新闻质量排除列表
- 继承原排除项：春雨落、百谷生、谷雨、舞蹈诗剧、三月三、时装周、DELVAUX、世界超级摩托车、节气、立夏、立春、立冬、冬至、夏至、春分、秋分、惊蛰、芒种、白露、寒露、霜降、小满
- 用户补充：娱乐、明星、八卦、综艺、影视、网剧、歌星、演唱会、直播、网红、选秀、真人秀

### D-04: 涉华过滤
- 删除原 `is_china_related()` 对参考消息的特殊分支
- 8 栏目分类的关键词匹配本身就是中国语境过滤，纯外国新闻匹配不到任何栏目会被丢弃

### D-05: 输出文件
- `1新闻_链接.md`，格式与原 skill 一致
- 每栏目一个 section，加信源标注

### D-06: 架构
- 独立 `step4.py`，不合并进 step1_3.py
- `--date`、`--dry-run` 参数与 step1_3.py 一致
- 全做完后通过 bash `&&` 串联

### the agent's Discretion
- 分类关键词表可以按实际运行结果微调
- 排除列表可后续补充
- 精选条数的精确算法（10-16 之间的具体值）

</decisions>

<canonical_refs>
## Canonical References

### 参考实现
- `/home/lmr/.hermes/skills/productivity/daily-china-news/scripts/classify_and_filter.py` — 分类逻辑参考（192行）
- `/mnt/e/Daily/step1_3.py` — 上游数据格式参考
- `/mnt/e/Daily/.planning/PROJECT.md` — 项目上下文 §Active
</canonical_refs>

<deferred>
## Deferred Ideas
- 正文提取 — Phase 3
- 摘要生成 — Phase 4
- 报纸渲染 — Phase 5
</deferred>

---

*Phase: 02-classify-filter*
*Context gathered: 2026-05-15*
