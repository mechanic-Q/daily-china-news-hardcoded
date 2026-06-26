---
source_commit: 5f76a1a
updated_at: 2026-06-24T10:01:04Z
generator: sillyspec-scan
author: lmr
created_at: 2026-06-24 18:01:00
---

# PROJECT — 每日新中国 · Daily China News

## 项目简介

- **名称**：每日新中国 · Daily China News（slogan：中国很大 我想去看看 / China is vast — let's take a look）
- **定位**：一键自动化的中国新闻数字报纸生成流水线，输出 1080px 双栏手机壁纸风格 HTML + PNG
- **流程**：7 信源采集 → 三淘汰验证（HTTP / HTTPS / 内容有效性）→ 涉华过滤 + 负面过滤 → 关键词加权 + LLM 双引擎分类 → 5 层策略链正文提取 → LLM 逐条摘要（含 retry×3 诊断回退）→ CSS Grid 双栏渲染 → Chromium headless 截图
- **状态**：v1.1 milestone 已 ship；2026/06/02 启动 v1.1 Quality Fix，2026/06/22 完成第 9 个 phase（smart-classify）并 archive
- **产量**：每日 10 条精选，分布于 8 个栏目 — 🔬 科研突破 / 🌾 农业 / 🤝 扶贫 / ⚡ 能源 / 🏥 医疗 / 🚀 科技 / 🧱 材料 / 🎖️ 军事
- **确定性承诺**：每个环节都是确定性的，LLM 调用有智能重试和回退；同一日输入产出同一份报纸

## 技术栈

| 类别 | 技术 | 用途 |
|------|------|------|
| Language | Python 3.12 | 5 个 step 脚本主语言 |
| LLM SDK | `openai` Python SDK | 作为 OpenAI 兼容客户端，通过 `base_url` 指向 Zhipu / MiniMax |
| LLM (分类+摘要) | Zhipu GLM-4 Flash | `llm_classify_single()`（step4）、摘要（step7） |
| LLM (涉华判断) | MiniMax (`step4.py:88` 写 `minimax-m2.7`，见 CONCERNS) | 中国相关性判定 |
| HTTP (异步) | `aiohttp` | `step1_3.py` 信源并发抓取与 HTTPS 三淘汰验证 |
| HTTP (同步) | `urllib.request` | step6 / step7 中的静态页面抓取 |
| 浏览器 | Chromium headless via `/snap/bin/chromium` | `--dump-dom` 抓取 JS 渲染页 + `--screenshot` 报纸截图 |
| 图像 | Pillow | `crop_bottom_whitespace()` 裁剪 PNG 底部空白 |
| 模板 | CSS Grid + 内联 HTML f-string | step8 双栏报纸布局 |
| 配置 | `python-dotenv`（README 提及，仅 step7 import） | `.env` 加载 API key |

## 仓库结构（根目录）

```
/mnt/e/Daily/
├── step1_3.py        475 LOC  多信源采集 + 三淘汰
├── step4.py          434 LOC  分类 + 涉华 / 负面过滤 + LLM 复核
├── step6.py          286 LOC  5 层策略链正文提取
├── step7.py          271 LOC  LLM 摘要 + retry×3 诊断
├── step8.py          513 LOC  CSS Grid 渲染 + Chromium 截图
├── run_all.sh         50 LOC  全流水线编排
├── README.md          双语项目说明（241 行）
├── CLAUDE.md          代码代理指引
├── AGENTS.md          多代理协作约定
├── idea.md            原始构思
└── .planning/         milestone / phase 工作流（9 phase 已 ship）
```

输出目录（独立 mount）：`/mnt/e/每日新中国/YYYY-MM-DD/`，含 `0新闻_粗筛.md` / `1新闻_链接.md` / `2新闻_已审核.md` / `3新闻_概述.md` + `*.html` + `*.png`。

## 入口

- **一键**：`./run_all.sh`（默认今日日期）
- **指定日期**：`./run_all.sh --date 2026-06-22`
- **预览**：`./run_all.sh --dry-run --date 2026-06-22`
- **分步**：`python3 stepN.py [--date YYYY-MM-DD] [--dry-run]`，N ∈ {1_3, 4, 6, 7, 8}

## 配置

- `.env`（已 gitignore，根目录存在）：
  - `ZHIPU_API_KEY` — 必需，GLM-4 Flash（分类 + 摘要）
  - `MINIMAX_API_KEY` — 涉华判断专用
- 仅 `step7.py:19-20` 主动 `load_dotenv()`；step4 直接读 `os.environ`，从 shell 跑 step4 需要先 `export`

## 代码规模

- Python：5 文件 / 共 1979 LOC（step1_3 475 / step4 434 / step6 286 / step7 271 / step8 513）
- Shell：1 文件 / 50 LOC（run_all.sh）
- 合计 ~2,029 LOC，README 的 "~2,000 LOC Python" 描述准确
- 无自动化测试（详见 `TESTING.md`）
- 无依赖锁文件（详见 `CONCERNS.md` 依赖风险）

## Milestone 历程

- **v1.0**（2026/05/15 - 2026/05/17，3 天）：5 phase 完成核心流水线
- **v1.1 Quality Fix**（2026/06/02 - 2026/06/22）：4 phase（06-fix-body-extract / 07-column-balance / 08-summary-robustness / 09-smart-classify），10/10 验收要求通过
- 最近提交：`5f76a1a docs: README — 每日新中国·Daily China News (bilingual, detailed)`

## 信源（7 个权威源）

新华社、人民日报、央视新闻、央视军事、参考消息、中国科学院 等（具体抓取实现见 `step1_3.py:109+`）。

## 许可

MIT — 详见 README。

---

*本文件由 sillyspec-scan 生成，依据 commit 5f76a1a 全仓 rg 扫描 + README + .planning/PROJECT.md。*
