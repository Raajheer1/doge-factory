"""Mobilize API for the SvelteKit frontend (/mobilize). Local only: run
`voice-agents console`."""

import json
import os
import threading
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ValidationError

from .. import call_logs, calls, confidence
from ..cli import load_demo
from .. import planner
from . import pipeline
from .pipeline import ConsoleAgent

FRONTEND_ORIGINS = ["http://127.0.0.1:5173", "http://localhost:5173"]
MAX_PERSONAS = 4


class Store:
    """Agents built this session, saved to a JSON file so a restart keeps them."""

    def __init__(self, path: Path | None):
        self.path = path
        self.lock = threading.Lock()
        self.agents: dict[str, ConsoleAgent] = {}
        if path and path.exists():
            for raw in json.loads(path.read_text()):
                agent = ConsoleAgent(**raw)
                self.agents[agent.id] = agent

    def save(self) -> None:
        if self.path:
            self.path.write_text(json.dumps(
                [a.model_dump(mode="json") for a in self.agents.values()], indent=2))

    def add(self, agent: ConsoleAgent) -> None:
        with self.lock:
            self.agents[agent.id] = agent
            self.save()

    def clear(self) -> None:
        with self.lock:
            self.agents.clear()
            self.save()


class PipelineRun(BaseModel):
    personas: int = Field(default=3, ge=1, le=MAX_PERSONAS)
    source: str = Field(default="sample", pattern="^(claude|sample)$")
    handoff: dict | None = None  # POST /api/runs/:id/mobilize response from the Go API


def create_app(*, store_path: Path | None = None, demo: dict | None = None,
               sample_pause: float = 0.6) -> FastAPI:
    app = FastAPI(title="DOGE Factory · Mobilize API")
    app.add_middleware(CORSMiddleware, allow_origins=FRONTEND_ORIGINS,
                       allow_methods=["*"], allow_headers=["*"])
    store = Store(store_path)
    demo = demo or load_demo()

    @app.get("/api/status")
    def status():
        return {
            "elevenlabs_key": bool(os.environ.get("ELEVENLABS_API_KEY")),
            "phone_number": bool(os.environ.get("ELEVENLABS_PHONE_NUMBER_ID")),
            "allowed_numbers": sorted(calls.allowed_numbers()),
            "persona_model": pipeline.PERSONA_MODEL,
            "planner_model": planner.MODEL,
            "confidence_model": confidence.MODEL,
            "max_personas": MAX_PERSONAS,
        }

    @app.get("/api/input")
    def draft_input():
        return {k: v for k, v in demo.items() if not k.startswith("_")}

    @app.get("/api/agents")
    def list_agents():
        return [a.model_dump(mode="json") for a in store.agents.values()]

    @app.delete("/api/agents")
    def reset_agents():
        store.clear()
        return {"ok": True}

    @app.post("/api/pipeline")
    def run_pipeline(body: PipelineRun):
        try:
            data = pipeline.input_from_handoff(body.handoff, demo) if body.handoff else demo
        except ValidationError as exc:
            raise HTTPException(422, f"Invalid mobilize.v1 handoff: {exc}")
        except (KeyError, TypeError) as exc:
            raise HTTPException(422, f"Handoff is missing {exc}")
        # A mobilize.v1 handoff with people gets one purpose-built agent per person.
        campaign = body.source == "claude" and bool(data.get("handoff", {}).get("people"))
        if body.source == "claude":
            source, label, pause = pipeline.claude_source(data), pipeline.CLAUDE_LABEL, 0.0
        else:
            source, label, pause = pipeline.sample_source(), "sample personas", sample_pause

        if campaign:
            confidence.start(data["handoff"])  # baseline score before any call

        def stream():
            store.clear()  # each run replaces the roster shown in the graph
            events = pipeline.run_campaign(data) if campaign else pipeline.run(
                data, persona_count=body.personas, next_persona=source, source_label=label, pause=pause)
            for ev in events:
                if "agent" in ev:
                    store.add(ConsoleAgent(**ev["agent"]))
                yield f"data: {json.dumps(ev)}\n\n"

        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.get("/api/confidence")
    def get_confidence(run: str | None = None):
        """confidence.v1 for one run (the last built by default): the latest snapshot and its history."""
        return confidence.view(run) or {"key": run, "current": None, "history": [], "reading": []}

    @app.post("/api/agents/{agent_id}/call")
    def place_call(agent_id: str):
        agent = store.agents.get(agent_id)
        if not agent:
            raise HTTPException(404, "Unknown agent")
        try:
            result = calls.place_call(agent.request)
        except calls.CallNotAllowedError as exc:
            raise HTTPException(403, str(exc))
        except KeyError as exc:
            raise HTTPException(500, f"Missing {exc.args[0]} in .env")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(502, f"ElevenLabs: {exc.response.text}")
        conversation_id = result.get("conversation_id")
        if conversation_id:
            with store.lock:
                agent.conversations.append(conversation_id)
                store.save()
        return result

    @app.get("/api/conversations/{conversation_id}")
    def conversation(conversation_id: str):
        try:
            convo = calls.get_conversation(conversation_id)
        except httpx.HTTPStatusError as exc:
            raise HTTPException(502, f"ElevenLabs: {exc.response.text}")
        if convo.get("status") in call_logs.FINAL:
            # Keep a local copy, with what we told the agent, for later analysis.
            agent = next((a for a in store.agents.values() if conversation_id in a.conversations), None)
            path = call_logs.save(convo, call_logs.agent_context(agent) if agent else None)
            call_logs.write_index()
            if path:
                confidence.on_call_async(json.loads(path.read_text()))  # rescore the run in the background
        analysis = convo.get("analysis") or {}
        return {
            "status": convo.get("status"),
            "duration": (convo.get("metadata") or {}).get("call_duration_secs"),
            "transcript": [
                {"role": turn.get("role"), "message": turn.get("message"),
                 "at": turn.get("time_in_call_secs")}
                for turn in convo.get("transcript") or [] if turn.get("message")
            ],
            "summary": analysis.get("transcript_summary"),
            "data_collection": {
                k: v.get("value") for k, v in (analysis.get("data_collection_results") or {}).items()
            },
            "evaluation": {
                k: v.get("result")
                for k, v in (analysis.get("evaluation_criteria_results") or {}).items()
            },
        }

    return app
