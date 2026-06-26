---
author: lmr
created_at: 2026-06-24 18:50:00
change: 2025-06-11-llm-console
stage: brainstorm
schema_version: 1
doc_type: design
---

# Design — Daily LLM 配置统一管理

## 1. 背景

Daily 项目当前 3 处 LLM 调用点散落在 `step4.py` 和 `step7.py` 中：

- `step4.py:86-88` 涉华兜底 → MiniMax `minimax-m2.7`（model id 疑似无效，known-issue）
- `step4.py:225-232` 栏目分类仲裁 → Zhipu `glm-4-flash`
- `step7.py:159-170` 摘要生成 → Zhipu `glm-4-flash`

每处独立构造 `OpenAI(base_url=..., api_key=...)`，model 字符串硬编码，切换 provider 需要逐文件改 5+ 处常量。配置不可见、不可比较、不可一键切换。

## 2. 设计目标

1. **统一管理**：3 处 LLM 调用全部走单一抽象层，配置写在一个 YAML 文件
2. **可一键切换 provider/model**：改 yaml 一行即可切回 Zhipu 应急
3. **未来扩展友好**：加新 LLM 调用点零样板代码（写 `call_sites.<new-id>` + 一处 `call_llm("new-id", ...)`）
4. **失败可见**：LLM 异常时打印 traceback，但保留 fallback 不中断流水线
5. **不引入新 SDK**：沿用 openai SDK + base_url 模式（符合现有 patterns.md）

## 3. 非目标

- ❌ 不实现 CLI / TUI / Web UI 控制台（D-003 用户明确「只要 YAML」）
- ❌ 不实现运行时 primary→secondary 自动 fallback（D-006，简化实现）
- ❌ 不动 `step1_3.py` / `step6.py` / `step8.py`（无 LLM 调用）
- ❌ 不重构 `_why_invalid` / `RETRY_PROMPTS` / `fallback_summarize`（业务逻辑保留）
- ❌ 不引入 vision profile 预留结构（D-009，未来真要加再扩 schema）
- ❌ 不修改 BASE_DIR 硬编码（独立 known-issue，本变更不打包）

## 4. 拆分判断

不拆分。理由：
- 3 个调用点 + 1 个 config loader + 1 个 client 工厂 = 单变更可完整交付
- 无独立的可交付子模块（yaml schema、client 工厂、3 处替换是一体的）
- 无角色权限、无审批流、无批量模式

## 5. 总体方案

### Phase 1：配置基础设施（先建后用）
- 新增 `/mnt/e/Daily/llm.yaml` —— 单一真相
- 新增 `/mnt/e/Daily/llm_client.py` —— 加载 + 校验 + 客户端工厂
- 新增 `/mnt/e/Daily/requirements.txt` —— 锁定依赖（PyYAML + openai + aiohttp + Pillow + python-dotenv）

### Phase 2：调用点替换
- 改 `step4.py` 2 处 LLM 调用 → `call_llm("china-relevance", ...)` / `call_llm("column-classify", ...)`
- 改 `step7.py` 1 处 LLM 调用 → `call_llm("summarize", ...)`，保留外层重试 / 诊断 / fallback 循环
- 3 处 except 块新增 `traceback.print_exc()`

### Phase 3：文档与环境
- `.env` 追加 `NINEROUTER_API_KEY=<placeholder>`，旧 key 保留
- 更新 `CLAUDE.md` 的「LLM 调用点」章节

## 6. 文件变更清单

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 新增 | `/mnt/e/Daily/llm.yaml` | LLM 配置单一真相 |
| 新增 | `/mnt/e/Daily/llm_client.py` | `load_config` / `get_client` / `call_llm` 三函数 |
| 新增 | `/mnt/e/Daily/requirements.txt` | 锁定依赖版本 |
| 修改 | `/mnt/e/Daily/step4.py` | 2 处 LLM 调用替换 + import + traceback |
| 修改 | `/mnt/e/Daily/step7.py` | 1 处 LLM 调用替换 + import + traceback |
| 修改 | `/mnt/e/Daily/.env` | 追加 `NINEROUTER_API_KEY` 占位 |
| 修改 | `/mnt/e/Daily/CLAUDE.md` | 「LLM 调用点」章节重写指向 llm.yaml |

不动：`step1_3.py` / `step6.py` / `step8.py` / `run_all.sh`。

## 7. 接口定义

### 7.1 `llm.yaml` schema

```yaml
# author: lmr, created_at: 2026-06-24
# 全局默认 LLM provider（3 个调用点都引用）
provider: 9router            # 必须在 providers 段存在
model: low                    # 具体 model 字符串

providers:                    # provider 端点定义
  9router:
    base_url: https://9router.example.com/v1  # ⚠️ TODO 用户后补
    api_key_env: NINEROUTER_API_KEY
  zhipu:                      # 应急切回保留
    base_url: https://open.bigmodel.cn/api/paas/v4/
    api_key_env: ZHIPU_API_KEY
  minimax:                    # 应急切回保留
    base_url: https://api.minimax.chat/v1
    api_key_env: MINIMAX_API_KEY

call_sites:                   # 每个调用点的请求参数
  china-relevance:
    temperature: 0.7          # 统一 0.7（D-011）
    max_tokens: 10
    timeout: 15
  column-classify:
    temperature: 0.7          # 统一 0.7（D-011）
    max_tokens: 10
    timeout: 15
  summarize:
    temperature: 0.7          # 统一 0.7（D-011）
    max_tokens: 300
    timeout: 30
```

### 7.2 `llm_client.py` 公开 API

```python
class ConfigError(Exception): pass
class LLMCallError(Exception): pass

def load_config() -> dict:
    """读取 llm.yaml，校验 yaml 格式完整性。
    
    校验内容：
    - 顶层 provider 必须在 providers 段中存在
    - 顶层 model 必须是非空字符串
    - 每个 provider 必须有 base_url + api_key_env
    - call_sites 段每个条目必须有 temperature/max_tokens/timeout
    
    **不**校验 api_key_env 对应的环境变量存在性（D-010 宽松模式）
    
    校验失败抛 ConfigError，不静默。
    缓存：functools.lru_cache(maxsize=1)。"""

def get_client(call_site_id: str) -> tuple:
    """返回 (openai.OpenAI 实例, model 字符串, kwargs dict)
    
    kwargs 含 call_site 段的 temperature / max_tokens / timeout（per-call timeout，
    通过 chat.completions.create(..., timeout=N) 传入，非 client 构造参数）。
    
    若 os.getenv(api_key_env) 返回 None，抛 LLMCallError("Missing API key for <provider>: <env_var>")。
    未知 call_site_id 抛 ConfigError。"""

def call_llm(call_site_id: str, messages: list, **override) -> str:
    """一次性封装：构造 client + chat.completions.create + 错误处理。
    
    返回：response.choices[0].message.content 字符串
    异常：
    - 失败时打印 traceback.print_exc() 到 stderr（D-007）
    - 重新抛出 LLMCallError，由上游决定 fallback
    - key 缺失也走该路径（D-010）
    
    override 可覆盖 temperature / max_tokens / timeout / model（被 step7.py 重试循环用来传不同 messages）。"""
```

### 7.3 调用点替换前后

**`step4.py:79-94 llm_is_china_related` 替换前**：
```python
def llm_is_china_related(title):
    api_key = os.getenv("MINIMAX_API_KEY", "").strip()
    if not api_key: return False
    try:
        from openai import OpenAI
        client = OpenAI(base_url="https://api.minimax.chat/v1", api_key=api_key)
        resp = client.chat.completions.create(
            model="minimax-m2.7",
            messages=[{"role": "user", "content": f"..."}],
        )
        return "是" in resp.choices[0].message.content
    except Exception:
        return False
```

**替换后**：
```python
def llm_is_china_related(title):
    try:
        from llm_client import call_llm
        ans = call_llm("china-relevance", messages=[{"role": "user", "content": f"..."}])
        return "是" in ans
    except Exception:
        import traceback; traceback.print_exc()
        return False
```

`column-classify` 和 `summarize` 同样模式替换。`step7.py` 的外层重试 / `_why_invalid` / `RETRY_PROMPTS` / `fallback_summarize` 循环不动，仅把内层 OpenAI 构造调用换成 `call_llm("summarize", ...)`。

## 8. 数据模型

无数据库。配置文件即数据模型，schema 见 7.1。

## 9. 兼容策略

### 9.1 未配置时行为不变
**不适用** —— 本变更不引入"可选"开关，而是把 3 处 LLM 调用全部迁移到新抽象层。配置文件必须存在。

### 9.2 旧逻辑的回退路径
应急切回 Zhipu：
1. 编辑 `llm.yaml`，改顶层 `provider: zhipu`, `model: glm-4-flash`
2. 确认 `.env` 中 `ZHIPU_API_KEY` 仍有效
3. 重跑 `./run_all.sh --date YYYY-MM-DD`
4. 完成。无需改任何代码

应急切回 MiniMax 涉华兜底：
1. 编辑 `llm.yaml`，改顶层 `provider: minimax`, `model: <user-fills>`
2. 注意：MiniMax `m2.7` 是 known-issue model id，切回时建议填实测可用的 id（如 `abab6.5*`）

### 9.3 不改变的内容
- `0新闻_粗筛.md` / `1新闻_链接.md` / `2新闻_已审核.md` / `3新闻_概述.md` 文件格式（接力契约不动）
- `BASE_DIR = Path("/mnt/e/每日新中国")` 输出目录
- `run_all.sh` 调用顺序和参数
- 8 栏目分类策略
- `_why_invalid` / `RETRY_PROMPTS` / `fallback_summarize` 算法
- 7 信源抓取逻辑

## 10. 风险登记

| 编号 | 风险 | 等级 | 应对策略 |
|------|------|------|---------|
| R-01 | base_url 占位 `https://9router.example.com/v1` 是假地址 | P0 | yaml 中加 `TODO` 注释 + verify 阶段必须由用户填入真实地址再实测 |
| R-02 | 9router low 实际 model 字符串可能不是 "low" | P1 | 由用户在 verify 前确认；llm.yaml 中加 `TODO` 注释指明可能要改 |
| R-03 | PyYAML 未安装会导致 import 错误 | P1 | 新增 requirements.txt，verify 阶段先 `pip install -r requirements.txt` |
| R-04 | 9router 接口与 OpenAI 兼容协议存在差异（如响应格式、token 计费字段） | P2 | 抽象层只用 chat.completions.create 标准方法，不依赖 provider 特有字段；测试时 dry-run 一次确认 |
| R-05 | `call_llm` 抛 LLMCallError 后上游 except 必须捕获，否则流水线中断 | P1 | 替换时确认 3 处 except Exception 块都保留并加 traceback |
| R-06 | 旧 model 字符串 `minimax-m2.7` 可能是占位符（known-issue），切到 9router 后兜底涉华判定的实际质量未知 | P2 | verify 阶段对比新旧涉华判定结果（同一标题集），偏差大于 10% 报告 |
| R-07 | functools.lru_cache 缓存 load_config 后，运行时改 yaml 不生效 | P2 | 文档说明：改完 yaml 必须重启进程；step 脚本本身就是一次性执行所以无影响 |
| R-08 | step7.py 重试循环里依赖 `for attempt in range(3)`，call_llm 抛异常即跳出当前 attempt 进入下次。需确保 call_llm 异常被 step7 内层 except 捕获，不破坏 3 次重试 | P0 | step7.py 替换时把 `call_llm("summarize", ...)` 放在现有 `try` 块内（与 `client.chat.completions.create` 同位置）；外层重试循环不动；call_llm 抛 LLMCallError 后 except 兜底走下次 attempt |
| R-09 | temperature 从 0.1/0/0.3 统一改为 0.7 (D-011)，可能导致涉华判定 / 栏目分类的稳定性下降（高温度更随机）| P2 | verify 阶段对比新旧涉华判定 + 分类结果，偏差大就回调 yaml temperature |

## 11. 决策追踪

本变更引用以下 D-xxx@vN 决策（详见 `decisions.md`）：

| 决策 ID | 主题 | 覆盖章节 |
|---------|------|----------|
| D-001@v1 | 9router 私有，base_url 待补 | 7.1（TODO 占位）, R-01 |
| D-002@v1 | "low" 是 9router 自定义档位字符串 | 7.1, R-02 |
| D-003@v1 | 仅 YAML 配置，不做 CLI / TUI / Web | 3 非目标 |
| D-004@v1 | 新增 NINEROUTER_API_KEY，旧 key 保留 | 7.1 providers 段, 9.2 应急切回 |
| D-005@v1 | 默认全局 + 单点 override（被 D-009 简化）| 7.1 + call_sites |
| D-006@v1 | 手动切回，不做运行时 fallback | 3 非目标, 9.2 |
| D-007@v1 | LLM 异常打 traceback，保留 fallback | 7.2 `call_llm`, 7.3 except 块 |
| D-008@v1 | 实现采用方案 B（抽象层） | 5 总体方案 |
| D-009@v1 | 统一管理，无 vision profile 预留 | 7.1 schema |
| D-010@v1 | Key 缺失策略宽松，load_config 不检 key | 7.2 `load_config` / `call_llm` |
| D-011@v1 | Temperature 统一 0.7 | 7.1 call_sites |

所有 D-xxx@v1 全部覆盖，无未决项。

## 12. 自审

### 12.1 需求覆盖
- ✅ 用户原始需求"3 处 LLM 改 9router low" → Phase 2 全部替换
- ✅ 用户"控制台/配置文件"→ Phase 1 `llm.yaml` 单一真相
- ✅ 用户"能看到调用什么模型" → `llm.yaml` 即可读列表

### 12.2 Grill 覆盖
9 条 D-xxx@v1 决策全部映射到设计章节（见 §11）。无遗漏。

### 12.3 约定一致性
- ✅ 沿用 `openai` SDK + `base_url` 模式（patterns.md「OpenAI 兼容客户端」）
- ✅ 沿用 `except Exception` 宽泛捕获 + fallback 兜底（conventions.md「错误处理风格」）
- ✅ 沿用文件接力契约不动（patterns.md「文件接力模式」）

### 12.4 真实性
- ✅ 现有符号：`llm_is_china_related` (step4:79), `llm_classify_single` (step4:209), `llm_summarize` (step7:150), `_why_invalid` (step7:126), `RETRY_PROMPTS` (step7:142), `fallback_summarize` (step7:101) — 来自 grep 实测
- ✅ 新增符号：`load_config` / `get_client` / `call_llm` / `ConfigError` / `LLMCallError` — 标注"新增"
- ✅ 文件路径全部绝对路径

### 12.5 YAGNI
- 移除了 vision profile 预留（D-009）
- 不实现 CLI（D-003）
- 不实现自动 fallback（D-006）

### 12.6 验收标准
1. `cat llm.yaml` 能看到当前 provider / model / call_sites（人眼可读）
2. `pip install -r requirements.txt` 不报错
3. `python3 step4.py --dry-run --date 2026-06-24` 不报错，输出 1新闻_链接.md
4. `python3 step7.py --dry-run --date 2026-06-24` 不报错，输出 3新闻_概述.md
5. 改 `llm.yaml` 顶层 `provider: zhipu` + `model: glm-4-flash` 重跑 step4 / step7 → 也成功
6. 故意把 `llm.yaml` 顶层 `provider` 改成不存在的 `xxx` → 期望 ConfigError 抛出，stderr 含 traceback

### 12.7 非目标清晰
§3 列出 6 项明确不做。

### 12.8 兼容策略（brownfield）
§9 三段：未配置 / 回退 / 不动。

### 12.9 风险识别
7 条 R-xx 含等级和应对策略。

### 12.10 生命周期契约表
不适用 —— 本变更无 session / lease / agent_run / daemon / lifecycle / claim / heartbeat 关键词。

### 12.11 自审结论
**全部通过**。无 ⚠️ 自审存疑项。可推进 Design Grill。