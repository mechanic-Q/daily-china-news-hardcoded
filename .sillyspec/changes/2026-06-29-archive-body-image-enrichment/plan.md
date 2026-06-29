---
author: lmr
created_at: 2026-06-29 14:13:38
schema_version: 1
plan_level: full
change_id: 2026-06-29-archive-body-image-enrichment
phase: 14B
---

# 实现计划

## Spike 前置验证

无。技术路径已由现有代码验证：`news_archive.py` 已有 JSONL load/write/upsert，`step6.py` 已有真实正文提取，新增图片逻辑仅使用标准库 HTML regex + urllib 下载。

## Wave 1 — Schema + preservation（基础兼容层）

- [ ] task-01: news_archive schema v2 与 IMAGES_DIR（覆盖：FR-09, D-006@v1）
- [ ] task-02: 14A upsert 保留 14B enrichment 字段（覆盖：FR-07, D-006@v1）

依赖说明：task-02 依赖 task-01 的 schema/路径常量语义，但二者都限定在 `news_archive.py`。

## Wave 2 — archive_enrich core（新增增强模块）

- [ ] task-03: 新增 archive_enrich.py CLI 与路径工具（覆盖：FR-05, FR-09, D-004@v1）
- [ ] task-04: 实现正文补全状态机（覆盖：FR-01, FR-02, D-001@v1, D-002@v1）
- [ ] task-05: 实现首图提取与下载（覆盖：FR-03, FR-04, FR-08, D-003@v1, D-007@v1）
- [ ] task-06: 实现 JSONL enrich 读写与统计（覆盖：FR-05, FR-06, FR-09, D-004@v1, D-005@v1）

依赖说明：task-03 提供 CLI/路径骨架；task-04 和 task-05 可在同一新文件中独立实现；task-06 汇总 task-03~05。

## Wave 3 — pipeline integration（主流程接入）

- [ ] task-07: step4 接入 archive_enrich best-effort（覆盖：FR-06, D-005@v1）

依赖说明：task-07 依赖 Wave 2 的 `archive_enrich.enrich_archive_best_effort` 已存在。

## Wave 4 — Tests + verification（回归与验收）

- [ ] task-08: 新增 tests/test_archive_enrich.py（覆盖：FR-01~FR-06, FR-08, FR-09, D-001@v1~D-005@v1, D-007@v1）
- [ ] task-09: 扩展 tests/test_news_archive.py（覆盖：FR-07, FR-09, D-006@v1）
- [ ] task-10: 运行验证命令（覆盖：FR-01~FR-09）

依赖说明：task-08/09 依赖 Wave 1~3 完成；task-10 依赖全部测试写完。

## 任务总表

| 编号 | 任务 | Wave | 优先级 | 依赖 | 覆盖 FR/D | 说明 |
|---|---|---|---|---|---|---|
| task-01 | news_archive schema v2 与 IMAGES_DIR | W1 | P0 | — | FR-09, D-006@v1 | 为 v2 JSONL 与图片目录建立基础常量 |
| task-02 | 14A upsert 保留 14B enrichment 字段 | W1 | P0 | task-01 | FR-07, D-006@v1 | 防止 14A 重跑清空正文/图片 |
| task-03 | 新增 archive_enrich.py CLI 与路径工具 | W2 | P0 | task-01 | FR-05, FR-09, D-004@v1 | 建立独立补跑入口与路径语义 |
| task-04 | 实现正文补全状态机 | W2 | P0 | task-03 | FR-01, FR-02, D-001@v1, D-002@v1 | 真实正文提取，失败只写状态/错误 |
| task-05 | 实现首图提取与下载 | W2 | P1 | task-03 | FR-03, FR-04, FR-08, D-003@v1, D-007@v1 | 仅 top10 首图，URL + 本地文件 |
| task-06 | 实现 JSONL enrich 读写与统计 | W2 | P0 | task-04, task-05 | FR-05, FR-06, FR-09, D-004@v1, D-005@v1 | 串起正文、图片、missing-only、dry-run、时间预算 |
| task-07 | step4 接入 archive_enrich best-effort | W3 | P0 | task-06 | FR-06, D-005@v1 | 自动路径不阻断日报 |
| task-08 | 新增 tests/test_archive_enrich.py | W4 | P0 | task-06, task-07 | FR-01~FR-06, FR-08, FR-09, D-001@v1~D-005@v1, D-007@v1 | 覆盖新增模块核心行为 |
| task-09 | 扩展 tests/test_news_archive.py | W4 | P0 | task-02 | FR-07, FR-09, D-006@v1 | 覆盖 schema v2 和 upsert 保留字段 |
| task-10 | 运行验证命令 | W4 | P0 | task-08, task-09 | FR-01~FR-09 | 单测 + dry-run 验证 |

## 关键路径

task-01 → task-02 → task-03 → task-04/task-05 → task-06 → task-07 → task-08/task-09 → task-10

说明：最长路径由 schema 兼容层、enrich 聚合逻辑、主流程接入和测试共同决定。

## 调用点搜索记录

| 目标 | 搜索方式 | 结果 | 计划覆盖 |
|---|---|---|---|
| `news_archive.archive_articles` | Serena references | `archive_news.py`、`news_archive.archive_articles_best_effort`、`tests/test_news_archive.py` | task-02、task-09 |
| `news_archive.archive_articles_best_effort` | Serena references | `step4.run`、`tests/test_news_archive.py` | task-07、task-09 |
| `step6.fetch_and_extract` | Serena references | `step6.run` 唯一现有调用 | task-04、task-08；不改变其返回契约 |
| `SCHEMA_VERSION/schema_version` | symbol overview + docs | 当前 `news_archive.py` 定义为 1，测试检查 record keys | task-01、task-09 |

## 全局验收标准

- [ ] `python3 tests/test_news_archive.py` 通过
- [ ] `python3 tests/test_archive_enrich.py` 通过
- [ ] `python3 archive_enrich.py --date <test-date> --dry-run` 不写 JSONL、不下载图片，并输出统计
- [ ] 正文补全不调用 LLM；失败时不写 fake body
- [ ] 非 top10 记录不下载图片，`image_status` 为 `not_selected`
- [ ] top10 图片成功时同时有 `image_url` 与 `image_path`
- [ ] 14A `archive_articles` 重新 upsert 不会清空既有 `body*` / `image*` 字段
- [ ] `step4.py` 自动触发 enrichment 失败时不影响 `1新闻_链接.md` 写入和主流程返回
- [ ] Brownfield 兼容：不修改 `run_all.sh`，不改变 `1新闻_链接.md` / `2新闻_已审核.md` / `3新闻_概述.md` / HTML / PNG 格式
- [ ] 无新增第三方依赖，无 type hints，CLI 保持手写 parse_args 风格

## 覆盖矩阵

| ID | 覆盖任务 | 验收证据 |
|---|---|---|
| D-001@v1 | task-04, task-05, task-08 | 所有记录补正文；仅 top10 图片测试 |
| D-002@v1 | task-04, task-08, task-10 | 正文来自提取结果；失败不写 fake body；无 LLM mock/调用 |
| D-003@v1 | task-05, task-08 | 图片成功时 `image_url` + `image_path` |
| D-004@v1 | task-03, task-06, task-08 | `archive_enrich.py` CLI 与 helper 行为测试 |
| D-005@v1 | task-06, task-07, task-08 | best-effort catch all、时间预算、step4 不阻断 |
| D-006@v1 | task-01, task-02, task-09 | schema v2；14A upsert 保留 14B 字段 |
| D-007@v1 | task-05, task-08 | 图片单独抓 HTML；`fetch_and_extract` 契约不变 |
| FR-01 | task-04, task-06, task-08 | 所有指定日期 records 尝试补正文 |
| FR-02 | task-04, task-08, task-10 | 禁 LLM 生成/补写正文 |
| FR-03 | task-05, task-08 | 非 top10 `not_selected` |
| FR-04 | task-05, task-08 | 首图 URL + 本地文件路径 |
| FR-05 | task-03, task-06, task-08 | CLI 支持 date/missing-only/dry-run/max-seconds |
| FR-06 | task-06, task-07, task-08 | 自动路径 best-effort |
| FR-07 | task-02, task-09 | 14A upsert 不覆盖 14B 字段 |
| FR-08 | task-05, task-08 | 不改变 step6 契约 |
| FR-09 | task-01, task-03, task-06, task-09 | schema v2 兼容旧记录 |

## 自检结果

| 检查项 | 结果 |
|---|---|
| 每个 task 有编号 | PASS |
| Wave 下有 checkbox | PASS |
| 已标注 Wave 分组和依赖关系 | PASS |
| 有任务总表且无估时列 | PASS |
| 有关键路径 | PASS |
| 有全局验收标准 | PASS |
| 覆盖全部当前版本 D-xxx@vN | PASS |
| 不存在 P0/P1 unresolved blocker | PASS |
| Brownfield 兼容验收 | PASS |
| 无实现细节代码块/函数签名 | PASS |
| plan.md 与 design.md 文件变更清单一致 | PASS |
| 调用点搜索已记录 | PASS |
| 无 Mermaid 图且依赖关系线性可读 | PASS |
| 无泛泛风险分析 | PASS |
