---
author: lmr
created_at: 2026-07-01 19:05:03
schema_version: 1
doc_type: plan
change_id: 2026-07-01-phase-15a-common-lib
phase: 15a
plan_level: full
---

# 实现计划

## 调用点搜索

命令：

`/usr/bin/rg -n 'COLUMN_ORDER|WEEKDAYS|CST|BASE_DIR|parse_args|detect_source|infer_source|fetch_html_static|chromium_dom|ssl_ctx|SSL_CTX|_preprocess_html' -g '*.py' .`

输出摘要：129 matches in 14 files。

| 分类 | 文件 | 处理 |
|---|---|---|
| 计划内源文件 | `step1_3.py`, `step4.py`, `step6.py`, `step7.py`, `step8.py`, `news_archive.py`, `archive_enrich.py`, `monthly_report.py` | 纳入 task-02 至 task-06 |
| 计划内新增文件 | `daily/__init__.py`, `daily/common.py`, `daily/http.py`, `.env.example`, `tests/manual/__init__.py`, `tests/manual/test_15a_diff_smoke.py` | 纳入 task-01, task-07, task-08 |
| 验收关联测试 | `tests/test_archive_enrich.py`, `tests/test_news_archive.py`, `tests/test_monthly_report.py` | 纳入 task-09 验证，不主动改测试 |
| 搜索补漏 | `perf_profile.py` | 纳入 task-07，避免硬编码输出根目录验收失败 |
| 范围外遗留 | `archive_news.py` | 仅命中本地 `parse_args`，无重复常量/HTTP helper；本 change 不改 |

## Wave 1（基础包，无依赖）

- [x] task-01: 新建 `daily/` 公共包并迁入共享常量、路径、日期、信源识别、HTTP/Chromium helper（覆盖：FR-01, FR-02, FR-03, FR-05, FR-06, D-001@v1, D-002@v1, D-003@v1, D-004@v1）

## Wave 2（依赖 Wave 1，可并行）

- [x] task-02: 迁移 collector 到公共包并保持采集入口行为不变（覆盖：FR-02, FR-04, FR-05, FR-07, D-002@v1, D-003@v1）
- [x] task-03: 迁移 classifier 到公共包并保持栏目排序、信源识别、归档调用行为不变（覆盖：FR-03, FR-04, FR-06, FR-07, D-002@v1, D-004@v1）
- [x] task-04: 迁移 extractor 到公共包并保留现有跨模块 re-export 兼容层（覆盖：FR-02, FR-04, FR-05, FR-07, D-001@v1, D-002@v1）
- [x] task-05: 迁移 summarizer 与 renderer 到公共包并保持日报输出结构不变（覆盖：FR-03, FR-04, FR-07, D-001@v1, D-002@v1）
- [x] task-07: 更新环境示例与搜索补漏文件，明确 `DAILY_OUTPUT_DIR` 输出根目录配置（覆盖：FR-02, D-003@v1）

## Wave 3（依赖 task-04）

- [x] task-06: 迁移 archive/news/monthly 兼容层并保留特殊参数解析边界（覆盖：FR-02, FR-03, FR-06, D-003@v1, D-004@v1, D-005@v1）

## Wave 4（依赖 task-02 至 task-06）

- [x] task-08: 新增手动 diff smoke 脚本，支持 refactor 前后 dry-run 关键输出对比（覆盖：FR-07）

## Wave 5（依赖 task-02 至 task-08）

- [x] task-09: 执行 import、重复定义、兼容层、pytest、dry-run 回归验证（覆盖：FR-01, FR-02, FR-03, FR-04, FR-05, FR-06, FR-07, D-001@v1, D-002@v1, D-003@v1, D-004@v1, D-005@v1）

## 任务总表

| 编号 | 任务 | Wave | 优先级 | 依赖 | 覆盖 FR/D | 说明 |
|---|---|---|---|---|---|---|
| task-01 | 新建 `daily/` 公共包 | W1 | P0 | — | FR-01, FR-02, FR-03, FR-05, FR-06, D-001@v1, D-002@v1, D-003@v1, D-004@v1 | 建立后续迁移的唯一公共入口 |
| task-02 | 迁移 collector | W2 | P0 | task-01 | FR-02, FR-04, FR-05, FR-07, D-002@v1, D-003@v1 | 保持 `step1_3.py` 单步与 `run_all.sh` 行为 |
| task-03 | 迁移 classifier | W2 | P0 | task-01 | FR-03, FR-04, FR-06, FR-07, D-002@v1, D-004@v1 | 保持精选、分类、归档入口兼容 |
| task-04 | 迁移 extractor | W2 | P0 | task-01 | FR-02, FR-04, FR-05, FR-07, D-001@v1, D-002@v1 | 保持 `step6` 对 archive 兼容的导出名 |
| task-05 | 迁移 summarizer 与 renderer | W2 | P0 | task-01 | FR-03, FR-04, FR-07, D-001@v1, D-002@v1 | 保持摘要排序与 HTML/PNG 产物结构 |
| task-06 | 迁移 archive/news/monthly 兼容层 | W3 | P0 | task-01, task-04 | FR-02, FR-03, FR-06, D-003@v1, D-004@v1, D-005@v1 | 保持归档、月报与特殊 CLI 参数兼容 |
| task-07 | 更新环境示例与补漏文件 | W2 | P1 | task-01 | FR-02, D-003@v1 | 覆盖 `.env.example` 与调用点搜索发现的输出根目录硬编码 |
| task-08 | 新增手动 diff smoke 脚本 | W4 | P1 | task-02, task-03, task-04, task-05, task-06 | FR-07 | 为 execute/verify 提供人工对比入口 |
| task-09 | 全局验证 | W5 | P0 | task-02, task-03, task-04, task-05, task-06, task-07, task-08 | 全部 FR/D | 对照 design.md 验收标准完成回归 |

## 关键路径

task-01 → task-04 → task-06 → task-08 → task-09。

说明：Wave 2 大部分可并行，但 archive/monthly 兼容层依赖 extractor re-export 稳定后再验收。

## 全局验收标准

- `daily.common` 与 `daily.http` 可直接 import
- 未设置 `DAILY_OUTPUT_DIR` 时输出根目录仍为 `/mnt/e/每日新中国`
- 设置 `DAILY_OUTPUT_DIR` 时新进程导入的输出根目录等于环境变量值
- 根目录 Python 文件不再保留重复的 `COLUMN_ORDER`、`chromium_dom`、禁用证书校验 helper 定义
- `news_archive.infer_source(url, {})`、`monthly_report.COLUMN_ORDER`、`step6.fetch_html_static` 兼容导入仍可用
- `python3 -m pytest tests/` 通过；若本地依赖缺失，记录阻塞原因
- `./run_all.sh --date 2026-06-30 --dry-run` 关键输出与重构前一致
- local.yaml 中 build/test/lint 未配置命令，不新增伪命令；验证优先执行 design.md 指定回归命令
- brownfield 兼容：未配置 `DAILY_OUTPUT_DIR`、未改 `run_all.sh`、未改输出文件命名与路径结构时，用户可按旧命令继续运行

## 覆盖矩阵

| ID | 覆盖任务 | 验收证据 |
|---|---|---|
| FR-01 | task-01, task-09 | daily 包 import smoke |
| FR-02 | task-01, task-02, task-04, task-06, task-07, task-09 | 默认路径与 `DAILY_OUTPUT_DIR` 断言 |
| FR-03 | task-01, task-03, task-05, task-06, task-09 | 重复常量 rg 检查与 import 兼容检查 |
| FR-04 | task-02, task-03, task-04, task-05, task-06, task-09 | CLI 参数兼容与 pytest |
| FR-05 | task-01, task-02, task-04, task-09 | HTTP/Chromium helper 唯一定义检查 |
| FR-06 | task-01, task-03, task-06, task-09 | `infer_source` shim 与 `detect_source` 行为检查 |
| FR-07 | task-02, task-03, task-04, task-05, task-08, task-09 | `run_all.sh --dry-run` 与 manual diff smoke |
| D-001@v1 | task-01, task-04, task-05, task-09 | `daily/` 包存在与 re-export 兼容 |
| D-002@v1 | task-01, task-02, task-03, task-04, task-05, task-09 | 手写 CLI 解析行为检查 |
| D-003@v1 | task-01, task-02, task-06, task-07, task-09 | 默认路径与 env 覆盖检查 |
| D-004@v1 | task-01, task-03, task-06, task-09 | 信源识别兼容检查 |
| D-005@v1 | task-06, task-09 | archive/monthly 特殊参数测试 |

## 自检结果

- 通过：每个 task 有编号（task-01、task-02 ...）
- 通过：每个 task 在 Wave 下有 checkbox（`- [ ] task-XX:` 格式）
- 通过：已标注 Wave 分组和依赖关系
- 通过：有任务总表（含优先级、依赖列，无估时列）
- 通过：有关键路径标注
- 通过：有全局验收标准
- 通过：当前版本 D-001@v1 至 D-005@v1 全部可追踪
- 通过：不存在 P0/P1 unresolved blocker
- 通过：brownfield 兼容性条款已列入全局验收
- 通过：未放接口定义或代码示例；实现细节留给 execute/task 文档
- 通过：覆盖 design.md 文件变更清单，并记录调用点搜索发现的 `perf_profile.py` 补漏
- 通过：已搜索相关调用点并记录命令输出摘要
- 通过：未生成 Mermaid 图，依赖关系为 Wave 线性 + Wave 2 并行
- 通过：未包含估时或泛泛风险分析
