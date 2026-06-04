# 5G_O-RAN_SIM LLM inference layer

Unified LLM client for the platform substrate. It is intentionally provider-neutral:
operators can route the ambiguous-path LLM seam to Anthropic, the OpenAI API, or an
OpenAI-compatible on-prem vLLM endpoint such as Red Hat OpenShift AI.

## What lives here

- `inference_client.py`: `completion(prompt, tier)` function. Reads
  `5G_O-RAN_SIM/.env` (template in `.env.example`) plus process environment and
  routes to the provider selected by `LLM_PROVIDER`.
- `__init__.py`: exposes `completion` at the package root.

## Providers

| Provider | When to use | Required configuration |
|---|---|---|
| `anthropic` | Hosted Claude model, also the provider used by the MacBook dashboard chat service | `ANTHROPIC_API_KEY`, optional `ANTHROPIC_BASE_URL`, model env vars |
| `openai` | Hosted OpenAI API | `OPENAI_API_KEY`, optional `OPENAI_BASE_URL`, model env vars |
| `vllm` | On-prem OpenAI-compatible inference, for example Red Hat OpenShift AI | `VLLM_BASE_URL`, optional `VLLM_API_KEY`, model env vars |

The `LLM_PROVIDER` env var selects which one `completion()` routes to. The default
provider is `anthropic` because the MacBook lab's chat service is Anthropic-backed
when the operator supplies `ANTHROPIC_API_KEY` in `macbook_lab/.env`.

## Provider safety

This directory ships no local LLM simulator. If the selected provider is not configured,
`completion()` returns a clear unavailable message rather than synthesizing a model
answer. The harness Router records that hint on the ambiguous path, but it
does not auto-apply the LLM response in v0.

## Quick start: Anthropic

```bash
cd 5G_O-RAN_SIM
cp .env.example .env
# edit .env: set ANTHROPIC_API_KEY and LLM_PROVIDER=anthropic
python -c "from llm import completion; print(completion('disambiguate ptp drift root cause', 'low'))"
```

## Quick start: OpenAI API

```bash
cd 5G_O-RAN_SIM
cp .env.example .env
# edit .env: set OPENAI_API_KEY and LLM_PROVIDER=openai
python -c "from llm import completion; print(completion('disambiguate ptp drift root cause', 'low'))"
```

## Quick start: on-prem vLLM / OpenShift AI

```bash
cd 5G_O-RAN_SIM
cp .env.example .env
# edit .env: set LLM_PROVIDER=vllm and VLLM_BASE_URL=https://<your-route>/v1
# set VLLM_API_KEY if your endpoint requires bearer auth
python -c "from llm import completion; print(completion('disambiguate ptp drift root cause', 'low'))"
```

## How the harness consumes this

The router at `harness/runtime/router.py` consumes this client from its
`ambiguous_path` branch when `ORAN_LLM_MODE=live` is set (Issue #49). Default
behavior (env unset) keeps the historical `NotImplementedError` path so the
existing verify gate stays deterministic and provider-independent.

```bash
# default: harness raises NotImplementedError on ambiguous_path (verify gate unaffected)
python3 -m harness.runtime.walker scenarios/A_fw_lldp_agent/fault_payload.json

# live mode: harness calls into this client for ambiguous_path
ORAN_LLM_MODE=live python3 -m harness.runtime.walker <ambiguous-scenario-fault-payload.json>
```

## Honest scope

The deterministic paper and verify-gate claims do not require any LLM provider. The
live LLM path is an optional support tier for ambiguous classifications. Anthropic,
OpenAI, and on-prem vLLM may produce different prose, so the harness treats the LLM
output as a bounded hint rather than a directly applied remediation decision.
