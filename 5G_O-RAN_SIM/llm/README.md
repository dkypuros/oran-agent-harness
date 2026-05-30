# 5G_O-RAN_SIM LLM inference layer

Unified LLM client for the platform substrate, plus a fake OpenShift AI vLLM mock server.

## What lives here

- `inference_client.py`: `completion(prompt, tier)` function. Reads
  `5G_O-RAN_SIM/.env` (template in `.env.example`) and routes to one of three providers
  based on the `LLM_PROVIDER` env var.
- `fake_vllm_server.py`: FastAPI mock on port 8090, implements
  `POST /v1/chat/completions` in the OpenAI shape. Returns canned but plausible
  disambiguation responses keyed on prompt content. NOT a real LLM.
- `__init__.py`: exposes `completion` at the package root.
- `mock_traces.jsonl`: appended by the fake server. Gitignored.

## Three providers, three behaviors

| Provider          | When to use                                                  | Default config                                |
|-------------------|--------------------------------------------------------------|-----------------------------------------------|
| `anthropic`       | Real production traffic against Anthropic Claude             | Stub key. Replace with real key in `.env`.    |
| `openai`          | Alternative production traffic against OpenAI                | Stub key. Replace with real key in `.env`.    |
| `vllm` (default)  | Demo, talks, local experimentation, p2p sync replay analysis | Points at the local fake server on `:8090`.   |

The `LLM_PROVIDER` env var in `.env` selects which one `completion()` routes to.

## Stub safety

If the configured provider's API key is missing, empty, or still set to the
`stub-replace-with-real-key` placeholder string, `completion()` skips the network call
and returns a deterministic canned disambiguation string. The harness's ambiguous_path
exercises the seam even when no real API keys are configured.

## Quick start: run the fake vLLM locally

```bash
cd 5G_O-RAN_SIM
cp .env.example .env
pip install fastapi uvicorn python-dotenv httpx pydantic
python llm/fake_vllm_server.py &
# in another shell:
python -c "from llm import completion; print(completion('disambiguate ptp drift root cause', 'low'))"
```

Expected output: a canned disambiguation string matching one of the keyword groups in
`fake_vllm_server.py` (ptp/phc/drift/host_driver/kmm). The fake server logs the request
to `mock_traces.jsonl` in this directory.

## Swap to real Anthropic or OpenAI

1. Edit `5G_O-RAN_SIM/.env`
2. Replace `ANTHROPIC_API_KEY=stub-replace-with-real-key` with your real key
3. Set `LLM_PROVIDER=anthropic` (or `openai`)
4. The next `completion()` call goes to the real provider

## How the harness consumes this

The router at `harness/runtime/router.py` consumes this client from its
`ambiguous_path` branch when `ORAN_LLM_MODE=live` is set (Issue #49). Default
behavior (env unset) keeps the historical `NotImplementedError` path so the
existing verify gate at 10/10 PASS is unaffected.

```bash
# default: harness raises NotImplementedError on ambiguous_path (verify gate unaffected)
python3 -m harness.runtime.walker scenarios/A_fw_lldp_agent/fault_payload.json

# live mode: harness calls into this client for ambiguous_path
ORAN_LLM_MODE=live python3 -m harness.runtime.walker <ambiguous-scenario-fault-payload.json>
```

## Honest scope

This is demo scaffolding. Real OpenShift AI vLLM deployments serve Granite, Llama,
Mistral, or other models on GPU-backed infrastructure. The fake server here returns
canned text; it does not load a model, does not perform inference, does not honor
temperature or max_tokens beyond echoing values into the response envelope. Swap the
`VLLM_BASE_URL` to a real OpenShift AI endpoint for production behavior.
