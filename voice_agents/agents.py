"""Registry of the ElevenLabs agents and the variables each one needs.

Prompts live in ElevenLabs; the variable lists here must match the
{{placeholders}} in those prompts. Builders turn DB records into a
CallRequest for each agent type.
"""

from dataclasses import dataclass

from .models import AgentType, CallRequest, Legislator, Lobbyist, Persona, Policy


@dataclass(frozen=True)
class AgentSpec:
    agent_id: str
    name: str
    required_variables: tuple[str, ...]


AGENTS: dict[AgentType, AgentSpec] = {
    AgentType.LEGISLATOR: AgentSpec(
        agent_id="agent_5501m7ck1rtnf0wt4z429ddj3130",
        name="Constituent → Legislator",
        required_variables=(
            "persona_name", "persona_background", "personal_impact",
            "target_title", "target_name", "district",
            "policy_title", "policy_summary", "fiscal_impact",
            "ask", "disclose_ai",
        ),
    ),
    AgentType.SURVEY: AgentSpec(
        agent_id="agent_2801m7cp2e12e5d89y6drn7g8arm",
        name="Constituent Survey",
        required_variables=(
            "caller_name", "org_name", "target_name", "district",
            "policy_title", "policy_summary", "fiscal_impact", "pain_point",
            "representative_title", "representative_name", "disclose_ai",
        ),
    ),
    AgentType.LOBBYIST: AgentSpec(
        agent_id="agent_5901m7cp2pj8frcaj8hh7sg83ajj",
        name="Lobbyist Pitch",
        required_variables=(
            "caller_name", "org_name", "target_name", "target_firm",
            "client_name", "client_benefit", "state",
            "policy_title", "policy_summary", "fiscal_impact",
            "key_legislators", "ask", "disclose_ai",
        ),
    ),
}

ORG_NAME = "DOGE Factory"


class MissingVariablesError(ValueError):
    pass


def _policy_vars(policy: Policy) -> dict[str, str]:
    return {
        "policy_title": policy.title,
        "policy_summary": policy.summary,
        "fiscal_impact": policy.fiscal_impact,
    }


def _finalize(agent_type: AgentType, to_number: str, variables: dict[str, str], **kwargs) -> CallRequest:
    missing = [k for k in AGENTS[agent_type].required_variables if not variables.get(k)]
    if missing:
        raise MissingVariablesError(f"{agent_type.value} call is missing: {', '.join(missing)}")
    return CallRequest(agent_type=agent_type, to_number=to_number, dynamic_variables=variables, **kwargs)


def legislator_call(
    *, to_number: str, persona: Persona, legislator: Legislator, policy: Policy,
    ask: str, disclose_ai: bool = False,
) -> CallRequest:
    variables = {
        **_policy_vars(policy),
        "persona_name": persona.name,
        "persona_background": persona.background,
        "personal_impact": persona.personal_impact,
        "target_title": legislator.title,
        "target_name": legislator.name,
        "district": legislator.district,
        "ask": ask,
        "disclose_ai": str(disclose_ai).lower(),
    }
    return _finalize(
        AgentType.LEGISLATOR, to_number, variables,
        voice_id=persona.voice_id or None,
    )


def survey_call(
    *, to_number: str, respondent_name: str, legislator: Legislator, policy: Policy,
    caller_name: str = "Jordan", disclose_ai: bool = False,
) -> CallRequest:
    variables = {
        **_policy_vars(policy),
        "caller_name": caller_name,
        "org_name": ORG_NAME,
        "target_name": respondent_name,
        "district": legislator.district,
        "pain_point": policy.pain_point,
        "representative_title": legislator.title,
        "representative_name": legislator.name,
        "disclose_ai": str(disclose_ai).lower(),
    }
    return _finalize(AgentType.SURVEY, to_number, variables)


def lobbyist_call(
    *, to_number: str, lobbyist: Lobbyist, policy: Policy, ask: str,
    caller_name: str = "Alex", disclose_ai: bool = False,
) -> CallRequest:
    variables = {
        **_policy_vars(policy),
        "caller_name": caller_name,
        "org_name": ORG_NAME,
        "target_name": lobbyist.name,
        "target_firm": lobbyist.firm,
        "client_name": lobbyist.client_name,
        "client_benefit": lobbyist.client_benefit,
        "state": policy.state,
        "key_legislators": policy.key_legislators,
        "ask": ask,
        "disclose_ai": str(disclose_ai).lower(),
    }
    return _finalize(AgentType.LOBBYIST, to_number, variables)
