---
author: lmr
created_at: 2026-06-29 14:13:38
schema_version: 1
doc_type: design
change_id: 2026-06-29-archive-body-image-enrichment
phase: 14B
---

# Phase 14B · Archive Body + Top Image Enrichment

## 1. 背景

Phase 14A 已把所有通过 Phase 13 栏目评分与筛选的合格文章写入 `/mnt/e/每日新中国/archive/articles/YYYY-MM.jsonl`，但当前记录仍是 `archive_status="metadata-only"`：只保存标题、URL、栏目、评分信号与是否进入 top10。

这解决了“合格新闻不再丢失”的核心问题，但还不足以支撑长期回溯与未来月报：只有标题和评分，无法验证文章原文内容，也无法在展示层或回顾层使用首图素材。

Phase 14B 的目标是在 14A JSONL 基础上补全两个内容层字段：

1. 对所有归档文章补充真实正文。
2. 对当日 top10 文章 best-effort 补充首图。

用户明确要求：正文必须是真实、可验证、来自原始网页提取的内容，不能含任何 LLM 虚构、生成、润色或补写成分。

## 2. 设计目标

| ID | 目标 |
|----|------|
| G-01 | 为所有归档文章补充 `body`，正文只来自原始 URL 页面提取 |
| G-02 | 明确记录正文提取状态、错误原因、提取时间与来源 URL，保证可审计 |
| G-03 | 仅为 `selected_in_top10=true` 的文章抓取首图 |
| G-04 | 首图同时记录原始 `image_url` 与本地 `image_path` |
| G-05 | 图片下载 best-effort：有图就补，没图或下载失败不阻断日报 |
| G-06 | run_all 默认 best-effort 触发增强，不因正文/图片失败导致日报失败 |
| G-07 | 提供独立 CLI 对指定日期补跑缺失或失败的正文/首图 |
| G-08 | 保持 14A JSONL 向后兼容，旧 `metadata-only` 记录仍可读取 |

## 3. 非目标

- 不抓取多图，只抓首图
- 不为非 top10 文章抓图
- 不用 LLM 生成、摘要、改写、润色或补全正文
- 不做 OCR，不从图片中提取正文
- 不生成月报（14C）
- 不做查询 UI / 搜索 UI / 统计报表
- 不引入 SQLite / DuckDB / 外部数据库
- 不新增第三方依赖
- 不改变 `1新闻_链接.md`、`2新闻_已审核.md`、`3新闻_概述.md`、HTML/PNG 的既有格式
- 不改变 Phase 13 栏目评分与 top10 选择逻辑

## 4. 拆分判断

本期不再继续拆分。

Phase 14 已在 14A 设计中拆为：

| 包 | 内容 | 状态 |
|----|------|------|
| 14A | metadata + score/signals JSONL | 已完成 |
| 14B | 正文 + 首图补全 | 本期 |
| 14C | 自动月报 | 后续 |

14B 内部虽涉及正文和图片两个字段簇，但它们都属于同一条 archive record 的内容增强，不构成独立业务模块。任务不是逐篇文章开发，不走批量模式；多篇文章通过通用 enrichment 函数循环处理。

## 5. 总体方案

### 5.1 选定方案：独立 archive_enrich helper + CLI

新增 `archive_enrich.py`，作为归档增强 helper，职责集中在 archive JSONL 的内容补全：

- 读取 `archive/articles/YYYY-MM.jsonl`
- 选择指定日期的记录
- 对所有记录补真实正文
- 对 top10 记录补首图
- 幂等更新 JSONL
- best-effort 包装，不阻断日报
- CLI 补跑指定日期

`step4.py` 在 14A 的 `archive_articles_best_effort(...)` 之后调用：

```python
archive_enrich.enrich_archive_best_effort(today_str, selected, dry_run=dry_run)
```

失败只打印 warning，不 raise，不影响日报主流程。

### 5.2 数据流

```
step1_3 → 0新闻_粗筛.md
  ↓
step4 (Phase 13 + 14A)
  ├─ 分类 / 评分 / top10 选择
  ├─ write 1新闻_链接.md
  ├─ archive_articles_best_effort(...)
  │     ↓
  │   archive/articles/YYYY-MM.jsonl  # metadata-only
  └─ enrich_archive_best_effort(...)
        ├─ all records: step6.fetch_and_extract(url, title) → body
        ├─ top10 only: first image url extraction + download
        └─ archive/articles/YYYY-MM.jsonl  # enriched upsert
```

### 5.3 正文真实性规则

正文只允许来自 `step6.fetch_and_extract(url, title)` 的页面提取结果。

禁止：

- LLM 生成正文
- LLM 改写正文
- LLM 润色正文
- 根据标题补写正文
- 用摘要当正文
- 提取失败时编造占位内容

提取失败时只写状态与错误，不写 fake body。

### 5.4 首图规则

首图只作用于 `selected_in_top10=true` 的记录。

查找顺序：

1. `og:image`
2. `twitter:image`
3. 正文 HTML 中第一个合理 `<img src="...">`

下载规则：

- URL 用 `urllib.parse.urljoin(article_url, image_src)` 归一化
- 只接受 `http/https`
- 下载时设置 User-Agent
- content-type 优先判断图片扩展名
- 本地路径：`archive/images/YYYY-MM/<article_id>.<ext>`
- 下载失败不影响正文、不影响日报

### 5.5 CLI 补跑

新增独立命令：

```bash
python3 archive_enrich.py --date 2026-06-29
python3 archive_enrich.py --date 2026-06-29 --missing-only
python3 archive_enrich.py --date 2026-06-29 --dry-run
python3 archive_enrich.py --date 2026-06-29 --max-seconds 0
```

语义：

- `--date`：指定处理日期
- `--missing-only`：只补缺失或失败记录，跳过已成功正文/图片
- `--dry-run`：只打印统计与目标路径，不写 JSONL，不下载图片
- `--max-seconds`：最大执行秒数；`0` 表示不限制

### 5.6 run_all best-effort 时间预算

run_all 触发的自动补全必须 best-effort。

自动路径使用时间预算，超过预算时停止处理剩余记录，已成功记录保留，未处理记录保持原状态，后续可用 CLI 补跑。

建议常量：

```python
AUTO_MAX_SECONDS = 180
```

CLI 默认不限制或由用户通过 `--max-seconds` 指定。

## 6. 文件变更清单

| 操作 | 文件路径 | 说明 |
|------|----------|------|
| 新增 | `archive_enrich.py` | 归档正文 + 首图增强 helper 与 CLI |
| 修改 | `step4.py` | 14A 归档后 best-effort 调用 `archive_enrich.enrich_archive_best_effort` |
| 修改 | `news_archive.py` | `SCHEMA_VERSION` 升至 2；新增/导出 `IMAGES_DIR`；14A `archive_articles` upsert 必须合并保留已有 14B enrichment 字段 |
| 新增 | `tests/test_archive_enrich.py` | 单元测试：正文状态、图片提取、路径、dry-run、best-effort、missing-only |
| 修改 | `tests/test_news_archive.py` | 如 JSONL schema 增加字段，需要补兼容断言 |
| 不变 | `run_all.sh` | 不修改；通过 step4 内部 best-effort 触发 |
| 不变 | `step6.py` | 优先复用 `fetch_and_extract`；只有计划阶段发现不可复用时才最小提取公共 helper |

## 7. 接口定义

### 7.1 `archive_enrich.py` 新增常量

```python
AUTO_MAX_SECONDS = 180
MAX_IMAGE_BYTES = 5 * 1024 * 1024
IMAGE_EXT_BY_TYPE = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
```

### 7.2 `archive_enrich.py` 新增函数

遵循项目风格，不写 type hints。

```python
def parse_args():
    """手写解析 --date / --missing-only / --dry-run / --max-seconds。"""


def image_month_dir(today_str):
    """返回 archive/images/YYYY-MM 目录。"""


def should_enrich_body(record, missing_only):
    """判断是否需要正文补全。"""


def should_enrich_image(record, missing_only):
    """仅 top10 且缺失/失败时补首图。"""


def enrich_body(record):
    """调用 step6.fetch_and_extract(url, title)，返回更新字段 dict。"""


def fetch_html_for_image(record):
    """仅为 top10 首图提取抓取 HTML；复用 step6 的 static/chromium 路由。"""


def extract_first_image_url(html, article_url):
    """从 og:image/twitter:image/img 中提取首图 URL。"""


def download_image(image_url, image_path, dry_run=False):
    """下载图片到本地，返回状态与错误。"""


def enrich_image(record, today_str, dry_run=False):
    """为 top10 文章提取并下载首图，返回更新字段 dict。"""


def enrich_records(today_str, records, selected=None, missing_only=False, dry_run=False, max_seconds=0):
    """补全指定日期记录，返回更新后的 records 与统计。"""


def enrich_archive(today_str, selected=None, missing_only=False, dry_run=False, max_seconds=0):
    """读取月度 JSONL → enrich_records → 写回。"""


def enrich_archive_best_effort(today_str, selected=None, dry_run=False):
    """捕获所有异常，只打印 warning，不阻断日报。"""
```

### 7.3 `step4.py` 调用点

在 14A 归档成功/失败处理之后追加 best-effort 调用：

```python
try:
    import archive_enrich
    archive_enrich.enrich_archive_best_effort(today_str, selected, dry_run=dry_run)
except Exception as e:
    print(f"⚠ 归档正文/首图补全失败: {e}", file=sys.stderr)
```

实际实现可把异常捕获放在 `archive_enrich.enrich_archive_best_effort` 内部；step4 保持最薄调用。

## 8. 数据模型

### 8.1 JSONL record v2 增量字段

`schema_version` 升至 `2`。14A 字段保持不变，14B 增加以下字段：

```json
{
  "body": "页面提取出的真实正文",
  "body_status": "extracted",
  "body_error": null,
  "body_extracted_at": "2026-06-29T14:07:38+08:00",
  "body_source_url": "https://...",
  "image_url": "https://.../image.jpg",
  "image_path": "/mnt/e/每日新中国/archive/images/2026-06/<id>.jpg",
  "image_status": "downloaded",
  "image_error": null,
  "image_downloaded_at": "2026-06-29T14:07:38+08:00",
  "archive_status": "body-image-enriched"
}
```

### 8.2 状态枚举

#### body_status

| 值 | 语义 |
|----|------|
| `missing` | 尚未尝试正文补全 |
| `extracted` | 正文成功提取，`body` 可用 |
| `failed` | 页面抓取或正文提取失败，`body_error` 说明原因 |
| `skipped` | 因时间预算或 dry-run 跳过 |

#### image_status

| 值 | 语义 |
|----|------|
| `not_selected` | 非 top10，不抓图 |
| `missing` | top10 但尚未尝试 |
| `downloaded` | 首图已下载，`image_url` / `image_path` 可用 |
| `not_found` | 页面未发现可用首图 |
| `failed` | 找到图但下载失败，`image_error` 说明原因 |
| `skipped` | 因时间预算或 dry-run 跳过 |

#### archive_status

| 值 | 语义 |
|----|------|
| `metadata-only` | 14A 状态，未成功补正文 |
| `body-enriched` | 正文已成功补全，图片未下载或不适用 |
| `body-image-enriched` | 正文已成功补全，top10 首图已下载 |
| `body-failed` | 正文补全失败，保留错误信息 |

## 9. 兼容策略

- 旧 JSONL 中没有 14B 字段时，读取逻辑视为 `body_status="missing"`、`image_status="missing"` 或 `not_selected`。
- `news_archive.load_month_records` 不需要强校验字段，旧记录可继续加载。
- `archive_articles` upsert 时必须保留已有 14B 字段，避免 14A 再跑覆盖掉正文/图片字段；新 record 只能覆盖 14A metadata/score/signals 字段。
- `run_all.sh` 不修改；失败语义不变。
- `1新闻_链接.md`、`2新闻_已审核.md`、`3新闻_概述.md`、HTML/PNG 格式不变。
- 如果 `archive_enrich.py` 不存在或运行失败，日报仍按 14A 行为继续。

## 10. 风险登记

| 编号 | 风险 | 等级 | 应对策略 |
|------|------|------|----------|
| R-01 | 正文提取失败或提取到导航/CSS/污染文本 | P0 | 复用 step6 的污染检测；失败只记录 `body_error`，不写 fake body |
| R-02 | 自动补全拖慢 run_all | P1 | best-effort + `AUTO_MAX_SECONDS` 时间预算 + CLI 补跑 |
| R-03 | 14A upsert 覆盖 14B 字段 | P0 | 修改 14A upsert 合并逻辑，保留已有 body/image 字段；测试先写旧记录再跑 archive_articles |
| R-04 | 图片站点反爬或无图 | P2 | best-effort；无图写 `not_found`，下载失败写 `failed` |
| R-05 | 图片 URL 相对路径或无扩展名 | P1 | `urljoin` 归一化；content-type 推断扩展名；失败保留错误 |
| R-07 | 图片提取需要 HTML，但正文 helper 只返回 body | P1 | `enrich_image` 为 top10 单独抓 HTML；不改变 step6.fetch_and_extract 的返回契约 |
| R-06 | 正文真实性被误解为摘要/改写 | P0 | design/requirements 明确禁止 LLM 参与正文生成；测试验证不调用 LLM |

## 11. 决策追踪

| 决策 | 覆盖章节 | 设计落实 |
|------|----------|----------|
| D-001@v1 范围：全量正文 + top10 首图 | §2, §3, §5 | 所有记录补 body，仅 top10 补 image |
| D-002@v1 正文真实性 | §5.3, §8, §10 | body 只来自 `step6.fetch_and_extract`，失败不写 fake body |
| D-003@v1 首图保存策略 | §5.4, §8 | 保存 `image_url` 与 `image_path` |
| D-004@v1 独立 helper + CLI | §5.1, §5.5, §7 | 新增 `archive_enrich.py` |
| D-005@v1 best-effort 不阻断 | §5.6, §9, §10 | 自动路径 catch all + 时间预算 + CLI 补跑 |
| D-006@v1 14A upsert 保留 14B 字段 | §6, §9, §10 | 修改 `news_archive.archive_articles` 合并逻辑 |
| D-007@v1 首图单独抓 HTML | §5.4, §7, §10 | 不改 `step6.fetch_and_extract` 返回契约 |

## 12. 自审

| 检查项 | 结果 |
|--------|------|
| 覆盖用户确认需求 | PASS：全量正文、top10 首图、URL+本地路径、best-effort、CLI 补跑均覆盖 |
| 正文真实性 | PASS：明确禁止 LLM 生成/润色/补写，失败只写状态 |
| Grill 决策覆盖 | PASS：D-001~D-005 均在设计章节和字段模型中体现 |
| 约定一致性 | PASS：手写 parse_args、中文 print、无 type hints、Path/JSONL 风格一致 |
| Brownfield 兼容 | PASS：不改 run_all，不改日报产物格式，旧 JSONL 可读 |
| YAGNI | PASS：不做多图、月报、搜索 UI、数据库 |
| 风险识别 | PASS：正文污染、运行耗时、upsert 覆盖、图片失败均登记 |
| 生命周期契约表 | N/A：不涉及 session/lease/daemon/heartbeat 等状态机协议 |

自审结论：通过，可进入 Design Grill。
