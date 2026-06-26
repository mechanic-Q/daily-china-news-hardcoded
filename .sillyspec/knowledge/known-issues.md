---
schema_version: 1
doc_type: knowledge
category: known-issues
author: lmr
created_at: 2026-06-24 18:16:00
---

# Known Issues

Daily 项目已知坑、历史兼容问题、维护陷阱。

## 🔴 MiniMax 模型字符串可能无效

- 位置：`step4.py:88`
- 当前值：`model="minimax-m2.7"`
- 风险：MiniMax 官方公开 model id 通常为 `abab6.5*` 或 `MiniMax-M2`，"minimax-m2.7" 未在官方文档出现
- 影响：调用失败被 `except Exception: return False` **静默吞掉**，涉华判定永远返回 False（即所有需要 LLM 兜底的标题都被判为"不涉华"，被过滤掉）
- 排查建议：临时打印异常确认是否真的成功
- 状态：**等待 9router 切换后一并修正**

## 🔴 BASE_DIR 硬编码

- 位置：所有 5 个 step 顶部 `BASE_DIR = Path("/mnt/e/每日新中国")`
- 风险：跨平台不可移植，新机器/容器部署需逐文件改
- 缓解：可改为读取环境变量或 `.env`

## 🔴 LLM 异常被宽泛 except 静默

- `step4.py:79-94` `llm_is_china_related`：`except Exception: return False`
- `step4.py:209-238` `llm_classify_single`：异常时回退到 keyword 分类
- `step7.py:llm_summarize`：异常 → 重试 → 仍失败 → fallback
- 风险：API key 错误、模型 id 无效、网络故障都被静默
- 维护建议：调试时临时在 except 中加 `print(traceback.format_exc())`

## 🟡 step1_3 / step6 重复定义 chromium_dom

- 位置：`step1_3.py:69` 和 `step6.py:48`
- 风险：函数同名但参数和超时不同（step1_3 timeout=35 / budget=20000；step6 timeout=45 / budget=30000），修改一处不会同步另一处
- 维护建议：保留两份（功能上不完全相同），但任何参数调整需 grep 两个文件

## 🟡 python-dotenv 在 README 提及但代码未统一使用

- README 提及 `pip install python-dotenv`
- 实际代码：仅 `step7.py` 主动 `load_dotenv()`，其他 step 直接 `os.getenv()`
- 风险：从 shell 跑 `python3 step4.py` 时若未 export，`.env` 不会自动加载
- 缓解：`./run_all.sh` 跑前 `set -a; source .env; set +a`，或者在所有 step 顶部统一 `load_dotenv()`

## 🟡 balance_columns O(2^n) 性能上限

- 位置：`step8.py:137`
- 实现：`for mask in range(1 << n)` 全枚举（n = 栏目数）
- 当前：n ≤ 8 → 256 次迭代，毫秒级，无压力
- 风险：未来若每栏目细分（如"科技 → AI/芯片/算力" 子栏目），n 上升到 12+，2^12 = 4096，可能仍可接受，但 n=20+ 会爆
- 维护建议：n 超过 10 时改用贪心或动态规划

## 🟡 无 requirements.txt / pyproject.toml

- 影响：依赖版本未锁定
- 隐式依赖：`openai`, `aiohttp`, `Pillow`, `python-dotenv`
- 缓解：建议生成 `requirements.txt`，至少锁定 openai SDK 版本（行为可能随版本变化）

## 🟡 信源 URL/正则硬编码

- 位置：`step1_3.py:399` `SOURCES` + 各 `fetch_*` 函数内的日期正则
- 风险：信源改版需要改代码 + 重新发布
- 缓解：可外置到 YAML 配置

## 🟢 step5 编号空缺

- `run_all.sh` 中 `STEPS=(step1_3 step4 step6 step7 step8)`，跳过 5
- 原因：历史合并（原 step5 已合入 step4），不需要补
- 不修：不要新增 step5 文件

## 🟢 chromium snap 路径

- `/snap/bin/chromium` 在 5 个 step 中硬编码
- snap 路径在 Ubuntu 上稳定，但在容器中可能不存在
- 缓解：可改为 `shutil.which("chromium")` 或环境变量

## 历史里程碑

- **v1.0 (2026/04-05)**：基础流水线 5 step 跑通
- **v1.1 (2026/06)**：Quality Fix milestone，9 个 phase，主要修正分类准确度（GLM-4 Flash 逐条仲裁、阈值调整、关键词优化）
- **当前状态**：v1.1 已 ship（2026/06/22），main 分支干净
