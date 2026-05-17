# Phase 5: 报纸渲染 - Research

**Researched:** 2026-05-17
**Domain:** Markdown→JSON→HTML→PNG 报纸渲染管道
**Confidence:** HIGH

## Summary

Phase 5 的核心任务是从 `3新闻_概述.md` 生成可视化报纸 PNG。整个管道由 `step8.py` 独立完成：解析 Markdown → 构造 JSON payload → 渲染 1080px 双栏 HTML → chromium headless 截图 → Pillow 裁白边。附加交付 `run_all.sh` 串联全管道（step1_3→step4→step6→step7→step8）。

参考实现 `render_newspaper.py`（820行）提供了完整的设计蓝图——JSON 规范化逻辑（`normalize_payload`）、中文期号计算（`_chinese_ordinal`）、双栏 HTML 模板（`build_html` 第一版，使用 grid 布局）、chromium 截图参数（`screenshot_with_browser`）和 Pillow 裁白边算法（`crop_bottom_whitespace`）。step8.py 需要移植这些设计思路，但将输入从 JSON 文件改为 Markdown 文件，并加入动态双栏平衡算法。

**Primary recommendation:** 从 render_newspaper.py 提取 CSS 样式、截图逻辑和裁白边算法；从 step7.py 的输出格式推导 Markdown 解析器；用贪心策略实现动态双栏平衡。step8.py 预计 400-500 行。

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

1. **D-01 架构**: step8.py 独立全流程（解析MD→构造JSON→渲染HTML→截图PNG），不调用 render_newspaper.py，但提取设计思路
2. **D-02 浏览器截图**: chromium headless，`--headless=new --disable-gpu --force-device-scale-factor=2`，宽度 1080px，高度超长值后 Pillow 裁白边
3. **D-03 报头信息**: 报纸名"紫音简报"，期号从 2026-04-19 起算，日期格式 `YYYY年M月D日 星期X`，页脚"Mobile Brief"印章
4. **D-04 动态双栏平衡**: 按摘要字数贪心分配 8 栏目到左/右栏，目标左右高度接近
5. **D-05 HTML 视觉风格**: 沿用 render_newspaper.py 报纸风格（1080px宽、仿纸背景、墨色文字、朱砂红点缀、双栏 grid + 2px 分隔线、内联 CSS）
6. **D-06 run_all.sh**: 按序调用 step1_3→step4→step6→step7→step8，`--date YYYY-MM-DD`（必填），`--dry-run`（可选），失败即停

### the agent's Discretion

- JSON payload 的具体字段命名（参考 render_newspaper.py 的 `columns` 结构）
- Markdown→JSON 的解析细节（标题匹配、空栏目处理、弯引号规范化）
- 动态平衡算法的具体实现（贪心/DP）
- CSS 细节（字号、行高、间距）——沿用原 skill 即可
- `--dry-run` 在 step8 中的具体行为
- Pillow 裁白边的 padding 参数
- step8.py 的具体行数预估和函数拆分

### Deferred Ideas (OUT OF SCOPE)

None
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REND-01 | 报纸渲染 — 从 3新闻_概述.md 生成可视化报纸 | render_newspaper.py 参考实现完整分析；chromium headless 截图方案已验证；Pillow 裁白边算法已提取；动态双栏平衡方案已设计 |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Markdown 解析 | Python 脚本层 | — | 纯文本处理，无外部依赖 |
| JSON payload 构造 | Python 脚本层 | — | 数据结构转换 |
| HTML 模板渲染 | Python 脚本层 | — | f-string 内联 CSS，无模板引擎 |
| 浏览器截图 | chromium headless | — | 外部进程调用，subprocess.run |
| 图片裁剪 | Pillow | — | Python 库，纯本地操作 |
| 管道串联 | bash 脚本 | — | run_all.sh 顺序调用各 step |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pillow | 12.1.1 (installed) | 裁白边 (ImageChops.difference) | render_newspaper.py 已用，项目唯一图片处理需求 [VERIFIED: PyPI registry] |
| chromium | 147.0.7727.116 snap | headless 截图 | step6.py 已在用同一 binary，零额外安装 [VERIFIED: local install] |
| Python stdlib | 3.12.3 | argparse/subprocess/re/html/json/datetime | 所有 step 脚本的统一依赖 |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathlib | stdlib | 文件路径操作 | 所有文件 I/O |
| html (stdlib) | stdlib | HTML 转义 | `html.escape()` 防 XSS |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| chromium CLI 截图 | Playwright full_page=True | SKILL.md Step 11 用 Playwright，但 CONTEXT D-02 已锁定 chromium CLI 方案，且 step8 需独立自足 |
| Pillow ImageChops | numpy pixel scan | ImageChops.getbbox() 更简洁，render_newspaper.py 已验证 |

**Installation:**
```bash
# 无需安装新包 — Pillow 12.1.1 已在系统 Python 中
# chromium 已在 /snap/bin/chromium
pip install Pillow  # 仅在环境中缺少时执行
```

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| Pillow | PyPI | 15+ yrs | 50M+/mo | github.com/python-pillow/Pillow | [OK] | Approved |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
3新闻_概述.md (step7 输出)
       │
       ▼
  ┌─────────────┐
  │ parse_md()  │  正则解析 ##栏目 + ###标题 + 摘要段落
  │             │  → List[Section{heading, bullets}]
  └─────┬───────┘
        │
        ▼
  ┌─────────────┐
  │ build_json()│  期号计算 + 日期格式化 + 动态双栏平衡
  │             │  → payload dict (columns 结构)
  └─────┬───────┘
        │
        ▼
  ┌─────────────┐
  │ build_html()│  f-string 模板，内联 CSS，1080px 双栏 grid
  │             │  → HTML 字符串 → 写入 .html 文件
  └─────┬───────┘
        │
        ▼
  ┌──────────────────┐
  │ chromium headless │  --headless=new --force-device-scale-factor=2
  │ --screenshot      │  --window-size=2160,10000
  │                   │  → 原始 PNG (2160×20000 px)
  └─────┬─────────────┘
        │
        ▼
  ┌───────────────────────┐
  │ crop_bottom_whitespace│  Pillow ImageChops.difference + getbbox
  │                       │  → 裁白边后最终 PNG
  └───────────────────────┘
```

### Recommended Project Structure

```
/mnt/e/Daily/
├── step8.py          # MD→JSON→HTML→PNG 全流程
├── run_all.sh        # 全管道串联
├── step1_3.py        # 采集 + 三淘汰（已有）
├── step4.py          # 分类筛选（已有）
├── step6.py          # 正文提取（已有）
├── step7.py          # 摘要生成（已有）
└── .env              # API keys（step7 需要，step8 不需要）

/mnt/e/每日新中国/{date}/
├── 3新闻_概述.md      # step8 输入
├── 4新闻_报纸.html    # step8 输出
└── 4新闻_报纸.png     # step8 输出
```

### Pattern 1: CLI 参数模式（所有 step 统一）

**What:** 统一 `--date YYYY-MM-DD` + `--dry-run` 参数解析
**When to use:** step8.py 和 run_all.sh 必须遵循

```python
# Source: 所有 step 脚本统一模式（step1_3.py, step4.py, step6.py, step7.py）
def parse_args():
    dry = "--dry-run" in sys.argv
    date_str = None
    for i, a in enumerate(sys.argv):
        if a == "--date" and i + 1 < len(sys.argv):
            date_str = sys.argv[i + 1]
    if date_str:
        try:
            dt = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            print(f"错误: 日期格式无效: {date_str}")
            sys.exit(1)
    else:
        dt = datetime.date.today()
    return dt, dry
```

### Pattern 2: 动态双栏平衡（贪心策略）

**What:** 按 section 累计字数，贪心分配到左/右栏
**When to use:** 将 8 个栏目（含空栏目）分配到两栏

```python
# D-04 锁定：贪心策略
def balance_columns(sections: list[dict]) -> tuple[list, list]:
    """按累计字数贪心分配 sections 到左右栏"""
    left, right = [], []
    left_chars, right_chars = 0, 0
    for sec in sections:
        char_count = sum(len(b) for b in sec.get("bullets", []))
        # 空栏目也分配，保持 8 栏目完整
        char_count = max(char_count, 1)  # 防止空栏目 0 字数
        if left_chars <= right_chars:
            left.append(sec)
            left_chars += char_count
        else:
            right.append(sec)
            right_chars += char_count
    return left, right
```

### Pattern 3: chromium headless 截图

**What:** chromium CLI 截图 + Pillow 后处理
**When to use:** HTML → PNG 转换

```python
# Source: render_newspaper.py screenshot_with_browser()（L751-773）
cmd = [
    "/snap/bin/chromium",
    "--headless=new",
    "--disable-gpu",
    "--hide-scrollbars",
    "--force-device-scale-factor=2",
    "--window-size=2160,10000",  # 1080*2=2160 宽，超长高度
    f"--screenshot={str(png_path.resolve())}",
    file_url,
]
proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
```

### Pattern 4: Pillow 裁白边

**What:** ImageChops.difference + getbbox 精确裁剪
**When to use:** chromium 截图后裁掉多余白色区域

```python
# Source: render_newspaper.py crop_bottom_whitespace()（L726-748）
def crop_bottom_whitespace(png_path: Path, pad: int = 24) -> tuple[bool, str]:
    img = Image.open(png_path).convert("RGB")
    bg = Image.new("RGB", img.size, img.getpixel((0, img.height - 1)))
    diff = ImageChops.difference(img, bg)
    bbox = diff.getbbox()
    if not bbox:
        return False, "image is empty"
    left, top, right, bottom = bbox
    crop_box = (
        max(0, left - pad),
        max(0, top - pad),
        min(img.width, right + pad),
        min(img.height, bottom + pad),
    )
    cropped = img.crop(crop_box)
    cropped.save(png_path)
    return True, f"cropped to {cropped.size[0]}x{cropped.size[1]}"
```

### Anti-Patterns to Avoid

- **不要用 sections 而非 columns 结构**: `build_html()` 有两条路径——`columns` 触发双栏 grid，`sections` 触发单栏回退。JSON payload 必须包含 `columns` 字段 [CITED: render_newspaper.py L236-250]
- **不要硬编码 issue 字段**: `normalize_payload()` 检测到纯数字或空字符串才触发自动计算期号。硬编码"第X期"会跳过计算 [CITED: render_newspaper.py L86-106]
- **不要在 bullets 中放对象**: `render_section()` 用 `str(x)` 处理 bullets，对象会被转成 Python dict 文本。必须用纯字符串列表 [CITED: SKILL.md 经验教训]
- **不要用 section["type"] 而非 section["heading"]**: 字段名错误会导致"未命名版块" [CITED: SKILL.md 铁律]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTML 转义 | 手写转义函数 | `html.escape(text, quote=True)` | render_newspaper.py 已用 `esc()` 函数（L154-155） |
| 期号计算 | 手写中文序数 | `_chinese_ordinal()` + `_compute_issue()` | render_newspaper.py 已实现，含边界处理（1-99） |
| 图片裁剪 | numpy pixel scan | `ImageChops.difference()` + `getbbox()` | 简洁可靠，已验证 |
| CSS 双栏布局 | float / flex 布局 | CSS grid `grid-template-columns: 1fr 2px 1fr` | render_newspaper.py 已验证的报纸风格布局 |

**Key insight:** render_newspaper.py 提供了所有关键组件的参考实现，step8.py 的核心工作是适配输入格式（MD→JSON）和精简代码（去掉不需要的 features 如 float-rail/highlights/quote）。

## Common Pitfalls

### Pitfall 1: chromium 截图尺寸不匹配 HTML 宽度

**What goes wrong:** PNG 宽度不是 2160px（1080×2x），导致报纸内容被裁切或缩放
**Why it happens:** `--window-size` 格式错误或忘记乘 scale-factor
**How to avoid:** `--window-size=2160,10000`，其中 2160 = 1080 × 2（force-device-scale-factor=2）
**Warning signs:** PNG 宽度 ≠ 2160px，或内容被截断

### Pitfall 2: JSON 缺少 columns 字段导致单栏回退

**What goes wrong:** 报纸变成单栏布局，所有内容挤在左半边
**Why it happens:** JSON payload 只包含 `sections` 而没有 `columns`，`build_html()` 走了回退路径
**How to avoid:** 确保 JSON 始终包含 `columns` 字段，且每个 column 有 `side: "left"/"right"` 和非空 `sections`
**Warning signs:** HTML 中出现 `<div class="story-main">` 而非 `<div class="content-col col-left">`

### Pitfall 3: 空栏目处理不当

**What goes wrong:** 某栏目无新闻时，摘要为空，字数为 0，贪心算法可能将所有空栏目堆到一栏
**Why it happens:** 8 个固定栏目中常有 2-3 个当日无报道
**How to avoid:** 空栏目也要加入 sections 列表（带空 bullets），且估算字数时给最小权重（如 20 字的标题开销）。或者只包含非空栏目
**Warning signs:** 左栏 6 个栏目（5 个空），右栏 2 个栏目

### Pitfall 4: 中文弯引号破坏 JSON

**What goes wrong:** `JSONDecodeError: Expecting ',' delimiter`
**Why it happens:** 摘要中的弯引号 `""` 与 JSON 字符串定界符冲突
**How to avoid:** step8 内部构造 dict 直接传给 build_html()，不经过 JSON 序列化/反序列化。如果需要写 JSON 中间文件，先替换弯引号为直角引号
**Warning signs:** 内部数据流不走 json.loads() 则无此问题

### Pitfall 5: run_all.sh 缺少错误处理

**What goes wrong:** 某步失败但后续步骤继续执行，产出不完整数据
**Why it happens:** bash 脚本默认不 `set -e`
**How to avoid:** `set -euo pipefail` + 每步检查 exit code
**Warning signs:** 最终 PNG 基于过期的输入数据

### Pitfall 6: Pillow 裁白边把有效内容裁掉

**What goes wrong:** 页脚 "Mobile Brief" 印章被裁掉
**Why it happens:** 页脚与背景色对比度太低（如 `#c0392b` 朱砂红文字在 `#f6f1e6` 背景上，但 body padding 区域有 `#ddd5c9` 外框色）
**How to avoid:** 确保 pad 参数足够大（默认 24px），且 HTML body padding 包含完整内容
**Warning signs:** PNG 底部被裁得过紧，看不到页脚

## Code Examples

### Markdown 解析器（3新闻_概述.md → sections）

```python
# Source: 从 step7.py 输出格式推导（L206-217）
import re
from pathlib import Path

COLUMN_ORDER = [
    '🔬 世界性科研突破', '🌾 农业', '🤝 扶贫', '⚡ 能源',
    '🏥 医疗', '🚀 科技', '🧱 材料', '🎖️ 军事',
]

def parse_md(md_path: Path) -> list[dict]:
    """解析 3新闻_概述.md → [{heading, bullets}, ...]"""
    content = md_path.read_text("utf-8")
    sections = []
    current_heading = None
    current_bullets = []

    for line in content.splitlines():
        # ## 栏目名
        m = re.match(r'^##\s+(.+)', line)
        if m:
            # 保存上一个 section
            if current_heading:
                sections.append({
                    "heading": current_heading,
                    "bullets": current_bullets,
                })
            current_heading = m.group(1).strip()
            current_bullets = []
            continue

        # ### 标题 + 后续摘要段落
        m = re.match(r'^###\s+(.+)', line)
        if m:
            title = m.group(1).strip()
            # 摘要段落会在后续行读取
            current_title = title
            current_summary_lines = []
            continue

        # 摘要段落（非空、非标题行）
        line_stripped = line.strip()
        if line_stripped and current_heading and not line_stripped.startswith('#'):
            current_bullets.append(line_stripped)

    # 最后一个 section
    if current_heading:
        sections.append({
            "heading": current_heading,
            "bullets": current_bullets,
        })

    return sections
```

### 完整 HTML 模板（精简版，双栏 columns 结构）

```html
<!-- Source: render_newspaper.py build_html() 第一版（L230-432），精简为报纸核心 -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>{title}</title>
  <style>
    :root {
      --paper: #f6f1e6;
      --ink: #141414;
      --muted: #5d5a53;
      --line: #1d1d1d;
      --soft-line: #c8beb0;
      --accent: #6f5a44;
    }
    * { box-sizing: border-box; }
    html, body { margin: 0; padding: 0; background: #ddd5c9; color: var(--ink); }
    body {
      font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", sans-serif;
      display: flex; justify-content: center; padding: 32px 0;
    }
    .page { width: 1080px; background: var(--paper); padding: 0 32px 24px; }
    .topbar { display: flex; justify-content: space-between; align-items: end;
              border-top: 6px solid var(--line); border-bottom: 2px solid var(--line);
              padding: 8px 0 5px; margin-bottom: 8px; }
    .paper-title { font-size: 52px; font-weight: 900; letter-spacing: 2px; line-height: 1; }
    .issue-date { font-size: 18px; color: var(--muted); white-space: nowrap; }
    .story-wrap { display: grid; grid-template-columns: 1fr 2px 1fr; gap: 0; }
    .content-col { min-width: 0; }
    .col-divider { background: var(--line); width: 2px; }
    .section-card { border-top: 2px solid var(--line); padding-top: 10px; margin-bottom: 18px; }
    .section-card h2 { margin: 0 0 8px; font-size: 32px; font-weight: 900; }
    .section-card ul { list-style: none; padding: 0; margin: 0; }
    .section-card li { font-size: 24px; line-height: 1.73; text-align: justify;
                       padding-left: 32px; position: relative; margin-bottom: 10px; }
    .section-card li::before { content: ""; width: 12px; height: 12px;
                                border-radius: 999px; background: var(--ink);
                                position: absolute; left: 4px; top: 8px; }
    .footer { margin-top: 10px; padding-top: 6px; border-top: 2px solid var(--line);
              font-size: 16px; color: #c0392b; display: flex; justify-content: space-between; }
    .stamp { display: inline-flex; align-items: center; gap: 8px;
             font-weight: 800; letter-spacing: 1px; text-transform: uppercase; }
    .stamp::before { content: ""; width: 12px; height: 12px;
                     border-radius: 999px; background: var(--ink); display: inline-block; }
  </style>
</head>
<body>
  <article class="page">
    <header class="topbar">
      <div class="paper-title">紫音简报</div>
      <div class="issue-date">2026年5月17日 星期日 第二十九期</div>
    </header>
    <div class="story-wrap">
      <div class="content-col col-left">
        <!-- 左栏 sections -->
        <div class="section-card">
          <h2>🔬 科研</h2>
          <ul><li>摘要内容...</li></ul>
        </div>
      </div>
      <div class="col-divider"></div>
      <div class="content-col col-right">
        <!-- 右栏 sections -->
      </div>
    </div>
    <footer class="footer">
      <div>来源：新华社/央视新闻 ｜ 每日新中国出品</div>
      <div class="stamp">Mobile Brief</div>
    </footer>
  </article>
</body>
</html>
```

### run_all.sh 模板

```bash
#!/usr/bin/env bash
# run_all.sh — 全管道串联脚本
# 用法: ./run_all.sh --date 2026-05-17 [--dry-run]

set -euo pipefail

DATE=""
DRY_RUN=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --date) DATE="$2"; shift 2 ;;
        --dry-run) DRY_RUN="--dry-run"; shift ;;
        *) echo "未知参数: $1"; exit 1 ;;
    esac
done

if [[ -z "$DATE" ]]; then
    echo "错误: --date YYYY-MM-DD 为必填参数"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

steps=(
    "step1_3.py"
    "step4.py"
    "step6.py"
    "step7.py"
    "step8.py"
)

for step in "${steps[@]}"; do
    echo "═══ 运行: $step --date $DATE $DRY_RUN ═══"
    python3 "$SCRIPT_DIR/$step" --date "$DATE" $DRY_RUN
    if [[ $? -ne 0 ]]; then
        echo "❌ $step 失败，停止执行"
        exit 1
    fi
    echo ""
done

echo "✅ 全管道完成: $DATE"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Playwright full_page=True | chromium CLI --screenshot | CONTEXT D-02 锁定 | 更简单，无 Playwright 依赖 |
| render_newspaper.py 外部调用 | step8.py 内嵌 build_html() | CONTEXT D-01 锁定 | 减少外部依赖，单文件全流程 |
| sections 单栏布局 | columns 双栏 grid 布局 | render_newspaper.py L236+ | 报纸风格必须双栏 |

**Deprecated/outdated:**
- render_newspaper.py 的 float-rail（侧边栏 TL;DR / quote 卡片）：step8 不需要，只有摘要和栏目

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 3新闻_概述.md 格式始终为 ## 栏目 + ### 标题 + 摘要段落，无变异 | Architecture Patterns | 解析器失败，需增加容错 |
| A2 | chromium --window-size=2160,10000 在所有情况下都能完整渲染 1080px HTML | Code Examples | 内容被截断，需调整高度 |
| A3 | Pillow getbbox() 能正确处理 #f6f1e6 仿纸背景 + #ddd5c9 外框色的差异 | Code Examples | 裁白边过度/不足 |
| A4 | 8 个固定栏目名与 COLUMN_ORDER 完全匹配 | Architecture Patterns | 空栏目匹配失败 |

## Open Questions

1. **空栏目在 HTML 中的呈现**
   - What we know: step7.py 输出"（当日无真实报道，栏目留空）"
   - What's unclear: step8 是否应该跳过空栏目（不渲染空卡片），还是渲染一个"暂无报道"占位
   - Recommendation: 跳过空栏目，只渲染有内容的 section。贪心算法只分配非空 section

2. **--dry-run 在 step8 中的行为**
   - What we know: CONTEXT 标记为 the agent's Discretion
   - Recommendation: `--dry-run` 时只生成 HTML 不截图（截图耗时较长且依赖 chromium）

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3 | step8.py | ✓ | 3.12.3 | — |
| Pillow | step8.py 裁白边 | ✓ | 12.1.1 | — |
| chromium headless | step8.py 截图 | ✓ | 147.0.7727.116 snap | — |
| /snap/bin/chromium | subprocess 调用 | ✓ | snap 安装 | — |

**Missing dependencies with no fallback:** none
**Missing dependencies with fallback:** none

## Validation Architecture

> workflow.nyquist_validation = false in config.json — SKIP

## Security Domain

> 此阶段为本地脚本管道，无网络输入、无用户认证、无数据存储。安全风险极低。

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes | Markdown 解析使用正则，HTML 输出使用 `html.escape()` |
| V6 Cryptography | no | — |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| HTML injection via markdown content | Tampering | `html.escape()` 所有用户内容 |
| Command injection via filename | Tampering | pathlib 处理路径，不拼接到 shell 命令 |

## Sources

### Primary (HIGH confidence)
- `/home/lmr/.hermes/profiles/glm51/skills/productivity/newspaper-brief/scripts/render_newspaper.py` — 完整 820 行参考实现，直接读取分析
- `/mnt/e/Daily/step7.py` — 上游数据格式定义，直接读取分析
- `/mnt/e/每日新中国/2026-05-14/3新闻_概述.md` — 真实输入样本

### Secondary (MEDIUM confidence)
- `/home/lmr/.hermes/skills/productivity/daily-china-news/SKILL.md` — 格式规范和经验教训
- `/mnt/e/Daily/step6.py` — chromium 使用方式参考
- `/mnt/e/Daily/.planning/phases/04-summary-gen/4-CONTEXT.md` — Phase 4 锁定的输出格式

### Tertiary (LOW confidence)
- none

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Pillow 已安装已验证，chromium 已安装已测试截图
- Architecture: HIGH — render_newspaper.py 提供完整参考，输入格式已从真实样本确认
- Pitfalls: HIGH — SKILL.md 包含大量历史翻车案例和铁律

**Research date:** 2026-05-17
**Valid until:** 2026-06-17（stable — 成熟技术栈，变化缓慢）

---

## 附：参考实现关键代码位置索引

| 函数/模块 | render_newspaper.py 行号 | step8 用途 |
|-----------|--------------------------|-----------|
| `_chinese_ordinal()` | L56-69 | 直接移植（期号转中文序数） |
| `_compute_issue()` | L71-82 | 直接移植（从日期算期号） |
| `normalize_payload()` | L84-151 | 参考字段结构，简化（不需要 tagline/highlights/quote） |
| `esc()` / `paragraphs()` | L154-160 | 直接移植（HTML 转义） |
| `render_section()` | L163-174 | 直接移植（渲染栏目卡片） |
| `build_html()` 第一版 | L230-432 | 提取 CSS + columns 双栏结构 |
| `crop_bottom_whitespace()` | L726-748 | 直接移植（Pillow 裁白边） |
| `screenshot_with_browser()` | L751-773 | 直接移植（chromium 截图命令） |
