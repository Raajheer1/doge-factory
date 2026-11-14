"""The `mobilize.v1` handoff from policy analysis. See docs/mobilize-handoff.md.

Mobilize consumes only this document; it does no retrieval of its own.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Model(BaseModel):
    model_config = ConfigDict(extra="ignore")  # producers may add fields before a version bump


class Jurisdiction(_Model):
    name: str
    level: Literal["federal", "state", "local"]


class HandoffPolicy(_Model):
    id: str
    title: str
    spoken_title: str = Field(max_length=120)
    citation: str = ""
    jurisdiction: Jurisdiction
    issuing_agency: str = ""
    document_type: str = ""
    status: str = ""
    source_url: str = ""
    effective_date: str = ""
    synthetic: bool


class HandoffChange(_Model):
    summary: str = Field(min_length=1, max_length=400)
    barrier: str = Field(min_length=1)
    evidence_quote: str = ""
    proposed_text: str = ""
    justification: str = ""
    safeguards: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)


class HandoffImpact(_Model):
    estimated_annual_savings: float | None = None  # None = not measured; never guessed
    savings_basis: str = ""
    affected_groups: list[str] = Field(min_length=1)


Relevance = Literal[
    "committee_jurisdiction", "administers", "authority_over_document",
    "lobbied_on_document", "represents_affected_client", "other",
]


class HandoffPerson(_Model):
    id: str
    name: str
    type: Literal["official", "lobbyist", "organization"]
    title: str = ""
    role: str = ""
    organization: str = ""
    state: str = ""
    district: str = ""
    clients: list[str] = Field(default_factory=list)
    relevance: Relevance
    verified_at: str
    source_url: str = ""

    @model_validator(mode="after")
    def _callable(self):
        if self.type == "lobbyist" and not self.clients:
            raise ValueError(f"lobbyist {self.name} needs at least one client")
        if self.type == "official" and not self.title:
            raise ValueError(f"official {self.name} needs a title (Senator, Representative, …)")
        return self


class MobilizeHandoff(_Model):
    version: Literal["mobilize.v1"]
    run_id: str = ""
    query: str = ""
    policy: HandoffPolicy
    change: HandoffChange
    impact: HandoffImpact
    people: list[HandoffPerson] = Field(default_factory=list)
    notes: str = ""

    @property
    def legislators(self) -> list[HandoffPerson]:
        """Officials with a state: the targets for constituent calls."""
        return [p for p in self.people if p.type == "official" and p.state]

    @property
    def lobbyists(self) -> list[HandoffPerson]:
        return [p for p in self.people if p.type == "lobbyist"]
