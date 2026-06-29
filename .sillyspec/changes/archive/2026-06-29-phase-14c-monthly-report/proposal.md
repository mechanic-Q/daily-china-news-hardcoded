---
author: lmr
created_at: 2026-06-29 21:05:00
schema_version: 1
doc_type: proposal
change_id: phase-14c-monthly-report
phase: 14C
---

# Phase 14C 自动月报 — 提案

## 1. 问题

Phase 14A/14B 已建立完整的归档体系：按月 JSONL 分片 + schema v2（含正文/首图）。但归档目前只是"原料库"，没有可发布的月度产物，无法直接对外分享或长期总结。

需要一个工具：在月末（或任意时间）基于 archive 数据，生成可发布的月度报告，含趋势统计和代表新闻精选，与日报形式对齐（Markdown + HTML + PNG）。

## 2. 价值

- 把归档数据沉淀为产品级月报，让长期数据"用起来"，不只是堆在硬盘里
- 月度趋势让运营/读者直观看到本月聚焦方向（哪些栏目、哪些信源活跃）
- 代表新闻精选给读者回顾本月最重要信号

## 3. 方案概述

新增 `monthly_report.py` 单文件 CLI，读 `archive/articles/YYYY-MM.jsonl`，输出到 `archive/monthly/YYYY-MM/`：

- `YYYY-MM_月报.md` — Markdown 月报（可阅读、可发布）
- `YYYY-MM_月报.html` — 报纸版式 HTML
- `YYYY-MM_月报.png` — chromium 截图 + Pillow 裁边
- `YYYY-MM_统计.json` — 机器可读的全量统计

LLM 用于生成总述/趋势段落，但必须 grounded 于 archive 真实标题/正文/统计；失败降级模板。

## 4. 范围

### 在范围内

- 输入：`archive/articles/YYYY-MM.jsonl`（schema v2）+ `archive/images/YYYY-MM/`
- 输出：`archive/monthly/YYYY-MM/` 四件套
- 全量 archive 参与统计；月报正文只展示每栏目 Top N 代表新闻
- LLM 总述 + 反幻觉约束 + 失败降级
- CLI 参数：`--month` `--dry-run` `--no-llm` `--top-per-column` `--max-llm-seconds`
- 单元测试覆盖 loader/stats/select/render/llm sanitize

### 不在范围内

- 不写月报到 archive JSONL（archive 只读）
- 不做月报 UI / 搜索 / 编辑功能
- 不做跨月对比 / 年报 / 多月趋势
- 不引入 SQLite / DuckDB / Pandas / jieba 等新依赖
- 不修改 archive schema、不改 step1_3/4/6/7/8/run_all.sh
- 不进 run_all.sh，按需手动触发（避免阻塞日报）

## 5. 影响

- 新增 1 个 Python 脚本 + 1 个测试文件
- 模块图新增 `monthly` 模块
- archive 目录新增子目录 `monthly/`（被 git 排除，仅运行时产物）
- 日报流水线零修改，零回归风险

## 6. 决策概要

D-001 输出 B+C；D-002 统计 B（全量）；D-003 LLM A（grounded+fallback）；D-004 方案 A（单体）；D-005 不改既有流水线；D-006 不引入新依赖。详见 `decisions.md`。
