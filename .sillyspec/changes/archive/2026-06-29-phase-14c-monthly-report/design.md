---
author: lmr
created_at: 2026-06-29 21:00:00
schema_version: 1
doc_type: design
change_id: phase-14c-monthly-report
phase: 14C
---

# Phase 14C 自动月报 — 设计文档

## 1. 背景

Phase 14A/14B 已建立完整的归档体系：每日新闻以月度 JSONL 分片存储（schema v2 含 metadata + score/signals + body + image），首图按月存档到 `archive/images/YYYY-MM/`。但当前归档数据只是"原料库"，没有可发布的月度产物。

需求：在月末（或任意时间）基于 archive 数据生成可发布的月报，包含：
- 月度总述与趋势解读（短小、可读）
- 月度统计/趋势数据报告（含栏目/信源/日历分布）
- 每栏目代表新闻条目（带正文摘要、原文链接、首图）

产物形式要与日报对齐：Markdown + HTML + PNG 三件套，加一份机器可读的统计 JSON。

## 2. 设计目标

| 编号 | 目标 |
|------|------|
| G-01 | 单文件 CLI 入口 `monthly_report.py`，遵循项目脚本风格 |
| G-02 | 全量 archive 参与统计；月报正文只展示代表新闻 |
| G-03 | 输出 4 件套：`月报.md` + `月报.html` + `月报.png` + `统计.json`，按 `archive/monthly/YYYY-MM/` 存放 |
| G-04 | 允许 LLM 生成总述/趋势文案，但必须 grounded 于 archive 真实数据；保留来源链接；LLM 失败降级模板 |
| G-05 | 幂等：相同 month 重跑覆盖输出，不污染 archive |
| G-06 | 不修改 step1_3/4/6/7/8/run_all.sh，不改变日报产物 |
| G-07 | 兼容 archive schema v2；缺 body/缺 image 也能跑 |

## 3. 非目标

- 不写月报到 archive JSONL（archive 仍是只读数据源）
- 不做月报 UI / 搜索 / 编辑功能
- 不做跨月对比 / 年报 / 多月趋势
- 不引入 SQLite / DuckDB / Pandas 等新依赖
- 不修改 archive schema
- 不并发抓取/不发起网络请求（仅 LLM 调用）
- 不改 Phase 13 栏目顺序、不改 Phase 14A/14B 现有字段语义
- 不引入 type hints；不使用 argparse；中文输出风格保持

## 4. 拆分判断

不拆分，不走批量模式。

理由：
- 单一交付物（月报），无多角色/多页面/多工作流
- 输入是若干篇文章但实现是通用统计 + 模板 + LLM grounding，不逐篇开发
- plan 任务可控制在 10 个以内

## 5. 总体方案

### 5.1 选定方案：方案 A — 单体 `monthly_report.py`

按"脚本是模块"约定，单文件 + 内部分层函数。

```
monthly_report.py
  parse_args()
  ── loader      load_month_jsonl, normalize_record
  ── stats       compute_stats（栏目/来源/日历/日趋势/keywords）
  ── select      pick_top_per_column
  ── llm         llm_monthly_overview / fallback_overview
  ── render      render_markdown / render_html / render_png
  main()
```

### 5.2 入口与参数

```
python3 monthly_report.py [--month YYYY-MM] [--dry-run] [--no-llm] [--top-per-column N] [--max-llm-seconds S]
```

| 参数 | 默认 | 说明 |
|------|------|------|
| `--month` | 今天所在月 | 处理月份 |
| `--dry-run` | 关 | 只打印统计与输出路径，不写 md/html/png/json |
| `--no-llm` | 关 | 跳过 LLM 文案，直接用 fallback 模板 |
| `--top-per-column` | 3 | 每栏目展示代表新闻数 |
| `--max-llm-seconds` | 30 | LLM 总预算，超时降级 fallback |

### 5.3 数据源与流程

```
archive/articles/YYYY-MM.jsonl  (14A schema v2 + 14B body/image)
        │
        ▼
  load_month_jsonl()          # 只读，返回 [record...]
        │
        ▼
  compute_stats()             # 聚合统计
        │
   ┌────┴─────┐
   ▼          ▼
 pick_top_per_column   llm_monthly_overview / fallback_overview
   │          │
   ▼          ▼
 render_markdown / render_html / render_png
        │
        ▼
 archive/monthly/YYYY-MM/{月报.md, 月报.html, 月报.png, 统计.json}
```

### 5.4 输出文件命名

```
/mnt/e/每日新中国/archive/monthly/
└── 2026-06/
    ├── 2026-06_月报.md
    ├── 2026-06_月报.html
    ├── 2026-06_月报.png
    └── 2026-06_统计.json
```

### 5.5 LLM Grounding（防幻觉契约）

LLM 仅用于生成月度"总述"段落（200~400 字）和"趋势解读"段落（150~300 字）。

Prompt 携带 grounding context：
- 月度统计（栏目分布、来源分布、日历范围、归档总数）
- 候选代表新闻列表（仅 selected_in_top10 且 body_status=extracted 的 article_id + title + body 截断到 300 字）

Prompt 约束（写入 system 与 user 双重提醒）：
- 输出必须基于上方提供的标题/正文/统计；不在上方出现的事实禁用
- 引用具体文章时必须用 `[article_id]` 形式标注
- 不允许编造数字、机构、地点、时间
- 输出仅中文，2 段，控制总字数 ≤ 700

后处理（render 前）：
- 移除所有不在 archive 内的 article_id 引用
- 检测明显的"未知字段"（如外语段落 / 占位符 `<...>` / "假设" / "可能" 比例 ≥ 30%）→ 抛弃 LLM 文案，使用 `fallback_overview`
- LLM 调用整体被 `try/except + 超时` 包裹

### 5.6 代表新闻选择

每栏目挑选 `--top-per-column` 篇（默认 3）：

排序键（高到低）：
1. `selected_in_top10`（True 优先）
2. `aggregate_score`（高优先）
3. `body_status == "extracted"`（已提取正文优先）
4. 归档时间倒序

字段：title、url、source、date、aggregate_score、body 前 200 字、image_path（若有）

### 5.7 统计内容

`compute_stats` 返回 dict：

```python
{
  "month": "2026-06",
  "total_records": 432,
  "by_column": {"🤖 AI智能前沿": 112, "🔬 世界性科研突破": 87, ...},
  "by_source": {"新华社": 165, "人民日报": 91, ...},
  "by_date": {"2026-06-01": 14, "2026-06-02": 18, ...},
  "body_coverage": {"extracted": 387, "failed": 23, "missing": 22},
  "image_coverage": {"downloaded": 78, "not_selected": 320, "failed": 18, "not_found": 16},
  "top_keywords": [("人工智能", 34), ("光刻", 12), ...],
}
```

`top_keywords` 用简单中文分词（按 jieba 不引入，改用基于已有 `CATEGORY_KEYWORDS` 词库统计命中次数）；不引入 jieba，避免新增依赖。

### 5.8 渲染层

- Markdown：人类可读 + 可直接发到群组；含统计表 + 总述/趋势 + 每栏目代表新闻
- HTML：复用日报报纸样式但模板独立，月报含统计图（ASCII 柱状 or 简易 CSS 柱状）+ 代表新闻卡片（含首图）
- PNG：调用 chromium 截图 + Pillow 裁边（复用 step8 思路；具体函数内联，不 import step8 以避免耦合）

## 6. 文件变更清单

| 操作 | 文件路径 | 说明 |
|------|----------|------|
| 新增 | `monthly_report.py` | Phase 14C 月报生成器 CLI + helper |
| 新增 | `tests/test_monthly_report.py` | 单元测试：loader/stats/select/render/grounding（mock LLM） |
| 修改 | `.sillyspec/docs/Daily/modules/_module-map.yaml` | 新增 `monthly` 模块（archive monthly 报表） |
| 新增 | `.sillyspec/docs/Daily/modules/monthly.md` | 模块卡片 |
| 不变 | `step1_3.py` / `step4.py` / `step6.py` / `step7.py` / `step8.py` / `run_all.sh` | 不修改 |
| 不变 | `news_archive.py` / `archive_enrich.py` | 不修改 |

## 7. 接口定义

不写 type hints；遵循项目脚本风格。

```python
# ===== loader =====
def load_month_jsonl(month):
    """读取 archive/articles/{month}.jsonl → list[dict]；缺失返回 None 并打印错误。"""

def normalize_record(rec):
    """补齐缺失字段默认值（body_status='missing' 等），不修改 archive。"""

# ===== stats =====
def compute_stats(records, month):
    """聚合统计，返回 dict（见 5.7）。"""

def top_keywords(records, limit):
    """基于 step4 CATEGORY_KEYWORDS 词库做简单关键词命中统计；不依赖 jieba。"""

# ===== select =====
def pick_top_per_column(records, top_n):
    """按栏目分组挑选代表新闻 → dict[column] = list[record]，按排序键。"""

# ===== llm =====
def build_grounding_context(stats, picks):
    """生成 LLM prompt 的 grounding 段（system + user）。"""

def llm_monthly_overview(context, max_seconds):
    """调用 ZHIPU glm-4-flash 生成总述+趋势两段；失败/超时返回 None。"""

def sanitize_llm_text(text, valid_ids):
    """移除未授权 article_id 引用 + 可疑外语/占位符；返回安全文本或 None。"""

def fallback_overview(stats, picks):
    """规则模板生成总述/趋势，无 LLM 时使用。"""

# ===== render =====
def render_markdown(month, stats, picks, overview):
    """返回完整 Markdown 字符串。"""

def render_html(month, stats, picks, overview):
    """返回完整 HTML 字符串（独立模板，单页式报纸样式）。"""

def render_png(html_path, png_path):
    """chromium --headless --screenshot + Pillow trim，复用 step8 思路。"""

# ===== main =====
def parse_args():
    """手写解析 --month / --dry-run / --no-llm / --top-per-column / --max-llm-seconds。"""

def main():
    """编排所有步骤；任意致命错误 sys.exit(1)；LLM/统计/渲染失败不互相阻断。"""
```

### 配置常量

```python
ARCHIVE_DIR = Path("/mnt/e/每日新中国/archive")
ARTICLES_DIR = ARCHIVE_DIR / "articles"
IMAGES_DIR = ARCHIVE_DIR / "images"
MONTHLY_DIR = ARCHIVE_DIR / "monthly"

DEFAULT_TOP_PER_COLUMN = 3
DEFAULT_MAX_LLM_SECONDS = 30
LLM_MODEL = "glm-4-flash"
LLM_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"

OVERVIEW_MAX_CHARS = 700
BODY_SNIPPET_CHARS = 300
```

不重新定义 `COLUMN_ORDER`：从 `step8` 或 `step7` 复用；为避免脚本互相 import，月报内自带一份与 step8 同步的常量并在卡片里注明"修改 COLUMN_ORDER 需同步 3 处"。

## 8. 数据模型

无新表/无 schema 变更。仅消费 archive schema v2，不修改字段语义。

新输出：

`archive/monthly/YYYY-MM/YYYY-MM_统计.json` 内容即 `compute_stats` 结果，schema 一致。

## 9. 兼容策略（brownfield）

- 未运行 monthly_report 时：archive、日报、run_all 完全不受影响
- archive JSONL 缺失：打印错误 + `sys.exit(1)`
- body_status≠extracted：仍可生成月报，统计部分会标注空正文比例，代表新闻按 5.6 排序键自然降权
- image_path 缺失：HTML/PNG 用占位符渲染，不影响其他栏目
- LLM 失败/超时：降级为 `fallback_overview`，并在月报中标注"本期总述使用规则模板"
- chromium 缺失：PNG 渲染失败，但 md/html/json 仍生成；返回 exit code 2 提示

## 10. 风险登记

| 编号 | 风险 | 等级 | 应对策略 |
|------|------|------|----------|
| R-01 | LLM 仍可能在 grounding 之外编造细节 | P0 | sanitize_llm_text 三层过滤 + grounding context + fallback ；通过测试 grounding harness 覆盖 |
| R-02 | 月度 JSONL 大（>10k 条） | P1 | loader 流式读取（已是 line-by-line）；compute_stats 一次遍历完成 |
| R-03 | chromium 截图失败/慢 | P1 | 60s 超时；超时不阻断 md/html 输出 |
| R-04 | 关键词频率统计无 jieba 易偏 | P2 | 用 CATEGORY_KEYWORDS 词库命中即足够（不追求完整 NLP） |
| R-05 | LLM API key 未配置 | P1 | 检测缺失自动走 fallback，不报错退出 |
| R-06 | top_per_column 设过大时月报很长 | P2 | 命令行 N 上限校验 ≤10 |
| R-07 | 时间预算与日报 cron 冲突 | P2 | monthly_report 不进入 run_all.sh，需手动触发或独立 cron |

## 11. 决策追踪

| ID | 状态 | 覆盖 FR / 章节 |
|---|---|---|
| D-001@v1 | accepted | 输出物 B+C（md+html+png+json） — §5.4, §7 render |
| D-002@v1 | accepted | 数据范围 B（全量统计 + 代表新闻正文） — §5.6, §5.7 |
| D-003@v1 | accepted | LLM A（允许 LLM，但 grounded + 引用 article_id + fallback） — §5.5, R-01 |
| D-004@v1 | accepted | 方案 A（单体 monthly_report.py） — §5.1 |
| D-005@v1 | accepted | 不修改 archive schema 与日报流水线 — §3, §6 |
| D-006@v1 | accepted | 不引入 jieba/Pandas/SQLite — §3, R-04 |

无剩余 P0 未决议项。

## 12. 自审

| 维度 | 检查项 | 结论 |
|------|------|------|
| 边界 | 输入(archive)/输出(monthly/)/不变(日报)是否明确 | ✅ §1~§6 |
| YAGNI | 是否包含不必要功能 | ✅ 单 CLI + 4 个输出，无额外依赖 |
| 验收标准 | 是否具体可测试 | ✅ §10 风险均可测；§7 接口可单测 |
| 非目标清晰 | 是否明确界定不做 | ✅ §3 列举 8 项 |
| 兼容策略 | 是否说明回退路径 | ✅ §9 全部失败分支处理 |
| 风险识别 | 是否识别关键技术风险 | ✅ §10 七项 P0/P1/P2 |
| 生命周期契约表 | 是否涉及 session/lease/agent_run/daemon | ❌ 不涉及 — 本变更纯离线脚本，无 lifecycle 关键词，故省略此表 |
| 决策追踪 | D-xxx@vN 当前版本是否清晰 | ✅ §11，D-001@v1~D-006@v1 均 accepted |
