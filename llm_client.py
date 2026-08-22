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
from pathlib import Path
from typing import Tuple, Dict, Any, List

from dotenv import load_dotenv
load_dotenv()  # 加载 .env，让所有 step 都能读到环境变量

from daily_logging import setup_logging

_logger = setup_logging()

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
        if not isinstance(p, dict):
            raise ConfigError(f"providers.{name} must be mapping")
        for k in ("base_url", "api_key_env"):
            if k not in p:
                raise ConfigError(f"providers.{name} missing {k}")
    for site, s in cfg["call_sites"].items():
        if not isinstance(s, dict):
            raise ConfigError(f"call_sites.{site} must be mapping")
        for k in ("temperature", "max_tokens", "timeout"):
            if k not in s:
                raise ConfigError(f"call_sites.{site} missing {k}")
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
        raise LLMCallError(
            f"Missing API key for {prov_name}: {prov['api_key_env']}"
        )
    client = OpenAI(base_url=prov["base_url"], api_key=api_key)
    site_cfg = cfg["call_sites"][call_site_id]
    kwargs = {
        "temperature": site_cfg["temperature"],
        "max_tokens": site_cfg["max_tokens"],
        "timeout": site_cfg["timeout"],
    }
    # ponytail: provider 可选键；仅 qwen-local 用，新 provider 加同键即可
    if "max_output_tokens" in prov:
        kwargs["max_tokens"] = min(kwargs["max_tokens"], prov["max_output_tokens"])
    if prov.get("reasoning") == "off":
        kwargs["extra_body"] = {"reasoning_effort": "none"}
    return client, cfg["model"], kwargs


def call_llm(
    call_site_id: str, messages: List[Dict[str, str]], **override
) -> str:
    """一次性封装：构造 client + create + 错误处理。

    返回：response.choices[0].message.content
    失败时日志记录脱敏信息到 _logger，重抛 LLMCallError。
    override 可覆盖 temperature/max_tokens/timeout/model。
    """
    try:
        client, model, kwargs = get_client(call_site_id)
        if "model" in override:
            model = override.pop("model")
        kwargs.update(override)
        resp = client.chat.completions.create(
            model=model, messages=messages, **kwargs
        )
        content = resp.choices[0].message.content
        if os.environ.get("DEBUG_LLM_TOKENS"):
            u = resp.usage
            print(f"  [TOKENS] {call_site_id}: prompt={u.prompt_tokens} completion={u.completion_tokens} total={u.total_tokens} finish={resp.choices[0].finish_reason}", flush=True)
        if not content or not content.strip():
            finish_reason = resp.choices[0].finish_reason
            rc = getattr(resp.choices[0].message, "reasoning_content", None)
            _logger.error(
                "LLM empty content: call_site_id=%s, finish_reason=%s, content_len=%d, reasoning_len=%d",
                call_site_id, finish_reason, len(content or ""), len(rc or ""),
            )
            raise LLMCallError(
                f"LLM returned empty content at '{call_site_id}': finish_reason={finish_reason}"
            )
        return content
    except LLMCallError:
        _logger.error("LLM call failed: call_site_id=%s, exception_type=%s", call_site_id, "LLMCallError")
        raise
    except Exception as e:
        _logger.error(
            "LLM call failed: call_site_id=%s, exception_type=%s, status_code=%s, error_code=%s",
            call_site_id, type(e).__name__,
            getattr(e, "status_code", None) or getattr(e, "code", None) or getattr(e, "http_status", None),
            getattr(e, "code", None) or getattr(e, "error", None),
        )
        raise LLMCallError(
            f"LLM call failed at '{call_site_id}'"
        ) from e
