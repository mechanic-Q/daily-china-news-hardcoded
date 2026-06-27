---
author: lmr
created_at: 2026-06-27 15:55:00
schema_version: 1
doc_type: requirements
change_id: 2026-06-27-column-scoring-v2
phase: 13
---

# Requirements · Phase 13 栏目评分 v2

## 角色

| 角色 | 说明 |
|------|------|
| Daily 流水线 | 每日运行 step1_3 → step4 → step6 → step7 → step8 的自动化新闻管线 |
| step4 (classifier) | 本期主要变更对象，负责涉华过滤 + 9 栏评分 + 全局 top-10 选取 |
| step7 / step8 | 下游消费者，本期仅同步 COLUMN_ORDER 常量 |
| 9router LLM 代理 | 本地 localhost:20128/v1 OpenAI 兼容代理，承载所有 LLM 调用 |
| 测试维护者 | 写/跑 tests/test_column_scoring.py 验证 12 条 AC |

## 功能需求

### FR-01: LLM 单次结构化打分
覆盖决策：D-002@v1, D-011@v1, D-012@v1

**Given** step4 处理一篇通过涉华过滤的新闻（含 title + source）
**When** 调 `score_signals(title, source)`
**Then** 内部调用 `call_llm("column-score", ...)` 一次，期望 LLM 返回 JSON：
```json
{
  "relevance": {"🔬 世界性科研突破": 0-10, "🤖 AI智能前沿": 0-10, ... 共 9 栏},
  "importance": 0-10,
  "timeliness": 0-10
}
```
**And** 经过 `_strip_think` + `_strip_codefence` + `json.loads` + `_validate_signals` 校验后返回 dict
**And** 失败时（任何异常）返回 None

### FR-02: JSON Schema 校验
覆盖决策：D-002@v1, D-012@v1

**Given** score_signals 收到 LLM 输出
**When** 调 `_validate_signals(data)`
**Then** 校验通过条件：
- `data` 是 dict
- `data["relevance"]` 是 dict，含**全部 9 个栏目 key**（与 COLUMN_ORDER 字节级一致）
- 每个 relevance 值是 0-10 整数
- `data["importance"]` 是 0-10 整数
- `data["timeliness"]` 是 0-10 整数
- 任一条件不满足 → 返回 False

### FR-03: 聚合公式
覆盖决策：D-003@v1, D-007@v1

**Given** 合法 signals
**When** 调 `aggregate_scores(signals)`
**Then** 对每个栏目 cat 返回：
```
aggregate[cat] = relevance[cat] × (0.5 + 0.3 × importance / 10 + 0.2 × timeliness / 10)
```
**And** 边界：全 10 → aggregate=10；relevance=0 → aggregate=0；全 0 → aggregate=0
**And** 系数硬编码为常量 `AGG_RELEV_BASE=0.5`, `AGG_IMP_W=0.3`, `AGG_TIME_W=0.2`，不外置

### FR-04: 🔬 世界级抢占规则（方案 X）
覆盖决策：D-015@v1

**Given** 任意 signals
**When** 调 `assign_category(signals)`
**Then**:
- 若 `relevance["🔬 世界性科研突破"] >= 7`（WORLD_CLASS_THRESHOLD） → 返回 `🔬 世界性科研突破`
- 否则在 8 个非 🔬 栏目中 argmax，若最高分 > 0 → 返回该栏目
- 否则返回 None
**And** 同一文章只归一个栏目，不重复出现在多栏

### FR-05: 9 栏 COLUMN_ORDER 三处同步
覆盖决策：D-012@v1, D-017@v1

**Given** step4.py / step7.py / step8.py 三处的 `COLUMN_ORDER` 常量
**When** 任一被读取（用于 prompt 构造 / md 解析 / HTML 渲染）
**Then** 三处必须返回完全一致的 9 元素列表：
```python
COLUMN_ORDER = [
    '🔬 世界性科研突破',
    '🤖 AI智能前沿',
    '🌾 农业',
    '🤝 扶贫',
    '⚡ 能源',
    '🏥 医疗',
    '🚀 科技',
    '🧱 材料',
    '🎖️ 军事',
]
```

### FR-06: 空栏目消失（路径 A）
覆盖决策：D-016@v1

**Given** step4.run() 完成所有归属，准备写 `1新闻_链接.md`
**When** 遍历 COLUMN_ORDER 生成 md 内容
**Then** 仅为 `col_selected != []` 的栏目写入 `## {栏目}` heading + items；空栏目**完全跳过**（不写 heading 也不写占位文字）

### FR-07: LLM 失败降级
覆盖决策：D-004@v1, D-009@v1

**Given** score_signals 返回 None（任意失败原因）
**When** 调用方处理该 article
**Then** 走 legacy_path：
- `score_all_categories(title)` 关键词加权
- 若多栏接近 → 尝试 `llm_classify_single`（保留为兜底）
- 若 `llm_classify_single` 也失败（9router 挂）→ 跳过仲裁直接取 `score_all_categories` 最高分
- `priority_score(title, cat)` 算栏目内排序
- 若关键词亦无命中 → 跳过该文章

### FR-08: 降级率监控
覆盖决策：D-004@v1

**Given** step4 处理完一批文章
**When** 统计降级率 = (LLM 失败 article 数) / (总 article 数)
**Then** 若 ≥ 30%，stderr 输出 `⚠ column-score 降级率 {X}%`；不中断流水线

### FR-09: CATEGORY_KEYWORDS 扩 🤖 + 调 🚀
覆盖决策：D-013@v1, D-014@v1

**Given** legacy_path 使用 `CATEGORY_KEYWORDS` 关键词词典
**When** 加载词典
**Then**:
- 字典含全部 9 栏目 key
- `'🤖 AI智能前沿'` 新增，包含 ≥30 关键词，覆盖：
  - 国产大模型（DeepSeek / Qwen / 文心 / Kimi / 智谱 / 大模型 / Agent / 千亿参数）
  - 国产 AI 芯片（昇腾 / 寒武纪 / 海光 DCU / 摩尔线程 / 沐曦 / 壁仞 / 燧原 / 天数智芯 / 平头哥 / 昆仑芯 / 算力 / 智算）
  - 国产机器人（人形机器人 / 宇树 / 智元 / 具身智能 / 工业机器人）
  - 量子计算（量子计算 / 量子通信 / 九章 / 量子比特）
  - AI 应用（智能体 / AI应用 / 智能制造 / 灯塔工厂）
- `'🚀 科技'` 剥离 AI/大模型/机器人/智能制造词条；新增国产 CPU 厂商（龙芯/飞腾/鲲鹏/海光/兆芯/申威 — 注意 "海光" 在 🤖 指 DCU、在 🚀 指通用 CPU，prompt 上下文区分）/ 国产 OS（鸿蒙/欧拉/统信/麒麟）
- 其他 7 栏词典不动

### FR-10: llm.yaml 新增 column-score call site
覆盖决策：D-002@v1, D-008@v1

**Given** `llm.yaml`
**When** 读取 `call_sites`
**Then** 含 `column-score` key，字段：
```yaml
column-score:
  max_tokens: 256
  temperature: 0.0
  timeout: 30
```

### FR-11: 单元测试
覆盖决策：所有 D-xxx@v1

**Given** `tests/test_column_scoring.py`
**When** 执行该文件
**Then** 覆盖：
- AC-03: `_validate_signals` 拒绝缺 key / 越界 / 非整数 / 非 dict（≥6 case）
- AC-04: `aggregate_scores` 边界（全 0、relev=0、全 10、混合）
- AC-09: 🔬 抢占（🔬=8、🌾=10 → 返回 🔬；🔬=6、🌾=10 → 返回 🌾）
- AC-10: 单文章归唯一栏目
- AC-11: 空栏目 md 输出不写 heading
- AC-07: COLUMN_ORDER 三处一致性 import 检查
- AC-12: CATEGORY_KEYWORDS 9 栏 + 🤖 ≥30 词

## 非功能需求

| 类别 | 要求 |
|------|------|
| **兼容性** | step1_3 / step6 输出 md 不动；step7/step8 仅 COLUMN_ORDER 改；1新闻_链接.md 行级格式不变 |
| **可回退** | git revert 即可恢复 8 栏版本；CATEGORY_KEYWORDS 与 legacy_path 完整保留 |
| **可测试** | 12 条 AC 全部可单测或脚本断言 |
| **性能** | step4 P95 ≤ 10 min（200 篇 × 2s LLM）；degraded 模式 P95 ≤ 2 min |
| **可观测** | 降级率 stderr 输出；现有 print() 状态信息保留 |
| **风格一致** | 实现代码不写 type hints；不直接 import openai；中文 emoji print；纯函数风格 |
| **依赖最小** | 不新增 pip 包；tests 不强依赖 pytest |

## 决策覆盖矩阵

| 决策 ID | 覆盖的 FR | 说明 |
|---------|----------|------|
| D-001@v1 | FR-01 ~ FR-11 | Phase 13 总范围 |
| D-002@v1 | FR-01, FR-02, FR-03, FR-10 | B+ 信号提取式骨架 |
| D-003@v1 | FR-03 | 聚合公式 |
| D-004@v1 | FR-07, FR-08 | 必降级 |
| D-005@v1 | (frontmatter) | 变更名 |
| D-006@v1 | FR-07 | 保留 llm_classify_single |
| D-007@v1 | FR-03 | 系数不外置 |
| D-008@v1 | FR-10 | temp=0.0 |
| D-009@v1 | FR-07 | 二级降级 |
| D-010@v1 | FR-01 ~ FR-11 实现 | 无 type hints |
| D-011@v1 | FR-01 prompt 引用 | §4.0 语义契约 |
| D-012@v1 | FR-05 | 新增 🤖 第 9 栏 |
| D-013@v1 | FR-09 | 🤖 T2 厂商列举 |
| D-014@v1 | FR-09 | 🚀 重切 + CPU 厂商列举 |
| D-015@v1 | FR-04 | 方案 X 抢占 |
| D-016@v1 | FR-06 | 空栏目消失 |
| D-017@v1 | FR-05 | step7/8 同步常量 |
| D-018@v1 | FR-01 prompt 引用 | 🔬 E 三维判定 |
| D-019@v1 | FR-01 prompt 引用 | 🔬 D.1/D.2 拆分 |
