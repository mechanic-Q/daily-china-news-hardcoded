# Project Instructions for AI Agents

## 项目概述

**每日新中国 · Daily China News** - 自动采集、筛选、分类、摘要、渲染全流程的 Python 新闻管道。每天从 7 个中国信源采集当日新闻，经 LLM 分类+摘要，渲染为手机壁纸风格报纸 (HTML + PNG)。

## 运行命令

```bash
# 完整管道（默认今天）
./run_all.sh
./run_all.sh --date 2026-06-24
./run_all.sh --dry-run --date 2026-06-24

# 单步执行
python3 step1_3.py --date 2026-06-24
python3 step4.py --date 2026-06-24
python3 step6.py --date 2026-06-24
python3 step7.py --date 2026-06-24
python3 step8.py --date 2026-06-24

# 测试（stdlib unittest）
python3 -m unittest discover -s tests
```

无 CI/CD。

## 管道架构

5 个 Python 脚本顺序执行，数据通过文件接力（Markdown），输出到 `/mnt/e/每日新中国/{YYYY-MM-DD}/`：

```
step1_3.py  (采集+校验)  ->  0新闻_粗筛.md
step4.py    (分类+过滤)  ->  1新闻_链接.md    ← LLM × 2
step6.py    (正文提取)   ->  2新闻_已审核.md
step7.py    (摘要生成)   ->  3新闻_概述.md    ← LLM × 1
step8.py    (渲染成报)   ->  HTML + PNG
```

关键设计决策：
- 步骤间无内存共享，纯文件接口，可独立运行
- `run_all.sh` 参数透传 (`--date`, `--dry-run`)，前一个步骤失败即终止
- 输出目录和 7 个信源 URL 都硬编码在脚本中，无外部配置

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

## LLM 调用点（共 3 处）

全部通过 `openai` SDK + 自定义 `base_url` 调用 OpenAI 兼容 API，统一由 `llm_client.py` 管理。

### 配置管理

- **唯一配置**：`llm.yaml` - 改一行即可切换 provider/model
- **抽象层**：`llm_client.py` - `get_client(call_site_id)` 返回 (OpenAI 实例, model, kwargs)；`call_llm(call_site_id, messages)` 一站式调用
- **切换 provider**：改 `llm.yaml` 顶层 `provider: <name>` + `model: <string>` 即可，不用改代码
- **环境变量**：`.env` 中 `NINEROUTER_API_KEY`（主 provider）+ `ZHIPU_API_KEY` / `MINIMAX_API_KEY`（应急保留）

### 调用点总览

| call_site_id | 位置 | 用途 | 关键参数 |
|---|---|---|---|
| `china-relevance` | `step4.py:llm_is_china_related()` | 涉华判定兜底 | temp=0.7, max_tokens=10, timeout=15s |
| `column-classify` | `step4.py:llm_classify_single()` | 8 栏目分类仲裁 | temp=0.7, max_tokens=10, timeout=15s |
| `summarize` | `step7.py:llm_summarize()` | 新闻摘要生成 | temp=0.7, max_tokens=300, timeout=30s, 智能重试×3 |

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

## Agent skills

### Issue tracker

Issues live as GitHub issues (uses `gh` CLI). See `docs/agents/issue-tracker.md`.

### Triage labels

Five canonical roles map to labels of the same name. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context - one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

## 已知问题

- `balance_columns()` 是 O(2^n) 暴力枚举，n≤8 够用
- 无 pip `requirements.txt`，依赖为 `openai` `aiohttp` `Pillow` `python-dotenv`
- 依赖外部 `/snap/bin/chromium`
- `step1_3.py` 无重试和缓存（cnnc 三级回退除外）
