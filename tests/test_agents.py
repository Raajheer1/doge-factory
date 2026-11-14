import pytest

from voice_agents import agents, calls
from voice_agents.cli import build_request, load_demo
from voice_agents.models import AgentType, CallRequest, Gender, AgeBand
from voice_agents.voices import PALETTE, pick_voice


@pytest.mark.parametrize("agent_type", list(AgentType))
def test_demo_fixture_builds_every_agent_type(agent_type):
    request = build_request(agent_type, load_demo(), persona_path=None)
    required = agents.AGENTS[agent_type].required_variables
    assert set(required) <= set(request.dynamic_variables)
    assert all(request.dynamic_variables[k] for k in required)


def test_missing_variable_is_rejected():
    demo = load_demo()
    demo["policy"]["key_legislators"] = ""
    with pytest.raises(agents.MissingVariablesError, match="key_legislators"):
        build_request(AgentType.LOBBYIST, demo, persona_path=None)


def test_disclose_ai_defaults_to_false_string():
    request = build_request(AgentType.LEGISLATOR, load_demo(), persona_path=None)
    assert request.dynamic_variables["disclose_ai"] == "false"


def test_payload_includes_voice_override_for_persona():
    request = build_request(AgentType.LEGISLATOR, load_demo(), persona_path=None)
    payload = calls.build_payload(request, "phnum_test")
    assert payload["agent_id"] == agents.AGENTS[AgentType.LEGISLATOR].agent_id
    client_data = payload["conversation_initiation_client_data"]
    assert client_data["conversation_config_override"]["tts"]["voice_id"] == "cgSgspJ2msm6clMCkdW9"
    assert client_data["dynamic_variables"]["persona_name"] == "Maya Thompson"


def test_payload_omits_override_when_not_set():
    request = build_request(AgentType.SURVEY, load_demo(), persona_path=None)
    payload = calls.build_payload(request, "phnum_test")
    assert "conversation_config_override" not in payload["conversation_initiation_client_data"]


def test_place_call_refuses_numbers_outside_allowlist(monkeypatch):
    monkeypatch.setenv("ALLOWED_TO_NUMBERS", "+19727652721")
    request = CallRequest(agent_type=AgentType.SURVEY, to_number="+15550000000", dynamic_variables={})
    with pytest.raises(calls.CallNotAllowedError):
        calls.place_call(request)


def test_pick_voice_is_stable_and_in_palette():
    voice = pick_voice(Gender.MALE, AgeBand.MIDDLE_AGED, seed="Dale")
    assert voice == pick_voice(Gender.MALE, AgeBand.MIDDLE_AGED, seed="Dale")
    assert voice in {v for v, _ in PALETTE[(Gender.MALE, AgeBand.MIDDLE_AGED)]}


def test_pick_voice_old_falls_back_to_middle_aged():
    voice = pick_voice(Gender.FEMALE, AgeBand.OLD, seed="Ruth")
    assert voice in {v for v, _ in PALETTE[(Gender.FEMALE, AgeBand.MIDDLE_AGED)]}
