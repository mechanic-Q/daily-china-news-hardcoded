---
author: lmr
created_at: 2026-06-27 21:09:09
id: task-04
title: 实现 score_signals + Schema 校验
priority: P0
depends_on: [task-02]
blocks: [task-05, task-06, task-07, task-09]
requirement_ids: [FR-01, FR-02]
decision_ids: [D-002@v1, D-011@v1, D-018@v1, D-019@v1]
allowed_paths:
  - step4.py
---

# task-04: 实现 score_signals + Schema 校验

## 修改文件
- step4.py (新增函数；不删现有 legacy 函数)

## 覆盖来源
- FR-01 LLM 单次结构化打分 / FR-02 Schema 校验 / D-002@v1 B+ / D-011@v1 9 栏语义契约 prompt / D-018@v1 🔬 E 三维 / D-019@v1 🔬 D 拆分

## 实现要求
1. 新增 `_strip_think(raw: str) -> str`: `re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()`
2. 新增 `_strip_codefence(raw: str) -> str`: 去 ```json ... ``` 和 ``` ... ```，返回净 JSON 字符串
3. 新增 `_build_score_prompt(title: str, source: str) -> str`: 模板见 design §6.3。要求：
   - 列出 9 栏目（按 COLUMN_ORDER）+ 各栏语义提示 (intent + 强信号词)
   - 🔬 提示包含 Must A-F 简化版（卡脖子/世界空白/独有工程/国产化推进 D.1+D.2/顶刊E.1+E.2+E.3 三维/独家壮举）
   - 明确要求 "如新闻达到 🔬 世界级 Must 标准，🔬 relevance 应打 7-10"（配合 task-06 抢占）
   - 输出 JSON schema 含 9 栏 relevance + importance + timeliness
   - 强调 "只输出 JSON，不要 markdown 代码块，不要 think 标签"
4. 新增 `_validate_signals(data: dict) -> bool`:
   - data 必须是 dict
   - `data['relevance']` 必须是 dict 且 `set(data['relevance'].keys()) == set(COLUMN_ORDER)`
   - 每个 relevance value 必须是 int 且 `0 <= v <= 10`
   - `data['importance']` 必须是 int 且 `0 <= v <= 10`
   - `data['timeliness']` 必须是 int 且 `0 <= v <= 10`
   - 任一不满足返回 False
5. 新增 `score_signals(title: str, source: str) -> dict | None`:
   - 调 `call_llm("column-score", messages=[{"role":"user","content":_build_score_prompt(title, source)}])`
   - 流程：`_strip_think` → `_strip_codefence` → `json.loads` → `_validate_signals`
   - 若 JSONDecodeError，重试 1 次（追加 "请仅输出严格 JSON，不要 markdown 代码块" 到 prompt 末尾）
   - 任何异常 (LLMCallError / JSONDecodeError / KeyError / ValidationError / 其他 Exception) → 返回 None
   - 不在函数内部 traceback；llm_client.call_llm 已经 traceback 过
   - 内部不打印日志（调用方负责降级监控）

## 接口定义
```python
COLUMN_ORDER = [...9 栏...]  # task-01 已建
WORLD_CLASS_THRESHOLD = 7    # task-06 用
AGG_RELEV_BASE = 0.5         # task-05 用
AGG_IMP_W = 0.3
AGG_TIME_W = 0.2
SCORE_SCHEMA_VERSION = 1     # 文档化用，本任务不强制使用

def _strip_think(raw): ...
def _strip_codefence(raw): ...
def _build_score_prompt(title, source): ...
def _validate_signals(data): ...
def score_signals(title, source): ...
```

返回结构 signals:
```python
{
    "relevance": {<9 栏目 key>: int 0-10},
    "importance": int 0-10,
    "timeliness": int 0-10
}
```

## 边界处理 (≥5)
1. title 为空字符串：仍调 LLM，让 LLM 自然返回低分；不前置校验
2. source 为空 / None：传给 prompt 时使用 "未知" 字符串占位
3. LLMCallError 立即返回 None，不重试（call_llm 内部已重试）
4. JSONDecodeError 重试 1 次后仍失败返回 None
5. `_validate_signals` 失败返回 None
6. JSON 内 relevance 仅 8 个 key（缺 🤖 或 🎖️）→ False
7. JSON 内 relevance 含多余 key → False
8. value 为 float (如 7.5) → False（要求整数）
9. value 越界 (如 11 或 -1) → False
10. 函数不写 type hints；不引入 typing 模块

## 非目标
- 不实现 `aggregate_scores` (task-05)
- 不实现 `assign_category` (task-06)
- 不修改 `run()` (task-07)
- 不删 `llm_classify_single`（task-07 legacy_path 仍用）

## 参考
- step4.py:225-226 现有 `_strip_think` 模式 (re.sub <think>)
- llm_client.call_llm 调用风格

## TDD 步骤
1. `tests/test_column_scoring.py` 加 `test_validate_signals_*`（缺 key/越界/非 int/非 dict/重复 key/正例 共 ≥6 case）
2. 加 `test_score_signals_mock`（mock call_llm 返回合法 JSON → 返回 dict；返回非法 JSON → 返回 None；call_llm 抛 LLMCallError → 返回 None；带 think 标签的 JSON → 解析成功）
3. 跑测试失败
4. 实现 `_strip_think` / `_strip_codefence` / `_build_score_prompt` / `_validate_signals` / `score_signals`
5. 跑测试通过

## 验收标准
| AC-ID | 验证步骤 | 通过标准 |
|-------|----------|----------|
| AC-01 | `_validate_signals` 拒绝 6+ 异常输入 | 全 False |
| AC-02 | `_validate_signals` 接受合法输入 | True |
| AC-03 | `score_signals` mock call_llm 抛 LLMCallError | 返回 None |
| AC-04 | `score_signals` 收到 ```json ... ``` 包裹的合法 JSON | 解析成功 |
| AC-05 | `score_signals` 收到含 `<think>...</think>` 的 JSON | 解析成功 |
| AC-06 | `_build_score_prompt` 输出含 9 栏目 emoji + 9 栏 relevance JSON 模板 | grep 命中 |
