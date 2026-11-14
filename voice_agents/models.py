"""Data shapes shared between the database and the call layer."""

from enum import Enum

from pydantic import BaseModel, Field


class AgentType(str, Enum):
    LEGISLATOR = "legislator"  # constituent calls a legislator's office
    SURVEY = "survey"  # org surveys a constituent
    LOBBYIST = "lobbyist"  # org pitches a lobbyist


class Gender(str, Enum):
    FEMALE = "female"
    MALE = "male"
    NEUTRAL = "neutral"


class AgeBand(str, Enum):
    YOUNG = "young"  # roughly 18-34
    MIDDLE_AGED = "middle_aged"  # roughly 35-59
    OLD = "old"  # 60+


class Policy(BaseModel):
    title: str
    summary: str
    fiscal_impact: str
    state: str
    pain_point: str = ""  # what residents personally run into; used by surveys
    key_legislators: str = ""  # who can move it; used by lobbyist pitches


class Legislator(BaseModel):
    title: str  # e.g. "Senator"
    name: str
    district: str


class Lobbyist(BaseModel):
    name: str
    firm: str
    client_name: str
    client_benefit: str  # why this policy serves their client


class Persona(BaseModel):
    """A constituent persona. Generated personas must stay synthetic=True so
    they are never mixed with real constituent data."""

    name: str
    age: int
    gender: Gender
    age_band: AgeBand
    occupation: str
    background: str
    personal_impact: str
    voice_id: str = ""
    synthetic: bool = True


class CallRequest(BaseModel):
    """Everything needed to place one call. Language-neutral: this is exactly
    what gets sent to ElevenLabs, so other services can build it too."""

    agent_type: AgentType
    to_number: str
    dynamic_variables: dict[str, str]
    voice_id: str | None = None
    first_message: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)  # ids to join outcomes back to the DB
