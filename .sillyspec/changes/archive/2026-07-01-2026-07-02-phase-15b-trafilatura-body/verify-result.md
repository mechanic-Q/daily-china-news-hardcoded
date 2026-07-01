---
author: lmr
created_at: 2026-07-02 01:33:35
schema_version: 1
doc_type: verify-result
change_id: 2026-07-02-phase-15b-trafilatura-body
---

# 验证报告

## 结论

PASS WITH NOTES

说明：核心功能、接口兼容、golden 回归、dry-run 格式均通过。存在一个非阻断质量风险：`2026-06-25` dry-run 的 CAS 样本正文仍包含部分站点页眉/导航噪声（如“主要职责 / 办院方针 / 科技奖励”等），表明 CAS postprocess 对页眉清理还不完整。该问题不破坏接口、输出格式或回归基线，但建议后续继续细化 CAS 清理。

## 任务完成度

| Task | 结果 | 证据 |
|---|---|---|
| task-01 | PASS | `requirements.txt` 含 `trafilatura>=1.12` |
| task-02 | PASS | `tests/fixtures/body_golden.jsonl` 20 行，覆盖 6 信源，字段齐全 |
| task-03 | PASS | `tests/manual/test_15b_body_golden.py` 存在，输出 ratio/diff/summary |
| task-04 | PASS | `step6.py` 使用 `tf_extract(...)`，ckxx fallback 抽为 `_extract_ckxx_content_txt` |
| task-05 | PASS | `SITE_POSTPROCESS` + `_people/_cas/_cctv_postprocess` + `_postprocess_text(text, url=None)` |
| task-06 | PASS | `fetch_and_extract(url, title)` 签名与 `2新闻_已审核.md` 输出格式保持 |
| task-07 | PASS | `verification.md` 记录 V1-V4 全 PASS |

完成率：7/7（100%）

## 设计一致性

| 设计点 | 状态 | 证据 |
|---|---|---|
| D-001@v1 通用正文抽取采用 trafilatura | PASS | `step6.py` 导入 `from trafilatura import extract as tf_extract`，`extract_body` 优先调用 `tf_extract(...)` |
| D-002@v1 站点特例保留为 fallback/postprocess | PASS | `_extract_ckxx_content_txt`、`SITE_POSTPROCESS`、三类 postprocess 函数 |
| D-003@v1 保持 `fetch_and_extract` 与输出格式稳定 | PASS | 签名检查通过；`run()` 仍输出 `## 【src】title`、`来源：`、`发布时间：`、`正文：` |
| D-004@v1 golden set 回归 | PASS | 20 条 golden，manual test 20/20 PASS |
| 非目标：不改 `needs_chromium` | PASS | 域名列表保持 `cctv.com/military.cctv/cnnc.com.cn/news.cctv` |
| 非目标：不改 `run_all.sh` / `step7.py` / archive schema | PASS | 未改相关文件 |

模块文档一致性：`modules/extractor.md` 仍描述旧 5 层 regex 策略。当前实现已按本 change 替换为 trafilatura。此为文档滞后，建议 archive/scan 阶段同步模块卡片；不阻断本次验证。

## 探针结果

- 未实现标记扫描：PASS，变更范围内 `TODO/FIXME/HACK/XXX/尚未实现` 0 命中。
- 关键词覆盖：PASS，`trafilatura`、`contentTxt`、`SITE_POSTPROCESS`、`fetch_and_extract`、`needs_chromium`、`body_golden`、`SequenceMatcher` 均有实现证据。
- 测试覆盖：PASS，存在 `tests/manual/test_15b_body_golden.py`；现有 `tests/test_archive_enrich.py` 覆盖 archiver 调用面。
- 决策追踪覆盖：PASS，未使用 `decisions.md`；D-001@v1 到 D-004@v1 均在 `design.md`、`plan.md`、实现证据中闭环。
- API Contract Parity：不适用，无 `contract-artifacts`，无 `backend/`/`frontend/` 目录。

## 决策追踪矩阵

| 决策 ID | FR | Task | Evidence | 状态 |
|---|---|---|---|---|
| D-001@v1 | FR-01 | task-01, task-04 | `requirements.txt`, `step6.py:21`, `step6.py:56` | PASS |
| D-002@v1 | FR-02, FR-03 | task-04, task-05 | `step6.py:29`, `step6.py:99` | PASS |
| D-003@v1 | FR-04 | task-06 | signature check, `step6.py:161`, `step6.py:228-232` | PASS |
| D-004@v1 | NFR golden set | task-02, task-03, task-07 | `tests/fixtures/body_golden.jsonl`, `tests/manual/test_15b_body_golden.py`, `verification.md` | PASS |

## 测试结果

| 命令 | 结果 |
|---|---|
| `python3 -c "import trafilatura"` | PASS |
| `python3 -m py_compile step6.py` | PASS |
| `python3 -c "import inspect, step6; assert list(inspect.signature(step6.fetch_and_extract).parameters)==['url','title']"` | PASS |
| `PYTHONPATH=. python3 tests/manual/test_15b_body_golden.py` | PASS，20/20 |
| `python3 step6.py --date 2026-06-25 --dry-run` | PASS，10/10 成功，格式字段存在 |

local.yaml：`build/test/lint` 均为空，`test_strategy=skip`，无正式 lint/typecheck 命令。

## 技术债务

- 变更范围 TODO/FIXME/HACK/XXX/尚未实现：0。
- 质量风险：CAS 正文仍可能包含页眉/导航噪声。建议后续针对 CAS 新增更精确的正文起点/模板剥离规则。

## 变更风险等级

change_risk_profile: unit-sufficient

理由：单模块 extractor 行为变更 + fixture/manual test；不涉及 daemon/backend/session/lease/state_machine/entrypoint/deployment。无需 Runtime Evidence。

## Runtime Evidence

不适用（非 integration-critical / deployment-critical）。

## 代码审查

总体评价：PASS WITH NOTES。

- 代码风格符合项目约定：snake_case、同步脚本、中文输出风格保留。
- 外部接口保持：`fetch_and_extract(url, title)`、`needs_chromium(url)`、`run(today, dry_run)` 均未破坏。
- 错误处理保持：`fetch_and_extract` 仍返回 `(None, reason)`，未新增异常外泄路径。
- 依赖声明明确：`requirements.txt` 新增 `trafilatura>=1.12`。
- 主要风险为质量类而非正确性类：CAS 页面抽取可用但清理不够彻底。
