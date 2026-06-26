---
id: task-02
author: lmr
created_at: 2026-06-24 19:40:00
title: 编写 llm_client.py 抽象层
priority: P0
depends_on: [task-01]
blocks: [task-05, task-06, task-07]
requirement_ids: [FR-01, FR-02, FR-03]
decision_ids: [D-005@v1, D-007@v1, D-008@v1, D-010@v1]
allowed_paths:
  - /mnt/e/Daily/llm_client.py
---

# task-02: 编写 llm_client.py 抽象层

## 修改文件
- 新增 `/mnt/e/Daily/llm_client.py`

## 覆盖来源
- Requirements: FR-01, FR-02, FR-03
- Decisions: D-005@v1 (call_site 级参数), D-007@v1 (traceback 可见), D-008@v1 (抽象层方案 B), D-010@v1 (Key 缺失走 fallback)

## 实现要求
1. 顶部含 docstring 说明此模块用途
2. 公开 3 个函数 + 2 个异常类
3. `load_config` 用 `functools.lru_cache(maxsize=1)` 缓存
4. `load_config` 只校验 yaml 格式完整性，**不**校验 env 变量存在性（D-010）
5. `call_llm` 失败时 `traceback.print_exc()` + 重抛 LLMCallError（D-007）
6. 使用 `openai` SDK，沿用现有 patterns.md「OpenAI 兼容客户端」模式

## 接口定义

```python
"""llm_client.py — Daily 项目 LLM 配置统一管理抽象层。

提供 load_config / get_client / call_llm 三个 API，把 3 处 LLM 调用统一到一个
配置文件 llm.yaml + 一个客户端工厂。详见 design.md §7.2。

作者：lmr
创建时间：2026-06-24
"""

from __future__ import annotations
import functools
import os
import sys
import traceback
from pathlib import Path
from typing import Tuple, Dict, Any, List

import yaml
from openai import OpenAI


CONFIG_PATH = Path(__file__).parent / "llm.yaml"


class ConfigError(Exception):
    """llm.yaml 解析或结构性错误。"""
    pass


class LLMCallError(Exception):
    """LLM 调用失败（包括 key 缺失、网络、API 错误）。"""
    pass


@functools.lru_cache(maxsize=1)
def load_config() -> Dict[str, Any]:
    """读取 llm.yaml，校验结构完整性，返回配置 dict。
    
    校验：
    - 顶层必须含 provider / model / providers / call_sites 4 个 key
    - provider 必须在 providers 中存在
    - model 必须是非空字符串
    - 每个 providers.<name> 必须含 base_url + api_key_env
    - 每个 call_sites.<id> 必须含 temperature + max_tokens + timeout
    
    **不**校验 api_key_env 对应的环境变量是否存在（D-010 宽松）
    
    Raises: ConfigError
    """
    if not CONFIG_PATH.exists():
        raise ConfigError(f"llm.yaml not found at {CONFIG_PATH}")
    try:
        cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise ConfigError(f"llm.yaml parse error: {e}") from e
    if not isinstance(cfg, dict):
        raise ConfigError("llm.yaml root must be a mapping")
    for key in ("provider", "model", "providers", "call_sites"):
        if key not in cfg:
            raise ConfigError(f"llm.yaml missing top-level key: {key}")
    prov = cfg["provider"]
    if prov not in cfg["providers"]:
        raise ConfigError(f"provider '{prov}' not defined in providers")
    if not isinstance(cfg["model"], str) or not cfg["model"]:
        raise ConfigError("model must be non-empty string")
    for name, p in cfg["providers"].items():
        if not isinstance(p, dict): raise ConfigError(f"providers.{name} must be mapping")
        for k in ("base_url", "api_key_env"):
            if k not in p: raise ConfigError(f"providers.{name} missing {k}")
    for site, s in cfg["call_sites"].items():
        if not isinstance(s, dict): raise ConfigError(f"call_sites.{site} must be mapping")
        for k in ("temperature", "max_tokens", "timeout"):
            if k not in s: raise ConfigError(f"call_sites.{site} missing {k}")
    return cfg


def get_client(call_site_id: str) -> Tuple[OpenAI, str, Dict[str, Any]]:
    """返回 (OpenAI 实例, model 字符串, kwargs)
    
    kwargs 含 temperature/max_tokens/timeout（per-call timeout）
    Raises:
        ConfigError: call_site_id 不存在
        LLMCallError: api_key_env 对应的环境变量未设置
    """
    cfg = load_config()
    if call_site_id not in cfg["call_sites"]:
        raise ConfigError(f"call_site '{call_site_id}' not defined")
    prov_name = cfg["provider"]
    prov = cfg["providers"][prov_name]
    api_key = os.environ.get(prov["api_key_env"])
    if not api_key:
        raise LLMCallError(f"Missing API key for {prov_name}: {prov['api_key_env']}")
    client = OpenAI(base_url=prov["base_url"], api_key=api_key)
    site_cfg = cfg["call_sites"][call_site_id]
    kwargs = {
        "temperature": site_cfg["temperature"],
        "max_tokens": site_cfg["max_tokens"],
        "timeout": site_cfg["timeout"],
    }
    return client, cfg["model"], kwargs


def call_llm(call_site_id: str, messages: List[Dict[str, str]], **override) -> str:
    """一次性封装：构造 client + create + 错误处理。
    
    返回：response.choices[0].message.content
    失败时 traceback.print_exc() 到 stderr，重抛 LLMCallError。
    override 可覆盖 temperature/max_tokens/timeout/model。
    """
    try:
        client, model, kwargs = get_client(call_site_id)
        if "model" in override:
            model = override.pop("model")
        kwargs.update(override)
        resp = client.chat.completions.create(model=model, messages=messages, **kwargs)
        return resp.choices[0].message.content
    except LLMCallError:
        traceback.print_exc()
        raise
    except Exception as e:
        traceback.print_exc()
        raise LLMCallError(f"LLM call failed at '{call_site_id}': {e}") from e
```

## 边界处理
1. **llm.yaml 不存在**：load_config 抛 ConfigError("llm.yaml not found at ...")
2. **yaml 解析失败**：抛 ConfigError 包装原 yaml.YAMLError
3. **顶层 key 缺失**：ConfigError 明确指出哪个 key 缺失
4. **provider 不在 providers 中**：ConfigError("provider 'xxx' not defined in providers")
5. **call_sites 段缺 ID**：get_client 抛 ConfigError("call_site 'xxx' not defined")
6. **api_key_env 对应环境变量未设**：get_client 抛 LLMCallError("Missing API key for ...")，不是 ConfigError（D-010 宽松，调用时报错而非加载时）
7. **call_llm 内部任何异常**：traceback.print_exc() 后重抛 LLMCallError
8. **override 不修改传入 dict**：用 .pop / .update 操作 kwargs 局部副本
9. **messages 参数不修改**：直接传给 SDK
10. **functools.lru_cache 缓存**：进程内 load_config 只读一次 yaml，重启进程才生效（R-07 已记录）

## 非目标
- 不实现运行时主备 fallback（D-006）
- 不实现 model 切换的热重载（lru_cache 限制，R-07 已记录）
- 不做 LLM 响应内容校验（业务侧 _why_invalid 负责）
- 不暴露 OpenAI client 之外的 SDK（仅一个 SDK 兼容）

## 参考
- design.md §7.2 API 定义
- `.sillyspec/knowledge/patterns.md` — 「OpenAI 兼容客户端」模式
- `.sillyspec/docs/Daily/modules/classifier.md` 现有 OpenAI(base_url=..., api_key=...) 用法

## TDD 步骤
（无单元测试框架，但可手测）
1. 手测：`python3 -c "import llm_client; print(llm_client.load_config())"` 输出完整 dict
2. 手测：故意写错 yaml `provider: xxx` → 期望 ConfigError
3. 手测：unset NINEROUTER_API_KEY → `python3 -c "import llm_client; llm_client.get_client('china-relevance')"` → 期望 LLMCallError

## 验收标准
| # | 验证步骤 | 通过标准 |
|---|----------|---------|
| AC-01 | `ls /mnt/e/Daily/llm_client.py` | 文件存在 |
| AC-02 | `python3 -c "from llm_client import load_config, get_client, call_llm, ConfigError, LLMCallError; print('OK')"` | 打印 OK |
| AC-03 | `cd /mnt/e/Daily && python3 -c "from llm_client import load_config; c = load_config(); print(c['provider'])"` | 输出 9router |
| AC-04 | `cd /mnt/e/Daily && python3 -c "from llm_client import get_client; client, model, kw = get_client('summarize'); print(model, kw)"` (确保 NINEROUTER_API_KEY 已设) | 输出 `low {'temperature': 0.7, 'max_tokens': 300, 'timeout': 30}` |
| AC-05 | `cd /mnt/e/Daily && NINEROUTER_API_KEY= python3 -c "from llm_client import get_client; get_client('summarize')"` 2>&1 | 输出含 "Missing API key for 9router: NINEROUTER_API_KEY" |
| AC-06 | `grep -E "def load_config|def get_client|def call_llm|class ConfigError|class LLMCallError" /mnt/e/Daily/llm_client.py | wc -l` | 输出 5 |
| AC-07 | `grep "traceback.print_exc" /mnt/e/Daily/llm_client.py | wc -l` | 输出 ≥ 2（call_llm 内异常处理）|
| AC-08 | `grep "lru_cache" /mnt/e/Daily/llm_client.py` | 输出含 lru_cache 装饰器 |
