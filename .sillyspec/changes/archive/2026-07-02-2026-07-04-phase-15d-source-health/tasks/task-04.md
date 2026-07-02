---
id: task-04
title: 将 `monthly_report.py` 的 overview LLM 调用迁移到 `llm_client.call_llm("monthly-overview", ...)`，并补齐 `llm.yaml` 配置。（覆盖：FR-04）
author: lmr
created_at: 2026-07-02 20:12:36
priority: P0
depends_on: []
blocks: []
requirement_ids:
  - FR-04
decision_ids: []
allowed_paths:
  - monthly_report.py
  - llm.yaml
goal: >
  Migrate `monthly_report.py`'s hand-written OpenAI client for overview to
  `llm_client.call_llm("monthly-overview", ...)`, add `monthly-overview` call
  site to `llm.yaml`. Unifies LLM config under Phase 15A's abstraction.
implementation:
  - 在 `llm.yaml` `call_sites` 中新增 `monthly-overview`: max_tokens=1200, temperature=0.7, timeout=30
  - `monthly_report.py` import 追加 `from llm_client import call_llm, LLMCallError`；删除 `from openai import OpenAI` 和 `import threading`
  - 将 `llm_monthly_overview()` 函数体替换为：按 `[{"role":"system","content":sys},{"role":"user","content":usr}]` 构造 messages 列表，调用 `call_llm("monthly-overview", messages, timeout=max_seconds)`，异常时返回 `None`
  - 删除不再使用的常量 `LLM_MODEL`、`LLM_BASE_URL`
acceptance:
  - `llm.yaml` 包含 `monthly-overview` call site（temperature/max_tokens/timeout）
  - `monthly_report.py` 不再 `from openai import OpenAI`，无 `LLM_BASE_URL`/`LLM_MODEL`/`threading.Thread`
  - `--no-llm`、`--max-llm-seconds` CLI flags 行为不变，fallback_overview 相同
  - LLM 调用失败返回 `None`（不崩溃），触发 `fallback_overview`
verify:
  - python3 -m py_compile monthly_report.py
  - python3 -c "import yaml; c=yaml.safe_load(open('llm.yaml')); assert 'monthly-overview' in c['call_sites']"
  - rg -n 'from openai import OpenAI|LLM_BASE_URL|LLM_MODEL|threading\.' monthly_report.py; echo "exit=$?"
constraints:
  - 只改 `monthly_report.py` 和 `llm.yaml`，不改其他文件
  - 保留 `--no-llm`/`--max-llm-seconds`，fallback_overview 行为不变
  - timeout 通过 `call_llm(**override)` 传入，不硬编码
  - `llm.yaml` 已有 provider/model/其他 call_sites 不动
  - 异常时返回 `None` 而非抛出
---
