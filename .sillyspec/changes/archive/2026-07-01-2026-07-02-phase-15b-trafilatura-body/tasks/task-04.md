---
id: task-04
title: >
  在 `step6.py` 中用 `trafilatura` 替换通用 regex 正文定位，
  并保留参考消息 fallback
  （覆盖：FR-01, FR-02, D-001@v1, D-002@v1）
author: lmr
created_at: 2026-07-01 22:36:46
priority: P0
depends_on: [task-01]
blocks: [task-03, task-06, task-07]
requirement_ids: [FR-01, FR-02]
decision_ids: [D-001@v1, D-002@v1]
allowed_paths: [step6.py]
goal: >
  将 extract_body 中 5 层 regex 策略链替换为 trafilatura.extract
  作为通用抽取核心，保留 ckxxapp/cankaoxiaoxi contentTxt fallback，
  fetch_and_extract 签名与 (body, err) 返回语义不变。
implementation:
  - "导入 trafilatura.extract；重写 extract_body(html, url) — tf_extract → 空/短文本且引用参考消息 → _extract_ckxx_content_txt fallback → 返回"
  - "移除全部通用 regex 层：TRS_Editor / article / div.content / div.detail / div.main-content / #ozoom / <p> 拼接"
  - "将 ckxx 内联 JS 字面量提取抽为 _extract_ckxx_content_txt(html) → 纯文本或 None"
  - "fetch_and_extract 流程不变：抓 HTML → extract_body → postprocess → 污染检查 → 返回"
acceptance:
  - extract_body 优先调 trafilatura.extract，不遍历通用 regex 容器
  - 参考消息 contentTxt fallback 在 trafilatura 返回空/短时生效
  - fetch_and_extract(url, title) 签名与返回语义不变
  - needs_chromium / run_all.sh / step7.py / archive schema 无变化
verify: [python3 -m py_compile step6.py]
constraints:
  - 不改 fetch_and_extract 签名与 (body, err) 返回约定
  - 不改 needs_chromium(url) 路由规则
  - 不改 run_all.sh / step7.py / archive schema
  - _postprocess_text / _is_contaminated / _aggressive_clean 由 task-05 处理
  - 不引入 playwright / selenium 等新浏览器依赖
---
