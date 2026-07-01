---
author: lmr
created_at: 2026-07-01 22:36:11
schema_version: 1
doc_type: plan
change_id: 2026-07-02-phase-15b-trafilatura-body
plan_level: light
---

# 轻量计划：Phase 15B · trafilatura body extraction

## 来源

来自 `proposal.md`：Phase 15B 目标是用 `trafilatura` 作为通用正文抽取核心，并把少数站点特例收敛到显式 postprocess registry，从根上降低正文污染和维护成本。

来自 `design.md`：保持 `fetch_and_extract(url, title) -> (body, err)` 外部接口不变，保持 `2新闻_已审核.md` 输出格式不变，保留参考消息 `contentTxt` fallback，建立 golden set 回归。

## 范围

- `requirements.txt`：声明 `trafilatura>=1.12`
- `step6.py` / extractor 模块：替换正文抽取核心，集中站点 postprocess，保持接口与输出格式
- `tests/fixtures/body_golden.jsonl`：保存真实历史正文 golden set
- `tests/manual/test_15b_body_golden.py`：提供手动回归脚本

## Tasks

## Wave 1
- [x] task-01: 新增或更新依赖声明，确保 `trafilatura` 可安装与导入（覆盖：FR-01, D-001@v1）
- [x] task-02: 建立 20 条真实信源正文 golden set fixture（覆盖：FR-04, D-004@v1）

## Wave 2
- [x] task-04: 在 `step6.py` 中用 `trafilatura` 替换通用 regex 正文定位，并保留参考消息 fallback（覆盖：FR-01, FR-02, D-001@v1, D-002@v1）

## Wave 3
- [x] task-05: 将 CAS / People / CCTV 清理收敛为站点 postprocess registry，并保持污染检查可用（覆盖：FR-03, D-002@v1）

## Wave 4
- [x] task-03: 新增 manual golden 回归脚本，输出相似度、失败样本与 diff（覆盖：FR-01, FR-04, D-004@v1）
- [x] task-06: 验证 `fetch_and_extract` 签名、返回语义与 `2新闻_已审核.md` 格式不变（覆盖：FR-04, D-003@v1）

## Wave 5
- [x] task-07: 执行可用验证命令并记录结果；若 local.yaml 无 build/test/lint，则至少执行 import 检查、manual golden test、`step6.py --dry-run` 样本验证（覆盖：全部）

## 验收

- AC-01: `python3 -c "import trafilatura"` 成功。
- AC-02: `tests/fixtures/body_golden.jsonl` 包含 20 条记录，字段含 `source`、`title`、`url`、`old_body`。
- AC-03: manual golden test 可运行，并输出每条 ratio；≥18/20 自动通过（ratio ≥0.85）或低分样本有人工确认说明。
- AC-04: `fetch_and_extract(url, title)` 仍返回 `(body, None)` 或 `(None, reason)`，调用点无需修改。
- AC-05: `python3 step6.py --date <可用样本日期> --dry-run` 输出仍包含标题、来源、发布时间、正文四类字段。
- AC-06: `needs_chromium(url)`、`run_all.sh`、`step7.py`、archive schema 不发生本 change 范围外改动。

## 覆盖矩阵

| ID | 覆盖任务 | 验收证据 |
|---|---|---|
| D-001@v1 | task-01, task-04 | AC-01, AC-03 |
| D-002@v1 | task-04, task-05 | AC-03, AC-06 |
| D-003@v1 | task-06 | AC-04, AC-05 |
| D-004@v1 | task-02, task-03, task-07 | AC-02, AC-03 |

## 自检结果

- [x] 输出明确标注 `plan_level: light`
- [x] 有来源、范围、任务列表、验收标准四个部分
- [x] 来源直接引用已有文档，未重新扩写
- [x] 任务列表清晰且无实现细节
- [x] 任务使用 checkbox 格式（`- [ ] task-XX:`）
- [x] 验收标准具体可验证
- [x] 当前版本 D-001@v1 到 D-004@v1 在 plan.md 中可追踪
- [x] 不存在 P0/P1 unresolved blocker
- [x] 没有 Mermaid 图、估时、风险分析
- [x] 没有函数签名、代码示例等实现细节
- [x] plan.md 与 design.md 的文件变更清单一致
- [x] 包含至少一个 `- [ ] task-XX:` 格式的 checkbox 任务
