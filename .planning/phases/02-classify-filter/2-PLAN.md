---
id: "2"
phase: "2"
plan_id: "01"
wave: 1
autonomous: true
objective: "编写 step4.py 分类筛选脚本"
files_modified:
  - "step4.py"
---

<objective>
Create step4.py — read 0新闻_粗筛.md, apply quality filter + 8-column classification + priority scoring, output 1新闻_链接.md.
</objective>

<tasks>

<task id="2-01-01">
<action>
Create `/mnt/e/Daily/step4.py` with `--date` and `--dry-run` CLI args. Parse 0新闻_粗筛.md from workdir, extract ✅ passed articles.
See step1_3.py for CLI pattern reference.
</action>
<read_first>
- /mnt/e/Daily/step1_3.py (for `--date`/`--dry-run` pattern, top ~50 lines)
</read_first>
<acceptance_criteria>
- `python3 -c "import py_compile; py_compile.compile('step4.py', doraise=True)"` exits 0
- `python3 step4.py --help 2>&1 || python3 step4.py --dry-run 2>&1` shows usage or runs without crash
</acceptance_criteria>
</task>

<task id="2-01-02">
<action>
Implement news quality filter with the agreed exclusion list:
Inherited: 春雨落、百谷生、谷雨、舞蹈诗剧、三月三、时装周、DELVAUX、世界超级摩托车、节气、立夏、立春、立冬、冬至、夏至、春分、秋分、惊蛰、芒种、白露、寒露、霜降、小满
User-added: 娱乐、明星、八卦、综艺、影视、网剧、歌星、演唱会、直播、网红、选秀、真人秀
Articles whose title matches any exclusion keyword are removed before classification.
</action>
<read_first>
- .planning/phases/02-classify-filter/2-CONTEXT.md §D-03
</read_first>
<acceptance_criteria>
- Exclusion list includes all agreed terms
- `python3 -c "from step4 import *; print(is_quality_news('谷雨养生食谱'))"` returns False
- `python3 -c "from step4 import *; print(is_quality_news('科研重大突破'))"` returns True
</acceptance_criteria>
</task>

<task id="2-01-03">
<action>
Implement 8-column classification function `classify()` using keyword matching.
Columns and keywords: 世界性科研突破(重编程/p53/诺贝尔/干细胞/iPS/发现/基因/宇宙/航天/火箭/卫星/探测/世界首次/考古), 农业(玉米/春播/农机/种业/耕地/畜牧/农业/粮食), 扶贫(扶贫/脱贫/乡村振兴/驻村书记/对口帮扶), 能源(石油/原油/核能/光伏/风电/氢能/人造太阳/核电/能源), 医疗(肿瘤/手术/疫苗/医保/健康中国/中药/医疗), 科技(机器人/AI/人工智能/无人机/专利/智能/科技/中关村/数据/算力/创新), 材料(钢铁/化工/稀土/矿产/新材料/重工), 军事(武器/军演/国防/海军/航母/战机/军事)
</action>
<read_first>
- /home/lmr/.hermes/skills/productivity/daily-china-news/scripts/classify_and_filter.py §68-89
</read_first>
<acceptance_criteria>
- `python3 -c "from step4 import *; print(classify('嫦娥六号月球采样'))"` returns '🔬 世界性科研突破'
- `python3 -c "from step4 import *; print(classify('机器人研发新突破'))"` returns '🚀 科技'
- `python3 -c "from step4 import *; print(classify('娱乐新闻'))"` returns None (handled by quality filter)
</acceptance_criteria>
</task>

<task id="2-01-04">
<imp>
Implement priority scoring, column sorting, and selection algorithm:
- priority_score: "首次/首条" +3, "自主创新/攻坚克难" +2, "我国/国产" +1
- Each column: sort by priority, pick top 1
- Total < 10: fill from remaining articles by global priority
- Source detection by URL (新华社/参考消息/央视新闻/央视军事/中科院/中核集团/人民日报)
- Output 1新闻_链接.md with format: `### [信源] 标题\nURL：链接\n`
</imp>
</task>

</tasks>

<verification>
Run `python3 step4.py --dry-run` and verify:
- All 8 columns show correct classification
- Exclusion list filters correctly
- Priority scoring produces correct ordering
- Output format matches 1新闻_链接.md spec
- No crashes or errors
</verification>

<must_haves>
1. step4.py written and syntax-valid
2. Quality filter and classification produce correct results
3. Output format compatible with downstream pipeline
</must_haves>
