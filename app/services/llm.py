"""Unified LLM layer.

One interface, two providers. Anthropic (Claude) is preferred when configured;
OpenAI is the fallback. If neither key is set, callers get None and fall back to
their own templates so the app keeps working offline.

    from .services import llm
    text = llm.complete("Write a haiku about pipelines.")
    data = llm.complete_json("Return JSON {a, b} ...")
"""
from __future__ import annotations

import json
import logging
import re

from ..config import settings

logger = logging.getLogger("outflow")


def provider() -> str:
    if settings.anthropic_api_key:
        return "anthropic"
    if settings.openai_api_key:
        return "openai"
    return "none"


def enabled() -> bool:
    return provider() != "none"


def complete(
    prompt: str,
    *,
    system: str | None = None,
    temperature: float = 0.5,
    max_tokens: int = 1200,
) -> str | None:
    """Return generated text, or None if no provider is configured / call fails."""
    p = provider()
    try:
        if p == "anthropic":
            return _anthropic(prompt, system, temperature, max_tokens)
        if p == "openai":
            return _openai(prompt, system, temperature, max_tokens, json_mode=False)
    except Exception:
        logger.warning("LLM completion failed (provider=%s)", p, exc_info=True)
    return None


def complete_json(
    prompt: str,
    *,
    system: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 1500,
) -> dict | None:
    """Return parsed JSON dict, or None on failure."""
    p = provider()
    try:
        if p == "anthropic":
            raw = _anthropic(
                prompt + "\n\nReturn ONLY valid JSON, no prose, no code fences.",
                system,
                temperature,
                max_tokens,
            )
        elif p == "openai":
            raw = _openai(prompt, system, temperature, max_tokens, json_mode=True)
        else:
            return None
        return _extract_json(raw) if raw else None
    except Exception:
        logger.warning("LLM json completion failed (provider=%s)", p, exc_info=True)
        return None


# --------------------------------------------------------------------------- #
# Provider implementations (SDKs imported lazily so they stay optional deps)
# --------------------------------------------------------------------------- #
def _anthropic(prompt, system, temperature, max_tokens) -> str:
    from anthropic import Anthropic

    client = Anthropic(api_key=settings.anthropic_api_key)
    msg = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system or "You are a precise B2B go-to-market assistant.",
        messages=[{"role": "user", "content": prompt}],
    )
    # content is a list of blocks; concatenate text blocks.
    return "".join(getattr(b, "text", "") for b in msg.content).strip()


def _openai(prompt, system, temperature, max_tokens, json_mode) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    kwargs = {
        "model": settings.openai_model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [],
    }
    if system:
        kwargs["messages"].append({"role": "system", "content": system})
    kwargs["messages"].append({"role": "user", "content": prompt})
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = client.chat.completions.create(**kwargs)
    return (resp.choices[0].message.content or "").strip()


def _extract_json(raw: str) -> dict | None:
    """Tolerant JSON parse: strips code fences, grabs the outermost object."""
    s = raw.strip()
    s = re.sub(r"^```(?:json)?|```$", "", s, flags=re.MULTILINE).strip()
    try:
        return json.loads(s)
    except Exception:
        pass
    start, end = s.find("{"), s.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(s[start : end + 1])
        except Exception:
            return None
    return None
