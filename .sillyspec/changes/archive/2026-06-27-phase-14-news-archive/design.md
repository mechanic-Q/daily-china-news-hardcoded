---
author: lmr
created_at: 2026-06-27 16:20:00
schema_version: 1
doc_type: design
change_id: 2026-06-27-news-archive-core
phase: 14A
status: draft
---

# Phase 14A · News Archive Core

## 1. 背景

Daily 当前流水线只把每日最适合展示的 top-10 写入 `1新闻_链接.md`，其余已经通过涉华过滤、质量过滤、栏目归属和评分的合格新闻会被丢弃。

用户的新目标是：**所有符合栏目规则的合格新闻都应长期保存**。top-10 是日报展示层，不应等同于知识资产边界。那些未进入 top-10、但仍符合栏目标准的文章，未来可用于沉淀中国发展方向、产业进展、科技突破和社会治理的长期脉络。

Phase 13（commit `b56d2c7`）已完成 9 栏栏目语义契约和评分方案设计，是 Phase 14 的前置条件。Phase 14A 只实现核心归档骨架：metadata + score/signals，不做正文、图片和月报。

## 2. 设计目标

| ID | 目标 |
|----|------|
| G-01 | 将所有符合 Phase 13 栏目规则、已分配栏目但未必进入 top-10 的文章写入长期归档 |
| G-02 | 使用按月分片的 JSONL 作为主数据层，支持 append/upsert 与后续分析 |
| G-03 | 记录 enough metadata：date/title/url/source/column/score/signals/selected_in_top10/score_source |
| G-04 | 归档默认随 `run_all.sh` 自动发生，但失败不阻断日报 |
| G-05 | 提供独立补跑命令 `archive_news.py --date YYYY-MM-DD` |
| G-06 | 为 14B 正文/图片、14C 月报预留 schema 与目录结构，但本期不实现 |

## 3. 非目标

- 不保存正文 `body`（14B）
- 不抓取图片（14B）
- 不生成月报 Markdown（14C）
- 不改 `step1_3.py` / `step6.py` / `step7.py` / `step8.py`
- 不改 Phase 13 的栏目语义、评分公式或 top-10 选择逻辑
- 不引入 SQLite / DuckDB / external database
- 不新增第三方依赖
- 不改变现有日报产物格式：`1新闻_链接.md`、`2新闻_已审核.md`、`3新闻_概述.md`、HTML/PNG 均保持现有职责

## 4. 拆分判断

Phase 14 拆为三个可独立交付包：

| 包 | 内容 | 原因 |
|----|------|------|
| 14A | 核心 JSONL 归档：metadata + score/signals | 最小闭环；只依赖 step4 / Phase 13 评分结果 |
| 14B | 正文与图片补全 | 正文抓取慢、失败率高、清洗复杂；图片更不稳定 |
| 14C | 自动月报 | 依赖稳定 archive 数据结构 |

本次只做 14A。不是批量模式：虽然每日记录很多，但任务是设计通用归档模块和 JSONL schema，不是逐条处理每篇文章。

## 5. 总体方案

### 5.1 选定方案：helper module

新增 `news_archive.py` 作为归档 helper，提供纯函数：

- normalize URL
- 生成 `sha1(normalized_url)` id
- 构造 archive record
- 读写月度 JSONL
- 同 URL upsert / 幂等更新
- best-effort wrapper

`step4.py` 在 Phase 13 分类/评分完成，并确定 selected top-10 后，调用：

```python
archive_articles_best_effort(today_str, classified, selected, dry_run=dry_run)
```

调用在 `news_archive.py` 内部捕获所有异常。失败只打印 `⚠ 新闻归档失败: ...`，不 raise，不影响 `1新闻_链接.md` 写入，也不影响 `run_all.sh` 继续。

**Design Grill 修正**：不修改 `run_all.sh`。因为 run_all 已默认执行 step4；归档挂在 step4 内部即可满足"默认接入 run_all"，同时避免 `set -euo pipefail` 下额外 best-effort shell 分支。见 D-007@v1。

### 5.2 数据流

```
step1_3 → 0新闻_粗筛.md
  ↓
step4 (Phase 13)
  ├─ 涉华/质量过滤
  ├─ 9 栏 signals/score
  ├─ classified = 所有合格文章按栏目分桶
  ├─ selected = 每日 top-10 展示子集
  ├─ write 1新闻_链接.md
  └─ best-effort archive_articles(today, classified, selected)
          ↓
      /mnt/e/每日新中国/archive/articles/YYYY-MM.jsonl
```

### 5.3 独立补跑

新增 `archive_news.py`：

```bash
python3 archive_news.py --date 2026-06-27
python3 archive_news.py --date 2026-06-27 --dry-run
```

职责：对指定日期执行 14A 归档写入，**不重写 `1新闻_链接.md`**。

为避免补跑命令只能重跑整个 step4，Phase 14A 要求 `step4.py` 暴露一个纯数据函数（新增）：

```python
def build_classification_result(today):
    """返回 (classified, selected)，不写 1新闻_链接.md，不触发 archive。"""
```

`step4.run()` 与 `archive_news.py` 共用该函数：

- `step4.run()`：`build_classification_result` → 写 `1新闻_链接.md` → `archive_articles_best_effort`
- `archive_news.py`：`build_classification_result` → `archive_articles`

如果 Phase 13 execute 尚未完成，则本期 plan 必须把 `archive_news.py` 的实现依赖明确挂到 Phase 13 代码落地之后。见 D-010@v1。

### 5.4 输出路径

```
/mnt/e/每日新中国/archive/
└── articles/
    ├── 2026-06.jsonl
    ├── 2026-07.jsonl
    └── ...
```

14A 只创建 `archive/articles/`。未来 14B/14C 可再新增：

```
archive/images/
archive/monthly/
archive/indexes/
```

## 6. 文件变更清单

| 操作 | 文件路径 | 说明 |
|------|----------|------|
| 新增 | `news_archive.py` | 归档 helper：record 构造、id 生成、JSONL upsert、best-effort write |
| 新增 | `archive_news.py` | 独立补跑 CLI：`--date` / `--dry-run`，调用 `news_archive` |
| 修改 | `step4.py` | 新增 `build_classification_result(today)`；`run()` 共用该函数并在写日报后 best-effort 调用 `news_archive.archive_articles_best_effort` |
| 不变 | `run_all.sh` | 不修改。run_all 已默认执行 step4，归档通过 step4 内部触发（D-007@v1） |
| 新增 | `tests/test_news_archive.py` | 单元测试：id、URL normalize、JSONL upsert、selected_in_top10、dry-run |

## 7. 接口定义

### 7.1 `news_archive.py`（新增）

实现签名遵循项目风格，不写 type hints。

```python
BASE_DIR = Path("/mnt/e/每日新中国")
ARCHIVE_DIR = BASE_DIR / "archive"
ARTICLES_DIR = ARCHIVE_DIR / "articles"
SCHEMA_VERSION = 1


def normalize_url(url):
    """去除 URL 片段、常见 tracking query，保留语义 query。"""


def article_id(url):
    """返回 sha1(normalized_url) 十六进制字符串。"""


def month_path(today_str):
    """返回 archive/articles/YYYY-MM.jsonl 路径。"""


def infer_source(url, article):
    """自包含信源推断；不 import step4.detect_source，避免 step4 ↔ news_archive 循环依赖。"""


def build_record(article, today_str, selected_urls):
    """从 step4 article dict 构造归档 record。"""


def load_month_records(path):
    """读取 JSONL 为 dict[id] = record；不存在返回空 dict。"""


def write_month_records(path, records):
    """按 date/id 稳定排序写回 JSONL。"""


def archive_articles(today_str, classified, selected, dry_run=False):
    """归档所有 classified 中的文章，返回统计 dict。"""


def archive_articles_best_effort(today_str, classified, selected, dry_run=False):
    """捕获所有异常，只打印 warning，不中断日报。"""
```

### 7.2 `archive_news.py`（新增）

```python
def parse_args():
    """手动解析 --date YYYY-MM-DD / --dry-run。"""


def main():
    """补跑指定日期归档。"""
```

## 8. 数据模型

### 8.1 JSONL record v1

```json
{
  "schema_version": 1,
  "id": "sha1(normalized_url)",
  "date": "2026-06-27",
  "archived_at": "2026-06-27T16:20:00+08:00",
  "updated_at": "2026-06-27T16:20:00+08:00",
  "source": "新华社",
  "url": "https://...",
  "normalized_url": "https://...",
  "title": "...",
  "column": "🤖 AI智能前沿",
  "category": "🤖 AI智能前沿",
  "rank_within_column": 3,
  "aggregate_score": 8.46,
  "priority": 8.46,
  "selected_in_top10": false,
  "score_source": "llm",
  "signals": {
    "relevance": {
      "🔬 世界性科研突破": 0,
      "🤖 AI智能前沿": 9
    },
    "importance": 7,
    "timeliness": 6
  },
  "archive_status": "metadata-only"
}
```

### 8.2 字段说明

| 字段 | 必填 | 来源 | 说明 |
|------|------|------|------|
| `schema_version` | yes | constant | 当前为 1 |
| `id` | yes | derived | `sha1(normalized_url)` |
| `date` | yes | CLI/date | 处理日期 |
| `archived_at` | yes | first write | ISO 8601，本地时区；首次入档时间，upsert 时保留 |
| `updated_at` | yes | every write | ISO 8601，本地时区；每次 upsert 更新时间 |
| `source` | yes | `infer_source(url, article)` | 信源名称；helper 自包含推断，不 import step4 |
| `url` | yes | article | 原始 URL |
| `normalized_url` | yes | derived | 用于去重 |
| `title` | yes | article | 标题 |
| `column` | yes | article | 最终栏目 |
| `category` | no | article | 与 column 同义，保留兼容 |
| `rank_within_column` | no | derived | 当前栏目排序序号，从 1 开始 |
| `aggregate_score` | no | Phase 13 | 新评分链分数 |
| `priority` | no | legacy/Phase13 | 兼容旧 priority 字段 |
| `selected_in_top10` | yes | selected set | 是否进入日报展示 |
| `score_source` | no | Phase 13 | `llm` / `keyword-fallback` |
| `signals` | no | Phase 13 | LLM 多维评分原始信号 |
| `archive_status` | yes | constant | 14A 固定 `metadata-only` |

## 9. 兼容策略

| 场景 | 行为 |
|------|------|
| 归档目录不存在 | 自动创建 `archive/articles/` |
| 月度 JSONL 不存在 | 创建新文件 |
| 同 URL 重复入档 | 用 `id` upsert，避免重复行；保留原 `archived_at`，刷新 `updated_at` |
| 归档失败 | `archive_articles_best_effort` 捕获异常并打印 warning，日报继续 |
| `signals` 字段缺失（Phase 13 未完全落地/legacy）| record 中 `signals=null`，仍写 metadata + priority |
| `aggregate_score` 缺失 | 回退到 `priority` |
| `source` 缺失 | 使用 `detect_source(url)` 或空字符串 |
| dry-run | 打印将写入数量和目标路径，不落盘 |
| 旧日期补跑 | `archive_news.py --date` 可重跑；同 URL 幂等更新 |

## 10. 风险登记

| 编号 | 风险 | 等级 | 应对策略 |
|------|------|------|----------|
| R-01 | Phase 14A 依赖 Phase 13 分类/评分代码落地；当前 Phase 13 只是 brainstorm commit | P0 | execute 前先完成 Phase 13；plan 中把 Phase 13 作为前置依赖 |
| R-02 | step4 当前只把 selected top10 写入 md，未暴露 classified 全量给外部命令 | P1 | 在 Phase 13/14A 中提取分类函数或在 step4 内直接调用 helper；独立补跑复用同一函数 |
| R-03 | JSONL upsert 需要重写整月文件，若文件损坏会影响整月 | P1 | 写临时文件 `.tmp` 后原子 replace；测试 malformed JSON 行处理 |
| R-04 | URL normalize 过度删除 query 导致不同文章合并 | P1 | 仅删除常见 tracking 参数和 fragment，保留业务 query |
| R-05 | 归档失败不阻断可能掩盖长期失败 | P1 | warning 明确输出；后续 14C/月报前检查归档数量；可增加 smoke test |
| R-06 | records 字段随 Phase 13 signals 改动而漂移 | P2 | `schema_version=1` 固化；未知字段可保留，必填字段最小化 |
| R-07 | JSONL 文件随时间增长 | P2 | 月分片；每日几百行规模可控 |
| R-08 | run_all best-effort 与 `set -e` 冲突 | P1 | Design Grill 决定不改 run_all；归档通过 step4 内部 helper catch 触发（D-007@v1） |
| R-09 | `archive_news.py` 补跑若直接调用 `step4.run()` 会重写 `1新闻_链接.md` | P1 | 新增 `step4.build_classification_result(today)`，补跑只获取 classified/selected 并写 archive，不重写日报（D-010@v1） |
| R-10 | `news_archive.py` import `step4.detect_source` 会与 step4 import news_archive 形成循环依赖 | P1 | `news_archive.py` 实现自包含 `infer_source(url, article)`，避免 import step4（D-009@v1） |

## 11. 决策追踪

| ID | 决策 | 覆盖 |
|----|------|------|
| D-001@v1 | Phase 14 拆分为 14A/14B/14C，本次只做 14A | §4, §5 |
| D-002@v1 | 14A 只存 metadata + score/signals，不存正文/图片/月报 | §2, §3, §8 |
| D-003@v1 | 默认随 run_all 自动归档，但失败不阻断日报 | §5, §9, R-08 |
| D-004@v1 | 提供独立补跑命令 `archive_news.py --date` | §5.3, §7.2 |
| D-005@v1 | Phase 13 commit `b56d2c7` 必须保留，先做 Phase 13 再做 Phase 14 | §1, R-01 |
| D-006@v1 | 实现方案选 B：helper module `news_archive.py` + step4 best-effort + archive_news CLI | §5, §6, §7 |
| D-007@v1 | 不修改 run_all.sh；归档通过 step4 内部 best-effort helper 默认触发 | §5.1, §6, R-08 |
| D-008@v1 | upsert 保留首次 archived_at，并刷新 updated_at | §8, §9 |
| D-009@v1 | news_archive.py 不 import step4；信源推断自包含，避免循环依赖 | §7.1, R-10 |
| D-010@v1 | step4 新增 build_classification_result(today)，run() 和 archive_news.py 共用，补跑不重写日报 | §5.3, §6, R-09 |

## 12. 自审

### 12.1 需求覆盖

- ✅ 覆盖“所有合格新闻都留下”：G-01 + §5 数据流
- ✅ 覆盖“14A 不含正文/图片”：§3 非目标 + §8 `archive_status=metadata-only`
- ✅ 覆盖“默认自动沉淀”：D-003 + §5.2
- ✅ 覆盖“失败不阻断”：§9 兼容策略 + R-08
- ✅ 覆盖“补跑历史日期”：D-004 + §5.3 + §7.2
- ✅ 覆盖“Phase 13 不能丢”：D-005 + R-01

### 12.2 Grill / 决策覆盖

- ✅ D-001~D-010 全部映射到设计章节（含 Design Grill 追加 D-007~D-010）
- ✅ 无未解决 P0/P1 业务问题

### 12.3 约束一致性

- ✅ 与 ARCHITECTURE 文件接力模式一致：仍使用 `/mnt/e/每日新中国` 文件系统，不引入 DB
- ✅ 与 CONVENTIONS 一致：新增 Python 文件手写 `parse_args`，无 type hints，中文 print，Path 写入
- ✅ 与 local.yaml 一致：无 build/test/lint，run_all 为完整管道
- ✅ 与 Phase 13 设计一致：依赖 Phase 13 的 `classified/selected/signals` 数据

### 12.4 真实性

- ✅ 现有文件：`step4.py`, `run_all.sh` 已读取确认
- ✅ 新增文件均标注“新增”：`news_archive.py`, `archive_news.py`, `tests/test_news_archive.py`
- ✅ 字段 `priority`, `category`, `column` 来自 step4 现有/Phase13 计划；`signals`, `aggregate_score`, `score_source` 来自 Phase 13 计划

### 12.5 YAGNI

- ✅ 不做正文、图片、月报
- ✅ 不做数据库
- ✅ 不做查询 UI
- ✅ 不做统计图

### 12.6 验收可测试

- ✅ URL normalize/id/upsert/dry-run 都可单元测试
- ✅ best-effort 不阻断可 mock 异常测试
- ✅ 月度 JSONL 路径可断言

### 12.7 生命周期契约表

- ❌ 不适用：本变更不涉及 session / lease / agent_run / daemon / lifecycle / claim / heartbeat

### 12.8 整体判断

**自审通过 ✅。** 可进入 Design Grill。

## 13. Design Grill Result

**status: passed**

### 13.1 Cross-Check Matrix

| ID | 层级 | 交叉点 | 证据 A | 证据 B | 结论 | 决策 |
|----|------|--------|--------|--------|------|------|
| X-001 | consistency | “默认接入 run_all” vs 是否修改 run_all.sh | D-003@v1 | run_all.sh:36 已执行 step4；run_all `set -euo pipefail` | 不应额外改 run_all；挂在 step4 内部更安全 | D-007@v1 |
| X-002 | definition | upsert 后 `archived_at` 语义 | design §8 record | `archive_news.py --date` 可重复补跑 | `archived_at` 必须代表首次入档，需新增 `updated_at` | D-008@v1 |
| X-003 | feasibility | `news_archive.py` 是否复用 step4.detect_source | design §8 source 来源写 detect_source | step4 将 import news_archive | 会循环依赖 | D-009@v1 |
| X-004 | feasibility | 独立补跑如何不重写日报 | design §5.3 archive_news | step4.py:277 run() 当前分类+写 `1新闻_链接.md` 耦合 | 需提取 `build_classification_result(today)` | D-010@v1 |
| X-005 | consistency | 非目标“不改 run_all” vs 文件清单“修改 run_all.sh” | design §3 | design §6 | 冲突 | §6 修正为 run_all 不变 |
| X-006 | compatibility | Phase 14A 依赖 Phase 13 signals，但 Phase 13 尚未 execute | design §1 / R-01 | 当前 step4.py 仍 8 栏 legacy | 是真实前置依赖 | 保留 R-01 P0，plan 必须先检查 Phase 13 已落地 |

### 13.2 Question Distribution

| 分类 | 数量 | 含义 |
|------|------|------|
| immediately_answered | 6 | 均可由 design + 源码确认并修正文档 |
| needs_thinking | 0 | 无需用户业务判断 |
| unresolved | 0 | 无阻塞项 |

### 13.3 Unresolved Blockers

无 P0/P1 unresolved blocker。

注意：R-01 是执行顺序风险，不是设计未决项。Phase 14A plan/execute 必须把 Phase 13 代码落地作为前置检查。

### 13.4 修订摘要

- `run_all.sh` 从“可能修改”改为“不变”；默认接入通过 step4 内部 best-effort helper 实现
- JSONL record 增加 `updated_at`，明确 upsert 保留首次 `archived_at`
- `news_archive.py` 增加 `infer_source`，禁止 import step4，避免循环依赖
- `step4.py` 增加 `build_classification_result(today)` 作为 archive_news 独立补跑的共享分类函数

**Design Grill passed ✅。** 可进入 Step 13 用户确认并生成规范文件。
