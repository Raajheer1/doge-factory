"""Build a roster of call-ready agents from Draft-phase input, emitting a trace
event at every step so the UI can show what is happening."""

import json
import os
import queue
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from collections.abc import Callable, Iterator
from datetime import datetime, timezone
from importlib import resources

from pydantic import BaseModel, Field

from .. import agents
from ..calls import build_payload
from ..handoff import MobilizeHandoff
from ..models import AgentType, CallRequest, Legislator, Lobbyist, Persona, Policy
from ..personas import MODEL as PERSONA_MODEL
from ..voices import DEFAULT_VOICE_ID, pick_voice, voice_label

STAGES = ("input", "plan", "persona", "think", "voice", "assemble", "ready")
THINK_FLUSH = 0.4  # seconds between streamed thinking updates
PLANNER_WORKERS = int(os.environ.get("PLANNER_WORKERS", "12"))  # call plans written at once


class ConsoleAgent(BaseModel):
    id: str
    kind: AgentType
    template: str  # the ElevenLabs agent this one is built on
    archetype: str = ""  # for generated agents: the kind of call the planner wrote
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
           persona: Persona | None = None, archetype: str = "") -> ConsoleAgent:
    voice_id = request.voice_id or DEFAULT_VOICE_ID
    return ConsoleAgent(
        id=uuid.uuid4().hex[:8], kind=kind, template=agents.AGENTS[kind].name, archetype=archetype,
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


def run_campaign(demo: dict) -> Iterator[dict]:
    """One purpose-built agent per person in a mobilize.v1 handoff, in handoff
    order (most relevant first). Plans are written in parallel and each model's
    reasoning streams out as `think` events, so the build can be watched."""
    from .. import planner

    h = MobilizeHandoff.model_validate(demo["handoff"])
    policy = Policy(**demo["policy"])
    to_number = demo["to_number"]
    people = h.people
    targets = [{"id": p.id, "name": planner.target_label(p)[0], "role": planner.target_label(p)[1],
                "archetype": planner.archetype_for(p).label, "relevance": p.relevance} for p in people]

    yield event("input", "done", f"Received handoff: {policy.title} ({policy.state}), {len(people)} people",
                data={"policy": policy.model_dump(), "targets": targets})
    yield event("plan", "done",
                f"Planned {len(people)} agents: " + ", ".join(
                    f"{n} {a}" for a, n in _counts(t["archetype"] for t in targets)),
                data={"targets": targets, "model": planner.MODEL})

    # Every plan is written at once; thinking streams out as it happens, and each
    # finished agent is emitted in handoff order so the graph fills in top to bottom.
    out: queue.Queue = queue.Queue()

    def work(i: int, person) -> None:
        started, phase, buffer, flushed = time.monotonic(), "thinking", "", time.monotonic()
        try:
            for item in planner.plan_agent(h, person, i - 1):
                if isinstance(item, planner.PlannedAgent):
                    if buffer:
                        out.put(("think", i, phase, buffer))
                    out.put(("done", i, item, time.monotonic() - started))
                    return
                kind, text = item
                if kind != phase and buffer:
                    out.put(("think", i, phase, buffer))
                    buffer = ""
                phase, buffer = kind, buffer + text
                if time.monotonic() - flushed > THINK_FLUSH:
                    out.put(("think", i, phase, buffer))
                    buffer, flushed = "", time.monotonic()
            out.put(("done", i, RuntimeError("no plan returned"), 0.0))
        except Exception as exc:  # one bad plan skips that target, not the run
            out.put(("done", i, exc, 0.0))

    for i, person in enumerate(people, start=1):
        name, _ = planner.target_label(person)
        yield event("persona", "running", f"Planning call {i}/{len(people)}: {targets[i - 1]['archetype']} to {name}",
                    data={"index": i, "target": name, "archetype": targets[i - 1]["archetype"]})
    with ThreadPoolExecutor(max_workers=min(PLANNER_WORKERS, len(people) or 1)) as pool:
        for i, person in enumerate(people, start=1):
            pool.submit(work, i, person)
        finished: dict[int, tuple] = {}
        built, next_i = 0, 1
        while next_i <= len(people):
            kind, i, *rest = out.get()
            if kind == "think":
                yield _think(i, planner.target_label(people[i - 1])[0], *rest)
                continue
            finished[i] = tuple(rest)
            while next_i in finished:
                result, seconds = finished.pop(next_i)
                person = people[next_i - 1]
                if isinstance(result, planner.PlannedAgent):
                    yield from _assemble(h, policy, to_number, next_i, person, result, seconds)
                    built += 1
                else:
                    name = planner.target_label(person)[0]
                    yield event("persona", "done", f"Skipped {name}: {result}", data={"index": next_i, "skipped": True})
                next_i += 1

    if not built:
        yield event("ready", "error", "No agents were built")
        return
    yield event("ready", "done", f"{built} agents ready to dial {to_number}")


def _assemble(h: MobilizeHandoff, policy: Policy, to_number: str, i: int, person, planned,
              seconds: float) -> Iterator[dict]:
    """The events for one planned agent: its persona, voice and bound ElevenLabs agent."""
    from .. import planner

    name, role = planner.target_label(person)
    persona, plan = planned.persona, planned.plan
    yield event("persona", "done", f"{persona.name}, {plan.caller_role}",
                data={"index": i, "person_id": person.id, "seconds": round(seconds, 2),
                      "persona": persona.model_dump(mode="json"), "plan": plan.model_dump()})
    yield event("voice", "done",
                f"Cast voice {voice_label(persona.voice_id)} for "
                f"{persona.gender.value}/{persona.age_band.value}",
                data={"voice_id": persona.voice_id})
    request = agents.generated_call(
        to_number=to_number, persona=persona, caller_role=plan.caller_role,
        target_name=name, target_role=role, policy=policy, goal=plan.goal,
        talking_points=plan.talking_points, objections=plan.objections,
        first_message=plan.first_message,
    )
    request.metadata = {"person_id": person.id, "run_id": h.run_id, "query": h.query,
                        "policy_id": h.policy.id, "jurisdiction": h.policy.jurisdiction.name}
    agent = _agent(AgentType.GENERATED, persona.name, name, request, persona,
                   archetype=planned.archetype.label)
    yield event("assemble", "done",
                f"Bound {len(request.dynamic_variables)} variables onto "
                f"'{agent.template}' as {agent.archetype} for {name}",
                agent=agent.model_dump(mode="json"))


def _think(index: int, name: str, phase: str, text: str) -> dict:
    verb = "Thinking about" if phase == "thinking" else "Writing the call plan for"
    return event("think", "progress", f"{verb} {name}", data={"index": index, "phase": phase, "delta": text})


def _counts(items) -> list[tuple[str, int]]:
    out: dict[str, int] = {}
    for x in items:
        out[x] = out.get(x, 0) + 1
    return list(out.items())


def input_from_handoff(handoff: dict, demo: dict) -> dict:
    """Turn a handoff into pipeline input: `mobilize.v1` (docs/mobilize-handoff.md)
    or the Go API's older `{finding: ...}` shape, which carries no people."""
    if handoff.get("version") == "mobilize.v1":
        return input_from_mobilize_v1(MobilizeHandoff.model_validate(handoff), demo)
    return _input_from_finding(handoff, demo)


def input_from_mobilize_v1(h: MobilizeHandoff, demo: dict) -> dict:
    """Targets come from `people`, most relevant first: the first official with a
    state and the first lobbyist. Missing roles fall back to demo targets. Every
    call still goes to the demo number (the user plays each role)."""
    state = h.policy.jurisdiction.name
    legislators, lobbyists = h.legislators, h.lobbyists
    savings = h.impact.estimated_annual_savings
    if savings is None:
        # Mobilize never invents a number the analysis didn't supply.
        fiscal = "No fiscal estimate yet; the DOGE Factory team is still preparing one."
    else:
        fiscal = f"About ${savings:,.0f} a year" + (f" ({h.impact.savings_basis})" if h.impact.savings_basis else "")
    legislator = demo["legislator"]
    if legislators:
        official = legislators[0]
        legislator = {"title": official.title, "name": official.name,
                      "district": official.district or f"{official.state} (statewide)"}
    lobbyist = demo["lobbyist"]
    if lobbyists:
        lead = lobbyists[0]
        lobbyist = {"name": lead.name, "firm": lead.organization or lead.clients[0],
                    "client_name": ", ".join(lead.clients),
                    "client_benefit": f"Their clients run into this directly: {h.change.barrier}"}
    groups = ", ".join(h.impact.affected_groups)
    return {
        **demo,
        "source": "handoff",
        "handoff": h.model_dump(mode="json"),
        "run_id": h.run_id,
        "query": h.query,
        "synthetic": h.policy.synthetic,
        "policy": {
            "title": h.policy.spoken_title,
            "summary": h.change.summary,
            "fiscal_impact": fiscal,
            "state": state,
            "pain_point": h.change.barrier,
            "key_legislators": ", ".join(f"{p.title} {p.name}" for p in legislators)
                               or demo["policy"]["key_legislators"],
        },
        "legislator": legislator,
        "district_profile": f"Residents of {state} affected by "
                            f"{h.policy.spoken_title}, including {groups}.",
        "lobbyist": lobbyist,
        "asks": {
            "legislator": f"Ask the {legislator['title'].lower()} to support this change: {h.change.summary}",
            "lobbyist": "Get them to raise this change with their client and agree to a 20-minute "
                        "meeting with the DOGE Factory team to review the proposed amendment.",
        },
    }


def _input_from_finding(handoff: dict, demo: dict) -> dict:
    """The Go API's current handoff (an approved finding). The finding supplies
    the policy; legislator, lobbyist and district stay demo targets."""
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
        # Placeholder when the handoff carries no people; don't invent a district.
        "legislator": {**demo["legislator"], "district": f"a demo district in {jurisdiction}"},
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
