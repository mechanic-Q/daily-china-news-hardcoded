---
author: lmr
created_at: 2026-07-01 18:07:32
schema_version: 1
doc_type: decisions
change_id: 2026-07-01-phase-15a-common-lib
phase: 15a
---

# Decisions · Phase 15A · common lib

## D-001@v1: 包结构使用 daily/ 目录（含 __init__.py）

- type: architecture
- status: accepted
- source: user
- priority: P0
- question: 抽出的公共模块是 `daily/` 包（含 `__init__.py`）还是平面文件 `common.py` + `http_utils.py`？
- answer: 用户在 Step 6 对话式探索选择「daily/ 包（推荐）」
- normalized_requirement: 项目根新增 `daily/` 目录，含 `__init__.py`、`common.py`、`http.py` 三文件；下游 15B–15G 可继续在 `daily/` 下扩子模块（`daily.classify` / `daily.render` 等）
- impacts: [FR-01, §6 文件变更清单, §7 接口定义]
- evidence: brainstorm Step 6 用户回答；覆盖 CONVENTIONS.md §STRUCTURE「无包结构」旧约定，用户明确同意打破

## D-002@v1: parse_common_args 保持手写 sys.argv 解析

- type: compatibility
- status: accepted
- source: user
- priority: P0
- question: `parse_common_args` 的 argv 解析用手写 sys.argv 还是 argparse？
- answer: 用户在 Step 6 选择「保持手写 sys.argv 解析（推荐）」
- normalized_requirement: `daily/common.py` 中 `parse_common_args()` 使用与旧 5 个 step 逐字节等价的手写 sys.argv 解析；不引入 argparse
- impacts: [NG-03, §7.1 parse_common_args 实现]
- evidence: brainstorm Step 6 用户回答；CONVENTIONS.md §1「不使用 argparse」

## D-003@v1: BASE_DIR 走 DAILY_OUTPUT_DIR 环境变量并保留 WSL 默认值

- type: compatibility
- status: accepted
- source: user
- priority: P0
- question: BASE_DIR 是必须环境变量 / 保留 WSL 默认值 / 迁移到 ~/DailyOutput 中的哪一个？
- answer: 用户在 Step 6 选择「os.environ.get + 默认 /mnt/e/每日新中国（推荐）」
- normalized_requirement: `BASE_DIR = Path(os.environ.get("DAILY_OUTPUT_DIR", "/mnt/e/每日新中国"))`；`.env.example` 追加说明；已有 `.env` 用户文件不修改
- impacts: [G-02, C-01, §7.1 BASE_DIR 定义]
- evidence: brainstorm Step 6 用户回答；plan mode 已答 Q2

## D-004@v1: infer_source 保留为薄 shim，逻辑合并到 detect_source

- type: compatibility
- status: accepted
- source: code
- priority: P1
- question: `news_archive.infer_source(url, article)` 与 `step4.detect_source(url)` 逻辑字面一致，如何合并？
- answer: 合并到 `daily.common.detect_source(url)`；`news_archive.py` 中保留 `def infer_source(url, article): return detect_source(url)` 薄 shim，以防外部/测试代码引用
- normalized_requirement: `daily.common.detect_source` 为唯一实现；`news_archive.infer_source` 存在但只转发；step4 中移除本地 `detect_source`
- impacts: [§6 文件变更清单 news_archive.py 行, §7.3 迁移对照, R-03, R-06]
- evidence: `rg -n 'def infer_source' news_archive.py`、`rg -n 'def detect_source' step4.py` 显示两处逻辑字面等价

## D-005@v1: 特殊参数保留本地 parse_args

- type: boundary
- status: accepted
- source: code
- priority: P1
- question: `archive_enrich.parse_args` 有 `--missing-only/--max-seconds`，`monthly_report.parse_args` 有 `--month/--no-llm/--top-per-column/--max-llm-seconds`，是否要通用化？
- answer: 只把「`--date` + `--dry-run` 组合」提取为 `parse_common_args`；两处特殊 arg 保留本地 `parse_args`，不迁移
- normalized_requirement: `parse_common_args()` 只处理 `--date` + `--dry-run`；`archive_enrich.py` 和 `monthly_report.py` 的 `parse_args` 保留（内部改成先调用 `parse_common_args()` 拿 date+dry，再补自己特殊 arg 的解析）
- impacts: [§7.1 parse_common_args 签名, R-01]
- evidence: `rg -n 'def parse_args' archive_enrich.py monthly_report.py step*.py`
