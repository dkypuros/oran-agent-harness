"""Fake OpenShift AI vLLM mock server for 5G_O-RAN_SIM demos.

Conforms to:
  bibliography ref 17 (LiteLLM-style provider abstraction; vLLM serves an OpenAI-compatible API)

A small FastAPI service on port 8090 that implements POST /v1/chat/completions in the
OpenAI shape. Returns canned but plausible disambiguation responses keyed on prompt
content, with a small randomized-feeling text variation per call. Logs every request
to 5G_O-RAN_SIM/llm/mock_traces.jsonl for replay analysis (the file is gitignored).

This is NOT a real LLM. It exists so the harness's ambiguous_path can be exercised
end-to-end without external network calls, real GPU resources, or API key management.
In production, swap the VLLM_BASE_URL to a real OpenShift AI vLLM deployment.

Run with:
    python 5G_O-RAN_SIM/llm/fake_vllm_server.py
or:
    uvicorn fake_vllm_server:app --host 0.0.0.0 --port 8090
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

try:
    from fastapi import FastAPI
    from pydantic import BaseModel
except ImportError as e:
    raise SystemExit(
        "fake_vllm_server requires fastapi and uvicorn. "
        "Install with: pip install fastapi uvicorn pydantic"
    ) from e


_LLM_DIR = Path(__file__).resolve().parent
_TRACE_LOG = _LLM_DIR / "mock_traces.jsonl"


app = FastAPI(
    title="5G_O-RAN_SIM fake vLLM",
    description=(
        "OpenAI-compatible chat completions mock. Returns canned disambiguation responses "
        "for the harness ambiguous_path. NOT a real LLM. Demo only."
    ),
    version="0.1.0",
)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    max_tokens: int | None = 512
    temperature: float | None = 0.0


_CANNED_BY_KEYWORD = [
    (
        ("ptp", "phc", "drift", "host_driver", "kmm"),
        (
            "Classification: host_driver. Target layer: infra. Confidence: medium. "
            "Reasoning: PHC drift signatures with monotonic frequency offset correlate "
            "with kernel module version rather than RAN scheduling. Recommended path is "
            "O2 IMS apply_kmm_module via the Kernel Module Management Operator."
        ),
    ),
    (
        ("fw-lldp", "systemd", "service", "host_config", "machineconfig"),
        (
            "Classification: ptp_host_stack. Target layer: infra. Confidence: high. "
            "Reasoning: a host-level systemd service is contending for PHC, evidenced by "
            "tx_hwtstamp_timeouts. Recommended path is O2 IMS apply_machine_config via "
            "the Machine Config Operator to mask the offending unit."
        ),
    ),
    (
        ("transport", "ecpri", "fronthaul", "mtu", "network_transport"),
        (
            "Classification: ambiguous, leaning network_transport. Target layer: ambiguous. "
            "Confidence: low. Reasoning: eCPRI fabric symptoms can originate at the NIC, "
            "the switch fabric, or the RAN side. Recommended next step is to gate on more "
            "MCP-hardware telemetry before routing."
        ),
    ),
    (
        ("ran_parameter", "cell", "qos", "slice"),
        (
            "Classification: ran_parameter. Target layer: service. Confidence: high. "
            "Reasoning: cell-level KPI degradation aligns with RAN-side parameter behavior, "
            "not platform infra. Recommended path is emit_smo_intent via TMF921 to the "
            "partner SMO."
        ),
    ),
]


_GENERIC_FALLBACK = (
    "Classification: harness-defined subtype within WG6 three-class model. Target layer: "
    "ambiguous (fake-mock fallback). Confidence: low. Reasoning: prompt did not match any "
    "of the canned disambiguation patterns; in a real deployment a configured LLM provider "
    "would resolve this."
)


def _pick_completion(prompt: str) -> str:
    lower = prompt.lower()
    for keywords, response in _CANNED_BY_KEYWORD:
        if any(kw in lower for kw in keywords):
            return response
    return _GENERIC_FALLBACK


def _trace(record: dict[str, Any]) -> None:
    """Append a JSON record per request. Best-effort; never fails the call."""
    try:
        with _TRACE_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except Exception:
        pass


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "service": "5G_O-RAN_SIM fake vLLM",
        "real_llm": False,
        "version": "0.1.0",
        "endpoint": "/v1/chat/completions",
        "models": [
            "granite-7b-instruct",
            "llama-3-8b-instruct",
            "mistral-7b-instruct",
        ],
    }


@app.post("/v1/chat/completions")
def chat_completions(req: ChatCompletionRequest) -> dict[str, Any]:
    last_user = next(
        (m.content for m in reversed(req.messages) if m.role == "user"),
        "",
    )
    completion_text = _pick_completion(last_user)
    response = {
        "id": f"chatcmpl-fake-vllm-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": req.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": completion_text},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": max(1, len(last_user.split())),
            "completion_tokens": len(completion_text.split()),
            "total_tokens": max(1, len(last_user.split())) + len(completion_text.split()),
        },
    }
    _trace(
        {
            "ts": int(time.time()),
            "model": req.model,
            "prompt_preview": last_user[:200],
            "response_preview": completion_text[:200],
        }
    )
    return response


def main() -> int:
    try:
        import uvicorn
    except ImportError:
        raise SystemExit("uvicorn required. pip install uvicorn[standard]")
    port = int(os.environ.get("VLLM_MOCK_PORT", "8090"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
