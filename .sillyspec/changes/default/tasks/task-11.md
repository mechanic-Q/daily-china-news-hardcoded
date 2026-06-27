---
author: lmr
created_at: 2026-06-27 21:09:09
id: task-11
title: 风格一致性扫描
priority: P2
depends_on: [task-09]
blocks: []
requirement_ids: []
decision_ids: [D-010@v1]
allowed_paths: []
---

# 风格一致性扫描

## 修改文件

无（仅扫描）

## 覆盖来源

- AC-08 / D-010@v1 实现代码不写 type hints

## 实现要求

1. type hints 扫描：
   `rg "->\s*(dict|str|int|None|list|tuple|bool|float|Any|Optional)" step4.py step7.py step8.py 2>&1`
   预期：返回空（仅 design.md 中允许）

2. typing import 扫描：
   `rg "^from typing|^import typing" step4.py step7.py step8.py`
   预期：返回空

3. openai SDK 直接 import 扫描（CONVENTIONS §3 一致性）：
   `rg "^from openai|^import openai" step4.py step7.py step8.py`
   预期：返回空（仅 llm_client.py 允许）

4. emoji 一致性扫描：
   ```
   python3 -c "
   import step4, step7, step8
   assert step4.COLUMN_ORDER == step7.COLUMN_ORDER == step8.COLUMN_ORDER
   print('OK 9 栏一致')
   "
   ```

5. yaml 字段扫描：
   `python3 -c "import yaml;c=yaml.safe_load(open('llm.yaml'));assert 'column-score' in c['call_sites'];assert c['call_sites']['column-score']['temperature']==0.0;print('OK')"`

6. 中文 print 扫描：
   `rg "print\(f?\"[^✅❌⚠═]" step4.py | head -20`
   预期：能看到所有 print 都用中文 emoji 前缀（容错性手检）

## 接口定义

不适用（命令型）

## 边界处理

1. rg 无匹配是好结果（exit 1 但是 success 语义）
2. 测试文件 tests/test_column_scoring.py 不在扫描范围（测试可用 type hints）
3. design.md / decisions.md 不在扫描范围
4. yaml 字段扫描脚本失败要明确报错
5. emoji 一致性失败要 print 出具体差异

## 非目标

- 不重构现有 type hint 不规范代码（如有）
- 不引入 ruff / mypy / flake8（依赖最小）
- 不自动修复

## 参考

CONVENTIONS.md §2.3

## TDD 步骤

1. 跑全部扫描命令
2. 任一失败 → 回到 task-04~08 修复
3. 全部通过 → mark AC-08

## 验收标准

| AC  | 描述 | 预期 |
|-----|------|------|
| AC-01 | rg type hints 在 step4/7/8 无匹配 | True |
| AC-02 | rg typing import 无匹配 | True |
| AC-03 | rg openai import 在 step4/7/8 无匹配 | True |
| AC-04 | python3 比对三处 COLUMN_ORDER 相等 | True |
| AC-05 | llm.yaml column-score temperature==0.0 | True |
| AC-06 | 全部 print 用中文 emoji 前缀（手检） | True |
