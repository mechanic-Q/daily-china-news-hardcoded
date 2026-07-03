---
author: lmr
created_at: 2026-07-03 19:59:01
schema_version: 1
doc_type: design
change_id: 2026-07-07-phase-15g-engineering
phase: 15g
status: confirmed
---

# Design · Phase 15G · Engineering Hardening

## 目标/背景/问题描述

Phase 15A-15F 已把 Daily 新闻流水线推进到结构整理、正文提取增强、采集加速、信源健康、LLM 批处理和图片质量提升。Phase 15G 的目标是补齐工程化护栏，让这些优化长期可维护、可测试、可在 CI 中回归。

当前问题：

- 日志仍以 `print` 为主，缺少统一日志级别和持久化入口。
- `llm_client.call_llm` 使用 `traceback.print_exc()`，异常上下文可能暴露 API key、Authorization header 或 provider 返回的敏感请求信息。
- `news_archive.py` 只有 `SCHEMA_VERSION` 和新记录写入逻辑，旧 JSONL 记录读取时没有显式 schema migration。
- 项目已有 `tests/`，但缺少 GitHub Actions CI，测试靠人工记忆。

## 设计目标

- 使用标准库 `logging` 提供零新增依赖的日志配置能力，支持 stdout 和文件持久化。
- 让 LLM 调用失败时只输出安全字段：`call_site_id`、异常类型、HTTP status/code（如有），不输出完整 traceback 和敏感 header。
- 新增 archive record migration，读取旧记录时补齐默认字段并升级到当前 `SCHEMA_VERSION`。
- 扩充关键单元测试，覆盖 LLM 脱敏、archive migration 和已有纯函数风险点。
- 新增 GitHub Actions CI：Python 3.12、安装 `requirements.txt`、运行 `python3 -m pytest tests/`。

## 非目标

- 不替换全流水线所有 `print`；本阶段只提供日志入口并接入工程护栏相关模块。
- 不改 `run_all.sh` 用户运行方式。
- 不改 step1_3/step4/step6/step7/step8 的业务算法。
- 不引入 loguru 或其他日志新依赖。
- 不引入数据库，不改变 archive 文件格式为 JSONL 的事实。
- CI 不跑 `tests/manual/`，不依赖 Chromium。

## 拆分判断

本变更不拆分：日志、脱敏、migration、测试和 CI 都服务同一个 engineering hardening 目标，任务数少于 10，且不属于模板乘数据的批量模式。后续 plan 用 Wave 划分实现顺序即可。

## 决策/方案选择

用户确认选择方案A：最小工程护栏。

| 方案 | 结论 | 原因 |
|---|---|---|
| 方案A：最小工程护栏 | 采用 | 覆盖日志、脱敏、migration、测试、CI，零新增日志依赖，diff 最小 |
| 方案B：全 pipeline 日志标准化 | 不采用 | 需横跨所有 step 替换输出，回归面过大 |
| 方案C：测试/CI 优先，日志延后 | 不采用 | 不满足本 phase 的日志持久化目标 |

## 总体方案

### Wave 1 · Logging 基础与 LLM 脱敏

- 新增 `daily_logging.py`，封装标准库 `logging` 配置。
- 默认同时输出到 stdout 和 `/mnt/e/每日新中国/logs/daily.log`。
- 日志目录不存在时自动创建；文件 handler 失败时保留 stdout，不阻断流水线。
- `llm_client.call_llm` 改为使用 logger 记录安全异常摘要。
- `LLMCallError` 文案只保留 `call_site_id` 和异常类别，不拼接完整异常对象字符串。

### Wave 2 · Archive Schema Migration

- 在 `news_archive.py` 新增 `migrate_record(record)`。
- 缺失 `schema_version` 的记录视为 v1。
- 补齐当前 schema 默认字段：`schema_version`、`normalized_url`、`selected_in_top10`、`score_source`、`archive_status`、`body_status`、`image_status`、`updated_at`。
- `load_month_records(month_path)` 读取每行后调用 `migrate_record`，再按 `id` 入 map。
- `write_month_records` 继续按现有 JSONL 排序写回，不改变文件格式。

### Wave 3 · Tests 与 CI

- 新增 LLM 脱敏测试：模拟 provider 异常中包含 API key 或 Authorization，断言 logger/LLMCallError 不包含敏感值。
- 新增 archive migration 测试：构造旧 record，断言读取后补齐默认字段并升级 schema。
- 补充现有 archive/monthly/step4/step6 纯函数测试；避免真实网络、LLM、Chromium。
- 新增 `.github/workflows/test.yml`，push/PR 触发，执行 `python3 -m pytest tests/`。

## 文件变更清单

| 操作 | 文件路径 | 说明 |
|---|---|---|
| 新增 | `daily_logging.py` | 标准库 logging 配置入口 |
| 修改 | `llm_client.py` | LLM 异常脱敏与日志接入 |
| 修改 | `news_archive.py` | 新增 `migrate_record`，load 时迁移旧 record |
| 新增/修改 | `tests/test_llm_client.py` | LLM 脱敏单元测试 |
| 修改 | `tests/test_news_archive.py` | archive migration 测试 |
| 新增/修改 | `tests/test_step4.py` | 分类纯函数回归测试 |
| 新增/修改 | `tests/test_step6.py` | 正文清洗纯函数回归测试 |
| 新增 | `.github/workflows/test.yml` | GitHub Actions CI |

## 接口定义

### `daily_logging.py`

```python
def setup_logging(log_file=None, level=None):
    """配置 Daily 日志，返回 root logger 或 Daily logger。"""
```

- `log_file` 缺省时写入 `/mnt/e/每日新中国/logs/daily.log`。
- `level` 缺省为 `INFO`，可从环境变量 `DAILY_LOG_LEVEL` 覆盖。
- 多次调用必须幂等，避免重复 handler。

### `llm_client.py`

```python
def call_llm(call_site_id: str, messages: list[dict[str, str]], **override) -> str:
    """调用 LLM，失败时记录脱敏摘要并抛出 LLMCallError。"""
```

异常摘要字段：

| 字段 | 来源 | 说明 |
|---|---|---|
| `call_site_id` | 入参 | 识别调用点 |
| `exception_type` | `type(exc).__name__` | 异常类别 |
| `status_code` | `getattr(exc, "status_code", None)` | 可选 HTTP 状态 |
| `error_code` | provider error/code 属性 | 可选错误码 |

### `news_archive.py`

```python
def migrate_record(record):
    """返回升级到当前 SCHEMA_VERSION 的 archive record 副本。"""
```

- 输入可以是旧 record dict。
- 输出必须包含当前 schema 所需默认字段。
- 不修改原 dict，降低调用方副作用。

## 数据模型

Archive JSONL 仍是一行一个 JSON object。当前 `SCHEMA_VERSION = 2`。

Migration 默认字段：

| 字段 | 默认值规则 |
|---|---|
| `schema_version` | 当前 `SCHEMA_VERSION` |
| `normalized_url` | `normalize_url(url)` |
| `selected_in_top10` | `False` |
| `score_source` | `unknown` |
| `archive_status` | 缺失时为 `metadata-only` |
| `body_status` | 缺失时为 `missing` |
| `image_status` | 缺失时为 `missing` |
| `updated_at` | 缺失时用当前北京时间 ISO 字符串 |

## 兼容策略

- 未设置任何新环境变量时，现有命令仍可运行。
- 日志文件创建失败不导致 pipeline 失败，只保留 stdout handler。
- `load_month_records` 自动迁移内存中的旧 record；只有后续写回时才落盘为新 schema。
- LLM 失败仍抛出 `LLMCallError`，调用方异常控制流不变。
- CI 只覆盖不依赖外部服务的单元测试，避免因网络、API key、Chromium 造成误报。

## 风险登记

| 编号 | 风险 | 等级 | 应对策略 |
|---|---|---|---|
| R-01 | 脱敏过度导致排查信息不足 | P1 | 保留 call_site_id、异常类型、status/code |
| R-02 | 日志 handler 重复导致重复输出 | P2 | `setup_logging` 幂等，检测已有 handler |
| R-03 | migration 默认值误导业务含义 | P1 | 默认值只表达缺失/metadata-only，不虚构正文或图片成功状态 |
| R-04 | CI 环境缺少系统依赖 | P2 | CI 不跑 manual tests，不触发 Chromium/网络/LLM |

## 决策追踪

- D-001@v1：日志采用标准库 `logging`。覆盖 FR-01、Wave 1、`daily_logging.py`。
- D-002@v1：采用方案A最小工程护栏。覆盖总体方案和非目标。
- D-003@v1：CI 不跑 manual tests，不依赖 Chromium。覆盖 Wave 3 和兼容策略。
- D-004@v1：Archive migration 在读取时执行，写回保持 JSONL 格式。覆盖 Wave 2 和数据模型。

## 自审

| 检查项 | 结果 |
|---|---|
| 需求覆盖 | 通过：覆盖中文交流、标准库 logging、方案A、脱敏、migration、测试、CI |
| Grill/决策覆盖 | 通过：design.md 引用 D-001@v1 至 D-004@v1 |
| 约束一致性 | 通过：保持 Python 脚本式项目、文件接力、现有 run_all.sh |
| 真实性 | 通过：`llm_client.call_llm`、`LLMCallError`、`news_archive.SCHEMA_VERSION`、`load_month_records` 来自真实代码；`daily_logging.py` 标注为新增 |
| YAGNI | 通过：不全量替换 print、不引入 loguru、不做数据库化 |
| 验收标准 | 通过：每个目标都有对应测试或 CI 检查 |
| 非目标清晰 | 通过 |
| 兼容策略 | 通过 |
| 风险识别 | 通过 |
| 生命周期契约表 | 不适用：本变更不涉及会话、租约、后台常驻进程或心跳协议 |
