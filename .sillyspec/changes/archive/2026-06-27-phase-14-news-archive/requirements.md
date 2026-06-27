---
author: lmr
created_at: 2026-06-27 20:53:53
schema_version: 1
doc_type: requirements
change_id: 2026-06-27-news-archive-core
phase: 14A
---

# Requirements

## 角色

| 角色 | 说明 |
|---|---|
| Daily 流水线 | 每日执行 step1_3 → step4 → step6 → step7 → step8 的自动化新闻流水线 |
| step4 classifier | Phase 14A 的归档触发点，拥有所有合格文章全量池与 top-10 子集 |
| archive helper | 新增 `news_archive.py`，负责 JSONL record 构造与幂等写入 |
| archive backfill CLI | 新增 `archive_news.py`，负责历史日期补跑 |
| 后续分析者 | 未来使用 JSONL 数据做月报、趋势分析、栏目回顾 |

## 功能需求

### FR-01: 归档所有合格文章元数据
覆盖决策：D-001@v1, D-002@v1, D-005@v1

Given Phase 13 step4 已完成涉华过滤、质量过滤、9 栏评分和栏目归属
When step4 得到 `classified` 全量文章池和 `selected` top-10 子集
Then Phase 14A 必须把 `classified` 中所有文章写入月度 JSONL
And 不限于进入 top-10 的文章
And 每条记录标记 `selected_in_top10=true|false`

### FR-02: JSONL record v1 字段
覆盖决策：D-002@v1, D-008@v1

Given 一篇合格文章 article
When `news_archive.build_record(article, today_str, selected_urls)` 被调用
Then 生成 record，至少包含：

- `schema_version`
- `id`
- `date`
- `archived_at`
- `updated_at`
- `source`
- `url`
- `normalized_url`
- `title`
- `column`
- `category`
- `rank_within_column`
- `aggregate_score`
- `priority`
- `selected_in_top10`
- `score_source`
- `signals`
- `archive_status="metadata-only"`

And `body` 与 `images` 不是必填字段

### FR-03: URL normalize 与稳定 id
覆盖决策：D-002@v1

Given 任意 article URL
When `normalize_url(url)` 被调用
Then 删除 fragment 与常见 tracking query 参数
And 保留业务 query 参数

Given normalized_url
When `article_id(url)` 被调用
Then 返回 `sha1(normalized_url)` 的 hex 字符串

### FR-04: 月度 JSONL 幂等 upsert
覆盖决策：D-002@v1, D-008@v1

Given `/mnt/e/每日新中国/archive/articles/YYYY-MM.jsonl` 已存在或不存在
When `archive_articles(today_str, classified, selected)` 被调用
Then 文件不存在时创建
And 文件存在时按 `id` upsert
And 同一 URL 重复运行不会产生重复行
And 已存在记录的 `archived_at` 保持不变
And `updated_at` 更新为本次写入时间

### FR-05: step4 默认 best-effort 触发归档
覆盖决策：D-003@v1, D-006@v1, D-007@v1

Given step4.run() 完成分类并准备/完成写入 `1新闻_链接.md`
When 调用 `news_archive.archive_articles_best_effort(today_str, classified, selected, dry_run=dry_run)`
Then 归档成功时打印统计信息
And 归档失败时仅打印 `⚠ 新闻归档失败: ...`
And 不 raise 异常
And 不影响 `run_all.sh` 继续运行
And 不修改 `run_all.sh`

### FR-06: step4 暴露纯数据分类函数
覆盖决策：D-004@v1, D-010@v1

Given `archive_news.py --date` 需要补跑指定日期
When 它需要获得指定日期的全量 classified 与 selected
Then `step4.py` 必须提供新增函数 `build_classification_result(today)`
And 该函数返回 `(classified, selected)`
And 不写 `1新闻_链接.md`
And 不触发 archive
And `step4.run()` 与 `archive_news.py` 共用该函数

### FR-07: 独立补跑命令
覆盖决策：D-004@v1, D-010@v1

Given 用户运行 `python3 archive_news.py --date 2026-06-27`
When 指定日期的上游 `0新闻_粗筛.md` 存在
Then 命令使用 `step4.build_classification_result(today)` 获取 classified/selected
And 调用 `news_archive.archive_articles(...)` 写入月度 JSONL
And 不重写 `1新闻_链接.md`

Given 用户运行 `python3 archive_news.py --date 2026-06-27 --dry-run`
When 归档逻辑执行
Then 只打印将写入的记录数量和目标路径
And 不落盘

### FR-08: news_archive 不依赖 step4 import
覆盖决策：D-009@v1

Given `step4.py` 会 import `news_archive`
When `news_archive.py` 需要推断 source
Then `news_archive.py` 必须使用自包含 `infer_source(url, article)`
And 不得 `import step4`
And 避免 step4 ↔ news_archive 循环依赖

### FR-09: 测试覆盖
覆盖决策：D-001@v1 ~ D-010@v1

Given `tests/test_news_archive.py`
When 执行 `python3 tests/test_news_archive.py`
Then 必须覆盖：

- URL normalize 删除 tracking 参数
- `article_id` 稳定
- `build_record` 字段完整
- `selected_in_top10` 标记正确
- JSONL upsert 幂等
- upsert 保留 `archived_at` 刷新 `updated_at`
- dry-run 不写文件
- best-effort 捕获异常不 raise

## 非功能需求

- 兼容性：不改变日报产物格式；不修改 `run_all.sh`
- 可回退：移除 step4 的 helper 调用即可停止归档；JSONL 数据不影响旧流水线
- 可测试：核心逻辑在 `news_archive.py` 纯函数中，可独立单测
- 可观测：归档成功/失败必须打印中文状态信息
- 幂等性：同日期重复运行不产生重复记录
- 无新增依赖：只使用 Python 标准库
- 风格一致：无 type hints，手写 parse_args，中文 print，Path 文件 I/O

## 决策覆盖矩阵

| 决策 ID | 覆盖的 FR | 说明 |
|---|---|---|
| D-001@v1 | FR-01, FR-02 | Phase 14 拆分，本期只做核心归档 |
| D-002@v1 | FR-01, FR-02, FR-03, FR-04 | 14A 只存 metadata + score/signals |
| D-003@v1 | FR-05 | 默认接入 run_all 但失败不阻断 |
| D-004@v1 | FR-06, FR-07 | 独立补跑命令 |
| D-005@v1 | FR-01 | Phase 13 前置依赖 |
| D-006@v1 | FR-05, FR-08 | helper module 方案 |
| D-007@v1 | FR-05 | 不修改 run_all.sh |
| D-008@v1 | FR-04 | archived_at / updated_at 语义 |
| D-009@v1 | FR-08 | 避免循环依赖 |
| D-010@v1 | FR-06, FR-07 | build_classification_result(today) |
