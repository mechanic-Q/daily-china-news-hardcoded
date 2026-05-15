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
**Status:** in-progress
**Plans:** 2 plans
**Success Criteria:**
1. MiniMax M2.7 API 逐条摘要 10-16 条精选新闻
2. 输出 3新闻_概述.md 格式与原 skill Step 7 一致
3. API 失败时规则截取回退

Plans:
- [ ] 04-01-PLAN.md — 验证 Test 9 + UAT 闭合 + Phase 4 关闭
- [ ] 04-02-PLAN.md — 5 项非阻塞健壮性改进（可选）

### Phase 5: 报纸渲染
**Goal:** JSON 生成 + HTML 渲染 + PNG 截图
**Status:** pending
