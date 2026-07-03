---
author: lmr
created_at: 2026-07-03 20:10:27
schema_version: 1
doc_type: plan
change_id: 2026-07-07-phase-15g-engineering
plan_level: full
---

# 实现计划

## Spike 前置验证

无。方案基于标准库 `logging`、现有 `llm_client.py`、现有 `news_archive.py` 和现有 pytest 结构，不涉及新技术栈或不可逆基础设施改造。

## Wave 1（并行，无依赖）

- [x] task-01: 建立标准库 logging 基础入口（覆盖：FR-01, D-001@v1, D-002@v1）
- [x] task-04: 增加 archive record schema migration（覆盖：FR-03, D-004@v1）

## Wave 2（依赖 Wave 1）

- [x] task-02: 为 LLM 调用失败路径加入脱敏日志与错误文案（覆盖：FR-02, D-001@v1, D-002@v1）
- [x] task-05: 增加 archive migration 回归测试（覆盖：FR-03, D-004@v1）

## Wave 3（依赖 Wave 2）

- [x] task-03: 增加 LLM 脱敏回归测试（覆盖：FR-02, D-001@v1, D-002@v1）
- [x] task-07: 补充 step6 纯函数回归测试（覆盖：FR-04, D-003@v1）

## Wave 4（依赖 Wave 3）

- [x] task-06: 补充 step4 纯函数回归测试（覆盖：FR-04, D-003@v1）

## Wave 5（依赖 Wave 4）

- [x] task-08: 新增 GitHub Actions 单元测试 CI（覆盖：FR-04, D-003@v1）

## 任务总表

| 编号 | 任务 | Wave | 优先级 | 依赖 | 覆盖 FR/D | 说明 |
|---|---|---|---|---|---|---|
| task-01 | 建立标准库 logging 基础入口 | W1 | P0 | - | FR-01, D-001@v1, D-002@v1 | 新增日志入口，保持零新增依赖 |
| task-02 | 为 LLM 调用失败路径加入脱敏日志与错误文案 | W2 | P0 | task-01 | FR-02, D-001@v1, D-002@v1 | 覆盖 `step4.py`、`step7.py`、`monthly_report.py` 使用的 `call_llm` 统一路径 |
| task-03 | 增加 LLM 脱敏回归测试 | W3 | P0 | task-02 | FR-02, D-001@v1, D-002@v1 | 断言敏感值不进入日志或 `LLMCallError` 文案 |
| task-04 | 增加 archive record schema migration | W1 | P0 | - | FR-03, D-004@v1 | 覆盖 `news_archive.py` 读取旧 JSONL 的兼容路径 |
| task-05 | 增加 archive migration 回归测试 | W2 | P0 | task-04 | FR-03, D-004@v1 | 覆盖旧 record 读取、默认字段补齐、schema 升级 |
| task-06 | 补充 step4 纯函数回归测试 | W4 | P1 | task-03 | FR-04, D-003@v1 | 不触发真实 LLM、网络或 Chromium |
| task-07 | 补充 step6 纯函数回归测试 | W3 | P1 | task-05 | FR-04, D-003@v1 | 不触发真实网络或 Chromium |
| task-08 | 新增 GitHub Actions 单元测试 CI | W5 | P0 | task-03, task-05, task-06, task-07 | FR-04, D-003@v1 | Python 3.12 安装 requirements 并运行非 manual 单元测试 |

## 关键路径

task-01 → task-02 → task-03 → task-06 → task-08

并行路径：task-04 → task-05 → task-07 → task-08。

## 调用点搜索记录

搜索命令：`rtk grep -n "\bcall_llm\(|\bload_month_records\(|\bmigrate_record\(|\barchive_articles\(" .`

结果摘要：27 matches in 9 files。代码调用点包括 `archive_enrich.py`、`archive_news.py`、`llm_client.py`、`monthly_report.py`、`news_archive.py`、`step4.py`、`step7.py`、`tests/test_news_archive.py`；`CLAUDE.md` 为文档引用。计划已将 `call_llm` 的下游调用点和 `load_month_records` 的 archive/test 调用点纳入任务范围。

## 全局验收标准

- [ ] `python3 -m pytest tests/` 通过，且不需要真实 API key、网络或 Chromium。
- [ ] LLM 调用失败时，日志和 `LLMCallError` 文案不包含 API key、Authorization header 或模拟敏感值。
- [ ] 旧 archive JSONL record 经 `load_month_records` 后补齐默认字段并升级到当前 `SCHEMA_VERSION`。
- [ ] 未设置新环境变量时，现有 `./run_all.sh` 使用方式不变。
- [ ] CI workflow 只运行非 manual 单元测试。
- [ ] 本变更不引入 loguru 或其他日志新依赖。

## 覆盖矩阵

| ID | 覆盖任务 | 验收证据 |
|---|---|---|
| FR-01 | task-01 | logging 入口存在；无新增日志依赖；未改 `run_all.sh` |
| FR-02 | task-02, task-03 | LLM 脱敏测试通过 |
| FR-03 | task-04, task-05 | archive migration 测试通过 |
| FR-04 | task-06, task-07, task-08 | `python3 -m pytest tests/` 与 GitHub Actions workflow |
| D-001@v1 | task-01, task-02, task-03 | 标准库 logging；无 loguru 依赖 |
| D-002@v1 | task-01, task-02, task-04, task-08 | 最小工程护栏任务完成；无全量 print 替换 |
| D-003@v1 | task-06, task-07, task-08 | CI 排除 manual/Chromium 依赖 |
| D-004@v1 | task-04, task-05 | load-time migration 测试通过 |

## 自检结果

- [x] 每个 task 有编号（task-01 至 task-08）。
- [x] 每个 task 在 Wave 下有 checkbox，格式为 `- [ ] task-XX:`。
- [x] 已标注 Wave 分组和依赖关系。
- [x] 有任务总表，含优先级、依赖列，无估时列。
- [x] 有关键路径标注。
- [x] 有全局验收标准。
- [x] 覆盖矩阵覆盖全部当前版本 D-001@v1 至 D-004@v1。
- [x] 不存在 P0/P1 unresolved blocker。
- [x] Brownfield 兼容性条款已列入全局验收。
- [x] 未包含接口定义、代码示例等实现细节。
- [x] plan.md 与 design.md 文件变更清单一致。
- [x] 已搜索 `call_llm`、`load_month_records`、`archive_articles` 调用点并记录结果。
- [x] 未生成 Mermaid 图；当前依赖可用 Wave 和关键路径表达。
- [x] 未包含泛泛风险分析。
