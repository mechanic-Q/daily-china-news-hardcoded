---
author: lmr
created_at: 2026-06-27 13:37:38
change: 2026-06-27-perf-profile
stage: brainstorm
doc_type: design
---

# Design — Phase 12 性能量化

## 背景

用户反馈当前 Daily 全流水线执行体感变慢，但没有可比对的量化数据。现有 `run_all.sh` 只串行执行 5 个 step，不记录每步耗时、失败前已耗时、最慢步骤排行，也没有可保存的性能报告。

Phase 12 只负责建立性能基线和定位慢点，为后续 Phase 14 性能优化提供证据；不直接优化。

## 设计目标

- FR-01：提供外部性能量化入口，能逐 step 运行并记录每步耗时、退出码、输出摘要。
- FR-02：生成结构化 JSON 报告和人类可读 Markdown 报告。
- FR-03：修改 `run_all.sh`，在日常运行时输出每个 step 耗时和总耗时。
- FR-04：报告能列出最慢 step 排名，帮助判断下一阶段优化重点。
- FR-05：保持现有 `run_all.sh` 参数、执行顺序、输入输出文件语义不变。

## 非目标

- 不做性能优化。
- 不并发化信源抓取、正文提取或 LLM 调用。
- 不重做栏目评分算法。
- 不深度插桩 5 个业务 step。
- 不新增数据库或长期性能数据仓库。
- 不改变现有报纸产物 HTML/PNG/markdown 文件格式。

## 拆分判断

本变更是单一横切能力：性能量化与报告。虽然涉及 orchestrator 和各 step 的执行时间，但不需要拆分成多个变更。Phase 14 才负责根据 Phase 12 数据做优化。

不走批量模式：没有大量重复文件或模板实例，只有一个 profiler 和一个 orchestrator 小改。

## 总体方案

### 1. 新增外部 profiler

新增 `perf_profile.py`：

- CLI 支持：`--date YYYY-MM-DD`、`--dry-run`、`--output-dir PATH`。
- 默认 step 列表与 `run_all.sh` 一致：`step1_3.py`、`step4.py`、`step6.py`、`step7.py`、`step8.py`。
- 每个 step 用 `subprocess.run()` 顺序执行。
- 使用 `time.perf_counter()` 记录开始/结束/耗时。
- 捕获 `stdout` / `stderr`，报告中保留 tail 摘要，避免报告过大。
- 任一 step 失败时停止后续 step，仍输出已完成/失败步骤的报告。
- 输出：
  - JSON：`/mnt/e/每日新中国/YYYY-MM-DD/perf/YYYY-MM-DD-profile.json`
  - Markdown：`/mnt/e/每日新中国/YYYY-MM-DD/perf/YYYY-MM-DD-profile.md`

### 2. 修改 run_all.sh 内置计时

在 `run_all.sh` 中保持原有参数和 steps 数组，新增：

- 管道开始时间。
- 每个 step 前后时间。
- 每个 step 成功后输出 `⏱ <step>: Ns`。
- 失败时输出已耗时再退出。
- 全部成功后输出总耗时。
- 为保留失败时计时输出，`python3 "$SCRIPT_DIR/$step" ...` 调用需要临时关闭 `set -e`（`set +e` → 捕获 exit_code → `set -e`），再按原语义 `exit 1`。

不改变命令行参数、不改变执行顺序、不改变失败短路语义。

### 3. 低侵入子阶段策略

默认以 step 级为主，不深度修改业务 step。可通过现有 stdout/stderr 观察 LLM 重试、Chromium 截图、网络失败等线索。子阶段精细插桩留给后续优化阶段按证据决定。

## 文件变更清单

| 操作 | 文件路径 | 说明 |
|---|---|---|
| 新增 | `perf_profile.py` | 外部性能量化脚本，输出 JSON + Markdown 报告 |
| 修改 | `run_all.sh` | 增加每步耗时和总耗时输出 |
| 新增 | `.sillyspec/changes/2026-06-27-perf-profile/prototype-perf-report.html` | 性能报告原型 |

## 接口定义

### perf_profile.py CLI

```bash
python3 perf_profile.py [--date YYYY-MM-DD] [--dry-run] [--output-dir PATH]
```

### JSON 报告结构

```json
{
  "date": "YYYY-MM-DD",
  "dry_run": true,
  "started_at": "ISO-8601",
  "ended_at": "ISO-8601",
  "total_duration_s": 0.0,
  "steps": [
    {
      "name": "step1_3.py",
      "command": ["python3", "step1_3.py", "--date", "YYYY-MM-DD"],
      "started_at": "ISO-8601",
      "ended_at": "ISO-8601",
      "duration_s": 0.0,
      "exit_code": 0,
      "stdout_tail": "...",
      "stderr_tail": "..."
    }
  ],
  "slowest": ["step7.py", "step1_3.py"]
}
```

### run_all.sh CLI

不变：

```bash
./run_all.sh [--date YYYY-MM-DD] [--dry-run]
```

## 数据模型

不涉及数据库。

新增文件输出目录：

```text
/mnt/e/每日新中国/YYYY-MM-DD/perf/
├── YYYY-MM-DD-profile.json
└── YYYY-MM-DD-profile.md
```

## 兼容策略

- `run_all.sh` 参数不变。
- step 顺序不变。
- 失败短路不变。
- 默认输出目录仍为 `/mnt/e/每日新中国/YYYY-MM-DD/`。
- profiler 是新增入口，不影响现有用户继续用 `./run_all.sh`。
- 报告写在 `perf/` 子目录，不覆盖现有 0/1/2/3/HTML/PNG 产物。

## 风险登记

| 编号 | 风险 | 等级 | 应对策略 |
|---|---|---|---|
| R-01 | profiler 完整运行会触发真实网络和 LLM 调用 | P1 | 支持 `--dry-run`；文档明确成本与前置条件 |
| R-02 | stdout/stderr 捕获过大 | P2 | 报告只保存 tail 摘要 |
| R-03 | run_all.sh 计时代码破坏原失败短路 | P1 | 保持原 exit_code 判断，失败仍 exit 1 |
| R-04 | 不深度插桩导致无法定位子阶段 | P2 | Phase 12 先做 step 级基线，后续按证据补充 |

## 决策追踪

| 决策 | 覆盖需求 | 设计覆盖 |
|---|---|---|
| D-001@v1 | FR-01, FR-02, FR-03 | 总体方案 1/2 |
| D-002@v1 | FR-01, FR-04 | 低侵入子阶段策略 |
| D-003@v1 | FR-05 | 非目标、兼容策略 |
| D-004@v1 | FR-01, FR-02 | 总体方案 1 |

## 自审

- 需求覆盖：PASS，覆盖外部 profiler + run_all 计时 + step 排名。
- Grill 覆盖：PASS，D-001/D-002 已纳入设计。
- 约束一致性：PASS，遵循文件接力、手动 CLI、无标准 test/lint 的现状。
- 真实性：PASS，涉及文件和命令来自现有项目；`perf_profile.py` 为新增。
- YAGNI：PASS，不做深度插桩和优化。
- 验收标准：PASS，可通过 py_compile、dry-run、报告文件存在、JSON schema 检查验证。
- 非目标：PASS，明确不优化、不并发、不改栏目算法。
- 兼容策略：PASS，不改变现有 run_all 参数和产物。
- 风险识别：PASS，真实网络/LLM调用风险已登记。
- 生命周期契约表：不适用；无 session/lease/daemon/state transition 等状态机变更。
