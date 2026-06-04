"""Unified LLM inference client for the 5G_O-RAN_SIM platform substrate.

Conforms to:
  bibliography ref 13 (Anthropic Model Context Protocol, the broader provider context),
  bibliography ref 17 (LiteLLM-style provider abstraction)

Reads 5G_O-RAN_SIM/.env (template at .env.example) to route LLM calls across
operator-selected providers:

- anthropic: Anthropic Claude messages API
- openai:    OpenAI chat completions API
- vllm:      OpenAI-compatible on-prem vLLM endpoint, for example Red Hat
             OpenShift AI

The harness Router consumes this client from harness/runtime/router.py when
ORAN_LLM_MODE=live is set (per Issue #49). Default behavior (env unset) keeps the
NotImplementedError path so the existing verify gate at 10/10 PASS is unaffected.

Provider safety: if the selected provider is not configured, completion() returns a
clear unavailable message rather than synthesizing a model answer. The router does
not auto-apply the hint in v0, so this remains safe for ambiguous-path tests.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_RUNTIME_DIR = Path(__file__).resolve().parent
_SIM_ROOT = _RUNTIME_DIR.parent

# Load .env if present. dotenv is optional; fall back to plain os.environ.
try:
    from dotenv import load_dotenv

    load_dotenv(_SIM_ROOT / ".env")
except ImportError:
    pass


STUB_KEY_SENTINEL = "stub-replace-with-real-key"


def _unavailable(provider: str, reason: str) -> str:
    """Return an explicit non-inference response for safe live-mode diagnostics."""
    return (
        f"LLM provider {provider!r} unavailable: {reason}. "
        "No LLM disambiguation was performed."
    )


def _env(name: str, default: str = "") -> str:
    """Read env var with default fallback."""
    return os.environ.get(name, default).strip()


def _is_stub_key(key: str) -> bool:
    """True if the key is missing, empty, or the .env.example placeholder."""
    return not key or key == STUB_KEY_SENTINEL


def _resolve_model(provider: str, tier: str) -> str:
    """Look up the configured model id for the provider/tier combination."""
    tier = tier.upper() if tier in ("high", "medium", "low") else "MEDIUM"
    return _env(f"{provider.upper()}_MODEL_{tier}", f"unknown-model-{tier.lower()}")


def _completion_anthropic(prompt: str, tier: str) -> str:
    """Call Anthropic Claude messages API."""
    key = _env("ANTHROPIC_API_KEY")
    if _is_stub_key(key):
        return _unavailable("anthropic", "set ANTHROPIC_API_KEY to use Claude")
    base = _env("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    model = _resolve_model("anthropic", tier)
    try:
        import httpx

        resp = httpx.post(
            f"{base}/v1/messages",
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 512,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]
    except Exception as e:
        return _unavailable("anthropic", f"provider call failed: {e}")


def _completion_openai_compatible(provider: str, prompt: str, tier: str) -> str:
    """Call any OpenAI-compatible chat completions endpoint (openai or vllm)."""
    key = _env(f"{provider.upper()}_API_KEY")
    base = _env(f"{provider.upper()}_BASE_URL")
    model = _resolve_model(provider, tier)
    if not base:
        return _unavailable(provider, f"set {provider.upper()}_BASE_URL")
    if provider == "openai" and _is_stub_key(key):
        return _unavailable("openai", "set OPENAI_API_KEY to use the OpenAI API")
    try:
        import httpx

        headers = {"content-type": "application/json"}
        if key and key not in ("demo-no-auth-required", STUB_KEY_SENTINEL):
            headers["authorization"] = f"Bearer {key}"
        resp = httpx.post(
            f"{base}/chat/completions",
            headers=headers,
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 512,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return _unavailable(provider, f"provider call failed: {e}")


def completion(prompt: str, tier: str = "medium") -> str:
    """Unified completion entry point.

    Args:
      prompt: free-form text input to the LLM
      tier:   "high" | "medium" | "low" mapped to the provider-specific model id

    Returns:
      The model's textual completion, or an explicit unavailable message when the
      selected provider is not configured or the call fails.
    """
    provider = _env("LLM_PROVIDER", "anthropic").lower()
    if provider == "anthropic":
        return _completion_anthropic(prompt, tier)
    if provider in ("openai", "vllm"):
        return _completion_openai_compatible(provider, prompt, tier)
    return _unavailable(provider, "LLM_PROVIDER must be anthropic, openai, or vllm")


if __name__ == "__main__":
    import sys

    prompt = sys.argv[1] if len(sys.argv) > 1 else "disambiguate ptp drift root cause"
    tier = sys.argv[2] if len(sys.argv) > 2 else "low"
    print(completion(prompt, tier))
