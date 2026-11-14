from types import SimpleNamespace

import pytest

from voice_agents.cli import load_demo
from voice_agents.models import AgeBand, Gender, Legislator, Policy
from voice_agents.personas import PersonaDraft, generate_persona
from voice_agents.voices import PALETTE


class StubMessages:
    def __init__(self, response):
        self.response = response
        self.kwargs = None

    def parse(self, **kwargs):
        self.kwargs = kwargs
        return self.response


def stub_client(response):
    messages = StubMessages(response)
    return SimpleNamespace(beta=SimpleNamespace(messages=messages)), messages


def demo_inputs():
    demo = load_demo()
    return dict(
        legislator=Legislator(**demo["legislator"]),
        policy=Policy(**demo["policy"]),
        district_profile=demo["district_profile"],
    )


def test_generate_persona_assigns_palette_voice_and_marks_synthetic():
    draft = PersonaDraft(
        name="Dale Whitaker", age=61, gender=Gender.MALE, age_band=AgeBand.OLD,
        occupation="horse farm manager", background="Runs a farm outside Lexington.",
        personal_impact="Loses a morning every time an ag permit needs a notary.",
    )
    client, messages = stub_client(SimpleNamespace(stop_reason="end_turn", parsed_output=draft))

    persona = generate_persona(**demo_inputs(), client=client)

    assert persona.synthetic is True
    assert persona.voice_id in {v for v, _ in PALETTE[(Gender.MALE, AgeBand.MIDDLE_AGED)]}
    assert messages.kwargs["output_format"] is PersonaDraft
    assert "Kentucky's 13th Senate District" in messages.kwargs["messages"][0]["content"]


def test_generate_persona_raises_on_refusal():
    client, _ = stub_client(SimpleNamespace(stop_reason="refusal", parsed_output=None))
    with pytest.raises(RuntimeError, match="refusal"):
        generate_persona(**demo_inputs(), client=client)
