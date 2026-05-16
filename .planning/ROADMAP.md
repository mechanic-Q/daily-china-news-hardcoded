# Roadmap: 每日新中国硬编码采集

## Milestone: v1.0

### Phase 1: 基础采集与优化
**Goal:** Step 1-3 硬编码完成 + 7信源全通 + 代码优化
**Status:** complete
**Success Criteria:**
1. 7信源全通（181条/日）
2. 正则拼写修复
3. aiohttp 并发优化
4. 验证简化为仅 HTTP 200

### Phase 2: 分类筛选
**Goal:** 按8栏目分类 + 涉华过滤
**Status:** complete
**Success Criteria:**
1. 8栏目分类（世界性科研突破/农业/扶贫/能源/医疗/科技/材料/军事）
2. 涉华过滤
3. 每栏目取最高优先级 1 条，补满至 10-16 条
4. 新闻质量排除列表过滤非新闻内容

### Phase 3: 正文提取
**Goal:** 从 URL 提取正文
**Status:** complete
**Success Criteria:**
1. 5 层策略链（TRS_Editor / 通用容器 / 参考消息关键词 / P标签 / chromium）
2. 信源分流（静态 urllib / 央视系 chromium）
3. 正文无上限保留

### Phase 4: 摘要生成
**Goal:** LLM API 逐条摘要 → 3新闻_概述.md
**Status:** complete

### Phase 5: 报纸渲染
**Goal:** 从 3新闻_概述.md 生成可视化报纸 PNG (step8.py + run_all.sh)
**Status:** in-progress
**Requirements:** REND-01
**Plans:** 2 plans
Plans:
- [ ] 05-01-PLAN.md — step8.py 全流程 (MD→HTML→PNG)
- [ ] 05-02-PLAN.md — run_all.sh 全管道串联
