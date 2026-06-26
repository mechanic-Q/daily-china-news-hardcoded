---
id: task-06
author: lmr
created_at: 2026-06-24 19:40:00
title: 改造 step4.py:llm_classify_single 为 call_llm("column-classify", ...)
priority: P0
depends_on: [task-01, task-02, task-05]
blocks: [task-09]
requirement_ids: [FR-04]
decision_ids: [D-007@v1, D-011@v1]
allowed_paths:
  - /mnt/e/Daily/step4.py
---

# task-06: 改造 step4.py:llm_classify_single

## 修改文件
- 修改 `/mnt/e/Daily/step4.py`（仅 llm_classify_single 函数）
- **注意**：与 task-05 同文件，必须在 task-05 完成后执行（避免 merge 冲突）

## 覆盖来源
- Requirements: FR-04
- Decisions: D-007@v1（traceback 可见），D-011@v1（temperature 0.7 通过 yaml）

## 实现要求
1. 顶部 import 已由 task-05 加入 `from llm_client import call_llm`，本任务不重复加
2. 替换 `llm_classify_single(articles)` 函数：内层 OpenAI 构造删除，改为循环内 `call_llm("column-classify", ...)`
3. **保留**原 prompt 文本（"从以下栏目中选一个..."）
4. **保留**返回值结构 `{title: category}`
5. **保留**响应后处理：`<think>` 剥离 + cat_simple 匹配 + 标点剥离
6. **保留**外层 except 兜底（不传递异常）

## 接口定义

新版本核心（参考现有 step4.py:209-249，逐条调用）：

```python
def llm_classify_single(articles):
    """逐条用 LLM 分类，返回 {title: category}。失败的条目不进 results。"""
    import re
    from llm_client import call_llm

    cat_names = list(CATEGORY_KEYWORDS.keys())
    cat_simple = {}
    for full in cat_names:
        simple = re.sub(r'^[^\s]+\s', '', full).strip()
        cat_simple[full] = full
        cat_simple[simple] = full

    results = {}
    for a in articles:
        prompt = f"从以下栏目中选一个最贴合的，只输出栏目名称，不要输出其他文字。\n\n栏目：科技、军事、医疗、能源、农业、科研突破、材料、扶贫\n\n标题：{a['title']}\n\n最贴合的栏目："

        try:
            raw = call_llm("column-classify", messages=[{"role": "user", "content": prompt}])
            cleaned = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()
            full_cat = cat_simple.get(cleaned.strip('。，、\'"').strip())
            if full_cat:
                results[a['title']] = full_cat
            else:
                for k, v in cat_simple.items():
                    if k in cleaned:
                        results[a['title']] = v
                        break
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"  ⚠ LLM分类失败: {a['title'][:30]}... {e}")
            # 不进 results，上游会用关键词分类回退
    return results
```

**对比**：

| 旧版 | 新版 |
|------|------|
| `os.environ.get("ZHIPU_API_KEY")` + early return {} | 由 call_llm 处理 key 缺失（抛 LLMCallError） |
| `OpenAI(base_url="open.bigmodel.cn/...", api_key=...)` 函数外构造 | 不构造 |
| 循环内 `client.chat.completions.create(model="glm-4-flash", ..., temperature=0, max_tokens=10, timeout=15)` | `call_llm("column-classify", messages=...)` |
| `print(f"  ⚠ LLM分类失败: ...")` 已有 | 保留 + 加 traceback.print_exc() |

## 边界处理
1. **key 缺失**：call_llm 抛 LLMCallError，被 except 捕获 → 该条目跳过（不进 results，与旧版 key 缺失 return {} 行为等价但更细粒度）
2. **单条调用失败**：traceback 打印 + 该条跳过，继续下一条
3. **响应解析失败**：cat_simple 匹配不到 → 该条不进 results（与旧版一致）
4. **<think> 标签剥离**：保留现有 re.sub（防 LLM 推理输出泄漏）
5. **空 articles 列表**：返回 `{}`（自然行为，无特判）
6. **traceback.print_exc()** 在 except 内执行
7. **不修改 articles 入参**：循环只读
8. **CATEGORY_KEYWORDS 不动**：依赖现有 8 栏目定义

## 非目标
- ❌ 不动 CATEGORY_KEYWORDS
- ❌ 不改 prompt
- ❌ 不改外层调用者（在 run() 中如何使用 results）
- ❌ 不删除关键词分类回退（在 run() 中，与本函数无关）

## 参考
- design.md §7.3
- 当前代码：/mnt/e/Daily/step4.py:209-249
- task-05 已经加入的 `from llm_client import call_llm` import

## TDD 步骤
1. task-05 完成后执行
2. 改造函数
3. dry-run：`python3 step4.py --dry-run --date <date>`
4. 验证：`grep "open.bigmodel.cn" step4.py` 输出 0 行
5. 故意删除 NINEROUTER_API_KEY 重测 → 期望 traceback + LLM 分类全失败但流水线走关键词回退

## 验收标准
| # | 验证步骤 | 通过标准 |
|---|----------|---------|
| AC-01 | `grep -c "open.bigmodel.cn" /mnt/e/Daily/step4.py` | 输出 0（旧 base_url 已移除）|
| AC-02 | `grep -c "ZHIPU_API_KEY" /mnt/e/Daily/step4.py` | 输出 0 |
| AC-03 | `grep -c "glm-4-flash" /mnt/e/Daily/step4.py` | 输出 0（旧 model 字符串已移除）|
| AC-04 | `grep -A2 "def llm_classify_single" /mnt/e/Daily/step4.py | grep call_llm` | 找到 |
| AC-05 | `cd /mnt/e/Daily && python3 -c "from step4 import llm_classify_single; print(type(llm_classify_single([])).__name__)"` | 输出 dict |
| AC-06 | `cd /mnt/e/Daily && python3 step4.py --dry-run --date 2026-06-24` 2>&1 | 不抛异常 |
| AC-07 | `grep "OpenAI(" /mnt/e/Daily/step4.py | wc -l` | 输出 0（step4 已无 OpenAI 直接构造）|
| AC-08 | `grep "traceback.print_exc" /mnt/e/Daily/step4.py | wc -l` | 输出 ≥ 2（llm_is_china_related + llm_classify_single 各一处）|
