---
id: task-05
author: lmr
created_at: 2026-06-24 19:40:00
title: 改造 step4.py:llm_is_china_related 为 call_llm("china-relevance", ...)
priority: P0
depends_on: [task-01, task-02]
blocks: [task-09]
requirement_ids: [FR-04]
decision_ids: [D-007@v1, D-011@v1]
allowed_paths:
  - /mnt/e/Daily/step4.py
---

# task-05: 改造 step4.py:llm_is_china_related

## 修改文件
- 修改 `/mnt/e/Daily/step4.py`（仅 llm_is_china_related 函数及顶部 import）

## 覆盖来源
- Requirements: FR-04（step4.py 2 处 LLM 调用替换）
- Decisions: D-007@v1（traceback 可见，保留 fallback），D-011@v1（temperature 0.7）

## 实现要求
1. 顶部 import 区追加：`from llm_client import call_llm, LLMCallError`
2. 替换 `llm_is_china_related(title)` 函数为新版（见接口定义）
3. **保留**原 prompt 文本（"判断以下新闻标题..."），仅改 LLM 调用方式
4. **保留**返回值语义：True / False
5. **保留**外层兜底逻辑：异常时返回 False（不是 raise，因为上游 is_china_related 期待 bool）

## 接口定义

新版本：

```python
def llm_is_china_related(title):
    """LLM 涉华兜底判定，失败时返回 False（保留现有 fallback 语义）。"""
    try:
        from llm_client import call_llm
        ans = call_llm(
            "china-relevance",
            messages=[{"role": "user", "content": f"判断以下新闻标题内容主体上是否直接与中国相关（报道或讨论中国事务/中国人/中国企业/中国政府/中美关系等）。只回答\"是\"或\"否\"。\n\n标题：{title}"}],
        )
        return ans.strip().startswith("是")
    except Exception:
        import traceback
        traceback.print_exc()
        return False
```

**对比**：

| 旧版（step4.py:79-95） | 新版 |
|------|------|
| 读 MINIMAX_API_KEY | 不读（call_llm 处理）|
| OpenAI(base_url=minimax..., api_key=...) | 不构造 client |
| model="minimax-m2.7" | call_llm("china-relevance", ...) |
| temperature=0.1, max_tokens=10, timeout=15 | 由 yaml call_sites.china-relevance 提供 |
| `except Exception: return False` 静默 | except 打 traceback + return False |

## 边界处理
1. **call_llm 抛 LLMCallError**：被 `except Exception` 捕获 → return False（保留兜底）
2. **call_llm 抛 ConfigError**：被 `except Exception` 捕获 → return False（避免启动崩溃）
3. **空标题**：`title=""` 不特殊处理，由 LLM 决定（与现有行为一致）
4. **响应非"是"/"否"**：`startswith("是")` 严格匹配，其他返回值视为"否"（与现有一致）
5. **traceback.print_exc()** 打印到 stderr（不影响 stdout 业务输出）
6. **不修改 is_china_source / is_china_related**：这两个上游函数不变
7. **保留 ans.strip()**：防止 LLM 返回带空白字符
8. **import 位置**：顶部新增 `from llm_client import call_llm` —— 注意 step4.py 顶部已有 import 集中区，加在那里；但 except 内的 `import traceback` 保留为局部 import 避免顶部冗余

## 非目标
- ❌ 不动 is_china_related（关键词匹配主路径）
- ❌ 不动 is_china_source（domain 白名单）
- ❌ 不改 prompt 文本
- ❌ 不删除其他 LLM 调用点（llm_classify_single 由 task-06 处理）
- ❌ 不引入新 import openai

## 参考
- design.md §7.3 调用点替换表
- 当前代码：/mnt/e/Daily/step4.py:79-95
- llm_client.py（task-02 产物）

## TDD 步骤
1. 备份 step4.py
2. 改造函数
3. 验证 import：`python3 -c "import step4; print('OK')"` (cd 到项目根)
4. dry-run：`python3 step4.py --dry-run --date <date>`
5. 故意删除 NINEROUTER_API_KEY 重测 → 期望 traceback + 流水线继续（is_china_related 返回 False）

## 验收标准
| # | 验证步骤 | 通过标准 |
|---|----------|---------|
| AC-01 | `grep "from llm_client import" /mnt/e/Daily/step4.py` | 找到 call_llm import |
| AC-02 | `grep -c "minimax-m2.7" /mnt/e/Daily/step4.py` | 输出 0（旧 model 字符串已移除）|
| AC-03 | `grep -c "MINIMAX_API_KEY" /mnt/e/Daily/step4.py` | 输出 0（已不直接读 key）|
| AC-04 | `grep -c "api.minimax.chat" /mnt/e/Daily/step4.py` | 输出 0（已不直接构造 client）|
| AC-05 | `grep -A3 "def llm_is_china_related" /mnt/e/Daily/step4.py | grep "call_llm"` | 函数体内调用 call_llm |
| AC-06 | `grep "traceback.print_exc" /mnt/e/Daily/step4.py` | 至少 1 处（D-007）|
| AC-07 | `cd /mnt/e/Daily && python3 -c "from step4 import llm_is_china_related; print(type(llm_is_china_related('美国签证政策')).__name__)"` | 输出 bool |
| AC-08 | `cd /mnt/e/Daily && python3 step4.py --dry-run --date 2026-06-24` 2>&1 | 不抛异常 |
