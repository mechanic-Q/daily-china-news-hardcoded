---
schema_version: 1
doc_type: knowledge
category: conventions
author: lmr
created_at: 2026-06-24 18:16:00
---

# Conventions

Daily 项目长期适用的命名/结构/接口约定。

## Step 脚本统一接口

5 个 step 脚本（`step1_3.py` / `step4.py` / `step6.py` / `step7.py` / `step8.py`）必须共享以下接口契约：

- 命令行参数：`--date YYYY-MM-DD`（可选，默认今天）+ `--dry-run`（可选）
- 解析方式：手写 `sys.argv` 解析（统一函数名 `parse_args()`），**不使用** argparse 库
- 入口结构：`parse_args()` → `def main(date_str, dry_run)` → `if __name__ == "__main__"`
- 退出码：异常用 `sys.exit(1)`，正常完成 exit 0
- `--dry-run` 必须跳过所有文件写入，仅打印将要做的事

修改任一 step 的命令行接口必须同步更新 `run_all.sh` 的参数透传。

## 输出目录规范

- 全局根目录：`BASE_DIR = Path("/mnt/e/每日新中国")`（硬编码在 5 个 step 顶部）
- 当日目录：`BASE_DIR / "{YYYY-MM-DD}"`
- 输出文件命名：
  - `0新闻_粗筛.md`（collector 输出，编号前缀 0）
  - `1新闻_链接.md`（classifier 输出，编号前缀 1）
  - `2新闻_已审核.md`（extractor 输出，编号前缀 2）
  - `3新闻_概述.md`（summarizer 输出，编号前缀 3）
  - `YYYY-MM-DD_每日新中国_第N期.html` 和 `.png`（renderer 输出）
- step5 编号空缺是历史原因，不要补

## 中文 + 状态 emoji 输出风格

- 注释和文档：中文为主，少量英文术语
- 控制台输出：`print(f"✅ ...")` / `print(f"❌ ...")` / `print(f"⚠ ...")` 状态前缀
- 字符串字面量：默认 UTF-8 encoding（`encoding="utf-8"`）

## LLM 调用约定

- 通过 `openai` Python SDK 调用 OpenAI 兼容 API（Zhipu / MiniMax）
- 客户端构造：`OpenAI(base_url=<provider-url>, api_key=os.getenv(<KEY>))`
- 调用方式：`client.chat.completions.create(model=..., messages=[{"role":"user","content":prompt}], ...)`
- 异常处理：`try / except Exception` 包裹，失败回退到非 LLM 路径
- API key 来源：`.env` 文件（gitignored），需 shell 先 export 或代码内 `load_dotenv()` (注：当前仅 step7 主动 load_dotenv)

## 错误处理风格

- 默认 `try / except Exception` 宽泛捕获（统计 step1_3=7 / step4=3 / step6=2 / step7=2 / step8=4）
- 单源/单条失败不中断，记录 print 后跳过
- 仅 orchestrator (`run_all.sh`) 用 `set -euo pipefail` 严格模式

## 分支策略

参考 `AGENTS.md`：每个 GSD phase 以 `phase-{NN}-{name}` 命名 feature 分支，PR merge 回 main。
