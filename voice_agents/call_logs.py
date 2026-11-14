"""Finished calls, saved for analysis.

Each call is saved as call_logs/<conversation_id>.json: the full ElevenLabs
conversation (transcript, analysis, metadata) plus the agent context we built it
with. calls.jsonl flattens them, one row per call, for pandas/duckdb. With
SUPABASE_URL and SUPABASE_SECRET_KEY set, each call is also upserted to the
`calls` and `call_turns` tables.
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
    saved = {
        "saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "context": context or {},
        "conversation": conversation,
    }
    path.write_text(json.dumps(saved, indent=2))
    push(saved)
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
    linked = ctx.get("metadata") or {}
    return {
        "conversation_id": c.get("conversation_id"),
        "elevenlabs_agent_id": c.get("agent_id"),
        "agent_name": c.get("agent_name"),
        "started_at": meta.get("start_time_unix_secs"),
        "duration_secs": meta.get("call_duration_secs"),
        "status": c.get("status"),
        "termination_reason": meta.get("termination_reason"),
        "archetype": ctx.get("archetype") or c.get("agent_name") or ctx.get("kind"),
        "caller": ctx.get("caller") or variables.get("caller_name") or variables.get("persona_name"),
        "target": ctx.get("target") or variables.get("target_name"),
        "target_role": variables.get("target_role"),
        "policy_title": variables.get("policy_title"),
        "goal": variables.get("goal") or variables.get("ask"),
        "run_id": linked.get("run_id"),
        "query": linked.get("query"),
        "policy_id": linked.get("policy_id"),
        "jurisdiction": linked.get("jurisdiction"),
        "person_id": linked.get("person_id"),
        "call_successful": analysis.get("call_successful"),
        "summary": analysis.get("transcript_summary"),
        "data_collection": {k: v.get("value") for k, v in (analysis.get("data_collection_results") or {}).items()},
        "evaluation": {k: v.get("result") for k, v in (analysis.get("evaluation_criteria_results") or {}).items()},
        "elevenlabs_sentiment": analysis.get("sentiment_analysis"),
        "turns": len(turns),
        "agent_words": sum(len(t["message"].split()) for t in turns if t.get("role") == "agent"),
        "user_words": sum(len(t["message"].split()) for t in turns if t.get("role") == "user"),
        "transcript": [{"role": t.get("role"), "at": t.get("time_in_call_secs"), "message": t["message"]} for t in turns],
    }


def upsert(table: str, rows: dict | list[dict], on_conflict: str | None = None) -> bool:
    """Upsert rows into a Supabase table; a no-op if Supabase isn't configured."""
    url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SECRET_KEY")
    if not url or not key:
        return False
    headers = {"apikey": key, "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates"}
    if key.startswith("eyJ"):  # a legacy service_role JWT also goes in Authorization
        headers["Authorization"] = f"Bearer {key}"
    params = {"on_conflict": on_conflict} if on_conflict else None
    httpx.post(f"{url.rstrip('/')}/rest/v1/{table}", headers=headers, params=params, json=rows,
               timeout=30).raise_for_status()
    return True


def push(saved: dict) -> bool:
    """Upsert one saved call (and its turns) to Supabase."""
    r = row(saved)
    c = saved["conversation"]
    record = {
        **{k: v for k, v in r.items() if k != "started_at"},
        "started_at": datetime.fromtimestamp(r["started_at"], timezone.utc).isoformat() if r["started_at"] else None,
        "transcript_text": "\n".join(f"{t['role']}: {t['message']}" for t in r["transcript"]),
        "context": saved.get("context") or {},
        # The useful parts of the ElevenLabs record; traces and realtime snapshots are left out.
        "raw": {k: c.get(k) for k in ("metadata", "analysis", "transcript", "conversation_initiation_client_data")},
    }
    if not upsert("calls", record):
        return False
    turns = [{"conversation_id": r["conversation_id"], "turn_index": i, "role": t["role"],
              "at_secs": t["at"], "message": t["message"]} for i, t in enumerate(r["transcript"])]
    if turns:
        upsert("call_turns", turns)
    return True


def write_index() -> Path:
    rows = [row(json.loads(p.read_text())) for p in sorted(log_dir().glob("conv_*.json"))]
    rows.sort(key=lambda r: r["started_at"] or 0)
    out = log_dir() / "calls.jsonl"
    out.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return out


def push_all() -> int:
    """Upsert every locally saved call to Supabase."""
    return sum(push(json.loads(p.read_text())) for p in sorted(log_dir().glob("conv_*.json")))


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
