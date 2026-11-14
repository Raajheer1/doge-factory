"""Plan one purpose-built agent per person in a mobilize.v1 handoff.

Code picks the archetype from the person's type and relevance; the model writes
the caller, goal and script for that archetype. Everything lands in the fixed
"Generated Caller" ElevenLabs prompt, which holds the call structure and rules.
"""

from dataclasses import dataclass

import anthropic
from pydantic import BaseModel, Field

from .handoff import HandoffPerson, MobilizeHandoff
from .models import AgeBand, Gender, Persona
from .personas import MODEL
from .voices import pick_voice


@dataclass(frozen=True)
class Archetype:
    key: str
    label: str
    caller: str  # who calls, for the model
    goal: str  # what this kind of call asks for, for the model


ARCHETYPES = {
    a.key: a for a in (
        Archetype("agency_appeal", "Stakeholder → Agency",
                  "a synthetic resident of the person's state from one of the affected groups, "
                  "who runs into the barrier in their work or life",
                  "ask the official to use their authority over the rule: guidance, a waiver, "
                  "or support for the amendment; get a staff contact"),
        Archetype("constituent_call", "Constituent → Legislator",
                  "a synthetic constituent in the legislator's district (or state) from one of the "
                  "affected groups",
                  "ask the legislator to support or sponsor the amendment this session"),
        Archetype("lobbyist_pitch", "Lobbyist pitch",
                  "an organizer at DOGE Factory, a policy-reform group",
                  "show how the change serves the lobbyist's named clients; ask them to raise it "
                  "with those clients and take a 20-minute meeting"),
        Archetype("coalition_invite", "Coalition invite",
                  "an organizer at DOGE Factory, a policy-reform group",
                  "ask the organization to sign on to a coalition letter supporting the amendment"),
    )
}

# Spread voices across a roster without asking the model to coordinate.
VOICE_MIX = [(Gender.FEMALE, AgeBand.MIDDLE_AGED), (Gender.MALE, AgeBand.OLD),
             (Gender.FEMALE, AgeBand.YOUNG), (Gender.MALE, AgeBand.MIDDLE_AGED),
             (Gender.FEMALE, AgeBand.OLD), (Gender.MALE, AgeBand.YOUNG)]
AGE_RANGE = {AgeBand.YOUNG: "22-34", AgeBand.MIDDLE_AGED: "35-59", AgeBand.OLD: "60-74"}
INITIALS = "MDRJTKLASCBNEPGW"  # distinct initials keep parallel plans from reusing names


def archetype_for(person: HandoffPerson) -> Archetype:
    if person.type == "lobbyist":
        return ARCHETYPES["lobbyist_pitch"]
    if person.relevance in ("authority_over_document", "administers"):
        return ARCHETYPES["agency_appeal"]  # an agency or its officials
    if person.type == "organization":
        return ARCHETYPES["coalition_invite"]
    return ARCHETYPES["constituent_call"]


def target_label(person: HandoffPerson) -> tuple[str, str]:
    """(name as spoken, their role) for the prompt and the UI."""
    name = f"{person.title} {person.name}" if person.type == "official" and person.title else person.name
    if person.type == "lobbyist":
        role = f"lobbyist{f' at {person.organization}' if person.organization else ''} for {', '.join(person.clients)}"
    else:
        parts: list[str] = []
        for x in (person.role or person.title, person.organization, person.district or person.state):
            if x and not any(x in p for p in parts):
                parts.append(x)
        role = ", ".join(parts)
    return name, role or person.type


SYSTEM = """You write call plans for a policy-advocacy demo. Each plan is one phone call to one real
public figure about one proposed policy change. The caller is synthetic; never present them as a real person.
Rules:
- Use only facts given to you about the policy and the person. Never invent statistics, bill numbers,
  dollar figures, quotes or votes. Personal stakes describe the caller's own plausible experience.
- Tailor the goal to this person's actual lever (their authority, committee, clients or members).
- Talking points: 2-3 short spoken sentences. Objections: 1-2 lines of the form
  "If they say <concern>, say <short answer>", grounded in the safeguards and justification.
- first_message: one or two sentences the caller opens with: their name, who they are, why this person.
  Do not mention being an AI."""


class CallPlan(BaseModel):
    caller_name: str
    age: int
    occupation: str
    caller_role: str = Field(description="one line, e.g. 'a used-car dealer in Bowling Green'")
    background: str = Field(description="2-3 sentences")
    personal_stake: str = Field(description="1-2 sentences on why this caller cares")
    goal: str = Field(description="the specific ask for this person, 1-2 sentences")
    talking_points: list[str]
    objections: list[str]
    first_message: str


@dataclass
class PlannedAgent:
    person: HandoffPerson
    archetype: Archetype
    persona: Persona
    plan: CallPlan


def policy_brief(h: MobilizeHandoff) -> str:
    c = h.change
    lines = [
        f"Policy: {h.policy.spoken_title} ({h.policy.citation or h.policy.title}, {h.policy.jurisdiction.name})",
        f"Proposed change: {c.summary}",
        f"Barrier today: {c.barrier}",
        f"Why: {c.justification}" if c.justification else "",
        f"Safeguards kept: {'; '.join(c.safeguards)}" if c.safeguards else "",
        f"Affected groups: {', '.join(h.impact.affected_groups)}",
        f"Evidence: \"{c.evidence_quote[:400]}\"" if c.evidence_quote else "",
    ]
    return "\n".join(line for line in lines if line)


def plan_agent(h: MobilizeHandoff, person: HandoffPerson, index: int,
               client: anthropic.Anthropic | None = None) -> PlannedAgent:
    client = client or anthropic.Anthropic()
    archetype = archetype_for(person)
    gender, band = VOICE_MIX[index % len(VOICE_MIX)]
    name, role = target_label(person)
    facts = [f"Calling: {name} ({role})", f"Why them: {person.relevance.replace('_', ' ')}"]
    if person.clients:
        facts.append(f"Their clients: {', '.join(person.clients)}")
    response = client.messages.parse(
        model=MODEL,
        max_tokens=4000,
        system=SYSTEM,
        messages=[{"role": "user", "content": (
            f"{policy_brief(h)}\n\n" + "\n".join(facts) + "\n\n"
            f"Call type: {archetype.label}. The caller is {archetype.caller}. "
            f"The call should {archetype.goal}.\n"
            f"The caller is {gender.value}, aged {AGE_RANGE[band]}, with a first name starting with "
            f"{INITIALS[index % len(INITIALS)]} and a surname starting with "
            f"{INITIALS[(index * 7 + 3) % len(INITIALS)]}.\nWrite the call plan."
        )}],
        output_format=CallPlan,
    )
    if response.stop_reason == "refusal" or response.parsed_output is None:
        raise RuntimeError(f"Call plan for {person.name} failed (stop_reason={response.stop_reason})")
    plan = response.parsed_output
    plan.talking_points, plan.objections = plan.talking_points[:3], plan.objections[:2]
    persona = Persona(
        name=plan.caller_name, age=plan.age, gender=gender, age_band=band,
        occupation=plan.occupation, background=plan.background,
        personal_impact=plan.personal_stake,
        voice_id=pick_voice(gender, band, seed=plan.caller_name),
    )
    return PlannedAgent(person=person, archetype=archetype, persona=persona, plan=plan)
