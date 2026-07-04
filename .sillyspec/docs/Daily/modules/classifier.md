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
- 输出：`1新闻_链接.md`（含栏目标签、来源、标题、URL、真实发布时间的精选 10 篇）
- 涉华判定三级回退：`is_china_source`（域名白名单） → `is_china_related`（关键词） → `llm_is_china_related`（LLM 兜底）
- 关键词加权打分：`CATEGORY_KEYWORDS` 每栏目独立 weights 词典，单标题对所有 9 栏目跑分
- 高置信关键词（`best≥6` 且 `margin≥3`）直接分栏，跳过 LLM 评分
- 低置信度标题以 20 条为 batch 批量 LLM 涉华判断 + 栏目评分
- batch 失败时先重试一次；仍失败则逐条回退到单条 LLM；仅逐条 LLM 也失败时才进入显式 `keyword-fallback`，不得把关键词结果伪装为 LLM signals

## LLM 调用点（⚠️ 本次变更目标）

### 1. MiniMax — 涉华兜底
- 位置：`step4.py:79` `llm_is_china_related(title)`
- SDK：`openai.OpenAI`
- `base_url`：`https://api.minimax.chat/v1`（L86）
- `model`：`"minimax-m2.7"`（L88）
- key 来源：`os.environ["MINIMAX_API_KEY"]`
- 失败处理：`except Exception: return False`（静默吞错）

### 2. 9router — 批量涉华判断 & 批量栏目评分（Phase 15E）
- 位置：`step4.py:121` `llm_is_china_related_batch()`, `step4.py:412` `score_signals_batch()`
- SDK/Provider：`llm_client.call_llm` + `llm.yaml` `9router` 配置
- `model`：`low`（`base_url: http://localhost:20128/v1`）
- 输入：20 条 / batch，index-based JSON prompt，`temperature=0.0`
- 失败处理：JSON/schema 失败先重试一次；仍失败后整轮禁用批量 → 逐条 fallback
- 容错：`_extract_json_array()` 容忍模型返回前后说明文字

### 3. Zhipu — 栏目仲裁
- 位置：`step4.py:209` `llm_classify_single(articles)`
- SDK：`openai.OpenAI` + 自定义 `base_url`
- `model`：`"glm-4-flash"`（L232）
- key 来源：`os.environ["ZHIPU_API_KEY"]`
- 输入：低置信度条目列表，逐条调用
- 返回：`{title: category}`

## 关键逻辑（伪代码）

```
parse_0(0新闻_粗筛.md, today)                # 正则提取 [date] title | url
  ↓
for article in articles:
    质量/黑名单过滤 → 涉华三级判定            # source → keyword → LLM
    涉华判定 LLM 用 batch 或逐条（见下）
  ↓
for article (through 涉华 filter):
    cat, kw = high_confidence_keyword_category(title)  # best≥6, margin≥3
    if cat: 直通分栏, a['score_source']='keyword-high-confidence'
    else:  llm_candidates += [a]
  ↓
if llm_candidates:
    batch_signals = score_signals_batch(llm_candidates)  # 20 条/batch, LLM column-score
    for each article:
        if batch signals valid:  assign category, a['score_source']='llm-batch'
        else:  score_signals(title) single  # 单条 LLM 回退
        if still invalid:  keyword-fallback → llm_classify_single() 仲裁，且 signals=None
  ↓
涉华判定（batch 路径）: llm_is_china_related_batch(china_llm_candidates)
  每次 20 条 batch, index JSON, system message + temperature=0
  JSON/schema 失败先重试一次；仍失败自动回退到逐条 llm_is_china_related(title)
  ↓
每栏目取最高分文章 → 汇总 top-10 → 写入 1新闻_链接.md，并把 date 写成 发布时间
```

## 关键词词典规模
- `EXCLUDE_TITLES`（L19）：低质标题黑名单
- `EXCLUDE_NEGATIVE`（L28）：负面词过滤
- `CHINA_KEYWORDS`（L33）：涉华关键词 ~20 项
- `CHINA_DOMAINS`（L56）：中国信源域名白名单
- `CATEGORY_KEYWORDS`（L143，约 57 行）：8 栏目 → 关键词 → 权重，约 45 个加权词条
- 8 栏目：科研突破 / 农业 / 扶贫 / 能源 / 医疗 / 科技 / 材料 / 军事

## 注意事项
- 🔴 **MiniMax model 字符串 `'minimax-m2.7'` 可能不是真实 model id**，异常被 `except Exception: return False` 静默吞掉 → 涉华兜底可能长期空跑而无报错
- 🔴 两个单条 LLM 调用均无超时配置、无重试、无日志；batch 调用有 `temperature=0` 和 `timeout=60s`
- batch 涉华/评分使用 `9router` provider + `llm.yaml` 配置，不依赖 MiniMax/Zhipu
- batch 失败先重试一次，再采用 fail-fast：首个 batch 失败后整轮禁用批量，回退单条
- batch JSON 容错：`_extract_json_array()` 自动剥离 think 块、markdown fence、前后说明文字
- `DEBUG_LLM_BATCH` 环境变量可打印 batch LLM 原始返回前 200 字符
- 修改时需同步检查的下游：extractor 读 `1新闻_链接.md`（格式：栏目标签 + 来源 + 标题 + URL）
- 环境变量依赖：`MINIMAX_API_KEY`、`ZHIPU_API_KEY`（单条兜底） + `NINEROUTER_API_KEY`（batch 路径）
- 文件总行数：约 640

## 人工备注

<!-- MANUAL_NOTES_START -->

## 变更索引

- ql-20260704-001-8f2a | 修复 Step4 LLM batch 降级不牺牲筛选准确度
- ql-20260704-002-a4d1 | 强制采集见报/发布日期为当天的新闻

<!-- MANUAL_NOTES_END -->
