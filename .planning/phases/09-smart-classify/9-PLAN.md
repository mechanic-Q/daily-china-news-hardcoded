---
phase: 09
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - step4.py
autonomous: true
requirements: []
---

<objective>
用 C+D 混合方案重写 step4.py 的分类逻辑：关键词加权评分替代线性优先级，高置信度直接归类（零 API），低置信度 LLM 批量裁决。同时 priority_score 按栏目差异化。

</objective>

<tasks>

<task id="1" type="execute">
<read_first>
  - step4.py (classify() 和 priority_score() 函数，全文)
  - .planning/phases/09-smart-classify/9-CONTEXT.md (所有决策)
</read_first>
<action>
**step4.py: 新增 CATEGORY_KEYWORDS 词典 + score_all_categories()**

1. 删除旧的 `classify()` 函数（第 143-170 行）和旧的 `priority_score()` 函数（第 173-181 行）。

2. 在 `def is_quality_news(title):` 之后新增 `CATEGORY_KEYWORDS` 词典：

```python
CATEGORY_KEYWORDS = {
    '🔬 世界性科研突破': {
        '诺贝尔': 5, '世界首次': 5, '全球首次': 5, '首次发现': 5,
        '基因': 4, '量子': 4, '干细胞': 4, 'iPS': 4, '重编程': 4,
        'p53': 4, '化学小分子': 4, '考古发现': 4,
        '航天': 3, '卫星': 3, '探测': 3, '嫦娥': 3, '天宫': 3,
        '火星': 3, '月球': 3, '宇宙': 3,
    },
    '🌾 农业': {
        '农业': 3, '粮食': 3, '农产品': 3, '农田': 3,
        '玉米': 2, '小麦': 2, '春播': 2, '春耕': 2, '育秧': 2,
        '农机': 2, '种业': 2, '耕地': 2, '畜牧': 2,
        '治沙': 2, '农村': 1,
    },
    '🤝 扶贫': {
        '精准扶贫': 5, '易地搬迁': 4, '扶贫': 4, '脱贫': 4,
        '对口帮扶': 3, '消费扶贫': 3, '驻村书记': 3,
    },
    '⚡ 能源': {
        '核电': 4, '核能': 4, '人造太阳': 4,
        '光伏': 3, '风电': 3, '氢能': 3, '能源': 3,
        '电力': 2, '石油': 2, '原油': 2, '油价': 2, '燃料': 2,
    },
    '🏥 医疗': {
        '医疗': 3, '疫苗': 3, '肿瘤': 3, '手术': 3, '医保': 3,
        '药品监管': 3, '健康管理': 2, '中药': 2, '健康中国': 2,
    },
    '🚀 科技': {
        '人工智能': 3, 'AI': 3, '机器人': 3, '无人机': 3,
        '算力': 3, '科创': 2, '数字': 2, '数据': 2, '智能': 2,
        '科技': 2, '创新': 1, '生产线': 1,
    },
    '🧱 材料': {
        '新材料': 4, '稀土': 3, '钢铁': 3, '化工': 3,
        '矿产': 3, '重工': 2, '造船': 2,
    },
    '🎖️ 军事': {
        '火箭炮': 4, '导弹': 4, '航母': 4, '战机': 4, '军演': 4,
        '军区': 3, '军事': 3, '军队': 3, '海军': 3, '国防': 3,
        '官兵': 2, '训练': 2,
    },
}
```

3. 在 `CATEGORY_KEYWORDS` 之后新增 `score_all_categories(title)`：

```python
def score_all_categories(title):
    scores = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        s = sum(w for kw, w in keywords.items() if kw in title)
        if s > 0:
            scores[cat] = s
    return scores
```

关键改动说明：
- D-04: `火箭` 从科研突破中移除（prev:"箭啸昆仑"误分类），`火箭炮` 只在军事(权重4)
- D-05: `发现` 从科研突破中移除（太泛），改为 `考古发现`(4)
- D-03: 科研突破关键词权重更高(3-5)，军事训练/官兵权重更低(2)
</action>
<acceptance_criteria>
  - step4.py 包含 CATEGORY_KEYWORDS 词典（8栏目 × 权重键值对）
  - step4.py 包含 score_all_categories(title) 函数
  - '火箭' 不在科研突破关键词中
  - '火箭炮' 只在军事关键词中
  - '发现' 不在科研突破关键词中
  - '考古发现' 在科研突破关键词中
  - 旧 classify() 函数已删除
  - 旧 priority_score() 函数已删除
</acceptance_criteria>
</task>

<task id="2" type="execute">
<read_first>
  - step4.py (task 1 修改后版本，llm_is_china_related() 作为参考格式)
  - .planning/phases/09-smart-classify/9-CONTEXT.md (D-08, D-09, D-10)
</read_first>
<action>
**step4.py: 新增 llm_classify_batch() 批量 LLM 裁决**

在 `score_all_categories()` 之后新增 `llm_classify_batch()`：

```python
def llm_classify_batch(articles, batch_size=5):
    """批量发送低置信度文章给 LLM 分类，返回 {title: category}"""
    import os
    from openai import OpenAI
    api_key = os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        return {}

    cat_names = list(CATEGORY_KEYWORDS.keys())
    results = {}

    for i in range(0, len(articles), batch_size):
        batch = articles[i:i+batch_size]
        prompt = "将以下新闻标题归入最贴切的栏目（只能选一个）。\n"
        prompt += "栏目：" + "、".join(cat_names) + "\n\n"
        prompt += "输出格式（每行一条）：序号|栏目名\n\n"
        for j, a in enumerate(batch):
            prompt += f"{j+1}. {a['title']}\n"

        try:
            client = OpenAI(base_url="https://api.minimax.chat/v1", api_key=api_key)
            resp = client.chat.completions.create(
                model="minimax-m2.7",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1, max_tokens=200, timeout=30,
            )
            text = resp.choices[0].message.content.strip()
            for line in text.split("\n"):
                parts = line.strip().split("|")
                if len(parts) == 2:
                    try:
                        idx = int(parts[0].strip()) - 1
                        cat = parts[1].strip()
                        if 0 <= idx < len(batch) and cat in CATEGORY_KEYWORDS:
                            results[batch[idx]['title']] = cat
                    except ValueError:
                        pass
        except Exception as e:
            print(f"  ⚠ LLM分类失败: {e}")

    return results
```

注意：
- 输入是 articles 列表（不是 title 字符串列表），这样可以根据得分回退
- LLM 返回格式要求："序号|栏目名"
- 解析失败的条目不加入 results，由调用方决定回退策略
</action>
<acceptance_criteria>
  - step4.py 包含 llm_classify_batch(articles, batch_size=5) 函数
  - 函数接受 articles 列表（含 title 字段）
  - 使用 MiniMax M2.7 API（OpenAI SDK）
  - 返回 {title: category} 字典
  - API 失败时不抛出异常，返回空字典
</acceptance_criteria>
</task>

<task id="3" type="execute">
<read_first>
  - step4.py (task 1-2 修改后版本)
  - .planning/phases/09-smart-classify/9-CONTEXT.md (D-06, D-07, D-11, D-12, D-13)
</read_first>
<action>
**step4.py: 替换 priority_score() 为差异化版本**

在 `llm_classify_batch()` 之后新增：

```python
def priority_score(title, category):
    score = 0
    for kw, w in [('世界首次', 5), ('全球首个', 5), ('首次', 3),
                   ('自主创新', 2), ('攻坚克难', 2), ('突破', 2),
                   ('我国', 1), ('国产', 1)]:
        if kw in title:
            score += w
    if category == '🔬 世界性科研突破':
        has_breakthrough = any(k in title for k in
            ['首次', '突破', '发现', '全球', '世界', '诺贝尔', '首台', '首个'])
        if not has_breakthrough:
            score = max(0, score - 2)
    return score
```
</action>
<acceptance_criteria>
  - step4.py 包含 priority_score(title, category) 函数（两个参数）
  - 科研突破栏目如果没有"首次/突破/发现/全球"等信号，基础分减 2
  - 其他栏目维持通用加分规则
</acceptance_criteria>
</task>

<task id="4" type="execute">
<read_first>
  - step4.py (task 1-3 修改后版本，run() 函数全文)
  - .planning/phases/09-smart-classify/9-CONTEXT.md (D-06, D-07, D-10, D-13)
</read_first>
<action>
**step4.py: 重写 run() 中的分类流程**

找到 run() 函数中的这段代码（约第 243-247 行）：

```python
for a in articles:
    cat = classify(a['title'])
    if cat and cat in classified:
        a['priority'] = priority_score(a['title'])
        classified[cat].append(a)
```

替换为 C+D 混合分类流程：

```python
# Phase 1: 关键词评分 → 分离高置信度 / 低置信度
high_confidence = {}
low_confidence = []

for a in articles:
    scores = score_all_categories(a['title'])
    if scores:
        sorted_cats = sorted(scores.items(), key=lambda x: -x[1])
        best_cat, best_score = sorted_cats[0]
        second_score = sorted_cats[1][1] if len(sorted_cats) > 1 else 0
        if best_score >= 3 and (best_score - second_score) >= 2:
            high_confidence[a['title']] = best_cat
        else:
            low_confidence.append(a)
    else:
        low_confidence.append(a)

# Phase 2: LLM 批量裁决低置信度
llm_results = {}
if low_confidence:
    print(f"  关键词高置信度: {len(high_confidence)}条, LLM裁决: {len(low_confidence)}条")
    llm_results = llm_classify_batch(low_confidence)

# Phase 3: 合并结果，归入栏目
for a in articles:
    cat = high_confidence.get(a['title'])
    if not cat:
        cat = llm_results.get(a['title'])
    if not cat and score_all_categories(a['title']):
        scores = score_all_categories(a['title'])
        cat = max(scores, key=scores.get)
    if cat and cat in classified:
        a['category'] = cat
        a['priority'] = priority_score(a['title'], cat)
        classified[cat].append(a)
```

同时修改 remaining 补选逻辑（约第 280 行）：
```python
# 修改前
pick['column'] = classify(pick['title'])

# 修改后
pick['column'] = pick.get('category', '🚀 科技')
```
</action>
<acceptance_criteria>
  - run() 中使用 score_all_categories() 评分
  - 高置信度（最高分 ≥ 3 且领先 ≥ 2）直接归类
  - 低置信度送 llm_classify_batch()
  - LLM 失败时有部分得分的取最高分，全 0 的丢弃
  - remaining 补选时使用 a['category'] 而不是 classify()
</acceptance_criteria>
</task>

<task id="5" type="execute">
<read_first>
  - step4.py (task 1-4 修改后的完整版本)
  - .planning/phases/09-smart-classify/9-CONTEXT.md (D-12: 先上线再调，dry-run 人工确认)
</read_first>
<action>
**E2E dry-run 验证**

1. 运行 `python3 step4.py --dry-run --date 2026-05-17`，检查：
   - 无运行时错误
   - "箭啸喀喇昆仑——新疆军区某团火箭炮分队训练影像" 被正确归入 🎖️ 军事
   - "航行警告：南海部分海域进行火箭发射，禁止驶入" 被正确归入 🎖️ 军事
   - 精选总数 ≥ 10 条
   - 扶贫栏目不含"乡村振兴"类新闻
   - LLM 调用次数合理（主要高置信度直接归类）

2. 如果分类结果明显有问题，退回调整 CATEGORY_KEYWORDS 权重后再试

3. 运行完整管道：
   ```bash
   python3 step4.py --date 2026-05-17
   python3 step7.py --date 2026-05-17
   python3 step8.py --date 2026-05-17
   ```
   确认所有 step 正常完成，HTML/PNG 正常生成

4. 查看 `3新闻_概述.md`，确认：
   - 各栏目新闻分类合理
   - 摘要质量可接受
</action>
<acceptance_criteria>
  - dry-run 无 Python 错误
  - "箭啸喀喇昆仑" 归入 🎖️ 军事
  - 精选 ≥ 10 条
  - step7 + step8 全流程正常
</acceptance_criteria>
</task>

</tasks>

<verification>
1. `python3 step4.py --dry-run --date 2026-05-17` — 确认分类正确、精选 ≥ 10 条
2. `python3 step7.py --date 2026-05-17` — 确认摘要正常
3. `python3 step8.py --date 2026-05-17` — 确认 HTML/PNG 正常生成
</verification>

<success_criteria>
- "箭啸喀喇昆仑" 不再归入科研突破，正确归入军事
- "航行警告：南海部分海域进行火箭发射" 不再归入科研突破，正确归入军事
- 科研突破栏目新闻有明确科研属性（基因/量子/诺贝尔/航天等）
- 精选 ≥ 10 条新闻
- LLM 调用次数 ≤ 20 次（大部分高置信度直接归类）
</success_criteria>

<must_haves>
- score_all_categories() 替换旧的线性 classify()
- 高置信度（≥3 且领先 ≥2）直接归类，不调 LLM
- llm_classify_batch() 批量 LLM 裁决（5条一批）
- priority_score 按栏目差异化（科研突破标准更高）
- run() 中 C+D 混合流程正确实现
</must_haves>
