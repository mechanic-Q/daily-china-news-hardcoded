---
author: lmr
created_at: 2026-06-27 14:10:00
last_session: Phase 12 已完成 (perf_profile.py + run_all.sh 计时)
---

# Next Phase

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
