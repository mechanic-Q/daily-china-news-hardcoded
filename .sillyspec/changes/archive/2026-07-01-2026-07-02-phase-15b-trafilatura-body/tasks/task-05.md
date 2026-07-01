---
id: task-05
title: 将 CAS / People / CCTV 清理收敛为站点 postprocess registry，并保持污染检查可用（覆盖：FR-03, D-002@v1）
author: lmr
created_at: 2026-07-01 22:36:46
priority: P0
depends_on: [task-04]
blocks: [task-03, task-06, task-07]
requirement_ids: [FR-03]
decision_ids: [D-002@v1]
allowed_paths: [step6.py]
goal: >
  将散落的站点特有正文后处理逻辑（CAS 页脚/People 元尾部/CCTV 播放器 UI）抽取为按站点注册的后处理函数，通过 SITE_POSTPROCESS registry 路由，同时保持通用清理和污染检查不变。
implementation:
  - 抽取 cas_postprocess(text): 清除 CAS 地址/邮编/电话页脚 + "贯彻落实"模板头。
  - 抽取 people_postprocess(text): 清除 enpproperty 时间戳尾部。
  - 抽取 cctv_postprocess(text): 分离 CCTV 播放器 UI 模式（视频播放器、ADCountdown、加载进度、高清画质、续播、跳过广告等）。
  - 定义 SITE_POSTPROCESS registry；_postprocess_text 签名改为(text, url=None)，按 URL 匹配执行 site postprocess → 通用清理 → 空白归一 → 重复句去重。
acceptance:
  - SITE_POSTPROCESS 包含 cas/people/cctv 三条目，pred 按 URL 匹配。
  - _postprocess_text(text, url=None) 兼容无 url 调用。
  - _is_contaminated 与 _aggressive_clean 签名/行为不变。
  - fetch_and_extract 污染检查仍拦截 CSS/JS/模板污染。
verify:
  - python3 -m py_compile step6.py
  - python3 -c "from step6 import SITE_POSTPROCESS; print('ok')"
constraints:
  - 只清理已抽出文本，不新增正文定位逻辑。
  - 不引入新依赖或新文件。
  - 保持污染检查 _is_contaminated / _aggressive_clean 可用，不改 fetch_and_extract 污染处理。
  - 不改通用清理（HTML unescape、空白归一、重复句去重）。
---
