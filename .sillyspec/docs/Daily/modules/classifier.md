---
schema_version: 1
doc_type: module-card
module_id: classifier
author: lmr
created_at: 2026-06-24 18:11:00
source_commit: 5f76a1a
---

# classifier

## 定位
- 负责：质量过滤 + 涉华判定 + 8 栏目分类 + 关键词加权打分 + 精选 top-10
- 不负责：信源抓取（collector）、正文提取（extractor）、摘要生成（summarizer）

## 契约摘要
- 输入：`0新闻_粗筛.md`（上游 collector 产出，HTTP 200 验证条目 ~200 篇）
- 输出：`1新闻_链接.md`（含栏目标签、来源、标题、URL 的精选 10 篇）
- 涉华判定三级回退：`is_china_source`（域名白名单） → `is_china_related`（关键词） → `llm_is_china_related`（LLM 兜底）
- 关键词加权打分：`CATEGORY_KEYWORDS` 每栏目独立 weights 词典，单标题对所有 8 栏目跑分
- 低置信度（多栏目得分相近 / 命中模糊）时调用 `llm_classify_single` 单条仲裁

## LLM 调用点（⚠️ 本次变更目标）

### 1. MiniMax — 涉华兜底
- 位置：`step4.py:79` `llm_is_china_related(title)`
- SDK：`openai.OpenAI`
- `base_url`：`https://api.minimax.chat/v1`（L86）
- `model`：`"minimax-m2.7"`（L88）
- key 来源：`os.environ["MINIMAX_API_KEY"]`
- 失败处理：`except Exception: return False`（静默吞错）

### 2. Zhipu — 栏目仲裁
- 位置：`step4.py:209` `llm_classify_single(articles)`
- SDK：`openai.OpenAI` + 自定义 `base_url`
- `model`：`"glm-4-flash"`（L232）
- key 来源：`os.environ["ZHIPU_API_KEY"]`
- 输入：低置信度条目列表，逐条调用
- 返回：`{title: category}`

## 关键逻辑（伪代码）

```
parse_0(0新闻_粗筛.md, today)            # L115，正则提取 [date] title | url ✅
  ↓
for article in articles:
    if any(neg in title for neg in EXCLUDE_NEGATIVE):  continue   # L28
    if any(bad in title for bad in EXCLUDE_TITLES):    continue   # L19
    is_china = is_china_source(url)              # L72 域名白名单
             or is_china_related(title)          # L65 CHINA_KEYWORDS
             or llm_is_china_related(title)      # L79 MiniMax 兜底
    if not is_china:  continue
    scores = score_all_categories(title)         # L200 8 栏目并行打分
  ↓
sorted_cats = sorted(scores.items(), key=-x[1])  # L336 取最高分栏目
若 top1/top2 得分相近 → llm_classify_single() 仲裁  # L209
  ↓
每栏目取最高分文章 → 汇总 top-10 → 写入 1新闻_链接.md
```

## 关键词词典规模
- `EXCLUDE_TITLES`（L19）：低质标题黑名单
- `EXCLUDE_NEGATIVE`（L28）：负面词过滤
- `CHINA_KEYWORDS`（L33）：涉华关键词 ~20 项
- `CHINA_DOMAINS`（L56）：中国信源域名白名单
- `CATEGORY_KEYWORDS`（L143，约 57 行）：8 栏目 → 关键词 → 权重，约 45 个加权词条
- 8 栏目：科研突破 / 农业 / 扶贫 / 能源 / 医疗 / 科技 / 材料 / 军事

## 注意事项
- 🔴 **MiniMax model 字符串 `'minimax-m2.7'` 可能不是真实 model id**（官方常见为 `abab6.5*` 或 `MiniMax-M2`），异常被 `except Exception: return False` 静默吞掉 → 涉华兜底可能长期空跑而无报错
- 🔴 两个 LLM 调用均无超时配置、无重试、无日志，失败只能从条数异常间接发现
- 修改时需同步检查的下游：extractor 读 `1新闻_链接.md`（格式：栏目标签 + 来源 + 标题 + URL）
- 环境变量依赖：`MINIMAX_API_KEY`、`ZHIPU_API_KEY`，缺失时直接 return（无告警）
- 文件总行数：434

## 人工备注

<!-- MANUAL_NOTES_START -->

<!-- MANUAL_NOTES_END -->
