---
schema_version: 1
doc_type: flow
flow_id: daily-pipeline
author: lmr
created_at: 2026-06-24 18:14:00
source_commit: 5f76a1a
generator: sillyspec-scan
---

# daily-pipeline

## 目标
每天从 7 个中国新闻信源生成 1 份双栏中文报纸（HTML + PNG），全程自动化，每日运行一次。

## 参与模块
- **orchestrator** (`run_all.sh`)：编排 5 个 step 串行执行，参数透传，失败短路
- **collector** (`step1_3.py`)：7 信源抓取 + HTTP-200 校验 → `0新闻_粗筛.md`
- **classifier** (`step4.py`)：质量过滤 + 涉华判定 + 关键词加权 + LLM 仲裁 → 选 top-10 → `1新闻_链接.md`
- **extractor** (`step6.py`)：5 层正文提取策略链 → `2新闻_已审核.md`
- **summarizer** (`step7.py`)：GLM-4 Flash 摘要 + 智能重试 ×3 + fallback → `3新闻_概述.md`
- **renderer** (`step8.py`)：CSS Grid 双栏 HTML + Chromium 截图 + Pillow 裁剪 → HTML/PNG

## 流程摘要

```text
./run_all.sh --date 2026-06-24
        │
        ▼
[step1_3] 7 信源 ──► aiohttp HTTP-200 校验 ──► 0新闻_粗筛.md (~200 条)
        │
        ▼
[step4]   读 0新闻_粗筛.md
          for each 文章:
            EXCLUDE_NEGATIVE 排除 → is_china_related(domain→keyword→LLM-minimax) →
            8 栏目 score → top-10 → 低置信度时 llm_classify_single(GLM)
          ──► 1新闻_链接.md (10 条精选)
        │
        ▼
[step6]   读 1新闻_链接.md
          for each URL:
            needs_chromium? chromium_dom : urllib →
            extract_body 5 层回退 → _is_contaminated? 二次清洗
          ──► 2新闻_已审核.md (10 篇正文)
        │
        ▼
[step7]   读 2新闻_已审核.md
          for each 篇:
            llm_summarize(GLM-4 Flash) → _why_invalid 校验 → RETRY_PROMPTS ×3 →
            仍失败 → fallback_summarize (首句+末句)
          ──► 3新闻_概述.md (10 条摘要)
        │
        ▼
[step8]   读 3新闻_概述.md
          parse_md → balance_columns (2^n 子集枚举) → build_html → 写 HTML →
          chromium --screenshot 2x DPR → crop_bottom_whitespace
          ──► YYYY-MM-DD_每日新中国_第N期.html + .png
```

## LLM 调用点（流程中）

| Step | 模块 | Provider | Model | 用途 | 调用频次 |
|------|------|----------|-------|------|----------|
| step4 | classifier | MiniMax | `minimax-m2.7` | 涉华回退 | 每次扫描 ~ 数十次 |
| step4 | classifier | Zhipu | `glm-4-flash` | 低置信度栏目仲裁 | 每次扫描 ~ 数次到十几次 |
| step7 | summarizer | Zhipu | `glm-4-flash` | 摘要生成 + 重试 | 每次扫描 ~ 10-30 次（含重试）|

## 失败回滚

| 失败点 | 处理 | 影响 |
|--------|------|------|
| `collector` 单信源抓取失败 | 该信源跳过，其他信源继续 | 少几条候选，不致命 |
| `collector` cnnc 抓取失败 | 三级回退链（cnnc → cnnpn → 跳过）| 单信源容错 |
| `classifier` LLM 调用异常 | `except Exception` 静默吞掉 → 涉华判定返回 False / 栏目仲裁回退到 keyword | 准确度下降，流水线继续 |
| `extractor` 单篇正文提取失败 | 5 层回退 + 污染检测 → 仍失败则该篇正文为空 | 该篇 summarizer 仅能用标题 |
| `summarizer` LLM 调用失败 | 3 次重试 → `fallback_summarize` 首句+末句拼接 | 摘要质量略低但管道继续 |
| `renderer` chromium 截图超时 | 120s timeout + `TimeoutExpired` 捕获 → 抛错 | 当日 PNG 缺失，HTML 仍可用 |
| **任一 step exit code != 0** | `run_all.sh` 立即 `exit 1` | 后续 step 不执行 |

## 关键文件接力契约

每个 step 都以**上一个 step 的输出 md** 为唯一输入，无 IPC，无内存共享。修改任一 step 的输出格式必须同步检查下游 parser：

- `step4.py:parse_0()` 读 `0新闻_粗筛.md`
- `step6.py` 读 `1新闻_链接.md`（`[date] 标题 | URL ✅` 格式）
- `step7.py:parse_2news()` 读 `2新闻_已审核.md`
- `step8.py:parse_md()` 读 `3新闻_概述.md`
