"""Place calls through ElevenLabs (Twilio-backed number)."""

import os

import httpx

from .agents import AGENTS
from .models import CallRequest

API_BASE = "https://api.elevenlabs.io/v1"


class CallNotAllowedError(RuntimeError):
    pass


def build_payload(request: CallRequest, phone_number_id: str) -> dict:
    """The JSON body for POST /v1/convai/twilio/outbound-call."""
    override: dict = {}
    if request.voice_id:
        override["tts"] = {"voice_id": request.voice_id}
    if request.first_message:
        override["agent"] = {"first_message": request.first_message}

    client_data: dict = {"dynamic_variables": request.dynamic_variables}
    if override:
        client_data["conversation_config_override"] = override

    return {
        "agent_id": AGENTS[request.agent_type].agent_id,
        "agent_phone_number_id": phone_number_id,
        "to_number": request.to_number,
        "conversation_initiation_client_data": client_data,
    }


def allowed_numbers() -> set[str]:
    raw = os.environ.get("ALLOWED_TO_NUMBERS", "")
    return {n.strip() for n in raw.split(",") if n.strip()}


def place_call(request: CallRequest) -> dict:
    """Start an outbound call. Returns ElevenLabs' response, which includes
    conversation_id for fetching the transcript and analysis afterward."""
    allowed = allowed_numbers()
    if request.to_number not in allowed:
        raise CallNotAllowedError(
            f"{request.to_number} is not in ALLOWED_TO_NUMBERS; refusing to dial."
        )
    payload = build_payload(request, os.environ["ELEVENLABS_PHONE_NUMBER_ID"])
    response = httpx.post(
        f"{API_BASE}/convai/twilio/outbound-call",
        headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]},
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def get_conversation(conversation_id: str) -> dict:
    """Transcript plus data_collection results (office_position, support_score, …)."""
    response = httpx.get(
        f"{API_BASE}/convai/conversations/{conversation_id}",
        headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()
