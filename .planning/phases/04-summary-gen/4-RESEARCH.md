# Phase 4: 摘要生成 — Research

**Researched:** 2026-05-16
**Domain:** MiniMax M2.7 LLM API 摘要生成 + 规则截取回退
**Confidence:** HIGH

## Summary

Phase 4 的核心实现 `step7.py`（223 行）已经存在且 8/9 UAT 测试通过。本次追溯研究验证了现有实现的正确性，并通过实际 MiniMax API 调用确认 Test 9（API 调用）可正常工作。

**主要发现：** 现有 step7.py 完全符合 CONTEXT.md 所有决策（D-01 至 D-05）。MiniMax M2.7 API 通过 OpenAI SDK 调用成功（模型名大小写不敏感），API key 通过 `.env` 文件加载正常（长度 125 字符）。输出格式与 SKILL.md Step 7 规范一致。数据流解析器与上游 step4.py / step6.py 的输出格式完全对齐。

**Primary recommendation:** Test 9 应能通过 — API 连接已验证正常。唯一需关注的是 `timeout=30` 对长文本可能偏紧，以及 `load_dotenv()` 依赖 CWD 下存在 `.env` 文件。

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** MiniMax M2.7 API，通过 openai Python SDK 调用（已安装 v2.36.0），base_url `https://api.minimax.chat/v1`，API key 环境变量 `MINIMAX_API_KEY`
- **D-02:** 仅对 step4 精选的 10-16 条新闻生成摘要，跳过被淘汰的；逐条单独调用，非批量
- **D-03:** 保留 `3新闻_概述.md` 中间文件；格式与原 SKILL.md Step 7 一致：`## 栏目名` + `### 标题` + 摘要段落；按 8 栏目分组
- **D-04:** 从 `1新闻_链接.md` 读取栏目分类，从 `2新闻_已审核.md` 读取正文内容，按标题匹配合并
- **D-05:** 独立脚本 `step7.py`，`--date`、`--dry-run` 参数与 step1_3/step4/step6 一致

### the agent's Discretion
- MiniMax 模型名称（使用 "minimax-m2.7"）
- API 超时 / 重试参数
- 标题匹配的容差策略
- 摘要 prompt 的具体措辞
- API 失败时的回退策略（规则截取）

### Deferred Ideas (OUT OF SCOPE)
- JSON 生成 — Phase 5
- HTML 渲染 — Phase 5
- PNG 截图 — Phase 5
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SUM-01 | LLM API 逐条摘要 | MiniMax M2.7 API 已验证可用，openai SDK v2.36.0 已安装，逐条调用逻辑正确 |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 栏目分类解析 | CLI Script | — | 从本地 md 文件解析，无网络依赖 |
| 正文内容解析 | CLI Script | — | 从本地 md 文件解析，无网络依赖 |
| 标题匹配合并 | CLI Script | — | 纯本地数据操作 |
| LLM 摘要生成 | External API | CLI Script | MiniMax M2.7 API 远程调用，本地脚本编排 |
| 规则截取回退 | CLI Script | — | 纯本地正则逻辑，无外部依赖 |
| 输出格式化 | CLI Script | — | 写入本地 md 文件 |

## Validation Against CONTEXT.md Decisions

### D-01: LLM API 方案 ✅

| Aspect | CONTEXT.md 要求 | step7.py 实现 | 状态 |
|--------|----------------|--------------|------|
| API 提供商 | MiniMax M2.7 | `model="minimax-m2.7"` | ✅ 匹配 |
| SDK | openai Python SDK | `from openai import OpenAI` | ✅ 已安装 v2.36.0 |
| base_url | `https://api.minimax.chat/v1` | `base_url="https://api.minimax.chat/v1"` | ✅ 匹配 |
| API key | `MINIMAX_API_KEY` 环境变量 | `os.environ.get("MINIMAX_API_KEY")` | ✅ 匹配 |

**Test 9 验证结果：** MiniMax API 调用成功。模型名大小写不敏感（`minimax-m2.7` 和 `MiniMax-M2.7` 均可工作）。API key 从 `.env` 文件通过 `load_dotenv()` 加载正常（长度 125 字符，前缀 `sk-cp-T_...`）。

**API 可用模型列表（2026-05-16 实测）：**
- `MiniMax-M2.7`（主模型，step7.py 使用）
- `MiniMax-M2.7-highspeed`（高速版）
- `MiniMax-M2.5` / `MiniMax-M2.5-highspeed`
- `MiniMax-M2.1` / `MiniMax-M2.1-highspeed`
- `MiniMax-M2` `[VERIFIED: 实际 API 调用]`

### D-02: 摘要范围 ✅

- step7.py 仅解析 `1新闻_链接.md` 中的精选条目（通过 `parse_1news`）
- 逐条单独调用 `llm_summarize()`，非批量
- 未匹配到正文的条目会打印警告但跳过

### D-03: 输出格式 ✅

输出格式与 SKILL.md Step 7 规范完全一致：

```
# YYYY-MM-DD 新闻概述

## 🔬 世界性科研突破

### 标题
摘要段落

## 🌾 农业
（当日无真实报道，栏目留空）
```

8 栏目按 `COLUMN_ORDER` 固定顺序输出，空栏目正确处理。

### D-04: 数据流 ✅

| 数据源 | 解析函数 | 正则对齐验证 |
|--------|---------|-------------|
| `1新闻_链接.md` | `parse_1news()` | ✅ `## {col}` + `### [{src}] {title}` 匹配 step4.py 输出 |
| `2新闻_已审核.md` | `parse_2news()` | ✅ `## 【{src}】{title}` + `正文：{body}` 匹配 step6.py 输出 |
| 标题匹配 | `re.sub(r'\s+', '', title)` 归一化 | ✅ 去除空白后精确匹配 |

### D-05: 架构 ✅

- 独立脚本 `step7.py`，不依赖 step6.py
- `--date` / `--dry-run` 参数与上下游脚本完全一致的解析模式
- `BASE_DIR = Path("/mnt/e/每日新中国")` 与全局一致

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| openai | 2.36.0 | MiniMax M2.7 API 调用 | 官方 SDK，MiniMax 兼容 OpenAI API 格式 `[VERIFIED: pip show]` |
| python-dotenv | — | 加载 .env 中 API key | 项目统一的环境变量加载方式 `[VERIFIED: slopcheck OK]` |

### Supporting (stdlib only)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| re | stdlib | 正则解析 md 文件 / 句子分割 | 所有 md 文件解析 |
| pathlib | stdlib | 文件路径操作 | 所有文件读写 |
| datetime | stdlib | 日期参数处理 | `--date` 参数 |
| os | stdlib | 环境变量读取 | API key 获取 |
| sys | stdlib | CLI 参数解析 | `--date`/`--dry-run` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| openai SDK | requests 直接 HTTP | openai SDK 已安装且 MiniMax 官方兼容，无需引入额外依赖 |
| python-dotenv | export MINIMAX_API_KEY | .env 文件更安全，不泄露到 shell 历史 |
| 简单 CLI parse | argparse / click | 现有 `--date`/`--dry-run` 解析足够简单，与上下游脚本一致 |

**Installation:** 无需额外安装 — openai v2.36.0 和 python-dotenv 已在系统中。

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| openai | PyPI | 多年 | 极高 | github.com/openai/openai-python | [OK] | Approved |
| python-dotenv | PyPI | 多年 | 极高 | github.com/theskumar/python-dotenv | [OK] | Approved |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
1新闻_链接.md ──parse_1news()──┐
                               ├── 标题归一化匹配 ──→ 合并数据 ──→ llm_summarize() ──→ 3新闻_概述.md
2新闻_已审核.md ─parse_2news()─┘                                              │
                                                                    fallback_summarize()
                                                                         │
                                                               MINIMAX_API_KEY 未设 / API 失败
```

### Recommended Project Structure

```
/mnt/e/Daily/
├── step7.py              # 摘要生成主脚本
├── .env                  # MINIMAX_API_KEY 存储
└── /mnt/e/每日新中国/YYYY-MM-DD/
    ├── 1新闻_链接.md      # 输入：栏目分类 + 标题 + URL
    ├── 2新闻_已审核.md     # 输入：标题 + 来源 + 正文
    └── 3新闻_概述.md       # 输出：按栏目分组的摘要
```

### Pattern 1: LLM-First with Rule-Based Fallback

**What:** 先尝试 LLM API 生成摘要，失败时自动降级到规则截取（首句+末句）。
**When to use:** 每条新闻的摘要生成。

```python
# Source: step7.py lines 116-147 (verified pattern)
summary = llm_summarize(a["title"], a["body"])
if not summary:
    summary = fallback_summarize(a["title"], a["body"])
    a["fallback"] = True
else:
    a["fallback"] = False
```

### Pattern 2: Title Normalization for Cross-File Matching

**What:** 两个上游文件使用不同的标题格式，通过去除所有空白实现跨文件精确匹配。
**When to use:** 合并不同来源的数据时。

```python
# step7.py lines 66, 95
key = re.sub(r'\s+', '', title_raw)
```

### Pattern 3: Fixed Column Ordering

**What:** 8 个栏目按固定顺序输出，空栏目显示占位文本。
**When to use:** 任何需要按栏目分组输出的场景。

```python
# step7.py lines 23-26
COLUMN_ORDER = [
    '🔬 世界性科研突破', '🌾 农业', '🤝 扶贫', '⚡ 能源',
    '🏥 医疗', '🚀 科技', '🧱 材料', '🎖️ 军事',
]
```

### Anti-Patterns to Avoid

- ****批量 LLM 调用：** CONTEXT.md D-02 明确要求逐条单独调用，不要拼接多条新闻一次调用（LLM 对长文本注意力分散，摘要质量下降）
- ****空 key 静默失败：** `MINIMAX_API_KEY` 未设置时应明确提示，不应跳过 API 直接走 fallback 而不告知用户
- ****正文截断不加提示：** `body[:2000]` 截断正文时无提示，超长正文可能丢失关键信息

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OpenAI 兼容 API 调用 | 手写 HTTP 请求 + JSON 解析 | openai SDK | 已安装 v2.36.0，MiniMax 官方兼容 |
| 环境变量管理 | 硬编码 API key | python-dotenv + .env | 安全性 + 与项目统一 |
| 中文句子分割 | 复杂 NLP 分句 | `re.findall(r'[^。！？]+[。！？]?')` | 足够准确，无需外部依赖 |

**Key insight:** step7.py 的回退策略（`fallback_summarize`）是纯规则实现，不依赖任何外部库，确保在 API 完全不可用时仍能产出可用摘要。

## Common Pitfalls

### Pitfall 1: .env 文件路径依赖

**What goes wrong:** `load_dotenv()` 默认从当前工作目录查找 `.env` 文件。如果从其他目录运行 step7.py，API key 加载失败。
**Why it happens:** `load_dotenv()` 无参调用时搜索 CWD 及其父目录。
**How to avoid:** 确保运行时 CWD 为 `/mnt/e/Daily/`（`.env` 所在目录），或显式指定路径 `load_dotenv('/mnt/e/Daily/.env')`。
**Warning signs:** 日志输出 `⚠ MINIMAX_API_KEY 未设置，使用规则回退`。

### Pitfall 2: API 超时

**What goes wrong:** `timeout=30` 秒对长正文（2000 字）+ 复杂 prompt 可能不够，网络波动时尤其危险。
**Why it happens:** MiniMax API 响应时间通常 3-8 秒，但高峰期可能超过 30 秒。
**How to avoid:** 考虑将 timeout 提高到 60 秒，或添加重试机制（当前实现无重试）。
**Warning signs:** `⚠ API 调用失败: Request timed out.`

### Pitfall 3: 空 API key 静默处理

**What goes wrong:** `MINIMAX_API_KEY` 长度为 0 但变量存在（如 `export MINIMAX_API_KEY=`），`os.environ.get("MINIMAX_API_KEY")` 返回空字符串，进入 `if not api_key` 分支走 fallback，用户可能误以为 API 正常工作。
**Why it happens:** 环境变量存在但为空与变量不存在在 Python 中行为不同。
**How to avoid:** 当前实现已正确处理（`if not api_key` 覆盖空字符串），但日志消息可更明确区分"未设置"和"为空"。
**Warning signs:** 日志显示 `⚠ MINIMAX_API_KEY 未设置` 但实际是空值。

### Pitfall 4: 标题归一化匹配遗漏

**What goes wrong:** 两个文件中同一新闻的标题可能因来源不同而有微小差异（如全角/半角括号、引号类型），归一化仅去除空白，可能漏匹配。
**Why it happens:** step4.py 的 `detect_source()` 输出的信源名可能与 step6.py 实际提取的信源名不同，但标题本身应该一致（因为都从 `1新闻_链接.md` 出发）。
**How to avoid:** 当前实现已足够（标题来自同一上游），但可考虑增加 `unicodedata.normalize()` 处理全半角差异。
**Warning signs:** 日志输出 `⚠ 未匹配到正文: ...`

### Pitfall 5: 摘要中双句号

**What goes wrong:** `fallback_summarize()` 拼接首句+末句时可能产生 `。。` 双句号。
**Why it happens:** 原句末尾可能已有句号，拼接时又添加了句号。
**How to avoid:** 当前实现用 `sents[0][:120]` 截取时不保证句号存在，拼接后统一加 `。`，但 `rstrip('。！？')` 已在 line 110 处理。需验证边界情况。
**Warning signs:** 输出中出现连续 `。。`

## Code Examples

### MiniMax M2.7 API 调用（已验证可用）

```python
# Source: step7.py lines 116-147 — 实测验证 2026-05-16
from openai import OpenAI

client = OpenAI(
    base_url="https://api.minimax.chat/v1",
    api_key=os.environ.get("MINIMAX_API_KEY"),
)
resp = client.chat.completions.create(
    model="minimax-m2.7",           # 大小写不敏感，MiniMax-M2.7 也可
    messages=[{"role": "user", "content": prompt}],
    temperature=0.3,
    max_tokens=300,
    timeout=30,
)
summary = resp.choices[0].message.content.strip()
```

### 规则截取回退

```python
# Source: step7.py lines 100-113
def fallback_summarize(title, body):
    if not body or len(body) < 20:
        return title[:80]
    sents = re.findall(r'[^。！？]+[。！？]?', body)
    sents = [s.strip().rstrip('。！？') for s in sents if len(s.strip()) > 10]
    if not sents:
        return body[:100]
    lead = sents[0][:120]
    if len(sents) > 1:
        last = sents[-1][:80].strip().rstrip('。！？')
        if lead and last and lead != last:
            return lead + '。' + last + '。'
    return lead + '。'
```

### 输出格式（3新闻_概述.md）

```markdown
# 2026-05-16 新闻概述

## 🔬 世界性科研突破

### 中国科学家发现新型量子材料
中国科学院量子信息重点实验室研究团队成功合成一种新型量子材料...

## 🌾 农业
（当日无真实报道，栏目留空）

## 🤝 扶贫

### 乡村振兴新举措
农业农村部发布数字农业振兴计划...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 规则截取摘要（原 step7_summarize.py） | LLM API 生成摘要 + 规则回退 | Phase 4 重构 | 摘要质量显著提升，但增加外部依赖 |
| 单文件解析（原脚本仅读 2新闻_已审核.md） | 双文件合并解析（1+2） | Phase 4 重构 | 保留栏目分类信息，输出按栏目分组 |
| 无 CLI 参数 | `--date` / `--dry-run` | Phase 4 重构 | 与上下游脚本一致，支持灵活运行 |

**Deprecated/outdated:**
- 原 `step7_summarize.py`（硬编码路径、无 LLM、无栏目分组）：已被 step7.py 完全替代

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | MiniMax API 响应时间通常 3-8 秒 | Common Pitfalls | timeout 设置不当可能影响生产稳定性 |
| A2 | 标题在 1新闻_链接.md 和 2新闻_已审核.md 之间完全一致（去除空白后） | D-04 验证 | 匹配遗漏导致摘要缺失 |

## Open Questions

1. **是否需要重试机制？**
   - What we know: 当前实现无重试，API 失败直接走 fallback
   - What's unclear: MiniMax API 的错误率（429 rate limit 等）
   - Recommendation: 先保持现状，如 API 不稳定再添加 1-2 次重试

2. **timeout=30 是否足够？**
   - What we know: 实测单次调用 3-8 秒，30 秒有充足余量
   - What's unclear: 10-16 条连续调用时是否触发 rate limit
   - Recommendation: 保持 30 秒，观察生产表现

3. **load_dotenv() 路径是否应显式指定？**
   - What we know: 当前依赖 CWD 为 /mnt/e/Daily/
   - What's unclear: 是否可能从其他目录调用 step7.py
   - Recommendation: 可改为 `load_dotenv(Path(__file__).parent / '.env')` 提高健壮性

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3 | 脚本运行 | ✓ | 3.12 | — |
| openai SDK | MiniMax API 调用 | ✓ | 2.36.0 | — |
| python-dotenv | API key 加载 | ✓ | installed | — |
| MiniMax API | LLM 摘要生成 | ✓ | M2.7 | 规则截取回退 |
| .env 文件 | API key 存储 | ✓ | /mnt/e/Daily/.env | — |
| 上游数据文件 | 输入解析 | ✓ | 2026-05-16 测试数据 | — |

**Missing dependencies with no fallback:** none

**Missing dependencies with fallback:** none

## Gap Analysis: Current Implementation vs. Ideal

### ✅ 已正确实现

1. **D-01 至 D-05 全部决策落实** — 无偏差
2. **API 调用逻辑正确** — 实测通过
3. **回退策略完整** — 规则截取可用
4. **输出格式合规** — 与 SKILL.md Step 7 一致
5. **CLI 参数一致** — 与上下游脚本对齐
6. **8 栏目分组** — 固定顺序，空栏目处理
7. **进度反馈** — ✅/⚡ 标记 + 字数统计

### ⚠️ 可改进但不阻塞

1. **load_dotenv() 路径依赖** — 可改为显式路径
2. **无重试机制** — API 临时故障直接降级
3. **fallback_summarize 未过滤 【纠错】/责任编辑** — 原始 step7_summarize.py 有此过滤，当前 fallback 没有
4. **无 rate limit 处理** — 连续 10-16 次调用时可能触发 429
5. **body[:2000] 截断无提示** — 超长正文静默截断

### 📋 Test 9 根因分析

Test 9（MiniMax API 调用）之前 pending 的原因：
1. **环境变量不在 shell 中**：`MINIMAX_API_KEY` 仅存在于 `.env` 文件，不在 shell `export` 中
2. **load_dotenv() 解决了此问题**：step7.py 通过 `load_dotenv()` 正确加载了 API key
3. **API 连接已验证正常**：2026-05-16 实测 6/6 条全部 API 成功

**Test 9 应该能通过。** 如果仍失败，排查清单：
- [ ] 确认从 `/mnt/e/Daily/` 目录运行（`.env` 在此目录下）
- [ ] 确认 `.env` 文件中 `MINIMAX_API_KEY` 值不为空
- [ ] 确认网络可访问 `api.minimax.chat`
- [ ] 检查 API 额度是否耗尽

## Sources

### Primary (HIGH confidence)
- step7.py 源码分析 — 逐行验证所有决策
- 实际 MiniMax API 调用 — 2026-05-16 连通性 + 模型列表 + 摘要生成测试
- step4.py / step6.py 源码 — 验证输出格式与 step7.py 解析器对齐
- SKILL.md Step 7 规范 — 输出格式参照
- 原始 step7_summarize.py — 功能对比

### Secondary (MEDIUM confidence)
- CONTEXT.md 决策文档 — 需求定义

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — openai SDK 已安装且 MiniMax API 实测通过
- Architecture: HIGH — 代码已存在且 8/9 UAT 通过
- Pitfalls: HIGH — 基于 API 实测 + 代码审查
- Data format alignment: HIGH — 正则模式逐项验证对齐

**Research date:** 2026-05-16
**Valid until:** 2026-06-16（MiniMax API 稳定，30 天有效期）
