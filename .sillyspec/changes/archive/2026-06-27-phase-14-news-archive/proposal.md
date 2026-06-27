---
author: lmr
created_at: 2026-06-27 20:53:53
schema_version: 1
doc_type: proposal
change_id: 2026-06-27-news-archive-core
phase: 14A
---

# Proposal

## 动机

Daily 当前每天只保留最终展示的 top-10 新闻，其余已经通过涉华过滤、质量过滤和栏目评分的合格新闻被丢弃。用户希望把这些“符合标准但未进入展示页”的新闻也长期沉淀下来，形成自己的中国发展进展数据库。

Phase 14A 的目标是建立这个数据库的最小可运行骨架：先保存元数据与评分信号，保证从第一天开始不再丢掉合格新闻。正文、图片、月报分别留给后续 14B/14C。

## 关键问题

### 1. top-10 是展示层，不是知识边界

进入最终 PNG/HTML 的 10 条新闻只是当天最适合展示的新闻。未进入 top-10 的文章可能仍然是农业、能源、AI、科技、材料等方向的重要进展，具有长期分析价值。

### 2. 现有中间产物不能重建全量合格集

`1新闻_链接.md` 只写 top-10；`2新闻_已审核.md` 和 `3新闻_概述.md` 都基于 top-10 继续处理。若不在 step4 阶段保存 `classified` 全量池，后续无法知道哪些合格文章被丢掉。

### 3. 正文/图片/月报会拖慢核心闭环

正文抓取依赖 step6 的多层清洗，图片抓取失败率更高，月报又依赖稳定数据结构。把三者放进同一包会增加失败面。14A 先做 JSONL 核心归档，风险最小。

## 变更范围

本次做 Phase 14A：

- 新增 `news_archive.py` helper：构造 archive record、URL normalize、id 生成、月度 JSONL upsert、best-effort wrapper
- 新增 `archive_news.py --date YYYY-MM-DD [--dry-run]` 独立补跑命令
- 修改 `step4.py`：新增 `build_classification_result(today)`，`run()` 和 `archive_news.py` 共用；step4 内部 best-effort 触发归档
- 新增 `tests/test_news_archive.py`：测试 JSONL 归档核心逻辑
- 输出 `/mnt/e/每日新中国/archive/articles/YYYY-MM.jsonl`
- 不修改 `run_all.sh`；默认接入通过 step4 内部触发完成

## 不在范围内（显式清单）

- 不保存正文 `body`（14B）
- 不下载或保存图片（14B）
- 不生成月度 Markdown 报告（14C）
- 不实现查询 UI / 搜索 UI
- 不引入 SQLite / DuckDB / 外部数据库
- 不新增第三方依赖
- 不改变日报 top-10 展示逻辑
- 不改变 `1新闻_链接.md`、`2新闻_已审核.md`、`3新闻_概述.md`、HTML/PNG 的既有格式
- 不修改 `run_all.sh`
- 不替代 Phase 13；Phase 14A 执行前必须先完成 Phase 13 代码落地

## 成功标准（可验证）

- `news_archive.py` 可把合格 article dict 转成 JSONL record
- record 包含 `schema_version/id/date/archived_at/updated_at/source/url/normalized_url/title/column/selected_in_top10/archive_status`
- 同一 URL 重复归档不会产生重复行；保留首次 `archived_at`，刷新 `updated_at`
- dry-run 不写文件，只输出目标路径和统计
- step4 归档失败时只打印 warning，不阻断 `1新闻_链接.md` 写入
- `archive_news.py --date YYYY-MM-DD` 可补跑指定日期，且不重写 `1新闻_链接.md`
- `run_all.sh` 不发生改动
- `tests/test_news_archive.py` 可独立运行并覆盖 URL normalize / id / upsert / selected_in_top10 / best-effort
