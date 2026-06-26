---
source_commit: 5f76a1a
updated_at: 2026-06-24T10:01:04Z
generator: sillyspec-scan
author: lmr
created_at: 2026-06-24 18:01:00
---

# Daily（每日新中国）— 目录与文件结构

## 1. 顶层目录树（深度 1，已排除 `get-shit-done/`、`__pycache__/`、`.git/`、`.sillyspec/`、`node_modules/`）

```
/mnt/e/Daily/
├── step1_3.py         475 LOC  — 抓取+去重+并发取标题（合并原 step1/2/3）
├── step4.py           434 LOC  — 标题智能分类（MiniMax 是否涉华 → Zhipu 8 栏目）
├── step6.py           286 LOC  — 5 层正文抓取（chromium / urllib 分流）
├── step7.py           271 LOC  — Zhipu 概述生成（3 次重试 + 失败原因诊断）
├── step8.py           513 LOC  — HTML 渲染 + chromium 截图 + Pillow 裁切
├── run_all.sh          50 LOC  — 顺序运行 step1_3 → step4 → step6 → step7 → step8
├── README.md          240 LOC  — 双语项目说明（流水线/输出/快速开始）
├── AGENTS.md           22 LOC  — Agent 行为约束（中文/无 emoji 等）
├── CLAUDE.md          112 LOC  — Claude Code 项目级指令
├── idea.md              5 LOC  — 原始灵感（短）
├── .env               206 B    — API keys（gitignored；ZHIPU_API_KEY / MINIMAX_API_KEY）
├── .gitignore          24 B    — 排除 .env / __pycache__ 等
├── package-lock.json    6 LOC  — 空骨架（npm 占位，无实际依赖）
├── __pycache__/                — Python 字节码缓存（跳过；不入仓核心）
├── demo/                       — 截图资产（screenshot-2026-05-18.png，1.3 MB 演示样张）
├── get-shit-done/              — vendored 第三方 GSD 框架（**不属于本项目**，整目录跳过）
├── .planning/                  — GSD workflow 状态（PROJECT.md / ROADMAP.md / STATE.md / milestones/ / phases/ / v1.0-MILESTONE-AUDIT.md / v1.1-MILESTONE-AUDIT.md / config.json）
├── .sillyspec/                 — spec-driven dev 工作目录（本扫描产物所在地）
├── .spec-workflow/             — spec-workflow 模板（templates/ + steering/ + specs/ + approvals/ + archive/）
└── .opencode/                  — OpenCode 插件（_env-detect.md）
```

## 2. 顶层 Python 文件职责（按调用顺序）

| 步骤 | 文件 | LOC | 入口/职责 |
|---|---|---|---|
| 1+2+3 | `/mnt/e/Daily/step1_3.py` | 475 | 7 个信源并行抓取链接 → 域名白名单/同源去重 → aiohttp 并发抓标题 → 输出 `0新闻_粗筛.md` |
| 4 | `/mnt/e/Daily/step4.py` | 434 | 第一阶段：MiniMax `minimax-m2.7` 判定"是否涉华"；第二阶段：Zhipu `glm-4-flash` 在 8 个栏目中分类 → `1新闻_链接.md` |
| 6 | `/mnt/e/Daily/step6.py` | 286 | 5 层正文抓取策略链（chromium → urllib → 退化），分流静态/JS 渲染源 → `2新闻_已审核.md` |
| 7 | `/mnt/e/Daily/step7.py` | 271 | Zhipu `glm-4-flash` 1–2 句概述，3 次重试 + 失败原因诊断（含 RETRY_PROMPTS） → `3新闻_概述.md` |
| 8 | `/mnt/e/Daily/step8.py` | 513 | 模板化 HTML 渲染 + `chromium --screenshot` 截图 + Pillow 裁切多余空白 → `*.html` / `*.png` |
| – | `/mnt/e/Daily/run_all.sh` | 50 | 顺序串联以上 5 个 step 的 bash orchestrator |

## 3. 输出目录布局 `/mnt/e/每日新中国/{YYYY-MM-DD}/`

每日运行后生成的标准产物（实测样例 `/mnt/e/每日新中国/2026-05-18/`）：

| 产物 | 大小级 | 生成者 | 内容 |
|---|---|---|---|
| `0新闻_粗筛.md` | ~17 KB | step1_3 | 7 信源全部链接+标题，按域名分组的粗筛清单 |
| `1新闻_链接.md` | ~2 KB | step4 | 仅保留"涉华 + 已归类到 8 栏目"的精炼链接表 |
| `2新闻_已审核.md` | ~19 KB | step6 | 抓取后的完整正文，5 层策略分流标注来源 |
| `3新闻_概述.md` | ~3 KB | step7 | LLM 1–2 句精炼概述（每条新闻一段） |
| `{YYYY-MM-DD}_每日新中国_第N期.html` | ~8 KB | step8 | 期刊样式 HTML 模板，单文件可独立打开 |
| `{YYYY-MM-DD}_每日新中国_第N期.png` | ~1.3 MB | step8 | chromium 全页截图 + Pillow 裁切后的发布图 |

## 4. 信源域名白名单（step1_3.py 内置）

`xinhuanet.com`, `news.cn`, `people.com.cn`, `cctv.com`, `gmw.cn`, `youth.cn`, `cas.cn`, `cnnpn.cn`, `cnnc.com`（及参考消息 `china.cankaoxiaoxi.com`、央视军事 `military.cctv.com`、人民日报 `paper.people.com.cn`）。

## 5. 关键运行约定

- 全部 Python 文件位于仓库根目录，无包结构（无 `__init__.py`，无 `requirements.txt`）。
- 依赖隐式声明：`openai`、`aiohttp`、`Pillow`、`python-dotenv`（详见 `INTEGRATIONS.md`）。
- 外部进程：唯一系统依赖为 `/snap/bin/chromium`（snap chromium v147）。
- 输出根路径硬编码为 `/mnt/e/每日新中国/`，按日期 `YYYY-MM-DD` 建子目录。
- API keys 从 `/mnt/e/Daily/.env` 经 `python-dotenv` 加载到环境变量后由 `os.environ.get()` 读取（step7.py 中使用 `from dotenv import load_dotenv`）。
