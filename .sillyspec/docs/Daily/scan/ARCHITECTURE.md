---
source_commit: 5f76a1a
updated_at: 2026-06-24T10:01:04Z
generator: sillyspec-scan
author: lmr
created_at: 2026-06-24 18:01:00
---

# Daily（每日新中国 · Daily China News）· 架构总览

> 一个完全脚本化、文件接力式的中国正面新闻日报流水线。每日采集 7 个权威信源，经分类、正文提取、LLM 摘要后，渲染为单页 HTML + 截图 PNG。

## 1. 技术栈

| 类别 | 选型 |
|------|------|
| 语言 / 运行时 | Python 3.12（项目根 `.gitignore`、`__pycache__/*.cpython-312.pyc` 印证），Bash（仅 `run_all.sh`） |
| HTTP（同步） | `urllib.request`（step1_3 / step6） |
| HTTP（异步） | `aiohttp`（step1_3.py 三淘汰阶段并发 200 校验） |
| LLM SDK | `openai`（OpenAI 兼容客户端，复用调用 Zhipu / MiniMax） |
| 图像处理 | `Pillow`（step8.py 用 `Image` + `ImageChops` 裁剪 PNG 边缘） |
| 浏览器渲染 | `/snap/bin/chromium`（snap chromium v147，`--dump-dom` 抓取动态首页 + `--headless --screenshot` 截图最终 HTML） |
| 配置 | `python-dotenv`（仅 step7 显式 `load_dotenv`，读取 `MINIMAX_API_KEY` / `ZHIPU_API_KEY`） |
| 依赖管理 | 无 `requirements.txt`，全部隐式依赖（见 §5） |

## 2. 架构概览

5 步流水线、单向数据流、上下游全部通过 **磁盘 Markdown 文件接力**，没有进程内共享状态：

```
┌──────────┐   ┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐
│ 7 信源   │──▶│ step1_3│──▶│ step4  │──▶│ step6  │──▶│ step7  │──▶ step8 ──▶ HTML+PNG
│ Web/API  │   │ 采集+  │   │ 分类+  │   │ 正文   │   │ LLM    │     渲染
│          │   │ 三淘汰 │   │ 筛选   │   │ 提取   │   │ 摘要   │
└──────────┘   └────────┘   └────────┘   └────────┘   └────────┘
                  │            │            │            │            │
                  ▼            ▼            ▼            ▼            ▼
              0粗筛.md     1链接.md     2已审核.md    3概述.md   {date}_每日新中国_{issue}.html
                                                                       + .png
```

| 脚本 | 行数 | 职责（一句话） |
|------|------|----------------|
| `step1_3.py` | 475 | 7 信源采集（urllib / chromium / 降级链）+ 三淘汰异步 HTTP 200 验证，产出 `0新闻_粗筛.md` |
| `step4.py`   | 434 | 8 栏目关键词打分 + LLM 兜底分类 + 质量过滤 + 优先级排序，产出 `1新闻_链接.md` |
| `step6.py`   | 286 | 5 层策略链正文提取（静态 urllib / 央视系 chromium 分流 + 污染清洗），产出 `2新闻_已审核.md` |
| `step7.py`   | 271 | 逐条 LLM 摘要（≤2 句），含规则回退与 3 次重试，产出 `3新闻_概述.md` |
| `step8.py`   | 513 | 解析摘要 MD → 双栏报纸 HTML 模板 → chromium 截图 → Pillow 裁边，产出 `.html` + `.png` |
| `run_all.sh` | 50  | 串行编排，任何一步非零退出立即中止 |

## 3. 关键设计

### 3.1 文件接力（File Relay），无内存共享
每个 step 都用 `BASE_DIR = Path("/mnt/e/每日新中国")` + 日期目录定位输入输出（5 处全部硬编码一致），脚本之间不通过 Python import 互调，仅通过磁盘 Markdown 中转。这带来三个直接收益：
- 任一 step 可单独 `--date YYYY-MM-DD` 重跑，无需重放上游；
- 失败可断点续跑（`run_all.sh` 失败即停，手工修 MD 后从下一步继续）；
- 流水线可观察 —— 0/1/2/3 四个中间文件就是天然的调试快照。

### 3.2 确定性流水线 + LLM 兜底
分类与摘要都先走规则，再用 LLM 兜底/精修，避免把流水线生死交给模型：
- **分类**（step4）：`CATEGORY_KEYWORDS`（8 栏目 × 加权关键词）先打分，分数为 0 才回退到 GLM 单条分类；
- **摘要**（step7）：`fallback_summarize()` 规则生成 + `_why_invalid()` 校验，LLM 失败 3 次降级到规则版本；
- **是否中国相关**（step4）：硬编码白名单/源域名先判，模糊样本才调 MiniMax 二判。

### 3.3 3 个 LLM 调用点（全部 OpenAI 兼容协议）

| # | 位置 | Provider | Base URL | Model | 用途 |
|---|------|----------|----------|-------|------|
| 1 | `step4.py:86-88` | MiniMax | `https://api.minimax.chat/v1` | `minimax-m2.7` | 标题是否中国相关（是/否） |
| 2 | `step4.py:225-232` | Zhipu | `https://open.bigmodel.cn/api/paas/v4/` | `glm-4-flash` | 单条标题分类到 8 栏目之一 |
| 3 | `step7.py:159-170` | Zhipu | `https://open.bigmodel.cn/api/paas/v4/` | `glm-4-flash` | 1-2 句新闻摘要（带 3 次重试 + 失败提示） |

Key 通过环境变量读取：`MINIMAX_API_KEY`、`ZHIPU_API_KEY`；step7 额外 `load_dotenv(Path(__file__).parent / '.env')`。

### 3.4 浏览器作为通用兜底
凡是 JS 渲染或反爬严的页面，统一走 `chromium --dump-dom`（step1_3、step6）或 `chromium --headless --screenshot`（step8），不引入 Playwright / Selenium 这类重依赖。

## 4. 数据存储

输出根目录硬编码：`/mnt/e/每日新中国/`，按日期分子目录，无数据库。

```
/mnt/e/每日新中国/
└── YYYY-MM-DD/
    ├── 0新闻_粗筛.md                          # step1_3 产出：7 信源原始链接（已过三淘汰）
    ├── 1新闻_链接.md                          # step4   产出：分类+优先级后的精选标题/链接
    ├── 2新闻_已审核.md                        # step6   产出：抽取完正文的链接清单
    ├── 3新闻_概述.md                          # step7   产出：含 1-2 句摘要的最终素材
    ├── YYYY-MM-DD_每日新中国_{issue}.html     # step8   产出：报纸版式单页
    └── YYYY-MM-DD_每日新中国_{issue}.png      # step8   产出：HTML 的 chromium 截图（Pillow 裁边）
```

`{issue}` 由 `step8.py:_compute_issue()` 从目标日期推算（中文序数刊号），`_chinese_ordinal()` 负责数字汉字化。

## 5. 依赖关系

仓库 **没有 `requirements.txt`**，全部为隐式依赖。安装清单（按脚本归集）：

| 包 | 来源脚本 | 用途 |
|----|----------|------|
| `aiohttp` | step1_3.py | 三淘汰阶段并发 `HEAD`/`GET` 200 校验 |
| `openai` | step4.py / step7.py | OpenAI 兼容客户端访问 MiniMax / Zhipu |
| `Pillow` | step8.py（`from PIL import Image, ImageChops`） | 截图后白边裁剪 |
| `python-dotenv` | step7.py（`from dotenv import load_dotenv`） | 加载 `.env` 中的 API Key |

标准库依赖：`asyncio`、`urllib.request`、`subprocess`、`ssl`、`re`、`json`、`html`、`pathlib`、`datetime` 等。

外部二进制：`/snap/bin/chromium`（snap chromium v147，step1_3 / step6 / step8 均直接调用绝对路径）。

数据接口（外部）：
- 7 个新闻信源域名：`news.cn`（新华社）、参考消息（urllib JSON API）、`news.cctv.com`、`military.cctv.com`、`cas.cn`（中科院）、中核集团（降级链）、人民日报（urllib 版面索引）。
- MiniMax `api.minimax.chat`、Zhipu `open.bigmodel.cn`。

## 6. 入口与编排

**全流水线**（推荐）：

```bash
./run_all.sh                 # 默认今天
./run_all.sh --date 2026-06-24
./run_all.sh --date 2026-06-24 --dry-run
```

`run_all.sh` 用 `set -euo pipefail` + 显式 `STEPS=("step1_3.py" "step4.py" "step6.py" "step7.py" "step8.py")` 循环执行，逐步 `python3` 调用并把 `--date` / `--dry-run` 透传给每个脚本；任一非零退出码立即 `exit 1` 终止。

**单步独立运行**（用于调试 / 断点续跑）：每个 step 都自带 `parse_args()`（5/5 脚本），可单独运行：

```bash
python3 step1_3.py --date 2026-06-24            # 仅重抓采集
python3 step4.py   --date 2026-06-24            # 仅重分类
python3 step6.py   --date 2026-06-24            # 仅重抽正文
python3 step7.py   --date 2026-06-24 [--dry-run] # 仅重摘要
python3 step8.py   --date 2026-06-24            # 仅重渲染
```

—— 因为上下游通过磁盘文件解耦，单步重跑只需要保证上游对应的 `N新闻_*.md` 已存在即可。

## 7. 流水线常量速查

- **7 信源**（`step1_3.py:399 SOURCES = [...]`）：新华社、参考消息、央视新闻、央视军事、中科院、中核集团、人民日报。
- **8 栏目**（`step4.py:143 CATEGORY_KEYWORDS = {...}`）：🔬 世界性科研突破 / 🌾 农业 / 🤝 扶贫 / ⚡ 能源 / 🏥 医疗 / 🚀 科技 / 🧱 材料 / 🎖️ 军事。
- **代码体量**（`wc -l` 实测）：step1_3 = 475，step4 = 434，step6 = 286，step7 = 271，step8 = 513，run_all.sh = 50，共 **2029 行**。
