---
author: lmr
created_at: 2026-06-27 21:09:09
id: task-02
title: llm.yaml 新增 column-score call site
priority: P0
depends_on: []
blocks: [task-04]
requirement_ids: [FR-10]
decision_ids: [D-002@v1, D-008@v1]
allowed_paths:
  - llm.yaml
---

# task-02: llm.yaml 新增 column-score call site

## 修改文件
- llm.yaml (call_sites 追加 column-score 键)

## 覆盖来源
- Requirement: FR-10 (llm.yaml 新增 column-score call site)
- Decisions: D-002@v1 (B+ 信号提取式 → 需 column-score site)、D-008@v1 (评分确定性 → temperature=0.0)

## 实现要求
在 `call_sites` 下追加 `column-score` 键。参数：max_tokens=256, temperature=0.0（区别于其他 site 默认 0.7，评分确定性 D-008@v1），timeout=30。沿用 llm.yaml 现有 provider/model（9router/low/localhost:20128/v1），不在 call_site 内重复声明。注释一行说明 "评分确定性 → temp=0.0"。

## 接口定义
YAML 片段示例：
```yaml
call_sites:
  column-score:
    max_tokens: 256
    temperature: 0.0   # 评分确定性 (D-008@v1)
    timeout: 30
```

## 边界处理
1. 现有 call_sites（china-relevance / column-classify / summarize）字段不动
2. provider/model 在文件顶层，不要在 column-score 内重复
3. yaml 缩进 2 空格保持一致
4. 非 ASCII 注释采用 UTF-8
5. 若 column-score 已存在则更新数值，不重复键
6. llm_client.call_llm("column-score", ...) 失败时上层负责降级，本任务不实现回退

## 非目标
- 不改 llm_client.py 逻辑
- 不改其他 call_site
- 不引入新 provider

## 参考
llm.yaml 内现有 china-relevance / column-classify 三键结构。设计 §6.2 示例。

## TDD 步骤
1. 写 `python3 -c "import yaml;assert 'column-score' in yaml.safe_load(open('llm.yaml'))['call_sites']"` — 当前失败
2. 编辑 llm.yaml 加 column-score
3. 重跑断言通过
4. 额外断言 temperature==0.0、max_tokens==256、timeout==30
5. 回归：`python3 -c "from llm_client import load_config; print(load_config())"` 不报错

## 验收标准
| # | 验证步骤 | 通过标准 |
|---|----------|----------|
| AC-01 | yaml.safe_load 读到 column-score 键 | True |
| AC-02 | temperature 字面 0.0 | True |
| AC-03 | max_tokens 字面 256 | True |
| AC-04 | timeout 字面 30 | True |
| AC-05 | yaml.safe_load 不抛错 | True |
