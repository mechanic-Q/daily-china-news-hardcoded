---
id: task-07
author: lmr
created_at: 2026-06-24 19:40:00
title: 改造 step7.py:llm_summarize 内层为 call_llm("summarize", ...)
priority: P0
depends_on: [task-01, task-02]
blocks: [task-09]
requirement_ids: [FR-05]
decision_ids: [D-007@v1, D-011@v1]
risk_ids: [R-08]
allowed_paths:
  - /mnt/e/Daily/step7.py
---

# task-07: 改造 step7.py:llm_summarize

## 修改文件
- 修改 `/mnt/e/Daily/step7.py`（仅 llm_summarize 函数 + 顶部 import）

## 覆盖来源
- Requirements: FR-05（step7.py 1 处 LLM 调用替换 + 兼容外层重试）
- Decisions: D-007@v1（traceback 可见），D-011@v1（temperature 0.7 通过 yaml）
- Risks: R-08（step7 重试循环兼容性）

## 实现要求
1. 顶部 import 区追加：`from llm_client import call_llm, LLMCallError`
2. **删除**：内部 `OpenAI(base_url="open.bigmodel.cn/...", api_key=...)` 构造、`api_key = os.environ.get("ZHIPU_API_KEY")` 读取
3. **替换**：内层 `client.chat.completions.create(model="glm-4-flash", ...)` 改为 `call_llm("summarize", messages=...)`
4. **必须保留**：
   - 外层 `for attempt in range(3)` 重试循环
   - `failures = set()` + RETRY_PROMPTS 注入逻辑（attempt > 0 时拼接修复提示）
   - `_why_invalid()` 调用 + `failures.add(reason)` 追加
   - `<think>` 标签剥离
   - `time.sleep(1)` / `time.sleep(2)` 重试间隔
   - 失败返回 `None`（让上游 fallback_summarize 兜底）

## 接口定义

新版本（在现有 step7.py:150-192 基础上修改）：

```python
def llm_summarize(title, body):
    """调用 LLM 逐条摘要（智能重试：诊断失败原因→针对性修复 prompt→重试）。
    失败返回 None，上游用 fallback_summarize 兜底。"""
    import time
    from llm_client import call_llm, LLMCallError

    base_prompt = f"用1-2句话精炼概括以下新闻的核心要点。简短、准确、完整，直接输出摘要。\n\n标题：{title}\n正文：{body}"

    failures = set()
    for attempt in range(3):
        try:
            prompt = base_prompt
            if attempt > 0 and failures:
                prompt += "\n\n" + "注意：" + " ".join(RETRY_PROMPTS.get(f, "") for f in failures)

            raw = call_llm("summarize", messages=[{"role": "user", "content": prompt}])
            if not raw:
                continue
            cleaned = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()
            reason = _why_invalid(cleaned, body)
            if not reason:
                return cleaned
            failures.add(reason)
            if attempt < 2:
                print(f"  ⚠ {reason}, 重试中...")
                time.sleep(1)
        except Exception as e:
            import traceback
            traceback.print_exc()
            if attempt < 2:
                print(f"  ⚠ API 异常: {e}, 重试中...")
                time.sleep(2)
            else:
                print(f"  ⚠ API 异常: {e}")
    return None
```

**关键点**（R-08 风险闭环）：
- `call_llm` 抛 LLMCallError 被外层 `except Exception` 捕获
- except 内打印 traceback + 走原有 sleep + 进入下次 attempt（行为与旧版 client.chat.completions.create 抛异常时一致）
- 3 次都失败 → return None → run() 内调用 fallback_summarize

## 边界处理
1. **call_llm 抛 LLMCallError**：被 `except Exception` 捕获 → 重试或最终 return None（保留旧版语义）
2. **LLM 返回空字符串 ""**：`if not raw: continue` 跳过该次（与旧版一致）
3. **`<think>` 剥离后空**：cleaned 为空 → `_why_invalid` 返回 too_short → 重试
4. **3 次重试全失败**：return None
5. **traceback.print_exc()** 在每次 attempt 异常时打印（不仅最后一次）
6. **不修改 RETRY_PROMPTS / COT_LEAK_PATTERNS / _why_invalid / fallback_summarize**
7. **base_prompt 不修改**：仅在循环内拼接修复提示
8. **不修改 run() 函数**：fallback_summarize 调用逻辑不动

## 非目标
- ❌ 不重构 _why_invalid 算法
- ❌ 不重构 RETRY_PROMPTS 文案
- ❌ 不改重试上限 3 次
- ❌ 不改 sleep 间隔
- ❌ 不删除 fallback_summarize（业务兜底）
- ❌ 不改 run() 中 None 处理逻辑

## 参考
- design.md §7.3 + R-08
- 当前代码：/mnt/e/Daily/step7.py:150-192
- llm_client.py（task-02 产物）

## TDD 步骤
1. 备份 step7.py
2. 改造函数
3. 验证 import：`python3 -c "from step7 import llm_summarize; print('OK')"` (cd 到项目根)
4. dry-run：`python3 step7.py --dry-run --date <date>`
5. 故意删除 NINEROUTER_API_KEY 重测 → 期望 traceback + 3 次重试都失败 → 走 fallback_summarize

## 验收标准
| # | 验证步骤 | 通过标准 |
|---|----------|---------|
| AC-01 | `grep "from llm_client import" /mnt/e/Daily/step7.py` | 找到 |
| AC-02 | `grep -c "glm-4-flash" /mnt/e/Daily/step7.py` | 输出 0 |
| AC-03 | `grep -c "ZHIPU_API_KEY" /mnt/e/Daily/step7.py` | 输出 0 |
| AC-04 | `grep -c "open.bigmodel.cn" /mnt/e/Daily/step7.py` | 输出 0 |
| AC-05 | `grep -c "OpenAI(" /mnt/e/Daily/step7.py` | 输出 0 |
| AC-06 | `grep "for attempt in range(3)" /mnt/e/Daily/step7.py` | 找到（外层重试循环保留）|
| AC-07 | `grep "RETRY_PROMPTS\|_why_invalid\|fallback_summarize\|COT_LEAK_PATTERNS" /mnt/e/Daily/step7.py | wc -l` | 输出 ≥ 4（业务逻辑保留）|
| AC-08 | `grep "traceback.print_exc" /mnt/e/Daily/step7.py` | 至少 1 处 |
| AC-09 | `cd /mnt/e/Daily && python3 step7.py --dry-run --date 2026-06-24` 2>&1 | 不抛异常 |
| AC-10 | `grep "call_llm" /mnt/e/Daily/step7.py` | 找到对 call_llm("summarize", ...) 的调用 |
