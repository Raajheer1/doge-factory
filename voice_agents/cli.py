"""Demo CLI.

    voice-agents preview legislator          # print the call payload, no dialing
    voice-agents call legislator             # place the call (needs .env)
    voice-agents persona                     # generate a persona for the demo district
    voice-agents call legislator --persona generated.json
    voice-agents result <conversation_id>    # transcript outcome fields
"""

import argparse
import json
from importlib import resources
from pathlib import Path

from dotenv import load_dotenv

from . import agents, calls
from .models import AgentType, CallRequest, Legislator, Lobbyist, Persona, Policy


def load_demo() -> dict:
    return json.loads(resources.files("voice_agents").joinpath("fixtures/demo.json").read_text())


def build_request(agent_type: AgentType, demo: dict, persona_path: str | None) -> CallRequest:
    policy = Policy(**demo["policy"])
    legislator = Legislator(**demo["legislator"])
    to_number = demo["to_number"]

    if agent_type is AgentType.LEGISLATOR:
        persona_data = json.loads(Path(persona_path).read_text()) if persona_path else demo["persona"]
        return agents.legislator_call(
            to_number=to_number, persona=Persona(**persona_data), legislator=legislator,
            policy=policy, ask=demo["asks"]["legislator"],
        )
    if agent_type is AgentType.SURVEY:
        return agents.survey_call(
            to_number=to_number, respondent_name="Harsh", legislator=legislator, policy=policy,
        )
    return agents.lobbyist_call(
        to_number=to_number, lobbyist=Lobbyist(**demo["lobbyist"]), policy=policy,
        ask=demo["asks"]["lobbyist"],
    )


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="voice-agents")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("preview", "call"):
        p = sub.add_parser(name)
        p.add_argument("agent_type", choices=[t.value for t in AgentType])
        p.add_argument("--persona", help="JSON file from `voice-agents persona` (legislator calls)")

    p = sub.add_parser("persona")
    p.add_argument("--out", default="generated_persona.json")

    p = sub.add_parser("result")
    p.add_argument("conversation_id")

    args = parser.parse_args()
    demo = load_demo()

    if args.command == "persona":
        from .personas import generate_persona

        persona = generate_persona(
            legislator=Legislator(**demo["legislator"]), policy=Policy(**demo["policy"]),
            district_profile=demo["district_profile"],
        )
        Path(args.out).write_text(persona.model_dump_json(indent=2))
        print(persona.model_dump_json(indent=2))
        print(f"\nSaved to {args.out}")
        return

    if args.command == "result":
        convo = calls.get_conversation(args.conversation_id)
        analysis = convo.get("analysis") or {}
        print(json.dumps({
            "status": convo.get("status"),
            "summary": analysis.get("transcript_summary"),
            "data_collection": {
                k: v.get("value") for k, v in (analysis.get("data_collection_results") or {}).items()
            },
            "evaluation": {
                k: v.get("result") for k, v in (analysis.get("evaluation_criteria_results") or {}).items()
            },
        }, indent=2))
        return

    request = build_request(AgentType(args.agent_type), demo, args.persona)
    if args.command == "preview":
        print(json.dumps(calls.build_payload(request, "<ELEVENLABS_PHONE_NUMBER_ID>"), indent=2))
        return

    result = calls.place_call(request)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
