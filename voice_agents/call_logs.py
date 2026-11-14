"""Local copies of finished calls for analysis.

Each call is saved as call_logs/<conversation_id>.json: the full ElevenLabs
conversation (transcript, analysis, metadata) plus the agent context we built it
with. calls.jsonl flattens them, one row per call, for pandas/duckdb.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx

from .agents import AGENTS
from .calls import API_BASE, get_conversation

FINAL = {"done", "failed"}


def log_dir() -> Path:
    path = Path(os.environ.get("CALL_LOG_DIR", "call_logs"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def save(conversation: dict, context: dict | None = None) -> Path | None:
    """Save a finished conversation; earlier context is kept if none is given."""
    cid = conversation.get("conversation_id")
    if not cid or conversation.get("status") not in FINAL:
        return None
    path = log_dir() / f"{cid}.json"
    if context is None and path.exists():
        context = json.loads(path.read_text()).get("context")
    path.write_text(json.dumps({
        "saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "context": context or {},
        "conversation": conversation,
    }, indent=2))
    return path


def agent_context(agent) -> dict:
    """What we told the agent: who called whom, as what, with which script."""
    return {
        "agent_id": agent.id, "kind": agent.kind.value, "archetype": agent.archetype,
        "template": agent.template, "caller": agent.caller, "target": agent.target,
        "voice": agent.voice, "persona": agent.persona.model_dump(mode="json") if agent.persona else None,
        "metadata": agent.request.metadata, "dynamic_variables": agent.request.dynamic_variables,
        "first_message": agent.request.first_message,
    }


def row(saved: dict) -> dict:
    """One flat record per call."""
    c, ctx = saved["conversation"], saved.get("context") or {}
    meta, analysis = c.get("metadata") or {}, c.get("analysis") or {}
    turns = [t for t in c.get("transcript") or [] if t.get("message")]
    variables = ctx.get("dynamic_variables") or (c.get("conversation_initiation_client_data") or {}).get("dynamic_variables") or {}
    return {
        "conversation_id": c.get("conversation_id"),
        "elevenlabs_agent_id": c.get("agent_id"),
        "started_at": meta.get("start_time_unix_secs"),
        "duration_secs": meta.get("call_duration_secs"),
        "status": c.get("status"),
        "termination_reason": meta.get("termination_reason"),
        "archetype": ctx.get("archetype") or c.get("agent_name") or ctx.get("kind"),
        "caller": ctx.get("caller") or variables.get("caller_name") or variables.get("persona_name"),
        "target": ctx.get("target") or variables.get("target_name"),
        "policy_title": variables.get("policy_title"),
        "goal": variables.get("goal") or variables.get("ask"),
        "run_id": (ctx.get("metadata") or {}).get("run_id"),
        "person_id": (ctx.get("metadata") or {}).get("person_id"),
        "call_successful": analysis.get("call_successful"),
        "summary": analysis.get("transcript_summary"),
        "data_collection": {k: v.get("value") for k, v in (analysis.get("data_collection_results") or {}).items()},
        "evaluation": {k: v.get("result") for k, v in (analysis.get("evaluation_criteria_results") or {}).items()},
        "turns": len(turns),
        "agent_words": sum(len(t["message"].split()) for t in turns if t.get("role") == "agent"),
        "user_words": sum(len(t["message"].split()) for t in turns if t.get("role") == "user"),
        "transcript": [{"role": t.get("role"), "at": t.get("time_in_call_secs"), "message": t["message"]} for t in turns],
    }


def write_index() -> Path:
    rows = [row(json.loads(p.read_text())) for p in sorted(log_dir().glob("conv_*.json"))]
    rows.sort(key=lambda r: r["started_at"] or 0)
    out = log_dir() / "calls.jsonl"
    out.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return out


def export_all() -> tuple[int, Path]:
    """Pull every finished call from our ElevenLabs agents that isn't saved yet."""
    headers = {"xi-api-key": os.environ["ELEVENLABS_API_KEY"]}
    saved = 0
    for spec in AGENTS.values():
        cursor = None
        while True:
            params = {"agent_id": spec.agent_id, "page_size": 100, **({"cursor": cursor} if cursor else {})}
            page = httpx.get(f"{API_BASE}/convai/conversations", headers=headers, params=params, timeout=30)
            page.raise_for_status()
            data = page.json()
            for item in data.get("conversations") or []:
                cid = item["conversation_id"]
                if item.get("status") in FINAL and not (log_dir() / f"{cid}.json").exists():
                    save(get_conversation(cid))
                    saved += 1
            cursor = data.get("next_cursor")
            if not data.get("has_more") or not cursor:
                break
    return saved, write_index()
