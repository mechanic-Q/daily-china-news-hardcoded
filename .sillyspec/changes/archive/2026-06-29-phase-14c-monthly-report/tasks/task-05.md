---
id: task-05
title: build_grounding_context + llm_monthly_overview
author: lmr
created_at: 2026-06-29 21:09:11
priority: P0
depends_on: [task-03, task-04]
blocks: [task-06, task-07, task-08, task-09]
requirement_ids: [FR-05]
decision_ids: [D-003@v1]
allowed_paths: [monthly_report.py]
goal: >
  生成 grounded prompt 并调用 ZHIPU glm-4-flash 产出月度总述/趋势；带超时、缺 key 与异常全部安全降级。
implementation:
  - build_grounding_context(stats, picks) 返回 (system_msg, user_msg) 二元组
  - system 显式禁止编造、要求只用所提供事实、要求用 [article_id] 引用、限 2 段共 ≤700 字、中文
  - user 含 stats 摘要（total/by_column/by_source/body_coverage）+ 每篇 picks 的 article_id+title+body[:BODY_SNIPPET_CHARS]
  - llm_monthly_overview(context, max_seconds) 复用 step7 风格 ZHIPU SDK 调用（base_url/model 用常量）
  - os.environ.get("ZHIPU_API_KEY")，缺失 return None
  - threading.Timer 或 signal 实现 max_seconds 超时；超时取消 + return None
  - 任何异常 try/except return None，不抛
  - 返回 LLM 文案字符串或 None
acceptance:
  - 缺 ZHIPU_API_KEY → return None 不抛
  - mock 抛异常 → return None
  - mock 返回长字符串 → 截断 ≤ OVERVIEW_MAX_CHARS
  - prompt 含 picks 内全部 article_id
verify:
  - 单测：mock openai client；用例覆盖 缺 key / 成功 / 异常 / 超时
constraints:
  - 不发起 HTML 抓取
  - 不修改 archive
  - prompt 显式要求引用 [article_id]
  - 不引入新 SDK（用项目已有 openai 客户端 base_url 风格）
