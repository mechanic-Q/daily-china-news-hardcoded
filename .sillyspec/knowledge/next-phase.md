---
author: lmr
created_at: 2026-06-27 14:10:00
last_session: Phase 12 已完成 (perf_profile.py + run_all.sh 计时)
---

# Next Phase

## Phase 14: 性能优化（基于 Phase 12 数据）

### 背景
Phase 12 (perf_profile.py) 量化显示瓶颈：
- step1_3.py ~88s — 7 信源串行 + chromium cold-start 5 次
- step7.py ~102s — LLM 逐条串行摘要
- step6.py ~73s — 正文串行提取 + chromium
- step4.py ~41s — LLM 分类
- step8.py ~7s — 渲染截图（快）

### 优化方向
1. **step1_3 信源并发抓取**：7 个信源由串行改为 `asyncio.gather` 或 `concurrent.futures`，预计节省 60-70s
2. **Chromium 进程复用**：改为 playwright 持久浏览器，避免每信源 cold-start（当前 5 次 × ~3s）
3. **step6/step7 LLM/正文并行**：`asyncio.gather` 并行调用 LLM，预计节省 40-50s
4. **详情页 URL 并发 fetch**：urllib 串行改 `aiohttp` 并发

### 约束
- 不改报纸产物 HTML/PNG 语义
- 不改栏目评分算法（Phase 13 已独立）
- 不改 `run_all.sh` CLI 和失败语义

### 来源
- Phase 11 对话用户确认："先量化再优化我同意"
- Phase 12 数据已落地

### 前置阶段
- Phase 11: 删 summary bar + USER_MANUAL.md ✅
- Phase 12: 性能量化 ✅
- Phase 13: 栏目算法完全重做 ✅

### 建议分支
`phase-14-perf-optimize`

### Change 命名
`YYYY-MM-DD-perf-optimize`

## Phase 13: 栏目算法完全重做（LLM 主导）

### 背景
当前 step4.py 基于关键词加权做栏目分类，准确性有限。用户反映：
- "俄军军事"误判为"🎖️ 军事"栏目（应属于国际/外军，非中国军事）
- "世界性突破"语义模糊（用户的定义：卡脖子破解 OR 全球首创，且主体是中国）

### 目标
完全替换 step4.py 的分类逻辑，从关键词加权切换到 LLM 主导：

- 每个新闻条目调用 LLM 做栏目相关度评分（0-10） + 中国主体判断
- 准入门槛：每个栏目额外检查"main_subject"是否为中国
- 排除关键词：俄军/美军/乌军/北约（对军事栏目）
- "世界性突破"须符合用户定义（卡脖子破解 or 全球首创，且是中国）

### 来源
- Phase 11 对话中用户确认："完全重做"
- 已知：用户说"你把你都设计了哪些功能，怎么使用，写一个手册放在项目里"
- 决策：不依赖关键词加权，LLM 主导

### 前置阶段
- Phase 11: 删除 top summary bar + USER_MANUAL.md ✅
- Phase 12: 性能量化 (perf_profile.py) ✅

### 建议分支
`phase-13-column-scoring-v2`

### Change 命名
`YYYY-MM-DD-column-scoring-v2`
