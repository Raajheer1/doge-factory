"""Confidence that a proposed change actually happens: before the calls and after them.

Before calls, the planner's read of each person (where they likely stand, from their
role and interests) moves the score as each agent is built. After a call, a model
reads each finished transcript into structured facts (reached,
position, commitment, sentiment, objections, quotes). Code turns those facts into
the score with fixed weights, so every point traces back to a factor and a quote:

    prior      how hard the change is to make (guidance < regulation < statute)
    stance     each person's stance, weighted by their leverage over the document:
               from their call (mostly sentiment) once reached, else the planner's
               expectation at a fraction of the weight
    evidence   few calls barely move the score; more reached people move it more

Each run keeps its state in call_logs/confidence/<run>.json and appends one
`confidence.v1` snapshot per planned agent and per call. With SUPABASE_URL and SUPABASE_SECRET_KEY set,
reads go to `call_reads` and snapshots to `confidence_scores`. See docs/confidence.md.
"""

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import openai
from pydantic import BaseModel, Field

from . import call_logs
from .handoff import MobilizeHandoff

VERSION = "confidence.v1"
MODEL = os.environ.get("CONFIDENCE_MODEL", "gpt-6-luna")

# How much a person's yes counts toward the change.
LEVERAGE = {"authority_over_document": 1.0, "administers": 0.9, "committee_jurisdiction": 0.75,
            "lobbied_on_document": 0.55, "represents_affected_client": 0.45, "other": 0.3}
# Starting point before any call, by how hard the change is to make.
PATH = {"guidance": 0.55, "policy": 0.5, "regulation": 0.45, "rule": 0.45, "ordinance": 0.4, "statute": 0.32}
POSITION = {"support": 1.0, "lean_support": 0.5, "undecided": 0.0, "lean_oppose": -0.5, "oppose": -1.0, "unknown": 0.0}
COMMITMENT = {"none": 0.0, "will_consider": 0.1, "follow_up": 0.2, "committed": 0.35}
# Sentiment carries the most weight while there are only a few calls.
W_SENTIMENT, W_POSITION = 0.55, 0.45
EVIDENCE_HALF = 0.6  # stance weight at which stances get half their full pull
EXPECTED_WEIGHT = 0.2  # a pre-call guess counts this much next to a clear call (read_confidence 1)
FLOOR, CEILING = 5.0, 95.0
BANDS = [(75, "likely"), (55, "promising"), (40, "toss-up"), (25, "uphill"), (0, "long shot")]


class CallRead(BaseModel):
    reached: bool = Field(description="spoke with the target or their office; false for voicemail, no answer or a hang-up before any exchange")
    position: Literal["support", "lean_support", "undecided", "lean_oppose", "oppose", "unknown"]
    commitment: Literal["none", "will_consider", "follow_up", "committed"]
    sentiment: float = Field(description="the target's tone toward the proposal, -1 hostile to 1 enthusiastic")
    engagement: float = Field(description="0 brushed off to 1 asked questions and engaged with details")
    read_confidence: float = Field(description="0-1, how clearly the transcript shows the target's stance")
    objections: list[str] = Field(description="the target's concerns, a few words each")
    evidence: list[str] = Field(description="up to 3 short verbatim quotes from the target that show their stance")
    rationale: str = Field(description="one sentence on why")


READER = """You read phone-call transcripts from a policy-advocacy campaign. An agent calls a
public figure (the "user" role is the person who answered) and asks them to back a proposed
change. Judge only what the person who answered said and how they said it, never the caller.
Do not infer support from politeness alone. If the transcript is empty or nobody engaged,
set reached to false, position to unknown and read_confidence near 0. Write in plain English;
give quotes without surrounding quotation marks."""


def runs_dir() -> Path:
    path = call_logs.log_dir() / "confidence"
    path.mkdir(parents=True, exist_ok=True)
    return path


def run_key(handoff: dict) -> str:
    return handoff.get("run_id") or handoff["policy"]["id"]


def _path(key: str) -> Path:
    return runs_dir() / f"{''.join(c if c.isalnum() or c in '-_' else '_' for c in key)}.json"


def load(key: str) -> dict | None:
    p = _path(key)
    return json.loads(p.read_text()) if p.exists() else None


def _store(state: dict) -> None:
    _path(state["key"]).write_text(json.dumps(state, indent=2))


_lock = threading.Lock()
_reading: set[str] = set()
current_key: str | None = None  # the run whose agents were built last


def start(handoff: dict) -> dict:
    """Begin (or resume) scoring a run: a baseline snapshot from the handoff alone."""
    global current_key
    MobilizeHandoff.model_validate(handoff)
    key = current_key = run_key(handoff)
    with _lock:
        state = load(key) or {"key": key, "reads": {}, "expected": {}, "history": []}
        state["handoff"] = handoff
        state.setdefault("expected", {})
        if not state["history"]:
            _append(state, {"type": "baseline", "summary": "Before any calls: path difficulty only"})
        _store(state)
    return state


def expect(handoff: dict, person_id: str, position: str, reason: str) -> dict | None:
    """Record the planner's pre-call read of one person and rescore."""
    with _lock:
        state = load(run_key(handoff))
        if not state:
            return None
        state["expected"][person_id] = {"position": position, "reason": reason}
        person = next((p for p in handoff["people"] if p["id"] == person_id), {})
        snap = _append(state, {"type": "plan", "person_id": person_id,
                               "summary": f"Planned {person.get('name', 'a call')}: expected {position.replace('_', ' ')}"})
        _store(state)
    return snap


def read_call(saved: dict, client: openai.OpenAI | None = None) -> CallRead:
    row = call_logs.row(saved)
    lines = "\n".join(f"{t['role']}: {t['message']}" for t in row["transcript"]) or "(no transcript)"
    collected = {k: v for k, v in row["data_collection"].items() if v}
    response = (client or openai.OpenAI()).responses.parse(
        model=MODEL, instructions=READER, text_format=CallRead,
        input=(f"Calling: {row['target']} ({row['target_role'] or 'role unknown'})\n"
               f"Proposal: {row['policy_title']}\nThe caller's ask: {row['goal']}\n"
               f"Call ended: {row['termination_reason']}, {row['duration_secs']}s\n"
               + (f"Fields the call agent extracted: {json.dumps(collected)}\n" if collected else "")
               + f"\nTranscript:\n{lines}"),
    )
    read = response.output_parsed
    if read is None:
        raise RuntimeError(f"Could not read call {row['conversation_id']}")
    read.sentiment = max(-1.0, min(1.0, read.sentiment))
    read.engagement = max(0.0, min(1.0, read.engagement))
    read.read_confidence = max(0.0, min(1.0, read.read_confidence))
    read.evidence = [q.strip().strip('"“”').strip() for q in read.evidence[:3]]
    return read


def on_call(saved: dict) -> dict | None:
    """Read one finished call and rescore its run. Returns the new snapshot, or
    None when the call isn't part of a scored run or was already counted."""
    meta = (saved.get("context") or {}).get("metadata") or {}
    key, cid = meta.get("run_id") or meta.get("policy_id"), saved["conversation"].get("conversation_id")
    with _lock:
        state = load(key) if key else None
        if not state or not cid or cid in state["reads"] or cid in _reading:
            return None
        _reading.add(cid)
    try:
        read = read_call(saved)
    finally:
        with _lock:
            _reading.discard(cid)
    row = call_logs.row(saved)
    entry = {**read.model_dump(), "conversation_id": cid, "person_id": meta.get("person_id"),
             "started_at": row["started_at"], "duration_secs": row["duration_secs"], "summary": row["summary"],
             "model": MODEL, "read_at": _now()}
    with _lock:
        state = load(key)
        state["reads"][cid] = entry
        person = next((p for p in state["handoff"]["people"] if p["id"] == entry["person_id"]), None)
        who = f"{person['title']} {person['name']}".strip() if person and person.get("title") else (person or {}).get("name", "unknown target")
        snapshot = _append(state, {"type": "call", "conversation_id": cid, "person_id": entry["person_id"],
                                   "summary": f"Call with {who}: {read.position.replace('_', ' ')}, "
                                              f"sentiment {read.sentiment:+.2f}"})
        _store(state)
    _push_read(key, state["handoff"], entry)
    return snapshot


def on_call_async(saved: dict) -> None:
    def work():
        try:
            on_call(saved)
        except Exception as exc:  # a failed read must not break the call view
            print(f"confidence: {exc}", flush=True)
    threading.Thread(target=work, daemon=True).start()


def score(handoff: dict, reads: dict, expected: dict | None = None) -> dict:
    """The confidence.v1 body for a handoff, the planner's expectations and the calls read so far."""
    h = MobilizeHandoff.model_validate(handoff)
    doc = h.policy.document_type.lower()
    prior = next((v for k, v in PATH.items() if k in doc), 0.4)
    path_notes = [f"{h.policy.document_type or 'unknown document type'} change"]
    if h.impact.estimated_annual_savings is not None:
        prior += 0.04
        path_notes.append("measured savings")
    if h.change.uncertainties:
        prior -= min(0.08, 0.02 * len(h.change.uncertainties))
        path_notes.append(f"{len(h.change.uncertainties)} open uncertainties")
    prior = round(100 * prior, 1)

    latest: dict[str, dict] = {}  # each person's most recent call counts
    for r in sorted(reads.values(), key=lambda r: r.get("started_at") or 0):
        if r.get("person_id"):
            latest[r["person_id"]] = r

    targets, weighted, mass = [], 0.0, 0.0
    for p in h.people:
        w = LEVERAGE.get(p.relevance, 0.3)
        r = latest.get(p.id)
        t = {"person_id": p.id, "name": f"{p.title} {p.name}".strip() if p.title else p.name, "type": p.type,
             "relevance": p.relevance, "leverage": w, "called": r is not None,
             "reached": bool(r and r["reached"]), "stance": None, "weight": 0.0, "source": None,
             "expected": (expected or {}).get(p.id)}
        if r:
            t.update({k: r[k] for k in ("position", "commitment", "sentiment", "engagement", "read_confidence",
                                        "objections", "evidence", "rationale", "conversation_id")})
            t["calls"] = sum(1 for x in reads.values() if x.get("person_id") == p.id)
        if r and r["reached"]:
            stance = W_SENTIMENT * r["sentiment"] + W_POSITION * POSITION[r["position"]] + COMMITMENT[r["commitment"]]
            stance = max(-1.0, min(1.0, stance))
            t["stance"], t["weight"], t["source"] = round(stance, 3), round(w * r["read_confidence"], 3), "call"
        elif t["expected"]:  # not reached yet: the planner's guess, at a fraction of a call's weight
            t["stance"], t["weight"], t["source"] = POSITION[t["expected"]["position"]], round(w * EXPECTED_WEIGHT, 3), "expected"
        if t["stance"] is not None:
            weighted += t["stance"] * t["weight"]
            mass += t["weight"]
        targets.append(t)

    support = weighted / mass if mass else 0.0
    pull = mass / (mass + EVIDENCE_HALF)
    shift = support * pull * ((CEILING - prior) if support > 0 else (prior - FLOOR))
    value = round(max(FLOOR, min(CEILING, prior + shift)), 1)
    for t in targets:  # each person's share of the shift, in points
        t["points"] = round(shift * (t["stance"] * t["weight"]) / weighted, 1) if t["stance"] is not None and weighted else 0.0
    reached = sum(t["reached"] for t in targets)
    by_source = {src: round(sum(t["points"] for t in targets if t["source"] == src), 1) for src in ("expected", "call")}
    objections = sorted({o for t in targets for o in t.get("objections") or []})
    return {
        "version": VERSION,
        "run_id": h.run_id, "policy_id": h.policy.id, "policy_title": h.policy.spoken_title,
        "citation": h.policy.citation, "jurisdiction": h.policy.jurisdiction.name,
        "change": h.change.summary, "synthetic": h.policy.synthetic,
        "score": value, "band": next(b for floor, b in BANDS if value >= floor),
        "factors": [
            {"key": "path", "label": "Path difficulty", "points": prior, "detail": ", ".join(path_notes)},
            {"key": "expected", "label": "Expected stance", "points": by_source["expected"],
             "detail": f"{sum(t['source'] == 'expected' for t in targets)} people not reached yet, planner's read"},
            {"key": "calls", "label": "Stance on calls", "points": by_source["call"],
             "detail": f"{reached} reached; overall support {support:+.2f} at {pull:.0%} pull"},
        ],
        "phase": "after_calls" if reads else "before_calls",
        "support": round(support, 3), "evidence_pull": round(pull, 3),
        "coverage": {"people": len(targets), "called": sum(t["called"] for t in targets), "reached": reached},
        "objections": objections,
        "targets": targets,
        "weights": {"sentiment": W_SENTIMENT, "position": W_POSITION, "evidence_half": EVIDENCE_HALF,
                    "expected": EXPECTED_WEIGHT},
        "reader_model": MODEL,
    }


def _append(state: dict, trigger: dict) -> dict:
    snap = score(state["handoff"], state["reads"], state.get("expected"))
    prev = state["history"][-1]["score"] if state["history"] else None
    snap.update({"seq": len(state["history"]), "trigger": trigger, "computed_at": _now(),
                 "delta": round(snap["score"] - prev, 1) if prev is not None else 0.0})
    state["history"].append(snap)
    _push_snapshot(state["key"], snap)
    return snap


def view(key: str | None = None) -> dict | None:
    """The latest snapshot and the score's history for one run (the last built by default)."""
    state = load(key or current_key or "")
    if not state:
        return None
    hist = state["history"]
    before = [s for s in hist if s.get("phase", "before_calls") == "before_calls"]
    after = [s for s in hist if s.get("phase") == "after_calls"]
    brief = lambda s: {k: s.get(k) for k in ("seq", "score", "band", "delta", "phase", "trigger", "computed_at")}
    return {"key": state["key"], "current": hist[-1] if hist else None,
            "before": brief(before[-1]) if before else None,  # where we stood once every agent was planned
            "after": brief(after[-1]) if after else None,  # where we stand after the calls so far
            "history": [brief(s) for s in hist],
            "reading": sorted(_reading)}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _upsert(table: str, row: dict, on_conflict: str | None = None) -> None:
    try:
        call_logs.upsert(table, row, on_conflict)
    except Exception as exc:  # Supabase is a copy; the local state file is the source of truth
        print(f"confidence: Supabase {table}: {exc}", flush=True)


def _push_snapshot(key: str, snap: dict) -> None:
    _upsert("confidence_scores", {
        "run_key": key, "seq": snap["seq"], "version": VERSION, "run_id": snap["run_id"] or None,
        "policy_id": snap["policy_id"], "policy_title": snap["policy_title"], "jurisdiction": snap["jurisdiction"],
        "score": snap["score"], "band": snap["band"], "delta": snap["delta"], "phase": snap["phase"],
        "support": snap["support"],
        "coverage": snap["coverage"], "factors": snap["factors"], "targets": snap["targets"],
        "objections": snap["objections"], "trigger": snap["trigger"], "snapshot": snap,
        "computed_at": snap["computed_at"],
    }, on_conflict="run_key,seq")


def _push_read(key: str, handoff: dict, entry: dict) -> None:
    _upsert("call_reads", {
        "conversation_id": entry["conversation_id"], "run_key": key, "run_id": handoff.get("run_id") or None,
        "policy_id": handoff["policy"]["id"], "person_id": entry["person_id"],
        **{k: entry[k] for k in ("reached", "position", "commitment", "sentiment", "engagement",
                                 "read_confidence", "objections", "evidence", "rationale", "model", "read_at")},
    })
