---
id: task-06
title: sanitize_llm_text + fallback_overview
author: lmr
created_at: 2026-06-29 21:09:11
priority: P0
depends_on: [task-05]
blocks: [task-07, task-08, task-09]
requirement_ids: [FR-05]
decision_ids: [D-003@v1]
allowed_paths: [monthly_report.py]
goal: >
  对 LLM 输出做反幻觉过滤，必要时降级到规则模板；保证月报始终有合法总述。
implementation:
  - sanitize_llm_text(text, valid_ids) 正则匹配 `\[([a-f0-9]{6,40})\]`，把不在 valid_ids 内的引用整段移除
  - 检测含 `<...>` 占位符或半角 ASCII 字母占比 ≥30% → 返回 None
  - 长度 > OVERVIEW_MAX_CHARS 截断
  - 通过 → 返回清洗后文本
  - fallback_overview(stats, picks) 返回模板拼接的 2 段中文：
    - 第 1 段：本月共归档 N 条、Top 3 栏目分布、主要信源
    - 第 2 段：日趋势峰值、body 覆盖率、image 覆盖率
    - 在结尾固定追加"⚠ 本期使用规则模板（LLM 未启用或失败）"
  - 长度 ≤ OVERVIEW_MAX_CHARS
acceptance:
  - sanitize 删除非授权 article_id，保留合法引用
  - 含 `<TODO>` 占位符 → 返回 None
  - fallback 输出含标注且 ≤700 字
verify:
  - 单测：sanitize 三类输入；fallback 用样本 stats 验证标注
constraints:
  - 不调 LLM/网络
  - 不引入新依赖
  - 标注文本固定，便于测试断言
