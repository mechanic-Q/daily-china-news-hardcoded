---
author: lmr
created_at: 2026-06-27 21:09:09
id: task-09
title: 新增 tests/test_column_scoring.py
priority: P0
depends_on: [task-01, task-02, task-03, task-04, task-05, task-06, task-07, task-08]
blocks: [task-10, task-11]
requirement_ids: [FR-11]
decision_ids: [D-001@v1, D-002@v1, D-003@v1, D-004@v1, D-006@v1, D-008@v1, D-010@v1, D-011@v1, D-012@v1, D-013@v1, D-014@v1, D-015@v1, D-016@v1, D-017@v1]
allowed_paths:
  - tests/test_column_scoring.py
  - tests/__init__.py
---

# task-09: 新增 tests/test_column_scoring.py

## 修改文件
- `tests/test_column_scoring.py`（新增）
- `tests/__init__.py`（空文件，若不存在则新建）

## 覆盖来源
- FR-11 测试覆盖
- 间接覆盖全部 D-xxx@v1

## 实现要求

### 测试框架与风格
- 纯 stdlib `unittest.TestCase`；不引入 pytest 依赖（`local.yaml test_strategy=skip`）。但若 pytest 可用，文件可被 pytest 发现。
- 文件可独立运行：`python3 tests/test_column_scoring.py` 入口含 `if __name__ == "__main__": unittest.main()`
- 不写 type hints
- mock 使用 `unittest.mock.patch`
- 离线可跑：不调真实 LLM

### Import
```python
from step4 import COLUMN_ORDER, CATEGORY_KEYWORDS, _validate_signals, aggregate_scores, assign_category, score_signals, WORLD_CLASS_THRESHOLD
from step7 import COLUMN_ORDER as STEP7_COL
from step8 import COLUMN_ORDER as STEP8_COL
```

### 必须包含的测试用例（≥22 个 test_ 函数）

| 测试方法 | 覆盖 AC | 描述 |
|----------|---------|------|
| `test_column_order_consistency_three_files` | AC-07 | 三处 COLUMN_ORDER 相等（list ==） |
| `test_column_order_has_ai_at_index_1` | AC-12 | `COLUMN_ORDER[1]` 含 `🤖` |
| `test_validate_signals_valid` | AC-03 | 合法 dict 通过 |
| `test_validate_signals_missing_key` | AC-03 | 缺 key 抛 ValueError |
| `test_validate_signals_extra_key` | AC-03 | 多 key 抛 ValueError |
| `test_validate_signals_out_of_range` | AC-03 | 值 >10 抛 ValueError |
| `test_validate_signals_non_int` | AC-03 | 值非 int 抛 ValueError |
| `test_validate_signals_not_dict` | AC-03 | 输入非 dict 抛 TypeError |
| `test_aggregate_all_zero` | AC-04 | 全 0 → 0 |
| `test_aggregate_all_ten` | AC-04 | 全 10 → 10 |
| `test_aggregate_relev_zero` | AC-04 | relev=0 总分不变？按实际逻辑 |
| `test_aggregate_mixed` | AC-04 | 混合值预期输出 |
| `test_assign_world_class_preempt_at_7` | AC-09 | world_class≥7 优先 |
| `test_assign_argmax_when_world_class_below_threshold` | AC-09 | <THRESHOLD 走 argmax |
| `test_assign_returns_none_all_zero` | AC-09 | 全 0 → None |
| `test_score_signals_llm_error_returns_none` | AC-02+FR-07 | LLM 抛异常返回 None |
| `test_score_signals_json_strip_codefence` | AC-04 | LLM 返回含 ```json fence 仍解析 |
| `test_score_signals_json_strip_think` | AC-04 | LLM 返回含 <｜end▁of▁thinking｜> 仍解析 |
| `test_score_signals_invalid_schema_returns_none` | AC-03 | JSON 缺 key 返回 None |
| `test_category_keywords_has_9_columns` | AC-12 | len(CATEGORY_KEYWORDS) == 9 |
| `test_category_keywords_ai_min_30_words` | AC-12 | `🤖 AI智能前沿` 关键词 ≥30 条 |
| `test_category_keywords_tech_no_ai_words` | AC-12 | `🚀 科技` 不含 AI 专属词（"GPT" / "Transformer" 等） |
| `test_category_keywords_tech_has_cpu_vendors` | AC-12 | `🚀 科技` 含 "英特尔" / "AMD" 等 CPU 厂商 |
| `test_run_writes_only_non_empty_columns` | AC-11 | mock `score_signals` + parse 0，验证仅非空栏写入 |
| `test_run_legacy_path_when_llm_fails` | AC-02+FR-07 | LLM 失败走 legacy path |

### 边界处理（≥7）
1. mock 不调真实 LLM（保证离线可跑）
2. tmp 输出路径使用 `tempfile.TemporaryDirectory`，不污染真实 `/mnt/e/每日新中国`
3. 三处 `COLUMN_ORDER` 比对用 list 相等，包含 emoji codepoint 完整性
4. 缺 `__init__.py` 时也能 `python3 tests/test_column_scoring.py` 跑（用 `sys.path` 调整或纯导入测试）
5. `CATEGORY_KEYWORDS` 词典断言：检查 `set(CATEGORY_KEYWORDS.keys()) == set(COLUMN_ORDER)`
6. 不调用 `step4.run()` 真实跑（除非 mock `parse_0` + `score_signals`）
7. 异常路径用 `patch` 抛 `LLMCallError` / `Exception`

## 非目标
- 不替代 dry-run 集成验证（task-10）
- 不覆盖 step6/step7/step8 内部逻辑
- 不引入 mock LLM server / pytest plugin

## 参考
- `unittest.mock` 标准库用法
- 项目无现有 `tests/` 目录，是 greenfield 测试入口

## TDD 步骤
1. 先写测试骨架（test_* 函数空 body 或 `self.skipTest("not implemented")`）
2. 实现 step4 各函数（task-04/05/06/07/08）后逐项填充测试
3. 跑 `python3 tests/test_column_scoring.py`，确认通过
4. 跑 `python3 -m unittest tests.test_column_scoring`，确认通过

## 验收标准
| # | 验证步骤 | 通过标准 |
|---|----------|----------|
| AC-01 | 文件存在 `tests/test_column_scoring.py` | True |
| AC-02 | `python3 tests/test_column_scoring.py` exit 0 | exit code 0 |
| AC-03 | 至少 22 个 `test_` 函数 | `rg "^    def test_" tests/test_column_scoring.py | wc -l` ≥ 22 |
| AC-04 | 不引入新 pip 依赖 | `rg "^import (pytest|nose)" tests/test_column_scoring.py` → 0 |
| AC-05 | 不调真实 LLM | mock.patch 包裹所有 `score_signals`/`call_llm` 调用 |
| AC-06 | 三处 COLUMN_ORDER 一致性测试 | `test_column_order_consistency_three_files` 存在且通过 |
