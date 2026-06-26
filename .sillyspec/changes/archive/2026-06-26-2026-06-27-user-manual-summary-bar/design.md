---
author: lmr
created_at: 2026-06-27 03:06:00
change: 2026-06-27-user-manual-summary-bar
stage: brainstorm
doc_type: design
---

# Design — 用户手册与顶部总摘要栏移除

## 背景

Daily 当前能生成完整日报，但用户缺少一个面向自查的项目手册，不方便查命令、计时方法、sillyspec 流程和故障排查。

同时 step8 渲染时会在大标题下方生成一个“所有新闻总和”的全局摘要栏。用户明确表示不想要该栏目，希望标题下方直接进入各栏目新闻正文。

## 设计目标

- FR-01：删除 step8 输出 HTML 中大标题下方的全局摘要栏。
- FR-02：新增根目录 `USER_MANUAL.md`，作为用户自查手册。
- FR-03：手册覆盖项目整体功能、运行命令、各 step 用法、sillyspec 阶段命令、`time` 计时、常见故障、后续 Phase 12/13/14 路线。
- FR-04：保持现有文件接力流水线、输入输出文件名、`--date` / `--dry-run` 接口不变。

## 非目标

- 不改栏目评分算法；该工作进入后续 Phase 13。
- 不做性能优化；先进入后续 Phase 12 量化，再进入 Phase 14 优化。
- 不新增 summary 开关；用户要求是删除，不保留配置复杂度。
- 不拆多份文档；本次仅新增单文件 `USER_MANUAL.md`。
- 不改 `run_all.sh`、`step1_3.py`、`step4.py`、`step6.py`、`step7.py`。

## 拆分判断

本变更是 Phase 11，仅包含两个小范围目标：文档新增 + 渲染层删除一个 UI 区块。性能量化、栏目算法完全重做、性能优化已经由用户确认拆为后续 phase，避免一个变更跨越太多模块。

不走批量模式：本次不是大量同构任务，没有配置生成或批处理需求。

## 总体方案

### 1. Renderer 调整

修改 `step8.py`：

- 删除 `generate_summary(sections)` 函数。
- 删除 `build_html()` 中 `summary_text = generate_summary(sections)`。
- 删除 HTML 模板中的 `<div class="summary">...</div>`。
- 删除 CSS 中 `.summary { ... }` 样式块。

结果：报纸页头仍保留标题、slogan、日期、期号；页头结束后直接进入双栏新闻正文。

### 2. 用户手册

新增根目录 `USER_MANUAL.md`，内容结构：

1. 项目是什么
2. 输出目录和文件接力流程
3. 一键运行命令
4. 分步运行命令
5. `--date` / `--dry-run` 用法
6. `time` / `/usr/bin/time -v` 计时方法
7. sillyspec 常用阶段命令
8. 常见故障排查
9. 当前已知风险
10. 后续 Phase 12/13/14 路线

## 文件变更清单

| 操作 | 文件路径 | 说明 |
|---|---|---|
| 修改 | `step8.py` | 删除顶部全局摘要栏相关函数、样式和模板输出 |
| 新增 | `USER_MANUAL.md` | 用户自查手册 |
| 新增 | `.sillyspec/changes/2026-06-27-user-manual-summary-bar/prototype-summary-removed.html` | 布局方向原型，实际实现不保留提示框 |

## 接口定义

### CLI 接口

不变：

```bash
python3 step8.py [--date YYYY-MM-DD] [--dry-run]
./run_all.sh [--date YYYY-MM-DD] [--dry-run]
```

### 函数接口

- `build_html(target_date, sections, left_sections, right_sections)` 签名不变。
- `generate_summary(sections)` 删除；当前无外部引用，仅 `build_html()` 内部使用。

## 数据模型

不涉及数据库或持久化结构变更。

输入仍为：`/mnt/e/每日新中国/YYYY-MM-DD/3新闻_概述.md`

输出仍为：

- `/mnt/e/每日新中国/YYYY-MM-DD/YYYY-MM-DD_每日新中国_<期号>.html`
- `/mnt/e/每日新中国/YYYY-MM-DD/YYYY-MM-DD_每日新中国_<期号>.png`

## 兼容策略

- 上游 `3新闻_概述.md` 格式不变。
- step8 输出文件路径和命名不变。
- `--dry-run` 行为不变：生成 HTML，跳过截图。
- 删除的是展示区块，不影响后续模块，因为 step8 是管道终点。
- 不提供旧摘要栏开关；若以后需要恢复，可从 git diff 找回。

## 风险登记

| 编号 | 风险 | 等级 | 应对策略 |
|---|---|---|---|
| R-01 | 删除摘要栏后页面高度变短，截图裁边结果变化 | P2 | 运行 step8 dry-run/截图验证 HTML 可生成 |
| R-02 | 手册随 Phase 12/13/14 继续演进后过期 | P2 | 后续 archive 时同步更新 USER_MANUAL.md |
| R-03 | 删除 `generate_summary` 若存在隐藏引用会报错 | P1 | 用代码搜索确认仅内部引用，运行 `python3 -m py_compile step8.py` |

## 决策追踪

| 决策 | 覆盖需求 | 设计覆盖 |
|---|---|---|
| D-001@v1 | FR-01 | Renderer 调整、兼容策略 |
| D-002@v1 | FR-02, FR-03 | 用户手册、文件变更清单 |
| D-003@v1 | FR-04 | 非目标、拆分判断 |
| D-004@v1 | FR-01, FR-02 | 总体方案、非目标 |

## 自审

- 需求覆盖：PASS，覆盖删除顶部总摘要栏和新增完整手册。
- Grill 覆盖：PASS，所有当前版本决策均在设计中引用。
- 约束一致性：PASS，符合文件接力、手动 CLI 参数、step8 为管道终点的既有架构。
- 真实性：PASS，涉及函数和文件来自真实代码；`USER_MANUAL.md` 为新增。
- YAGNI：PASS，拒绝配置开关和多文档拆分。
- 验收标准：PASS，可用 py_compile、dry-run、HTML 字符串检查验证。
- 非目标：PASS，明确排除性能和栏目算法。
- 兼容策略：PASS，上游输入和输出路径不变。
- 风险识别：PASS，风险均有应对。
