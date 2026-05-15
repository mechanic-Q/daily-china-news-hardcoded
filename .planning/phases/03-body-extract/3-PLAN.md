---
id: "3"
phase: "3"
plan_id: "01"
wave: 1
autonomous: true
objective: "编写 step6.py 正文提取脚本"
files_modified:
  - "step6.py"
---

<objective>
Create step6.py — read 1新闻_链接.md, extract body text from each URL, output 2新闻_已审核.md.
</objective>

<tasks>

<task id="3-01-01">
<action>
Create `/mnt/e/Daily/step6.py` with `--date` and `--dry-run` CLI args. Implement 5-tier extraction strategy:
1. TRS_Editor div (人民日报/中科院)
2. article/content/article-content div (通用容器)
3. 参考消息 keyword positioning (搜索"据…报道"/"报道称"到"责任编辑")
4. &lt;p&gt; tags universal fallback
5. CCTV chromium long-paragraph extraction (>30 chars, filter copyright/icp/登录/cctv/二维码)
Source routing: static → urllib, CCTV/CNNC → chromium --dump-dom.
No body length limit.
</action>
<read_first>
- /home/lmr/.hermes/skills/productivity/daily-china-news/scripts/step56_fetch_body.py
- .planning/phases/03-body-extract/3-CONTEXT.md
- /mnt/e/Daily/step4.py (CLI arg pattern)
</read_first>
<acceptance_criteria>
- `python3 -c "import py_compile; py_compile.compile('step6.py', doraise=True)"` exits 0
- `python3 step6.py --dry-run` runs without crashing (will error if no 1新闻_链接.md)
- Syntax check passes
</acceptance_criteria>
</task>

</tasks>

<verification>
Run `python3 step6.py --dry-run` and verify:
- All article URLs processed
- Body text extracted (not empty for accessible sources)
- Failed extractions marked `[正文提取失败]`
- No crashes
</verification>

<must_haves>
1. step6.py written and working
2. Compatible with step4.py output format
3. Error handling for each URL (one failure doesn't block others)
</must_haves>
