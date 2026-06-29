---
author: lmr
created_at: 2026-06-29 21:05:00
schema_version: 1
doc_type: requirements
change_id: phase-14c-monthly-report
phase: 14C
---

# Phase 14C 需求 — 自动月报

## 角色

| 角色 | 描述 |
|------|------|
| 运营/读者 | 浏览月报 .md / .html / .png，获取月度趋势与代表新闻 |
| 自动化触发器 | 月初手动或 cron 触发 `monthly_report.py --month YYYY-MM` |
| 后续 14D+ 消费者 | 读 `archive/monthly/YYYY-MM/统计.json` 做跨月对比/年报（不在本期实现） |

## 决策追踪

| 决策 ID | 当前版本 | 摘要 |
|---|---|---|
| D-001@v1 | v1 | 输出 4 件套（md+html+png+json） |
| D-002@v1 | v1 | 全量 archive 做统计，月报正文展示代表新闻 |
| D-003@v1 | v1 | LLM 文案允许，但必须 grounded + 反幻觉 + fallback |
| D-004@v1 | v1 | 单体 monthly_report.py 方案 A |
| D-005@v1 | v1 | 不改既有流水线与 archive schema |
| D-006@v1 | v1 | 不引入新依赖（jieba/pandas/sqlite/duckdb） |

无 unresolved P0/P1 blocker。

## 功能需求

### FR-01：月份选择
**Given** 用户运行 `monthly_report.py`
**When** 提供 `--month YYYY-MM` 或不提供
**Then** 使用指定月或当前所在月作为处理月份
**And** 日期格式不合法时 `sys.exit(1)` 并打印错误（D-005@v1：脚本风格一致）

### FR-02：读取 archive
**Given** `archive/articles/YYYY-MM.jsonl` 存在
**When** loader 读取
**Then** 逐行 JSON 解析得到 records 列表；schema v2 字段缺失时使用默认值
**And** 文件缺失时 `sys.exit(1)` 并打印错误（D-002@v1）

### FR-03：全量统计
**Given** records 列表
**When** `compute_stats` 执行
**Then** 输出 dict 含 month / total_records / by_column / by_source / by_date / body_coverage / image_coverage / top_keywords（D-002@v1, D-006@v1）

### FR-04：代表新闻选择
**Given** records 列表 + `--top-per-column N`（默认 3，上限 10）
**When** `pick_top_per_column` 执行
**Then** 每栏目挑选 N 条按"selected_in_top10 → aggregate_score → body_status=extracted → 归档时间倒序"排序（D-002@v1）

### FR-05：LLM 总述与反幻觉
**Given** stats + picks
**When** 调用 `llm_monthly_overview` 且未指定 `--no-llm`
**Then** 调用 ZHIPU glm-4-flash，prompt 携带 grounding context（统计+候选文章 title/body 截断 300 字），输出 ≤700 字（D-003@v1）
**And** 输出后经 `sanitize_llm_text` 移除未授权 article_id、可疑外语片段
**And** sanitize 失败或 API 异常或超过 `--max-llm-seconds`（默认 30s）时降级 `fallback_overview`（模板生成）
**And** API key 缺失时直接 fallback，不报错退出（R-05）

### FR-06：渲染输出
**Given** stats + picks + overview 文本
**When** render 执行
**Then** 写入 `archive/monthly/YYYY-MM/YYYY-MM_月报.md` + `YYYY-MM_月报.html` + `YYYY-MM_统计.json`
**And** 调用 chromium 截图生成 `YYYY-MM_月报.png`；截图失败仍生成其他三件套并 exit code 2 提示（D-001@v1, R-03）
**And** 每条代表新闻必须附 url、source、归档日期；有 image_path 时嵌入图片，缺失用占位符（R-01）

### FR-07：dry-run
**Given** `--dry-run` 标志
**When** 主流程执行
**Then** 只打印统计与目标路径，不写任何文件，不调用 LLM，不调用 chromium

### FR-08：兼容退化
**Given** archive records 中 body_status≠extracted 或 image 缺失
**When** 月报生成
**Then** 仍能完成全部输出；统计中体现空正文/缺图比例；代表新闻按排序键自然降权（D-005@v1）

### FR-09：测试覆盖
**Given** `tests/test_monthly_report.py`
**When** `python3 tests/test_monthly_report.py` 执行
**Then** 单元测试覆盖 loader / normalize / compute_stats / top_keywords / pick_top_per_column / sanitize_llm_text / fallback_overview / render_markdown 快照断言 / parse_args；LLM 用 mock，不发起网络请求

### FR-10：不污染日报
**Given** monthly_report.py 运行
**When** 任何错误发生
**Then** archive/articles/、archive/images/、日报输出、run_all.sh 行为完全不变（D-005@v1）

## 关键场景

### 场景 A — 默认月报
`python3 monthly_report.py` → 处理本月 → 写四件套 → exit 0

### 场景 B — 指定月报 + 无 LLM
`python3 monthly_report.py --month 2026-06 --no-llm` → 走 fallback overview → 四件套生成

### 场景 C — dry-run 预览
`python3 monthly_report.py --month 2026-06 --dry-run` → 只打印统计与目标路径，不写文件

### 场景 D — LLM 超时降级
prompt 30s 内未返回 → 主动取消 → fallback_overview → 月报中标注"本期使用规则模板"

### 场景 E — chromium 缺失
chromium 不可用 → md/html/json 仍生成 → png 缺失 → exit code 2 提示
