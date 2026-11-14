"""Build a roster of call-ready agents from Draft-phase input, emitting a trace
event at every step so the UI can show what is happening."""

import json
import time
import uuid
from collections.abc import Callable, Iterator
from datetime import datetime, timezone
from importlib import resources

from pydantic import BaseModel, Field

from .. import agents
from ..calls import build_payload
from ..models import AgentType, CallRequest, Legislator, Lobbyist, Persona, Policy
from ..personas import MODEL as PERSONA_MODEL
from ..voices import DEFAULT_VOICE_ID, pick_voice, voice_label

STAGES = ("input", "persona", "voice", "assemble", "ready")


class ConsoleAgent(BaseModel):
    id: str
    kind: AgentType
    template: str  # the ElevenLabs agent this one is built on
    caller: str
    target: str
    persona: Persona | None = None
    voice_id: str
    voice: str
    request: CallRequest
    payload: dict  # the exact outbound-call body, phone number id redacted
    created_at: str
    conversations: list[str] = Field(default_factory=list)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def event(stage: str, status: str, message: str, **extra) -> dict:
    return {"t": now(), "stage": stage, "status": status, "message": message, **extra}


def sample_personas() -> list[Persona]:
    raw = json.loads(
        resources.files("voice_agents").joinpath("fixtures/sample_personas.json").read_text()
    )["personas"]
    personas = [Persona(**p) for p in raw]
    for p in personas:
        p.voice_id = pick_voice(p.gender, p.age_band, seed=p.name)
    return personas


def _agent(kind: AgentType, caller: str, target: str, request: CallRequest,
           persona: Persona | None = None) -> ConsoleAgent:
    voice_id = request.voice_id or DEFAULT_VOICE_ID
    return ConsoleAgent(
        id=uuid.uuid4().hex[:8], kind=kind, template=agents.AGENTS[kind].name,
        caller=caller, target=target, persona=persona,
        voice_id=voice_id, voice=voice_label(voice_id), request=request,
        payload=build_payload(request, "<ELEVENLABS_PHONE_NUMBER_ID>"), created_at=now(),
    )


PersonaSource = Callable[[list[Persona]], Persona]


def run(demo: dict, *, persona_count: int, next_persona: PersonaSource,
        source_label: str, pause: float = 0.0) -> Iterator[dict]:
    """Yield trace events; events with an `agent` key carry a finished agent.

    `next_persona(already_made)` returns the next persona (Claude or sample).
    `pause` slows the sample source down so the flow is watchable.
    """
    policy = Policy(**demo["policy"])
    legislator = Legislator(**demo["legislator"])
    lobbyist = Lobbyist(**demo["lobbyist"])
    to_number = demo["to_number"]
    target = f"{legislator.title} {legislator.name}"

    yield event("input", "done", f"Received Draft output: {policy.title} ({policy.state})",
                data={"policy": policy.model_dump(), "legislator": target,
                      "district": legislator.district, "lobbyist": f"{lobbyist.name}, {lobbyist.firm}"})

    made: list[Persona] = []
    for i in range(1, persona_count + 1):
        yield event("persona", "running", f"Drafting persona {i}/{persona_count} via {source_label}",
                    data={"index": i})
        started = time.monotonic()
        try:
            persona = next_persona(made)
        except Exception as exc:  # surface any model/auth error in the trace
            yield event("persona", "error", f"Persona {i} failed: {exc}")
            return
        time.sleep(pause)
        made.append(persona)
        yield event("persona", "done",
                    f"{persona.name}, {persona.age}, {persona.occupation}",
                    data={"index": i, "seconds": round(time.monotonic() - started, 2),
                          "persona": persona.model_dump(mode="json")})

        yield event("voice", "done",
                    f"Cast voice {voice_label(persona.voice_id)} for "
                    f"{persona.gender.value}/{persona.age_band.value}",
                    data={"voice_id": persona.voice_id})
        time.sleep(pause / 2)

        request = agents.legislator_call(
            to_number=to_number, persona=persona, legislator=legislator,
            policy=policy, ask=demo["asks"]["legislator"],
        )
        agent = _agent(AgentType.LEGISLATOR, persona.name, target, request, persona)
        yield event("assemble", "done",
                    f"Bound {len(request.dynamic_variables)} variables onto "
                    f"'{agent.template}' for {persona.name}",
                    agent=agent.model_dump(mode="json"))

    for kind, request, caller, callee in (
        (AgentType.SURVEY,
         agents.survey_call(to_number=to_number, respondent_name="Harsh",
                            legislator=legislator, policy=policy),
         "Jordan (DOGE Factory)", "District constituent"),
        (AgentType.LOBBYIST,
         agents.lobbyist_call(to_number=to_number, lobbyist=lobbyist, policy=policy,
                              ask=demo["asks"]["lobbyist"]),
         "Alex (DOGE Factory)", f"{lobbyist.name}, {lobbyist.firm}"),
    ):
        time.sleep(pause / 2)
        agent = _agent(kind, caller, callee, request)
        yield event("assemble", "done",
                    f"Bound {len(request.dynamic_variables)} variables onto '{agent.template}'",
                    agent=agent.model_dump(mode="json"))

    yield event("ready", "done", f"{persona_count + 2} agents ready to dial {to_number}")


def input_from_handoff(handoff: dict, demo: dict) -> dict:
    """Turn the Go API's mobilization handoff (an approved finding) into
    pipeline input. The finding supplies the policy; legislator, lobbyist and
    district are not in the handoff yet, so they stay demo targets (the user
    plays all of them)."""
    finding = handoff["finding"]
    provision = finding["provision"]
    jurisdiction = provision.get("jurisdiction") or "the state"
    return {
        **demo,
        "source": "handoff",
        "run_id": handoff.get("run_id", ""),
        "query": handoff.get("query", ""),
        "synthetic": bool(provision.get("synthetic")),
        "policy": {
            "title": provision["title"],
            "summary": f"{finding['desired_change']} {finding['justification']}".strip(),
            # The analysis never estimates savings; don't let the agents invent one.
            "fiscal_impact": "No fiscal estimate yet; the DOGE Factory team is still preparing one.",
            "state": jurisdiction,
            "pain_point": finding["barrier"],
            "key_legislators": demo["policy"]["key_legislators"],
        },
        "legislator": {**demo["legislator"], "district": f"{jurisdiction}'s 13th Senate District"},
        "district_profile": f"A mixed urban and rural district in {jurisdiction} with residents, "
                            "small businesses and public-sector workers affected by state rules.",
        "lobbyist": {
            **demo["lobbyist"],
            "client_name": f"a statewide association affected by {provision['title']}",
            "client_benefit": f"Their members run into this barrier directly: {finding['barrier']}",
        },
        "asks": {
            "legislator": f"Ask the senator to support this change this session: {finding['desired_change']}",
            "lobbyist": "Get them to raise this change with their client and agree to a 20-minute "
                        "meeting with the DOGE Factory team to review the proposed amendment.",
        },
    }


def claude_source(demo: dict) -> PersonaSource:
    from ..personas import generate_persona

    def next_persona(made: list[Persona]) -> Persona:
        return generate_persona(
            legislator=Legislator(**demo["legislator"]), policy=Policy(**demo["policy"]),
            district_profile=demo["district_profile"], avoid=made,
        )
    return next_persona


def sample_source() -> PersonaSource:
    pool = sample_personas()
    return lambda made: pool[len(made) % len(pool)]


CLAUDE_LABEL = f"Claude ({PERSONA_MODEL})"
