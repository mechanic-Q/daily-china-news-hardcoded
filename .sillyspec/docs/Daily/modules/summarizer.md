---
schema_version: 1
doc_type: module-card
module_id: summarizer
author: lmr
created_at: 2026-06-24 18:11:00
source_commit: 5f76a1a
---

# summarizer

## 定位
- 负责：单篇正文 → 1-2 句中文摘要（LLM 调用 + 智能重试 + 回退）
- 不负责：栏目分类（classifier）、版式渲染（renderer）
- 上游：extractor（产出 `2新闻_已审核.md`）
- 下游：renderer（消费 `3新闻_概述.md`）
- **正文质量闸门**：run() 开头检查每条正文是否以 `[正文提取失败:` 开头；命中则 raise SystemExit(1)，不生成摘要

## 契约摘要
- LLM 唯一可控环节：诊断失败原因 → 注入针对性修复提示 → 重试 ×3（attempt 0/1/2）
- 4 类失败模式（`_why_invalid` 返回值）：
  - `too_short`：长度 < 20，或 < 正文 2% 且 < 30 字
  - `too_long`：长度 > 200
  - `body_copy`：摘要文本整段包含于正文中
  - `cot_leak`：命中 `COT_LEAK_PATTERNS`（思维链泄漏）
- 重试失败兜底：`fallback_summarize`（首句 + 末句拼接，并清洗"责任编辑/记者/来源"等噪声）
- 输出格式：`3新闻_概述.md`（每条 1-2 句中文）

## LLM 调用点（⚠️ 本次变更目标）
- 位置：`step7.py:159-173`，模型 `glm-4-flash`（智谱 GLM-4 Flash）
- 调用方式：`openai` SDK + `base_url=https://open.bigmodel.cn/api/paas/v4/`
- 参数：`temperature=0.3, max_tokens=300, timeout=30`
- env：`ZHIPU_API_KEY`（未设置时直接返回 None → 走回退）
- Prompt 模板：`用1-2句话精炼概括以下新闻的核心要点。简短、准确、完整，直接输出摘要。\n\n标题：{title}\n正文：{body}`
- 重试增强：`attempt > 0` 时在 prompt 末尾追加 `"\n\n注意：" + RETRY_PROMPTS[failure]` 拼接
- 后处理：剥离 `<think>...</think>` 块（兼容部分模型的思维链输出）

## 关键逻辑
```
parse_2news(2新闻_已审核.md)              # → {key: {title, src, body}}
for each item:
    summary = llm_summarize(title, body)   # 内部循环 3 次
        attempt 0..2:
            prompt = base_prompt (+ RETRY_PROMPTS[failures] if attempt>0)
            raw = GLM-4-Flash(prompt, T=0.3, max_tokens=300, timeout=30)
            cleaned = strip(<think>...</think>)
            reason = _why_invalid(cleaned, body)
                # too_short / too_long / body_copy / cot_leak / None
            if reason is None: return cleaned
            failures.add(reason); sleep(1); 继续重试
     if summary is None:
         summary = fallback_summarize(title, body)   # 首句+末句
     summary = summary.replace("习近平", "")         # 敏感词清洗
 写入 3新闻_概述.md（按 COLUMN_ORDER 分栏目排序）
```

## 注意事项
- 这是流水线唯一逐条调用 LLM 的环节，~10 次/天（每篇 1-3 次含重试）
- `COT_LEAK_PATTERNS`：用于检测思维链泄漏，包含中英双语线索
  （"用户要求我"/"让我分析"/"我需要确保"/"Potential answer"/"The user wants"/
  "I need to"/"核心要点应该"/"用1-2句话"/"直接输出摘要"/"让我总结"/
  "关键在于"/"主要信息"/"关键点"/"core points"）
- 异常重试间隔：校验失败 `sleep(1)`，API 异常 `sleep(2)`，第 3 次失败不再 sleep 直接退出
- 重试上限硬编码为 `range(3)`（即最多 3 次调用），若调参需同步检查 `attempt < 2` 判断
- 修改时需同步检查的下游：renderer 读 `3新闻_概述.md`，依赖 `COLUMN_ORDER` 栏目顺序
- 切换模型/服务商时只需改 `base_url` + `model` + env 名，调用形态保持 OpenAI 兼容协议
- `parse_1news` / `parse_2news`：两阶段解析；摘要器主要消费 `parse_2news` 的已审核结果
- `failures` 是 `set()`：同一失败模式不会重复注入提示，多种失败模式叠加注入
- `fallback_summarize` 噪声清洗清单：`【纠错】 / 【责任编辑 / 责任编辑 / 记者 / 编辑 / 来源 / 免责声明`
- 回退策略保证：即使 LLM 完全不可用（无 key / 网络故障 / 三次失败），仍能产出可用摘要
- 命令行入口：`python3 step7.py [--date YYYY-MM-DD] [--dry-run]`，默认处理当天

## 失败诊断阈值速查
| 类别 | 触发条件 |
| --- | --- |
| `too_short` | `len(summary) < 20` 或 `(len(summary) < len(body)*0.02 and len(summary) < 30)` |
| `too_long` | `len(summary) > 200` |
| `body_copy` | `summary in body`（整段被正文包含） |
| `cot_leak` | 命中 `COT_LEAK_PATTERNS` 任一子串 |

## 人工备注

<!-- MANUAL_NOTES_START -->

## 变更索引

- ql-20260704-003-ef92 | Step7 新闻概述正文删除习近平三字
- ql-20260705-001-b3e8 | Step6/7 正文提取必须成功，失败则 pipeline fail closed
<!-- MANUAL_NOTES_END -->
