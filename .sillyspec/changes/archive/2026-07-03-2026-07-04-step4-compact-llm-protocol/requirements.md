---
author: lmr
created_at: 2026-07-04 00:23:08
---

# Requirements

## 角色

| 角色 | 说明 |
|---|---|
| 开发者 | 维护 Step4 分类筛选、LLM 调用和测试的人 |
| 运行者 | 每天执行新闻流水线并检查输出的人 |
| 月报生成器 | 读取归档 JSONL 并生成月报的现有脚本 |

## 功能需求

### FR-01: 涉华 batch 使用位串协议

覆盖决策：D-001@v1, D-002@v1

Given Step4 需要对中国信源但标题无显式中国关键词的 batch 做涉华判断
When 调用 `china-relevance`
Then prompt 要求模型输出长度等于 batch size 的 `0/1` 位串

Given 位串包含非 `0/1` 字符或长度不匹配
When parser 校验输出
Then 当前 batch 触发既有单条 fallback，不静默接受脏结果

### FR-02: 栏目评分 batch 使用矩阵协议

覆盖决策：D-001@v1, D-003@v1

Given Step4 需要对 LLM 候选文章评分
When 调用 `column-score`
Then prompt 要求每行输出 `index|r1,r2,r3,r4,r5,r6,r7,r8,r9|importance|timeliness`

Given 矩阵行缺失、重复 index、列数不是 9 或数值超出 0-10
When parser 校验输出
Then 对应 batch 评分失败并进入现有 fallback 路径

### FR-03: parser 还原旧 signals 结构

覆盖决策：D-002@v1, D-003@v1

Given 矩阵协议解析成功
When Step4 继续分类流程
Then parser 输出必须是 `{"relevance": {COLUMN_ORDER[i]: score}, "importance": n, "timeliness": n}`

Given parser 输出 signals
When `aggregate_scores()` 和 `assign_category()` 执行
Then 不需要修改其算法或入参结构

### FR-04: low 模型调用禁 reasoning 并使用 256k 输出上限

覆盖决策：D-004@v1

Given 当前 provider/model 为 9router `low`
When Step4 调用 `china-relevance` 或 `column-score`
Then 调用参数必须包含 `reasoning_effort="none"` 和 `max_tokens=262144`

Given Chat Completions API 不提供独立 context-window 参数
When 程序配置 low 模型预算
Then 程序只设置可控的输出上限，1m context 由模型能力本身提供

### FR-05: 空 content 必须诊断并 fail-fast

覆盖决策：D-004@v1

Given LLM 响应 `message.content` 为空
When `llm_client.call_llm()` 处理响应
Then 抛出 `LLMCallError`，并记录 `call_site_id`、`finish_reason`、`content_len`、`reasoning_len`

### FR-06: 上下游结构保持兼容

覆盖决策：D-002@v1, D-003@v1

Given Step4 完成分类与归档
When `news_archive.build_record()` 写入 JSONL
Then 字段结构保持现状，包含 `signals/category/priority/selected_in_top10/score_source`

Given 月报脚本读取归档
When `monthly_report.py` 统计栏目和代表新闻
Then 不需要知道紧凑协议存在

## 非功能需求

- 兼容性：不修改归档 schema 和月报读取字段。
- 可回退：紧凑协议解析失败时保留现有 fallback，不中断整条流水线。
- 可诊断：空 content 与解析失败需要暴露明确错误原因。
- 可测试：parser、LLM 空 content、mock batch 端到端必须有自动化测试。
- 性能：紧凑协议输出 token 应显著少于原 JSON 重复 key 方案。

## 决策覆盖矩阵

| 决策 ID | 覆盖的 FR | 说明 |
|---|---|---|
| D-001@v1 | FR-01, FR-02 | 紧凑协议作为 Step4 主路径 |
| D-002@v1 | FR-01, FR-03, FR-06 | 不改算法和上下游结构 |
| D-003@v1 | FR-02, FR-03, FR-06 | parser 还原旧 signals |
| D-004@v1 | FR-04, FR-05 | low 模型禁 reasoning 与大输出上限 |
