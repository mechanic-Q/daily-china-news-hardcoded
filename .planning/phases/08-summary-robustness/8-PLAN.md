---
phase: 08
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - step4.py
  - step7.py
autonomous: true
requirements:
  - SUM-01
  - SUM-02
  - SUM-03
---

<objective>
修复 step4.py 的分类筛选质量（涉华过滤、负面新闻过滤、扶贫定义缩宥）和 step7.py 的摘要生成健壮性（精简 prompt、无效摘要检测回退）。
</objective>

<tasks>

<task id="1" type="execute">
<read_first>
  - step4.py (全文，EXCLUDE_TITLES、is_quality_news()、classify())
  - .planning/phases/08-summary-robustness/8-CONTEXT.md (D-01, D-02)
</read_first>
<action>
**step4.py: 新增涉华检测 + 负面关键词过滤**

1. 在 EXCLUDE_TITLES 后新增 `EXCLUDE_NEGATIVE` 列表：
   ```python
   EXCLUDE_NEGATIVE = ['审查调查', '违纪违法', '纪律审查', '监察调查', '落马', '双开', '接受审查', '涉嫌严重']
   ```

2. 在 classify() 前新增 `CHINA_KEYWORDS` 列表和 `is_china_related(title)` 函数：
   ```python
   CHINA_KEYWORDS = [
       '中国', '我国', '国产', '中华', '中方', '在华', '访华', '驻华', '对华', '涉华',
       '山东', '浙江', '江苏', '广东', '北京', '上海', '深圳', '四川', '河南', '湖北', '湖南',
       '中央', '纪委', '监委', '十四届', '全国政协', '全国人大', '国务院', '乡村振兴', '扶贫',
   ]
   
   def is_china_related(title):
       clean = title.replace('新华社', '').replace('参考消息', '').replace('央视', '').replace('人民', '')
       return any(kw in clean for kw in CHINA_KEYWORDS)
   ```

3. 修改 `is_quality_news(title)`：在现有 EXCLUDE_TITLES 检查后，增加：
   ```python
   if not is_china_related(title):
       return False
   for kw in EXCLUDE_NEGATIVE:
       if kw in title:
           return False
   ```

4. 注意：`is_china_related()` 的调用必须在 `is_quality_news()` 内部已有的 EXCLUDE_TITLES 循环之后，新增的 EXCLUDE_NEGATIVE 循环之前。
</action>
<acceptance_criteria>
  - step4.py 包含 EXCLUDE_NEGATIVE 列表（含审查调查、违纪违法等）
  - step4.py 包含 CHINA_KEYWORDS 列表
  - step4.py 包含 is_china_related(title) 函数
  - is_quality_news() 中调用 is_china_related() 和 EXCLUDE_NEGATIVE
</acceptance_criteria>
</task>

<task id="2" type="execute">
<read_first>
  - step4.py (classify() 函数)
  - .planning/phases/08-summary-robustness/8-CONTEXT.md (D-03)
</read_first>
<action>
**step4.py: 扶贫栏目关键词缩宥**

修改 classify() 函数中扶贫栏目的关键词匹配：
```python
# 修改前
if any(k in h for k in ['扶贫', '脱贫', '乡村振兴', '驻村书记', '对口帮扶', '消费扶贫', '新就业形态']):
    return '🤝 扶贫'

# 修改后
if any(k in h for k in ['扶贫', '脱贫', '对口帮扶', '消费扶贫', '驻村书记', '精准扶贫', '易地搬迁']):
    return '🤝 扶贫'
```

去掉：`'乡村振兴'`、`'新就业形态'`
新增：`'精准扶贫'`、`'易地搬迁'`
</action>
<acceptance_criteria>
  - classify() 扶贫关键词列表不再包含 '乡村振兴' 和 '新就业形态'
  - classify() 扶贫关键词列表包含 '精准扶贫' 和 '易地搬迁'
</acceptance_criteria>
</task>

<task id="3" type="execute">
<read_first>
  - step7.py (全文，llm_summarize()、fallback_summarize())
  - .planning/phases/08-summary-robustness/8-CONTEXT.md (D-04, D-05)
</read_first>
<action>
**step7.py: 精简 prompt + 无效摘要检测 + 回退**

1. 修改 `llm_summarize()` 中 prompt 文本：
   ```python
   # 修改前
   prompt = f"""用2-3句中文概括以下新闻。直接输出摘要，不要输出思考过程。
   
   标题：{title}
   正文：{body}"""
   
   # 修改后
   prompt = f"""用1-2句话精炼概括以下新闻的核心要点。简短、准确、完整，直接输出摘要。
   
   标题：{title}
   正文：{body}"""
   ```
   
   去掉 `"""用` 前面的 `f` 后的注释标记——这是实际代码修改。

2. 不修改 max_tokens（保持 300），用户明确要求不设硬上限。

3. 在 llm_summarize() 之前新增 `is_valid_summary(summary, body)` 函数：
   ```python
   def is_valid_summary(summary, body):
       if len(summary) < 20:
           return False
       if summary in body:
           return False
       if len(summary) < len(body) * 0.02 and len(summary) < 30:
           return False
       return True
   ```

4. 在 `llm_summarize()` 中 `cleaned = re.sub(...)` 之后添加验证：
   ```python
   cleaned = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()
   if cleaned and not is_valid_summary(cleaned, body):
       return None
   return cleaned if cleaned else None
   ```
   
   这样无效摘要会返回 None，触发外层的 fallback_summarize() 回退。
</action>
<acceptance_criteria>
  - llm_summarize() prompt 内容改为"1-2句话精炼概括"
  - step7.py 包含 is_valid_summary(summary, body) 函数
  - llm_summarize() 在返回前调用 is_valid_summary() 验证
  - max_tokens 保持 300
</acceptance_criteria>
</task>

<task id="4" type="execute">
<read_first>
  - step4.py (task 1-2 修改后版本)
  - step7.py (task 3 修改后版本)
</read_first>
<action>
**E2E 验证：用 2026-05-17 数据测试 step4 + step7**

1. 运行 `python3 step4.py --dry-run --date 2026-05-17`
   - 确认输出不包含"审查调查"相关新闻（被 EXCLUDE_NEGATIVE 过滤）
   - 确认输出不包含纯外国新闻（被 is_china_related 过滤）
   - 确认扶贫栏目不含"乡村振兴"类新闻
   - 需评估过滤后的新闻条数变化：当前是 10 条，过滤后应为
     step4 过滤结果会直接影响后续 step7 输入

2. 运行 `python3 step7.py --date 2026-05-17`
   - 确认所有摘要长度 > 20字
   - 确认无"由于霍"类截断
   - 确认摘要更精简

3. 运行完整管道 `python3 step8.py --date 2026-05-17`
   - 确认 HTML/PNG 正常生成
   
**注意**：由于 step4 过滤逻辑变化，step7/step8 的输入新闻数量和栏目分布可能与之前不同——这是预期行为。
</action>
<acceptance_criteria>
  - step4 --dry-run 不显示被负面关键词过滤的新闻
  - step4 --dry-run 不显示纯外国新闻
  - step4 --dry-run 扶贫栏目不含"乡村振兴"类新闻
  - step7 运行后所有摘要 > 20字
  - step7 运行后无截断片段摘要
  - step8 运行后 HTML/PNG 正常生成
</acceptance_criteria>
</task>

</tasks>

<verification>
1. `python3 step4.py --dry-run --date 2026-05-17` — 确认涉华/负面/扶贫缩宥生效
2. `python3 step7.py --date 2026-05-17` — 确认摘要质量和回退机制
3. `python3 step8.py --date 2026-05-17` — 确认端到端正常
4. 检查 `3新闻_概述.md` — 确认所有摘要 > 20字、无截断
</verification>

<success_criteria>
- step4 过滤：6条纯外国新闻 + "王晓东接受审查调查" 被正确过滤
- 扶贫栏目：不含"乡村振兴"类新闻
- 所有 API 摘要有效（>20字、非正文片段），无效时走规则回退
- 摘要长度明显缩短（1-2句话）
- E2E 管道正常运行
</success_criteria>

<must_haves>
- is_china_related() 正确排除纯外国新闻
- EXCLUDE_NEGATIVE 正确排除审查调查类新闻
- 扶贫关键词列表不再包含"乡村振兴"
- 摘要 prompt 引导 LLM 精简输出
- is_valid_summary() 检测无效摘要并触发回退
</must_haves>
