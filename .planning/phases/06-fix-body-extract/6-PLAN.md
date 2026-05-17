---
wave: 1
depends_on: []
files_modified:
  - step6.py
requirements: [EXT-01, EXT-02, EXT-03, EXT-04, EXT-05]
autonomous: true
---

# Plan 1: 正文提取清洗增强

## Goal

修复 step6.py 正文提取中的5类污染：JS代码混入、CSS样式混入、HTML实体未解码、视频播放器标记/UI文字、段落重复。

## must_haves

- 提取结果不包含 JavaScript 代码（无 `var `、`function(`、`$( `）
- 提取结果不包含 CSS 样式（无 `font-family`、`margin:`、`{`）
- HTML实体已解码（无 `&ldquo;`、`&rdquo;`、`&nbsp;`）
- 视频播放器标记和UI文字已清理
- 人民日报 `paper.people.com.cn` 页面能提取到正文（而非整页CSS/导航）
- 重复段落已去重
- 输出格式不变，下游 step7.py 无需修改
- 原本成功的文章（如新疆军区火箭炮训练）仍然成功提取

---

## Task 1: 预处理 — 剥离 script/style 块

<read_first>
- step6.py（当前 extract_body 函数）
</read_first>

<action>

在 step6.py 中添加 `_preprocess_html(html)` 函数：

```python
def _preprocess_html(html):
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.I | re.S)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.I | re.S)
    return html
```

在 `extract_body()` 函数体第一行调用：`html = _preprocess_html(html)`

确保在所有5层策略链执行前调用，使策略链处理的 HTML 已无 script/style 内容。
</action>

<acceptance_criteria>
- step6.py 包含 `_preprocess_html` 函数定义
- `extract_body()` 函数第一行调用 `_preprocess_html(html)`
- 用包含 `<script>var x=1;</script>` 的 HTML 测试，提取结果不含 `var x=1`
- 用包含 `<style>body{margin:0}</style>` 的 HTML 测试，提取结果不含 `body{margin:0}`
- 无 script/style 的正常 HTML 提取不受影响
</acceptance_criteria>

---

## Task 2: 人民日报 #ozoom 提取策略

<read_first>
- step6.py（当前 extract_body 函数层2的通用div搜索部分）
- /mnt/e/每日新中国/2026-05-17/2新闻_已审核.md（人民日报污染样本，分析 ozoom 结构）
</read_first>

<action>

在 `extract_body()` 的层2通用div搜索 pattern 列表中，**末尾**新增：

```python
r'<div[^>]*id=["\']ozoom["\'][^>]*>(.*?)</div>',
```

注意 `#ozoom` 内可能有嵌套 div。如果上述正则匹配结果长度 < 100 字符（说明被嵌套 div 截断），回退到：定位 `<div id="ozoom">` 位置后，从中提取所有 `<p>` 标签内容。

```python
# 回退方案伪代码：
ozoom_start = html.find('id="ozoom"') or html.find("id='ozoom'")
if ozoom_start > 0:
    ozoom_section = html[ozoom_start:ozoom_start + 5000]  # 取5k字符内容
    paras = re.findall(r'<p[^>]*>(.*?)</p>', ozoom_section, re.S)
```

保持现有 pattern 顺序不变，只在末尾追加。
</action>

<acceptance_criteria>
- `extract_body()` 层2 pattern 列表新增 ozoom id 匹配 pattern
- 人民日报 `paper.people.com.cn` 文章正文不再包含 `font-family: '宋体'` 等 CSS 规则
- 人民日报文章正文不再包含日报/周报/杂志导航菜单
- 其他信源提取不受影响（layer 2提前匹配的 pattern 优先级不变）
</acceptance_criteria>

---

## Task 3: 后处理管道（实体解码 + 视频标记清理 + 去重）

<read_first>
- step6.py（当前 fetch_and_extract 函数）
- step6.py（当前文件顶部 import 列表）
- /mnt/e/每日新中国/2026-05-17/2新闻_已审核.md（央视新闻视频标记样本，查看 `[!--begin:htmlVideoCode--]`、`静音(m)全屏(f)` 等）
</read_first>

<action>

### 3a. 添加 import

文件顶部新增：`import html`

### 3b. 新增 `_postprocess_text(text)` 函数

3步顺序执行：

**Step 1 — HTML实体解码：**
```python
text = html.unescape(text)
```

**Step 2 — 视频标记/播放器UI清理：**
```python
# 视频嵌入标记块
text = re.sub(r'\[!--begin:htmlVideoCode--\].*?\[!--end:htmlVideoCode--\]', '', text, flags=re.S)
# 播放器UI文字
ui_patterns = [
    r'静音\(m\)', r'全屏\(f\)',
    r'ADCountdown\s*(Time|时间)?', r'广告关闭广告',
    r'正在加载[\s\S]*?视频播放器', r'播放视频播放\([pP]\)',
    r'播放\([pP]\)', r'当前时间[\s\S]*?时长[\s\S]*?\d+:\d+',
    r'媒体流类型[\s\S]*?高清', r'高清画质超清高清',
    r'加载完成:\s*\d+%-?\d*:\d*',
    r'您上次观看至[\s\S]*?已为您续播',
    r'尊贵的用户[\s\S]*?跳过广告',
]
for pat in ui_patterns:
    text = re.sub(pat, '', text, flags=re.S)
# 清理多余空白行
text = re.sub(r'\n{3,}', '\n\n', text)
text = re.sub(r'\s{2,}', ' ', text).strip()
```

**Step 3 — 段落去重：**
```python
import html.parser  # 已通过 import html 获得
sentences = re.split(r'(?<=[。；])', text)  # 按句号/分号分割
deduped = []
for s in sentences:
    s_stripped = s.strip()
    if s_stripped and (not deduped or s_stripped != deduped[-1].strip()):
        deduped.append(s)
text = ''.join(deduped)
```

### 3c. 在 `fetch_and_extract()` 中调用

在 `extract_body()` 返回后、return 前插入：

```python
body = _postprocess_text(body)
```

只在 body 非 None 时调用（提取成功的文章才做后处理）。

</action>

<acceptance_criteria>
- step6.py 文件顶部包含 `import html`
- step6.py 包含 `_postprocess_text` 函数
- `fetch_and_extract()` 在 `extract_body()` 返回后调用 `_postprocess_text(body)`
- 输入含 `&ldquo;` 的文本，输出为 `"`
- 输入含 `&nbsp;` 的文本，输出为空格
- 输入含 `[!--begin:htmlVideoCode--]xxx[!--end:htmlVideoCode--]` 的文本，该标记块被移除
- 输入含 `静音(m)全屏(f)` 的文本，该播放器UI文字被移除
- 输入含「天舟十号。天舟十号。」的文本（连续重复），输出为「天舟十号。」
- `body` 为 None 时不调用 `_postprocess_text`
</acceptance_criteria>

---

## Task 4: 污染检测 + 重试回退

<read_first>
- step6.py（当前 fetch_and_extract 函数）
</read_first>

<action>

### 4a. 新增 `_is_contaminated(text)` 函数

任一条件匹配即为污染：

```python
def _is_contaminated(text):
    css_signals = ['font-family', 'margin:', 'padding:', 'line-height:', 'border-spacing']
    js_signals = ['var ih =', 'var p =', 'document.getElementById', 'console.log']
    nav_signals = ['日报', '周报', '杂志']  # 三者连续出现
    for s in css_signals:
        if s in text: return True
    for s in js_signals:
        if s in text: return True
    # 导航垃圾：日报、周报、杂志在100字符内连续出现
    rl_comb = all(kw in text for kw in nav_signals)
    if rl_comb:
        positions = [text.index(kw) for kw in nav_signals]
        if max(positions) - min(positions) < 100:
            return True
    return False
```

### 4b. 新增 `_aggressive_clean(html)` 函数

在 `_preprocess_html` 基础上额外处理：

```python
def _aggressive_clean(html):
    html = _preprocess_html(html)
    html = re.sub(r'<!--.*?-->', '', html, flags=re.S)  # HTML注释
    html = re.sub(r'\sstyle="[^"]*"', '', html, flags=re.I)  # inline style
    return html
```

### 4c. 修改 `fetch_and_extract()` 实现重试

```python
def fetch_and_extract(url, title):
    try:
        if needs_chromium(url):
            html = chromium_dom(url)
        else:
            html = fetch_html_static(url)
        if not html or len(html) < 500:
            return None, "页面过短或为空"

        body = extract_body(html, url)
        if body:
            body = _postprocess_text(body)
            if _is_contaminated(body):
                cleaned_html = _aggressive_clean(html)
                body2 = extract_body(cleaned_html, url)
                if body2:
                    body2 = _postprocess_text(body2)
                    if not _is_contaminated(body2):
                        return body2, None
                return None, "提取结果被污染"
            return body, None
        return None, "未找到正文区域"
    except Exception as e:
        return None, str(e)
```

</action>

<acceptance_criteria>
- step6.py 包含 `_is_contaminated` 函数
- step6.py 包含 `_aggressive_clean` 函数
- `fetch_and_extract()` 实现了 提取→后处理→检测→重试→再检测→返回 的流程
- 含 CSS 规则（如 `font-family`）的文本被检测为污染
- 含 JS 代码（如 `var ih =`）的文本被检测为污染
- 重试后仍污染时返回 `None` + 错误描述 `"提取结果被污染"`
- 成功时保持现有返回格式 `(body, None)`
</acceptance_criteria>

---

## Task 5: 用 2026-05-17 数据端到端验证

<read_first>
- step6.py（修改后的完整文件）
- /mnt/e/每日新中国/2026-05-17/1新闻_链接.md（输入）
- /mnt/e/每日新中国/2026-05-17/2新闻_已审核.md（旧输出，对比用）
</read_first>

<action>

运行命令：
```bash
cd /mnt/e/Daily && python3 step6.py --date 2026-05-17
```

检查输出文件 `/mnt/e/每日新中国/2026-05-17/2新闻_已审核.md`：

逐条验证：
1. **参考消息（DNA进化）** — 正文不含 `var ih`、`var p =`、`document.getElementById`
2. **央视新闻（天宫日志）** — 正文不含 `&ldquo;`、`[!--htmlVideoCode--]`、`静音(m)`、`全屏(f)`；无重复段落
3. **央视军事（火箭禁止驶入）** — 仍为 `[正文提取失败]`
4. **央视军事（火箭炮训练）** — 仍成功提取，正文长度变化在合理范围内
5. **人民日报（贵州农业）** — 正文不含 `font-family: '宋体'`、`日报`+`周报`+`杂志`
6. **人民日报（能源强国）** — 正文不含 `font-family`、导航菜单；无重复段落

如果不通过，根据失败原因调整对应的 Task 代码。
</action>

<acceptance_criteria>
- `python3 step6.py --date 2026-05-17` 执行成功（exit code 0）
- 输出文件格式不变（`## 【信源】标题` / `来源：` / `正文：`）
- 所有参考消息文章正文不含 JS 代码污染
- 所有央视新闻文章正文不含视频标记/播放器UI/重复段落
- 所有人民日报文章正文不含 CSS 样式/导航菜单
- 原本成功的正文提取仍然成功
- 原本失败的正文提取仍然失败（行为一致）
</acceptance_criteria>

---

## Verification Criteria

- [x] 5项 EXT 需求全部覆盖（EXT-01 到 EXT-05）
- [x] 所有 Task 有可验证的 acceptance_criteria
- [x] 单文件修改（step6.py）
- [x] 输出格式不变，下游脚本不感知
- [x] 有测试数据（2026-05-17）可验证
