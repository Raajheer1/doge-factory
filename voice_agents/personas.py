"""Generate a synthetic constituent persona for a legislator's district."""

import os

import anthropic
from pydantic import BaseModel

from .models import AgeBand, Gender, Legislator, Persona, Policy
from .voices import pick_voice

# Haiku is plenty for short persona sketches; override with PERSONA_MODEL.
MODEL = os.environ.get("PERSONA_MODEL", "claude-haiku-5-5")

SYSTEM = """You create realistic, specific constituent personas for a policy-advocacy demo.
Each persona is one plausible resident of the given district who is personally affected by the policy.
Prefer a concrete individual (occupation, town, a specific recurring hassle) over a statistical average.
Ground details in the district profile you are given. Do not invent statistics about the policy itself;
personal_impact should describe this person's own experience in plain, first-person-friendly language.
Keep background to 2-3 sentences and personal_impact to 1-2 sentences."""


class PersonaDraft(BaseModel):
    name: str
    age: int
    gender: Gender
    age_band: AgeBand
    occupation: str
    background: str
    personal_impact: str


def generate_persona(
    *, legislator: Legislator, policy: Policy, district_profile: str,
    client: anthropic.Anthropic | None = None,
) -> Persona:
    client = client or anthropic.Anthropic()
    response = client.messages.parse(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM,
        messages=[{
            "role": "user",
            "content": (
                f"District: {legislator.district} (represented by {legislator.title} {legislator.name})\n"
                f"District profile:\n{district_profile}\n\n"
                f"Policy: {policy.title}\n{policy.summary}\n"
                f"Who it affects: {policy.pain_point or 'residents and small businesses'}\n\n"
                "Create one persona."
            ),
        }],
        output_format=PersonaDraft,
    )
    if response.stop_reason == "refusal" or response.parsed_output is None:
        raise RuntimeError(f"Persona generation failed (stop_reason={response.stop_reason})")
    draft = response.parsed_output
    return Persona(
        **draft.model_dump(),
        voice_id=pick_voice(draft.gender, draft.age_band, seed=draft.name),
    )
