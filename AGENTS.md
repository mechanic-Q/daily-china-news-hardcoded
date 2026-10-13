# Project Instructions for AI Agents

## 项目概述

**每日新中国 · Daily China News** - 自动采集、筛选、分类、摘要、渲染全流程的 Python 新闻管道。每天从 7 个中国信源采集当日新闻，经 LLM 分类+摘要，渲染为手机壁纸风格报纸 (HTML + PNG)。

## 运行命令

Windows 原生（逻辑单一真源 = `run_all.sh`，须 Git 的 **MSYS bash** 执行；仓库文件在 WSL ext4，Windows 侧经 `\\wsl.localhost\Ubuntu\home\lmr\projects\Daily` 访问）。首次准备：`py -3 -m venv .venv && .venv/Scripts/pip install -r requirements.txt`

```powershell
# 推荐入口（无人值守/定时任务一律走这里）：run_all.ps1 自动甄别 Git 的 MSYS bash，
# 显式排除 System32 的 WSL bash。WSL bash 入口已随 Windows 原生化（2026-10-12）退役：
# venv/Chrome/LLM 全在 Windows 侧，WSL bash 下路径与工具语义均不成立，勿再改回
# `wsl -e bash` 调用（2026-10-13 9:00 定时任务即因此未产出，当日刊为 15:49 手动补跑）
powershell -NoProfile -ExecutionPolicy Bypass -File "\\wsl.localhost\Ubuntu\home\lmr\projects\Daily\run_all.ps1" --date 2026-10-14
```

```bash
# 等价入口：已在本机 Git Bash 时直接
cd //wsl.localhost/Ubuntu/home/lmr/projects/Daily && ./run_all.sh
# 完整管道（默认今天；run_all.sh 自动启停 Strata LLM 服务）；--dry-run 干跑
./run_all.sh --dry-run --date 2026-06-24

# 单步执行（用项目 venv）
.venv/Scripts/python.exe step1_3.py --date 2026-06-24
.venv/Scripts/python.exe step4.py --date 2026-06-24
.venv/Scripts/python.exe step6.py --date 2026-06-24
.venv/Scripts/python.exe step7.py --date 2026-06-24
.venv/Scripts/python.exe step8.py --date 2026-06-24

# 测试（stdlib unittest）
.venv/Scripts/python.exe -m unittest discover -s tests
```

CI：GitHub Actions（.github/workflows/test.yml，Python 3.12 单测；main 有分支保护，docs 改动也走 PR，required check 过后 admin merge）。

## 管道架构

5 个 Python 脚本顺序执行，数据通过文件接力（Markdown），输出到 `E:\每日新中国\{YYYY-MM-DD}\`：

```
step1_3.py  (采集+校验)  ->  0新闻_粗筛.md
step4.py    (分类+过滤)  ->  1新闻_链接.md    ← LLM × 2
step6.py    (正文提取)   ->  2新闻_已审核.md
step7.py    (摘要生成)   ->  3新闻_概述.md    ← LLM × 1
step8.py    (渲染成报)   ->  HTML + PNG
```

> **下游契约**：`3新闻_概述.md`（含当日报纸 PNG）是 video-pipeline（B站读报视频）直接读报模式的每日输入，9:15 定时任务自动消费。人工改写仅限摘要质量闸门修复路径（改写后重跑 `python3 step8.py --date <日期>`），其余情况不要手改产物。

关键设计决策：
- 步骤间无内存共享，纯文件接口，可独立运行
- `run_all.sh` 参数透传 (`--date`, `--dry-run`)，前一个步骤失败即终止
- 输出目录和 7 个信源 URL 都硬编码在脚本中，无外部配置
- **敏感词剔除（全链路）**：标题或正文含 `daily/common.py:BLOCKED_NEWS_TERMS`（习近平/习主席/习总书记）的条目整体剔除，报纸与视频均不出现。闸门设在 step4（标题级，进 LLM 前剔除省开销）、step6（标题+抓取后正文级）、step7（组装概述前最后一道，防重跑旧数据绕过）。日志省略敏感标题原文，不留存

## 7 个信源

| 信源 | 采集方式 |
|------|---------|
| 新华社 news.cn | chromium `--dump-dom` + 正则 `YYYYMMDD/c.html` |
| 参考消息 cankaoxiaoxi.com | JSON API (`list.json` × 9 频道) |
| 央视新闻 news.cctv.com | chromium `--dump-dom` |
| 央视军事 military.cctv.com | chromium `--dump-dom` |
| 中科院 cas.cn | urllib 静态 + `YYYYMM` 日期前缀 |
| 中核集团 cnnc.com.cn -> cnnpn.cn | chromium + 三级回退链 |
| 人民日报 paper.people.com.cn | `node_NN.html` 扫描 1-9 |

## LLM 调用点（共 6 处）

全部通过 `openai` SDK + 自定义 `base_url` 调用 OpenAI 兼容 API，统一由 `llm_client.py` 管理。

### 配置管理

- **唯一配置**：`llm.yaml` - 改一行即可切换 provider/model
- **抽象层**：`llm_client.py` - `get_client(call_site_id)` 返回 (OpenAI 实例, model, kwargs)；`call_llm(call_site_id, messages)` 一站式调用
- **切换 provider**：改 `llm.yaml` 顶层 `provider: <name>` + `model: <string>` 即可，不用改代码
- **本地后端**：`strata`（Strata 引擎 + Qwen3.8-Flash-Next IQ3_S @ 8080，Windows 原生，`bash start-llm.sh` 启动含自检，见 ADR-0005）。引擎默认开思维链、小 max_tokens 会拿空 content，`reasoning: "off"` 键不可去；加载后显存 ~15.7/16GB，与一切 GPU 负载互斥（run_all.sh/start-llm.sh 用 nvidia-smi 阈值把关）。27B 旧栈（kvmem 27182 / qwen-local 8899）随模型文件删除退役，见 ADR-0004
- **环境变量**：`.env` 中 `STRATA_API_KEY`（本地 Strata，值不校验）+ `ZHIPU_API_KEY` / `MINIMAX_API_KEY`（应急备用）

### 调用点总览

温度 / max_tokens / timeout 以 `llm.yaml` 的 `call_sites` 为唯一真源。

| call_site_id | 位置 | 用途 |
|---|---|---|
| `china-relevance` | `step4.py:llm_is_china_related()` | 涉华判定兜底 |
| `column-classify` | `step4.py:llm_classify_single()` | 8 栏目分类仲裁 |
| `column-score` | `step4.py:score_signals()` | 栏目新闻价值评分 |
| `event-dedup` | `step4.py:llm_review_duplicate_candidates()` | 跨信源同事件去重 |
| `summarize` | `step7.py:llm_summarize()` | 新闻摘要生成 |
| `monthly-overview` | `monthly_report.py` | 月度报告综述 |

### 旧 provider 切回

```bash
# 切回 Zhipu GLM-4 Flash
# 编辑 llm.yaml: 改 provider: zhipu, model: glm-4-flash
# 重跑流水线，不需改代码
```

## 关键文件

| 文件 | 职责 |
|------|------|
| `step1_3.py` | 7 信源异步采集器，HTTP-200 校验 |
| `step4.py` | 关键词加权评分 + LLM 分类，选前 10 |
| `step6.py` | 5 层正文提取策略链（TRS_Editor -> article -> class 匹配 -> `<p>` 回退）|
| `step7.py` | LLM 摘要生成 + 诊断重试 |
| `step8.py` | HTML 双栏渲染 + Chromium 截图 + Pillow 裁剪 |
| `run_all.sh` | 管道编排 |

## 分支策略（自 Phase 6 起）

每个 GSD phase 的 discuss 阶段开头，必须先创建 feature 分支：

```bash
git checkout -b phase-{NN}-{name}
```

例如 Phase 7 讨论开头：`git checkout -b phase-07-column-balance`

所有 plan/execute/verify 的 commits 在该分支上进行。ship 时 push -> `gh pr create` -> merge，然后切回 main 继续。

## 分支自动检测

每次 GSD phase 的 discuss 阶段，在进入灰色地带讨论前（present_gray_areas），检测当前 git 分支：

- 如果在 `main` 上 -> 自动 `git checkout -b phase-{NN}-{slug}`
- 如果已在 feature 分支上 -> 正常继续

这确保即使忘记手动建分支，workflow 也能自动补救。

## 提交与文档流（2026-10-13 起）

- **docs 直推 main**：AGENTS.md、docs/、ADR 等纯文档改动直接 commit 到 main，不建分支不走 PR
- **实现票走 feat+PR**：实现类改动建 feat 分支 → PR → merge，PR 正文用**中文详记踩坑**
- **README 只在里程碑动**：平时不动 README
- **graphify 开工先查一把**：实现票开工先跑 `node .opencode/get-shit-done/bin/gsd-tools.cjs graphify status` 查能力图谱（当前 disabled；启用：`gsd-tools config-set graphify.enabled true`）

## Agent skills

### Issue tracker

Issues live as GitHub issues (uses `gh` CLI). See `docs/agents/issue-tracker.md`.

### Triage labels

Five canonical roles map to labels of the same name. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context - one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

## 已知问题

- `balance_columns()` 是 O(2^n) 暴力枚举，n≤8 够用
- 依赖外部 Chrome（`daily/http.py:CHROMIUM` 单点硬编码，缺装则采集降级/渲染失败）
- `step1_3.py` 抓取有 tenacity 重试（3 次指数退避+抖动），无磁盘缓存（cnnc 三级回退除外）
- `daily_china_news_full_to_feishu.py`（飞书/视频投递编排）：飞书凭据已迁 Windows 侧 ~/.hermes/.env（2026-10-13，发送链路已验证）；管道调用与视频构建仍绑定 WSL（~/projects/Daily + ~/.hermes 视频技能 + ffmpeg）
