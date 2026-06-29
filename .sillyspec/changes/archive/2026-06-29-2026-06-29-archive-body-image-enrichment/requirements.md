---
author: lmr
created_at: 2026-06-29 14:13:38
schema_version: 1
doc_type: requirements
change_id: 2026-06-29-archive-body-image-enrichment
phase: 14B
---

# Requirements

## 角色

| 角色 | 说明 |
|---|---|
| Daily 流水线 | 每日执行 step1_3 → step4 → step6 → step7 → step8 的自动化新闻流水线 |
| archive writer | 14A `news_archive.py`，负责 metadata + score/signals JSONL 写入 |
| archive enricher | 14B 新增 `archive_enrich.py`，负责补真实正文与 top10 首图 |
| extractor | `step6.py`，提供真实页面正文提取能力 |
| backfill operator | 手动运行 CLI 补跑历史日期或失败记录的用户 |
| future monthly reporter | 后续 14C 使用正文与首图生成月报的消费者 |

## 功能需求

### FR-01: 为所有归档文章补真实正文
覆盖决策：D-001@v1, D-002@v1

Given 月度 archive JSONL 中存在指定日期的记录
When `archive_enrich.py --date YYYY-MM-DD` 执行
Then 系统必须遍历该日期所有 records
And 对每条 record 调用页面正文提取逻辑
And 正文成功时写入 `body`
And 写入 `body_status="extracted"`
And 写入 `body_extracted_at` 与 `body_source_url`

### FR-02: 正文禁止 LLM 生成或补写
覆盖决策：D-002@v1

Given 任意归档 record 需要补正文
When 正文提取执行
Then `body` 字段只能来自原始 URL 页面提取结果
And 不得调用 LLM 生成正文
And 不得调用 LLM 改写、润色或补全正文
And 不得用标题、摘要或推测内容冒充正文

Given 页面正文提取失败
When 写回 archive record
Then 不得写 fake body
And 必须写入 `body_status="failed"`
And 必须写入 `body_error`

### FR-03: 仅 top10 文章补首图
覆盖决策：D-001@v1

Given 指定日期 archive records
When `archive_enrich` 执行图片补全
Then 只有 `selected_in_top10=true` 的 record 可以尝试抓首图
And 非 top10 record 必须保持无图片下载
And 非 top10 record 可写 `image_status="not_selected"`

### FR-04: 首图保存 URL 与本地文件
覆盖决策：D-003@v1

Given top10 record 页面存在可用首图
When 图片补全成功
Then record 必须包含 `image_url`
And record 必须包含 `image_path`
And 图片文件必须保存到 `archive/images/YYYY-MM/<article_id>.<ext>`
And `image_status` 必须为 `downloaded`

Given top10 record 页面无可用首图
When 图片提取结束
Then `image_status` 必须为 `not_found`
And 不得影响正文状态

Given 图片 URL 存在但下载失败
When 写回 record
Then `image_status` 必须为 `failed`
And `image_error` 必须记录失败原因
And 不得阻断日报

### FR-05: 新增独立 archive_enrich helper + CLI
覆盖决策：D-004@v1

Given 用户需要补跑历史日期
When 用户执行 `python3 archive_enrich.py --date YYYY-MM-DD`
Then 命令必须读取对应月度 JSONL
And 只处理指定日期 records
And 写回同一 JSONL 文件

Given 用户执行 `python3 archive_enrich.py --date YYYY-MM-DD --missing-only`
When record 已有 `body_status="extracted"`
Then 正文补全必须跳过该 record

Given 用户执行 `python3 archive_enrich.py --date YYYY-MM-DD --dry-run`
When 命令运行
Then 只打印统计和目标路径
And 不写 JSONL
And 不下载图片

### FR-06: run_all 路径 best-effort 不阻断日报
覆盖决策：D-005@v1

Given `step4.py` 已完成 14A archive 写入
When `archive_enrich.enrich_archive_best_effort(...)` 被调用
Then enrichment 内部异常必须被捕获
And 不得导致 `run_all.sh` exit 1
And 日报既有输出必须保留

Given 自动 enrichment 超过时间预算
When 时间预算耗尽
Then 系统必须停止处理剩余记录
And 保留已成功写入的 enrichment 字段
And 未处理记录保持可补跑状态

### FR-07: 14A upsert 不得覆盖 14B 字段
覆盖决策：D-006@v1

Given 某 record 已包含 `body` 或 `image_path`
When 14A `news_archive.archive_articles(...)` 对同一 URL 重新 upsert
Then 已存在的 `body*` 字段不得被清空
And 已存在的 `image*` 字段不得被清空
And 14A metadata/score/signals 字段仍可更新

### FR-08: 图片流程不改变 step6.fetch_and_extract 契约
覆盖决策：D-007@v1

Given `step6.fetch_and_extract(url, title)` 当前返回 `(body, err)`
When Phase 14B 实现图片提取
Then 不得要求 `fetch_and_extract` 返回 HTML
And 图片提取必须在 `archive_enrich` 中单独抓 HTML
And `step6.py` 原有消费者不需要修改

### FR-09: JSONL schema v2 向后兼容
覆盖决策：D-006@v1

Given 旧 JSONL record 只有 14A 字段
When `archive_enrich` 读取该 record
Then 系统必须视为 `body_status="missing"`
And top10 record 视为 `image_status="missing"`
And 非 top10 record 视为 `image_status="not_selected"`

Given 新 record 写回
When 写入 JSONL
Then `schema_version` 应为 2
And 14A 旧字段必须保留

## 非功能需求

- 真实性：正文不得由 LLM 生成、润色、改写或补全
- 兼容性：不修改 `run_all.sh`；不改变日报 Markdown/HTML/PNG 产物格式
- 可回退：删除 step4 中 enrichment 调用即可回到 14A 行为；JSONL 字段向后兼容
- 可测试：核心逻辑在 `archive_enrich.py` 纯函数中测试；网络下载通过 mock 覆盖
- 可观测：正文/图片必须记录 status/error/extracted_at/downloaded_at
- 幂等性：重复补跑同一日期不产生重复记录，不重复下载已成功图片
- 无新增依赖：只使用 Python 标准库和已有 step6 能力
- 风格一致：无 type hints，手写 parse_args，中文 print，Path 文件 I/O

## 决策覆盖矩阵

| 决策 ID | 覆盖的 FR | 说明 |
|---|---|---|
| D-001@v1 | FR-01, FR-03 | 范围：所有文章补正文，仅 top10 补图 |
| D-002@v1 | FR-01, FR-02 | 正文必须来自原页面提取，禁止 LLM 虚构 |
| D-003@v1 | FR-04 | 首图保存 URL 与本地文件 |
| D-004@v1 | FR-05 | 独立 helper + CLI |
| D-005@v1 | FR-06 | best-effort 不阻断日报，支持补跑 |
| D-006@v1 | FR-07, FR-09 | 14A upsert 保留 14B 字段，schema v2 兼容 |
| D-007@v1 | FR-08 | 图片单独抓 HTML，不改变 step6 契约 |
