"""oh-my-tiny-oran service.

A deliberately tiny replication of the OMC (Yeachan-Heo/oh-my-claudecode) pattern
scoped to this project's oran-discover skill bundle. The user chats; when they
type a slash command like /oran-discover:plan, the service inlines the full
skill markdown into the next user message exactly the way OMC's keyword-detector
hook does (scripts/keyword-detector.mjs:343-359 in upstream OMC). The agent
then executes with tool use against the lab's HTTP wrappers and committed files.

Tiny on purpose. No persistent-mode loop, no team orchestration, no MCP server,
no slash registry beyond inline injection. Two tools: curl_endpoint, read_file.
Sessions persist in memory keyed by session_id. The user's ANTHROPIC_API_KEY
in macbook_lab/.env is what powers the agent.

References (upstream OMC):
  scripts/keyword-detector.mjs:343-359  inline skill injection pattern
  src/utils/skill-pipeline.ts:10-22     slash command normalization
  src/tools/state-tools.ts              session-keyed state (we keep it in-memory)
"""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

APP_ROOT = Path("/app")
SKILL_DIR = APP_ROOT / "omc-skills" / "oran-discover"
ALLOWED_READ_ROOTS = [
    APP_ROOT / "5G_O-RAN_SIM",
    APP_ROOT / "harness",
    APP_ROOT / "scenarios",
    APP_ROOT / "omc-skills",
    APP_ROOT / "docs",
]
ALLOWED_CURL_HOSTS = {
    "ptp-operator-stub": 8091,
    "metal3-bmo-stub": 8092,
    "redfish-bmc-stub": 8093,
    "tmf921-smo-stub": 8094,
    "harness-walker": 8096,
}

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL_LOW", "claude-haiku-4-5-20251001")
MAX_AGENT_TURNS = int(os.environ.get("TINY_ORAN_MAX_TURNS", "10"))

app = FastAPI(title="oh-my-tiny-oran")

TOOLS_SPEC = [
    {
        "name": "curl_endpoint",
        "description": (
            "GET a URL from one of the lab's HTTP wrappers. Returns the response body. "
            "Allowed hosts: ptp-operator-stub:8091, metal3-bmo-stub:8092, redfish-bmc-stub:8093, "
            "tmf921-smo-stub:8094, harness-walker:8096. Use this to inspect live lab state."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    },
    {
        "name": "read_file",
        "description": (
            "Read a committed file from the repo. Allowed roots: 5G_O-RAN_SIM/, harness/, "
            "scenarios/, omc-skills/, docs/. Use this for taxonomy, guardrails, scenario fixtures, "
            "or any skill markdown."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
]

SLASH_PATTERN = re.compile(r"^/(oran-discover):([a-z][a-z0-9_-]*)\b\s*(.*)$", re.IGNORECASE)


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str


class ToolCallRecord(BaseModel):
    name: str
    input: dict[str, Any]


class ChatTurn(BaseModel):
    role: str
    content: str
    tool_uses: list[ToolCallRecord] = []
    input_tokens: int = 0
    output_tokens: int = 0
    latency_s: float = 0.0
    skill_invoked: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    turn: ChatTurn
    history_length: int


SKILLS: dict[str, dict[str, Any]] = {}
SESSIONS: dict[str, list[dict[str, Any]]] = {}


def load_skills() -> None:
    SKILLS.clear()
    if not SKILL_DIR.exists():
        return
    for md in sorted(SKILL_DIR.glob("*.md")):
        if md.name in ("README.md", "conformance.md"):
            continue
        body = md.read_text()
        m = re.search(r"^name:\s*(\S+)", body, re.MULTILINE)
        name = m.group(1).strip() if m else f"oran-discover:{md.stem}"
        desc_m = re.search(r"^description:\s*(.+)$", body, re.MULTILINE)
        description = desc_m.group(1).strip() if desc_m else ""
        SKILLS[name] = {"name": name, "description": description, "body": body, "stem": md.stem}


load_skills()


def detect_slash_skill(user_message: str) -> tuple[str | None, str]:
    """Detect a slash command at the start of the message; mirrors OMC keyword-detector.

    Returns (skill_name_or_none, remaining_user_text).
    """
    m = SLASH_PATTERN.match(user_message.strip())
    if not m:
        return None, user_message
    bundle, stem, remainder = m.group(1), m.group(2), m.group(3).strip()
    skill_name = f"{bundle}:{stem}"
    if skill_name not in SKILLS:
        return None, user_message
    return skill_name, remainder


def expand_user_message(user_message: str) -> tuple[str, str | None]:
    """If the message starts with a known slash command, inline the skill MD.

    Mirrors OMC scripts/keyword-detector.mjs:343-359 where the SKILL.md is injected
    as `[MAGIC KEYWORD: <name>]\\n\\n<body>` into the user message.
    """
    skill, remainder = detect_slash_skill(user_message)
    if skill is None:
        return user_message, None
    body = SKILLS[skill]["body"]
    follow_up = remainder if remainder else "Run this skill now and produce the documented output."
    wrapped = (
        f"[SKILL INVOKED: {skill}]\n\n"
        f"{body}\n\n"
        f"=== USER MESSAGE ===\n{follow_up}"
    )
    return wrapped, skill


def _resolve_curl(url: str) -> str:
    """Parse the URL via urllib.parse (not regex) to avoid host-confusion edge cases.

    urlparse correctly separates scheme/userinfo/host/port/path/query/fragment per RFC 3986,
    rejecting auth-credential injection like http://evil@allowed-host/path.
    """
    try:
        parsed = urlparse(url)
    except ValueError as e:
        return json.dumps({"error": f"unrecognized URL: {url} ({e})"})
    if parsed.scheme not in ("http", "https"):
        return json.dumps({"error": f"scheme not allowed: {parsed.scheme}"})
    host = parsed.hostname
    port = parsed.port or 0
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    if host is None:
        return json.dumps({"error": f"could not parse host from URL: {url}"})
    expected = ALLOWED_CURL_HOSTS.get(host)
    if expected is None or (port and port != expected):
        return json.dumps({"error": f"host not allowed: {host}:{port}"})
    if parsed.username or parsed.password:
        return json.dumps({"error": f"auth credentials not allowed in URL"})
    target = f"http://{host}:{expected}{path}"
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(target)
        return json.dumps({"status": resp.status_code, "body": resp.text[:4000]})
    except httpx.HTTPError as e:
        return json.dumps({"error": f"http error: {type(e).__name__}: {e}"})


def _resolve_read(path: str) -> str:
    target = (APP_ROOT / path).resolve()
    if not any(str(target).startswith(str(root.resolve())) for root in ALLOWED_READ_ROOTS):
        return json.dumps({"error": f"path not allowed: {path}"})
    if not target.exists() or not target.is_file():
        return json.dumps({"error": f"file not found: {path}"})
    try:
        return json.dumps({"path": path, "content": target.read_text()[:8000]})
    except UnicodeDecodeError:
        return json.dumps({"error": f"binary file not readable: {path}"})


def _run_tool(name: str, args: dict[str, Any]) -> str:
    if name == "curl_endpoint":
        return _resolve_curl(args.get("url", ""))
    if name == "read_file":
        return _resolve_read(args.get("path", ""))
    return json.dumps({"error": f"unknown tool: {name}"})


def _system_prompt() -> str:
    skill_lines = [f"  /{s['name']}: {s['description']}" for s in SKILLS.values()]
    skills_block = "\n".join(skill_lines) if skill_lines else "  (no skills loaded)"
    return (
        "You are oh-my-tiny-oran, a tiny chat-driven harness for the O-RAN Agent Harness research bench. "
        "The user is exploring the lab and asking questions. Be conversational and concise.\n\n"
        "Tools available:\n"
        "  curl_endpoint(url) - GET state from the lab's HTTP wrappers\n"
        "  read_file(path) - read committed repo files\n\n"
        "Lab wrapper endpoints (these are the ONLY paths that exist; do not guess others):\n"
        "  ptp-operator-stub:8091    /health  /state  /history\n"
        "  metal3-bmo-stub:8092      /health  /state  /history\n"
        "  redfish-bmc-stub:8093     /health  /state  /history\n"
        "  tmf921-smo-stub:8094      /health  /state  /history\n"
        "  harness-walker:8096       /health  /scenarios  /run/{scenario_id}  /bench/all  /traces  /traces/{scenario_id}\n\n"
        "The harness-walker's /run/{scenario_id} endpoint returns the FULL audit event including "
        "remediation, blast radius, taxonomy match, and a companion_intent field for dual-route "
        "scenarios. That single call IS the result; do not look for separate /approve or /results.\n\n"
        "To verify a scenario actually fired, GET /history on the corresponding wrapper (e.g. "
        "metal3-bmo-stub:8092/history shows the firmware phases, tmf921-smo-stub:8094/history "
        "shows emitted intents).\n\n"
        "Skills you can be invoked with (the user prefixes with `/`):\n"
        f"{skills_block}\n\n"
        "When the user invokes a slash command, the skill markdown will be injected into their "
        "message as `[SKILL INVOKED: ...]`. Execute the Steps section of that skill using the "
        "tools above. For ordinary questions, answer directly with tool use when needed. "
        "Stay read-only; do not propose actions that mutate state. "
        "Always synthesize a final answer for the user, even if you are running low on turns."
    )


def _run_agent_turn(session_id: str, raw_user_message: str) -> ChatTurn:
    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "stub-replace-with-real-key":
        raise HTTPException(503, "ANTHROPIC_API_KEY is not set in macbook_lab/.env")
    try:
        import anthropic
    except ImportError as e:
        raise HTTPException(500, f"anthropic SDK not installed: {e}")

    expanded_message, skill_invoked = expand_user_message(raw_user_message)
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    history = SESSIONS.setdefault(session_id, [])
    history.append({"role": "user", "content": expanded_message})

    total_in = 0
    total_out = 0
    tool_uses_collected: list[ToolCallRecord] = []
    final_text = ""
    start = time.monotonic()
    system = _system_prompt()

    for _ in range(MAX_AGENT_TURNS):
        try:
            resp = client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=2048,
                system=system,
                tools=TOOLS_SPEC,
                messages=history,
            )
        except anthropic.RateLimitError:
            final_text = "[Anthropic rate-limited the request. Wait a moment and retry.]"
            break
        except anthropic.APIStatusError as e:
            final_text = f"[Anthropic API error: HTTP {e.status_code}. Retry shortly.]"
            break
        except anthropic.APIError as e:
            final_text = f"[Anthropic API error: {type(e).__name__}: {e}]"
            break
        total_in += resp.usage.input_tokens
        total_out += resp.usage.output_tokens
        text_parts = []
        tool_uses = []
        for block in resp.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_uses.append(block)
                tool_uses_collected.append(ToolCallRecord(name=block.name, input=block.input))
        history.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason == "end_turn" or not tool_uses:
            final_text = "\n".join(text_parts).strip()
            break

        tool_results = []
        for tu in tool_uses:
            result = _run_tool(tu.name, tu.input)
            tool_results.append({"type": "tool_result", "tool_use_id": tu.id, "content": result})
        history.append({"role": "user", "content": tool_results})
    else:
        final_text = "[agent loop reached MAX_AGENT_TURNS]"

    elapsed = time.monotonic() - start
    return ChatTurn(
        role="assistant",
        content=final_text or "(no text)",
        tool_uses=tool_uses_collected,
        input_tokens=total_in,
        output_tokens=total_out,
        latency_s=round(elapsed, 2),
        skill_invoked=skill_invoked,
    )


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "service": "oh-my-tiny-oran",
        "skill_count": len(SKILLS),
        "session_count": len(SESSIONS),
        "anthropic_key_set": bool(ANTHROPIC_API_KEY) and ANTHROPIC_API_KEY != "stub-replace-with-real-key",
        "model": ANTHROPIC_MODEL,
        "max_turns": MAX_AGENT_TURNS,
    }


@app.get("/skills")
def list_skills() -> dict[str, Any]:
    return {
        "count": len(SKILLS),
        "skills": [{"name": s["name"], "description": s["description"]} for s in SKILLS.values()],
    }


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    sid = req.session_id or uuid.uuid4().hex[:16]
    turn = _run_agent_turn(sid, req.message)
    return ChatResponse(session_id=sid, turn=turn, history_length=len(SESSIONS[sid]))


@app.delete("/chat/{session_id}")
def clear_session(session_id: str) -> dict[str, Any]:
    existed = session_id in SESSIONS
    SESSIONS.pop(session_id, None)
    return {"session_id": session_id, "cleared": existed}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8098")))
