---
author: lmr
created_at: 2026-07-01 18:38:54
schema_version: 1
doc_type: requirements
change_id: 2026-07-01-phase-15a-common-lib
phase: 15a
---

# Requirements · Phase 15A common lib

## 角色

| 角色 | 说明 |
|---|---|
| 开发者 | 维护 Daily 爬虫系统，执行后续 Phase 15B–15G change |
| 运行者 | 通过 `./run_all.sh` 或 `python3 stepN.py` 跑每日流水线 |
| 测试者 | 运行 pytest 与 manual smoke diff 验证 refactor 零行为变化 |

## 功能需求

### FR-01: 新增 daily 公共包

覆盖决策：D-001@v1

Given 项目根目录存在多个 step 脚本  
When Phase 15A 执行完成  
Then 项目根目录存在 `daily/__init__.py`、`daily/common.py`、`daily/http.py` 三个文件  
And 现有 step 脚本继续位于项目根目录，不迁入包内

### FR-02: 输出根目录支持 DAILY_OUTPUT_DIR

覆盖决策：D-003@v1

Given 未设置 `DAILY_OUTPUT_DIR`  
When 导入 `daily.common.BASE_DIR`  
Then `BASE_DIR` 等于 `/mnt/e/每日新中国`

Given 设置 `DAILY_OUTPUT_DIR=/tmp/daily-output`  
When 在新进程中导入 `daily.common.BASE_DIR`  
Then `BASE_DIR` 等于 `/tmp/daily-output`

### FR-03: 栏目与时区常量唯一定义

覆盖决策：D-001@v1

Given 根目录 Python 文件中曾存在多个 `COLUMN_ORDER` 定义  
When Phase 15A 执行完成  
Then `COLUMN_ORDER` 只在 `daily/common.py` 定义  
And `step4.py`、`step7.py`、`step8.py`、`monthly_report.py` 从 `daily.common` 导入  
And `monthly_report.COLUMN_ORDER` 仍可被测试 import

Given `CST` 曾在多个归档/月报文件重复定义  
When Phase 15A 执行完成  
Then `CST` 只在 `daily/common.py` 定义  
And `news_archive.py`、`archive_enrich.py`、`monthly_report.py` 复用该常量

### FR-04: 通用参数解析保持旧行为

覆盖决策：D-002@v1, D-005@v1

Given 用户运行 `python3 step4.py --date 2026-06-30 --dry-run`  
When `step4.py` 调用 `parse_common_args()`  
Then 返回日期 `2026-06-30` 与 `dry_run=True`

Given 用户运行 `python3 step4.py --date bad`  
When `parse_common_args()` 解析日期  
Then 打印中文错误并退出 code=1

Given `archive_enrich.py` 与 `monthly_report.py` 有特殊参数  
When Phase 15A 执行完成  
Then 两个文件保留本地 `parse_args()` 处理特殊参数  
And 不把 `--missing-only`、`--max-seconds`、`--month`、`--no-llm` 等参数塞进 `parse_common_args()`

### FR-05: HTTP/Chromium helper 集中到 daily.http

覆盖决策：D-001@v1

Given `step1_3.py` 和 `step6.py` 曾重复定义 `chromium_dom` 和 `fetch_html_static`  
When Phase 15A 执行完成  
Then 真实实现只在 `daily/http.py`  
And `step1_3.py` 调用 `fetch_html_static(url, timeout=15)` 保持旧默认  
And `step6.py` 通过 top-level import re-export `fetch_html_static`、`chromium_dom`、`ssl_ctx`、`_preprocess_html`

### FR-06: 信源识别合并且保持兼容

覆盖决策：D-004@v1

Given 外部测试调用 `news_archive.infer_source("https://news.cn/x", {})`  
When Phase 15A 执行完成  
Then 返回 `新华社`

Given 分类器需要输出 `src`  
When `step4.py` 写 `1新闻_链接.md`  
Then 使用 `daily.common.detect_source(url)` 得到与旧 `step4.detect_source` 相同结果

### FR-07: 运行步骤与主流程不变

覆盖决策：D-001@v1, D-002@v1, D-003@v1

Given 用户使用旧命令 `./run_all.sh --date 2026-06-30 --dry-run`  
When Phase 15A 执行完成后运行该命令  
Then 命令仍按 `step1_3.py → step4.py → step6.py → step7.py → step8.py` 顺序执行  
And 输出文件命名与路径结构不变

## 非功能需求

- **兼容性**：未设置 `DAILY_OUTPUT_DIR` 时行为不变
- **可回退**：若出现问题，可 revert 本 change；无数据 schema 迁移，无 archive 变更
- **可测试**：pytest 全绿；manual smoke diff 可对比 refactor 前后 dry-run 输出
- **可维护性**：跨模块共享常量与 HTTP helper 只有一个定义点
- **无新增依赖**：本 change 不引入 trafilatura/httpx/loguru 等依赖

## 决策覆盖矩阵

| 决策 ID | 覆盖的 FR | 说明 |
|---|---|---|
| D-001@v1 | FR-01, FR-03, FR-05, FR-07 | daily/ 包结构与 import 迁移 |
| D-002@v1 | FR-04, FR-07 | 手写 sys.argv，保持现有 CLI 行为 |
| D-003@v1 | FR-02, FR-07 | DAILY_OUTPUT_DIR env 化但默认兼容 |
| D-004@v1 | FR-06 | detect_source 为唯一实现，infer_source shim 兼容 |
| D-005@v1 | FR-04 | archive_enrich/monthly_report 特殊参数保留本地 |
