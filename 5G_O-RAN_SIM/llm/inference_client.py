"""Unified LLM inference client for the 5G_O-RAN_SIM platform substrate.

Conforms to:
  bibliography ref 13 (Anthropic Model Context Protocol, the broader provider context),
  bibliography ref 17 (LiteLLM-style provider abstraction)

Reads 5G_O-RAN_SIM/.env (template at .env.example) to route LLM calls across three
providers:

- anthropic: Anthropic Claude messages API
- openai:    OpenAI chat completions API
- vllm:      OpenAI-compatible vLLM endpoint, default local fake mock on port 8090

The harness Router consumes this client from harness/runtime/router.py when
ORAN_LLM_MODE=live is set (per Issue #49). Default behavior (env unset) keeps the
NotImplementedError path so the existing verify gate at 10/10 PASS is unaffected.

Stub safety: if the configured provider key is missing, empty, or the placeholder
"stub-replace-with-real-key" string from .env.example, completion() returns a canned
response without making a network call. This lets the demo run end-to-end without
real API keys.
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

_CANNED_RESPONSE = (
    "stub disambiguation: the platform-layer signal is dominant; classify as host_driver "
    "with target_layer infra and confidence medium. Reasoning: PHC drift correlates with "
    "kernel module version, not RAN-side processing. Recommended path: O2 IMS apply_kmm_module."
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
        return _CANNED_RESPONSE
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
        return f"{_CANNED_RESPONSE}\n[anthropic call failed: {e}]"


def _completion_openai_compatible(provider: str, prompt: str, tier: str) -> str:
    """Call any OpenAI-compatible chat completions endpoint (openai or vllm)."""
    key = _env(f"{provider.upper()}_API_KEY")
    base = _env(f"{provider.upper()}_BASE_URL")
    model = _resolve_model(provider, tier)
    # vllm uses an OpenAI-compatible mock so empty key is fine there; still bail on stub
    if provider == "openai" and _is_stub_key(key):
        return _CANNED_RESPONSE
    try:
        import httpx

        headers = {"content-type": "application/json"}
        if key and key != "demo-no-auth-required":
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
        return f"{_CANNED_RESPONSE}\n[{provider} call failed: {e}]"


def completion(prompt: str, tier: str = "medium") -> str:
    """Unified completion entry point.

    Args:
      prompt: free-form text input to the LLM
      tier:   "high" | "medium" | "low" mapped to the provider-specific model id

    Returns:
      The model's textual completion. Falls back to a deterministic canned response
      if the configured provider key is a stub or the network call fails.
    """
    provider = _env("LLM_PROVIDER", "vllm").lower()
    if provider == "anthropic":
        return _completion_anthropic(prompt, tier)
    if provider in ("openai", "vllm"):
        return _completion_openai_compatible(provider, prompt, tier)
    return f"{_CANNED_RESPONSE}\n[unknown LLM_PROVIDER {provider!r}, used canned response]"


if __name__ == "__main__":
    import sys

    prompt = sys.argv[1] if len(sys.argv) > 1 else "disambiguate ptp drift root cause"
    tier = sys.argv[2] if len(sys.argv) > 2 else "low"
    print(completion(prompt, tier))
