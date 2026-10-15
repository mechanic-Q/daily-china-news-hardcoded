---
name: daily-china-news
description: 每日新中国（Daily China News）新闻管道操作技能：7 个中国信源采集 → LLM 分类/去重 → 正文提取 → 摘要 → 渲染手机壁纸风报纸（HTML+PNG）。Use when 用户要跑/补跑当日或指定日期的报纸、管道某一步失败要排障、要改信源或 LLM provider、或需要报纸产物喂给 video-pipeline 读报。
---

# daily-china-news

《每日新中国》每日报纸管道。一条命令从 7 个信源采集当日新闻，经 LLM 分类+摘要，渲染为手机壁纸风格报纸（HTML + PNG）。

本文件是**该技能的规范源**（随仓库分发）；本机安装位是 `~/.agents/skills/daily-china-news/SKILL.md`，内容与本文件保持一致。

## 项目位置

| 项 | 值 |
|---|---|
| 本机检出 | `E:\Daily\daily-china-news-hardcoded`（clone 自上游） |
| git | `origin` = 上游仓库；同步用 `git pull --ff-only` |
| venv | `.venv/Scripts/python.exe`（已装好，146M） |
| 产物根 | `E:\每日新中国\{YYYY-MM-DD}\` |
| 文档真源 | 项目内 `AGENTS.md`（项目约定）、`USER_MANUAL.md`、`docs/adr/`、`docs/agents/` |

**先读项目自己的 `AGENTS.md` 再动手**——它是该项目的 agent 约定真源，本 skill 只做入口与红线摘要，不复制它。

> 历史坑：文档里出现过 WSL 路径 `\\wsl.localhost\Ubuntu\home\lmr\projects\Daily`。WSL 入口已随 2026-10-12 Windows 原生化退役（WSL 下 venv/Chrome/LLM 路径与工具语义均不成立），该 UNC 路径当前从 Windows 侧访问是 `E_ACCESSDENIED`。**一律走 E: 检出**。

## 跑法

### 整条管道（推荐入口）

```powershell
# 无人值守/定时任务一律走这里：run_all.ps1 自动甄别 Git 的 MSYS bash，
# 显式排除 System32 的 WSL bash（WSL bash 不容忍 CRLF，且缺 taskkill/nohup/netstat 语义）
powershell -NoProfile -ExecutionPolicy Bypass -File "E:\Daily\daily-china-news-hardcoded\run_all.ps1" --date 2026-10-14
```

省略 `--date` 即跑今天。加 `--dry-run` 干跑。参数原样透传给 `run_all.sh`（逻辑单一真源是 bash），前一步失败即终止。

已在本机 Git Bash 时等价：

```bash
cd /e/Daily/daily-china-news-hardcoded
./run_all.sh --date 2026-10-14
```

### 单步（用项目 venv）

```bash
P=E:/Daily/daily-china-news-hardcoded
$P/.venv/Scripts/python.exe step1_3.py --date 2026-06-24   # 采集+校验
$P/.venv/Scripts/python.exe step4.py   --date 2026-06-24   # 分类+过滤
$P/.venv/Scripts/python.exe step6.py   --date 2026-06-24   # 正文提取
$P/.venv/Scripts/python.exe step7.py   --date 2026-06-24   # 摘要生成
$P/.venv/Scripts/python.exe step8.py   --date 2026-06-24   # 渲染成报
```

### 测试

```bash
cd /e/Daily/daily-china-news-hardcoded && .venv/Scripts/python.exe -m pytest tests/ --ignore=tests/manual
```

CI 同款命令（`.github/workflows/test.yml`，Python 3.12，required check 名 `test (3.12)`）。

## 管道架构（文件接力，步骤间无内存共享）

```
step1_3.py 采集+校验 → 0新闻_粗筛.md
step4.py   分类+过滤 → 1新闻_链接.md     ← LLM × 2
step6.py   正文提取   → 2新闻_已审核.md
step7.py   摘要生成   → 3新闻_概述.md     ← LLM × 1
step8.py   渲染成报   → HTML + PNG
```

产物全部落在 `E:\每日新中国\{YYYY-MM-DD}\`。步骤可独立运行，便于失败后从断点续跑。

## LLM 后端

- **唯一配置**：`llm.yaml`。切 provider/model 只改顶层 `provider:` + `model:`，不改代码。当前 `provider: strata` / `model: qwen3.8-flash-next-iq3_s`。
- **抽象层**：`llm_client.py` —— `get_client(call_site_id)` 返回 `(OpenAI 实例, model, kwargs)`；`call_llm(call_site_id, messages)` 一站式调用。全部走 `openai` SDK + 自定义 `base_url`。
- **本地后端 Strata**：`bash start-llm.sh` 后台拉起 + 健康自检（Windows 原生，端口 8080，`STRATA_HOME=E:/AI/LLM/Strata`）。`run_all.sh` 会自动启停它。
  - **GPU 红线**：模型加载后显存 15.7/16.3GB，空闲基线 ~600MB。`start-llm.sh` 用 `nvidia-smi` 阈值（`VRAM_LIMIT_MB=2000`）把关，**与一切其它 GPU 负载互斥**；GPU 被占时拒绝启动，不要替用户杀进程。
  - **CoT 坑**：引擎默认开思维链，小 `max_tokens` 会拿到空 content（实测 `content=null`）。自检与 `llm.yaml` 都带 `reasoning_effort=none` / `reasoning: "off"`，该键不可删。
  - 端口改 `start-llm.sh` 的 `PORT` 时必须同步改 `llm.yaml` 的 `strata.base_url`。
- **凭据**：`.env` 里 `STRATA_API_KEY`（本地，值不校验）+ 注释掉的 `ZHIPU_API_KEY` / `MINIMAX_API_KEY`（云应急回滚用，切 provider 时才需填真 key）。
- **6 个调用点**（温度/max_tokens/timeout 以 `llm.yaml: call_sites` 为唯一真源）：

| call_site_id | 位置 | 用途 |
|---|---|---|
| `china-relevance` | `step4.py:llm_is_china_related()` | 涉华判定兜底 |
| `column-classify` | `step4.py:llm_classify_single()` | 8 栏目分类仲裁 |
| `column-score` | `step4.py:score_signals()` | 栏目新闻价值评分 |
| `event-dedup` | `step4.py:llm_review_duplicate_candidates()` | 跨信源同事件去重 |
| `summarize` | `step7.py:llm_summarize()` | 新闻摘要生成 |
| `monthly-overview` | `monthly_report.py` | 月度报告综述 |

## 7 个信源

| 信源 | 采集方式 |
|---|---|
| 新华社 news.cn | chromium `--dump-dom` + 正则 `YYYYMMDD/c.html` |
| 参考消息 cankaoxiaoxi.com | JSON API（`list.json` × 9 频道） |
| 央视新闻 news.cctv.com | chromium `--dump-dom` |
| 央视军事 military.cctv.com | chromium `--dump-dom` |
| 中科院 cas.cn | urllib 静态 + `YYYYMM` 日期前缀 |
| 中核集团 cnnc.com.cn → cnnpn.cn | chromium + 三级回退链 |
| 人民日报 paper.people.com.cn | `node_NN.html` 扫描 1-9 |

输出目录与 7 个信源 URL **硬编码在脚本中**，无外部配置。

## 红线（写死，不可违反）

1. **敏感词全链路剔除**：标题或正文含 `daily/common.py:55 BLOCKED_NEWS_TERMS`（`['习近平', '习主席', '习总书记']`）的条目整体剔除，报纸与视频均不得出现。三道闸门：step4（标题级，进 LLM 前剔除省开销）、step6（标题+抓取后正文级）、step7（组装概述前最后一道，防重跑旧数据绕过）。日志省略敏感标题原文，不留存。
2. **产物不手改**：`3新闻_概述.md`（含当日报纸 PNG）是下游契约。唯一允许的人工改写路径是摘要质量闸门修复——改写后**必须重跑** `python step8.py --date <日期>`，其余情况不要手改任何产物。
3. **GPU 独占**：Strata 与任何其它 GPU 负载互斥，见上。
4. **依赖外部 Chrome**：`daily/http.py:11 CHROMIUM = "C:/Program Files/Google/Chrome/Application/chrome.exe"` 单点硬编码，缺装则采集降级/渲染失败。

## 仓库约定（提交/文档流，2026-10-13 起）

详见 `AGENTS.md:135` 起。要点：

- **docs 直推 main**：AGENTS.md、docs/、ADR 等纯文档改动意图是直接 commit 到 main，不建分支不走 PR。
- **但 main 有分支保护**（`enforce_admins: true`，required check `test (3.12)`，`strict` + `required_linear_history`）：**直接 push 会被拒，owner 也一样**。实际路径是 `docs/*` 分支 → PR → CI 绿 → merge（历史 PR #64/#67 均如此）。
- **实现票走 feat+PR**：实现类改动建 feat 分支 → PR → merge，PR 正文用**中文详记踩坑**。
- **README 只在里程碑动**：平时不动 README。
- **graphify 开工先查一把**：`node .opencode/get-shit-done/bin/gsd-tools.cjs graphify status`（当前 disabled；启用：`gsd-tools config-set graphify.enabled true`）。
- `.gitattributes` 锁 `*.sh text eol=lf`——别用会写 CRLF 的工具改 shell 脚本。

## 下游契约

`E:\每日新中国\{日期}\3新闻_概述.md` 是 **video-pipeline**（B 站读报视频）直接读报模式的每日输入，由 9:15 定时任务自动消费。改动这一步的产物格式前先确认 video-pipeline 的读取约定（见 `video-pipeline` skill）。

## 已知问题

- `balance_columns()` 是 O(2^n) 暴力枚举，n≤8 够用。
- `step1_3.py` 抓取有 tenacity 重试（3 次指数退避+抖动），**无磁盘缓存**（cnnc 三级回退除外）。
- `daily_china_news_full_to_feishu.py`（飞书/视频投递编排）：飞书凭据已迁 Windows 侧 `~/.hermes/.env`（2026-10-13，发送链路已验证）；管道调用与视频构建仍绑定 WSL。

## 排障入口

- 先看 `E:\每日新中国\logs\` 当日日志，再按上面「单步」从失败那一步续跑。
- 报错「项目虚拟环境不存在」→ 按 `run_all.sh` 提示重建：`py -3 -m venv .venv && .venv/Scripts/pip install -r requirements.txt`。
- `run_all.ps1` 报「未找到 Git for Windows 的 bash.exe」→ 确认 Git 安装位（候选：`%ProgramFiles%\Git\bin\bash.exe`、`%ProgramFiles(x86)%\Git\bin\bash.exe`、`%LOCALAPPDATA%\Programs\Git\bin\bash.exe`），它按设计排除 System32 的 WSL bash。
- 需要项目内部约定/提交规矩/分支策略时读项目根 `AGENTS.md`；issue/标签/领域文档见 `docs/agents/`。

## 沙箱注意

`E:\Daily\...` 与 `E:\每日新中国\...` 在 DSH 的 workspace-write 策略下**只读**；`danger-full-access` 下可直接写。若沙箱回落到 workspace-write 而要改项目源码或写产物，需先提权或由用户自行执行。
