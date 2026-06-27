---
author: lmr
created_at: 2026-06-28 02:10:51
id: task-09
title: 运行静态/单元验证
priority: P2
depends_on: [task-08]
blocks: []
requirement_ids: [FR-09]
decision_ids: []
allowed_paths: []
---

# task-09: 运行静态/单元验证

## 修改文件
- 无（仅运行命令，检查输出）

## 覆盖来源
- Requirements: FR-09 (测试覆盖验证)

## 实现要求

1. 运行单元测试：
   - `python3 tests/test_news_archive.py`
   - 确认全部通过

2. 静态检查：
   - `rg "from step4" news_archive.py` → 预期无匹配（D-009@v1）
   - `rg "->" news_archive.py archive_news.py` → 预期无匹配（no type hints）
   - `git diff run_all.sh` → 预期无 diff（D-007@v1）

3. 回归测试：
   - `python3 tests/test_column_scoring.py` → 确认未破坏
   - `python3 step4.py --date 2026-06-25 --dry-run 2>&1 | head -40` → 确认归档提示出现

4. 幂等性测试：
   - 跑两次同一日期的 archive_news.py → archived_at 不变

## 边界处理

1. `rg` 无匹配是好结果（成功语义）
2. 回归测试失败 → 回到任务修复
3. 无数据日期 → `build_classification_result` 返回空，正常退出
4. JSONL 路径不存在 → 自动创建

## 非目标
- 不跑完整 run_all.sh
- 不跑 step6/step7/step8
- 不引入 CI

## 参考
- CONVENTIONS.md §2.3 type hints 约定
- D-009@v1 不 import step4
- D-007@v1 不改 run_all.sh

## TDD 步骤

1. 跑单元测试 → 确认通过
2. 跑静态检查 → 确认无违规
3. 跑回归 → 确认未破坏
4. 记录结果

## 验收标准
| # | 验证步骤 | 通过标准 |
|---|----------|----------|
| AC-01 | `python3 tests/test_news_archive.py` | exit 0 |
| AC-02 | `rg "from step4" news_archive.py` | 无匹配 |
| AC-03 | `rg "->" news_archive.py archive_news.py` | 无匹配（type hints） |
| AC-04 | `git diff run_all.sh` | 空 |
| AC-05 | `python3 tests/test_column_scoring.py` | 全部通过 |
| AC-06 | 同 URL 再跑 archive → archived_at 不变 | 幂等 |
