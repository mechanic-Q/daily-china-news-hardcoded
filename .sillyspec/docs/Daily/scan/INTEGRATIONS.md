---
source_commit: 5f76a1a
updated_at: 2026-06-24T10:01:04Z
generator: sillyspec-scan
author: lmr
created_at: 2026-06-24 18:01:00
---

# Daily（每日新中国）— 外部集成清单

按集成类型分组，列出全部外部服务、信源、本地工具与第三方 Python 包。所有调用点均给出绝对文件路径 + 行号。

## 1. LLM 服务（OpenAI 兼容 API）

| 提供商 | base_url | 模型 | 环境变量 | 调用点 | 用途 |
|---|---|---|---|---|---|
| **MiniMax** | `https://api.minimax.chat/v1` | `minimax-m2.7` | `MINIMAX_API_KEY` | `/mnt/e/Daily/step4.py:86` | 标题二分类"是否涉华"（temperature=0.1, max_tokens=10, timeout=15） |
| **Zhipu AI（智谱）** | `https://open.bigmodel.cn/api/paas/v4/` | `glm-4-flash` | `ZHIPU_API_KEY` | `/mnt/e/Daily/step4.py:225` | 8 栏目分类（科技/军事/医疗/能源/农业/科研突破/材料/扶贫） |
| **Zhipu AI（智谱）** | `https://open.bigmodel.cn/api/paas/v4/` | `glm-4-flash` | `ZHIPU_API_KEY` | `/mnt/e/Daily/step7.py:159` | 1–2 句新闻概述（3 次重试 + RETRY_PROMPTS 失败原因注入） |

调用方式：均通过 `from openai import OpenAI`（`openai` SDK 的 OpenAI 兼容客户端）发起，调用 `client.chat.completions.create(...)`。Key 通过 `os.environ.get("...")` 读取（`/mnt/e/Daily/step4.py:81`、`/mnt/e/Daily/step4.py:212`、`/mnt/e/Daily/step7.py:153`）。

## 2. 新闻信源（HTTP 抓取，7 大主源）

| 信源 | 抓取入口 URL | 抓取方式 | 调用点 |
|---|---|---|---|
| **新华社** | `https://www.news.cn/` | chromium `--dump-dom`，正则匹配 `YYYYMMDD/c.html` | `/mnt/e/Daily/step1_3.py:111` |
| **参考消息** | `https://china.cankaoxiaoxi.com/json/channel/{alias}/list.json?_t={ts}` | urllib JSON API（带 Referer 头），9 个频道 | `/mnt/e/Daily/step1_3.py:135` |
| **央视新闻** | `https://news.cctv.com/` | chromium `--dump-dom`，过滤 today_path + `.shtml` | `/mnt/e/Daily/step1_3.py:168` |
| **央视军事** | `https://military.cctv.com/` | chromium `--dump-dom`，同上过滤模式 | `/mnt/e/Daily/step1_3.py:188` |
| **中科院** | `https://www.cas.cn/` | urllib 静态 + UA 伪装，正则匹配 `YYYYMM` 前缀链接 | `/mnt/e/Daily/step1_3.py:207` |
| **中核集团** | `https://www.cnnc.com.cn/` → `https://www.cnnpn.cn/` | chromium `--dump-dom`（三级回退：cnnc.com.cn 方案1 → cnnpn.cn 聚合站 CF 绕过 方案2 → 失败兜底） | `/mnt/e/Daily/step1_3.py:230`、`:247` |
| **人民日报** | `https://paper.people.com.cn/rmrb/pc/layout/{YYYYMM}/{DD}/node_{NN}.html` | urllib + node_NN 版面顺序扫描 | `/mnt/e/Daily/step1_3.py:291` |

正文抓取（step6.py）复用 chromium / urllib 两路：`/mnt/e/Daily/step6.py:49` 启动 chromium 子进程，`/mnt/e/Daily/step6.py:57-58` 走 urllib 直拉静态页（带 `User-Agent: Mozilla/5.0` 头与 SSL context）。

## 3. 外部进程工具

| 二进制路径 | 用途 | 调用方式 | 调用点 |
|---|---|---|---|
| `/snap/bin/chromium`（snap chromium v147） | DOM 渲染 dump | `subprocess.run([CHROMIUM, "--headless", "--virtual-time-budget={budget}", "--dump-dom", url])` | `/mnt/e/Daily/step1_3.py:26+71`、`/mnt/e/Daily/step6.py:22+49` |
| `/snap/bin/chromium` | 全页截图（成品图渲染） | `subprocess.run([chromium, "--headless", f"--screenshot={png_path}", ...])`，超时 120s（`subprocess.TimeoutExpired` 捕获） | `/mnt/e/Daily/step8.py:433+443+447+457` |

二进制存在性检查：`/mnt/e/Daily/step8.py:435` 显式提示 `chromium not found at /snap/bin/chromium`。

## 4. Python 标准库 / 内置依赖

| 模块 | 用途 | 调用点 |
|---|---|---|
| `subprocess` | 启动 chromium 子进程，捕获 stdout/stderr，处理超时 | `/mnt/e/Daily/step1_3.py:17`、`/mnt/e/Daily/step6.py:16`、`/mnt/e/Daily/step8.py:7` |
| `urllib.request` | 静态 HTTP 抓取（参考消息 JSON、中科院首页、人民日报版面、step6 正文回退） | `/mnt/e/Daily/step1_3.py:21`、`/mnt/e/Daily/step6.py:18` |
| `ssl` | 自定义 SSL context 处理证书 | step1_3 / step6（`context=ssl_ctx`） |
| `json` | 解析参考消息 JSON API 响应 | `/mnt/e/Daily/step1_3.py:141` |

## 5. 第三方 Python 包（无 requirements.txt，隐式依赖）

| 包名 | 用途 | import 点 |
|---|---|---|
| **openai** | OpenAI 兼容客户端（MiniMax / Zhipu 共用） | `/mnt/e/Daily/step4.py:85`、`/mnt/e/Daily/step4.py:224`、`/mnt/e/Daily/step7.py:158` |
| **aiohttp** | 并发抓取链接标题（step1_3 第三阶段） | `/mnt/e/Daily/step1_3.py:13` |
| **Pillow（PIL）** | 截图后裁切多余空白（`Image`, `ImageChops`） | `/mnt/e/Daily/step8.py:13` |
| **python-dotenv** | 从 `/mnt/e/Daily/.env` 加载 API key 到环境变量 | `/mnt/e/Daily/step7.py:19`（`from dotenv import load_dotenv`） |

README 提及但代码内仅在 step7 显式 `import`：`python-dotenv` 实际只在 step7.py 中显式 `load_dotenv()` 调用；step4.py 假设环境变量已通过其它途径注入（或上游 step7 先运行已加载）。

## 6. 集成拓扑摘要

```
 [chromium /snap/bin/chromium] ──┐
                                  ├── step1_3.py（信源 1/3/4/6） ─┐
 [urllib + ssl] ──────────────────┘                                │
                                                                   ├── 0新闻_粗筛.md
 [aiohttp] ── step1_3.py（并发取标题阶段） ────────────────────────┘
                                                                   │
 [openai → api.minimax.chat] ── step4.py（涉华判定） ──┐           │
                                                        ├── 1新闻_链接.md
 [openai → open.bigmodel.cn] ── step4.py（栏目分类）───┘           │
                                                                   │
 [chromium + urllib]    ─── step6.py（5 层正文抓取） ─── 2新闻_已审核.md
                                                                   │
 [openai → open.bigmodel.cn] ── step7.py（概述生成）─── 3新闻_概述.md
                                                                   │
 [chromium --screenshot + Pillow] ── step8.py ─── *.html / *.png
```
