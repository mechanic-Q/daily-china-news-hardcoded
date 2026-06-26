---
schema_version: 1
doc_type: glossary
author: lmr
created_at: 2026-06-24 18:14:00
source_commit: 5f76a1a
generator: sillyspec-scan
---

# Glossary

Daily 项目专有术语表。

## 业务术语

### 期号 (issue)
报纸版面右上角的"第 N 期"，由 `step8.py:_compute_issue(target_date)` 根据某基准日期递增计算得出，每天 +1。

### 栏目 (column / category)
8 个固定主题分类，定义在 `step4.py:CATEGORY_KEYWORDS` 和 `step7.py:COLUMN_ORDER`：
- 🔬 世界性科研突破 / Scientific Breakthrough
- 🌾 农业 / Agriculture
- 🤝 扶贫 / Poverty Alleviation
- ⚡ 能源 / Energy
- 🏥 医疗 / Healthcare
- 🚀 科技 / Technology
- 🧱 材料 / Materials
- 🎖️ 军事 / Military

每个栏目有独立的关键词权重词典，权重范围 1-5。

### 涉华判定 (china-relevance)
三级回退判定一篇文章是否与中国相关：
1. **domain 白名单**：URL 在 `CHINA_DOMAINS`（xinhuanet.com、people.com.cn 等 9 个域名）→ 命中即涉华
2. **keyword 匹配**：标题命中 `CHINA_KEYWORDS`（中国、华、京、沪... 等）
3. **LLM 兜底**：上述都失败时调用 MiniMax `minimax-m2.7` 判定

### 文件接力 (file relay)
本项目特有架构：5 个 step 模块间无 import、无 IPC，全部通过文件传递数据：
`0新闻_粗筛.md → 1新闻_链接.md → 2新闻_已审核.md → 3新闻_概述.md → HTML/PNG`

### 智能重试 (intelligent retry)
`step7.py` 摘要生成时的 LLM 调用策略：失败 → `_why_invalid()` 诊断 → 从 `RETRY_PROMPTS` 注入对应修复提示 → 重试。最多 3 次。

### 失败诊断分类
`_why_invalid()` 返回的 4 种摘要失败模式：
- `too_short`：摘要过短
- `too_long`：摘要过长
- `body_copy`：摘要直接复制正文（未做归纳）
- `cot_leak`：思维链泄漏（出现"首先"、"然后"、"Step 1"等 14 种模式）

### 污染检测 (contamination)
`step6.py:_is_contaminated()` 检测提取的"正文"是否实为导航/CSS/JS 残片，5 类信号：
- CSS 残片
- JS 残片
- "日报+周报+杂志" 100 字内共现
- `enpproperty-->` 字面量
- "地址：+邮编：" 200 字内共现

## 信源专有术语

### CKXX (参考消息)
`china.cankaoxiaoxi.com`，唯一提供 JSON API 的信源（`list.json`，9 个频道）。

### TRS_Editor
新华社/人民日报系列网站使用的 CMS，正文通常包在 `<div id="ozoom">` 或 `class="TRS_Editor"` 中。step6.py 5 层提取的第 1 层即匹配此模式。

### cnnc 三级回退
中核集团抓取链：
1. `cnnc.com.cn` chromium dump（主路径）
2. `cnnpn.cn` 聚合站点（备用）
3. 跳过（前两个都不可达时）

## 技术术语

### dry-run
所有 step 脚本支持的预览模式，`--dry-run` 跳过文件写入，仅打印计划。

### chromium_dom
封装函数（同名出现在 step1_3.py:69 和 step6.py:48），调用 `/snap/bin/chromium --headless=new --dump-dom <url>`，用于 JS 渲染网站的 HTML 抓取。

### balance_columns
`step8.py:137` 双栏布局算法，O(2^n) 子集枚举（n = 栏目数），最小化左右两栏 `_estimate_weight` 总和差。

### COT_LEAK_PATTERNS
`step7.py:119` 定义的 14 条中英双语正则模式，用于检测 LLM 摘要中泄漏的思维链（Chain-of-Thought）痕迹。

### OpenAI 兼容 API
本项目所有 LLM 调用都通过 `openai` Python SDK，但 `base_url` 指向 Zhipu 或 MiniMax 而非 OpenAI 官方。这是 Zhipu/MiniMax 提供的兼容协议。

## 配置术语

### BASE_DIR
全局常量 `Path("/mnt/e/每日新中国")`，硬编码于所有 5 个 step 脚本顶部。所有输出文件均落在 `BASE_DIR / {YYYY-MM-DD}/` 子目录下。

### EXCLUDE_TITLES / EXCLUDE_NEGATIVE
`step4.py:19/28` 两个排除词列表：前者排除非新闻类型（招标、招聘、目录），后者排除负面内容（事故、灾难、伤亡）。
