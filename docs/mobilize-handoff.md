# Mobilize handoff (`mobilize.v1`)

The contract between **policy analysis** (producer) and **Mobilize** (consumer).
Analysis decides *what* changes and *who* matters; Mobilize turns that into voice
agents and calls. Mobilize does no retrieval of its own: everything it needs is
in this JSON document.

Send it as the body of `POST /api/runs/:id/mobilize`'s response (or anywhere the
frontend can pass it on). Mobilize validates it with `voice_agents/handoff.py`
and rejects it with a field-level error if something required is missing.

## Example (HUD EIV pilot)

```json
{
  "version": "mobilize.v1",
  "run_id": "3f9c2a…",
  "query": "Reduce paperwork in federal housing assistance",
  "policy": {
    "id": "hud-eiv:notice:pih-2018-18",
    "title": "HUD Notice PIH 2018-18 — Administrative Guidance for Effective and Mandated Use of EIV",
    "spoken_title": "HUD's pay-stub rule for housing assistance",
    "citation": "Notice PIH 2018-18",
    "jurisdiction": { "name": "United States", "level": "federal" },
    "issuing_agency": "HUD/PIH",
    "document_type": "notice",
    "source_url": "https://www.hud.gov/sites/dfiles/OCHCO/documents/18-18pihn.pdf",
    "status": "verify_current_status",
    "synthetic": false
  },
  "change": {
    "summary": "Let housing agencies accept approved, auditable electronic wage records instead of two paper pay stubs at routine recertification.",
    "barrier": "Agencies must collect at least two current, consecutive paper pay stubs to verify wages, even when the same income is already visible electronically.",
    "evidence_quote": "The PHA is required to obtain at a minimum, two current and consecutive pay stubs for determining annual income from wages.",
    "proposed_text": "Draft a narrowly scoped allowance for approved, auditable electronic evidence in routine wage recertification; preserve EIV use, consent, exception handling, tenant correction rights, and existing data-sharing limits.",
    "justification": "Removes a duplicate paper step while keeping EIV as the primary check.",
    "safeguards": ["EIV use stays mandatory", "Tenant consent and correction rights preserved"],
    "uncertainties": ["Current status of the notice must be verified"]
  },
  "impact": {
    "estimated_annual_savings": null,
    "savings_basis": "",
    "affected_groups": [
      "tenants with housing choice vouchers",
      "residents of public housing",
      "property managers of HUD-assisted housing",
      "public housing agency caseworkers",
      "small landlords who rent to voucher holders"
    ]
  },
  "people": [
    {
      "id": "hud-eiv:actor:katie-boyd-britt",
      "name": "Katie Boyd Britt",
      "type": "official",
      "title": "Senator",
      "role": "Chair, Senate Banking Subcommittee on Housing, Transportation, and Community Development",
      "organization": "U.S. Senate",
      "state": "Alabama",
      "relevance": "committee_jurisdiction",
      "verified_at": "Current public directory, checked 2026-11-14",
      "source_url": "https://www.banking.senate.gov/"
    },
    {
      "id": "hud-eiv:actor:carlie-christensen",
      "name": "Carlie Christensen",
      "type": "lobbyist",
      "role": "Reported lobbyist (historical filing)",
      "organization": "Equifax, Inc.",
      "clients": ["Equifax, Inc."],
      "relevance": "represents_affected_client",
      "verified_at": "2017 Q3 filing; historical, current role unverified",
      "source_url": "https://lda.gov/filings/public/filing/…/print/"
    }
  ],
  "notes": ""
}
```

## Fields

**Required** fields are marked ✱. Use `null` or `""` for anything unknown; never fill a gap with a guess.

### Top level

| Field | Type | Notes |
| --- | --- | --- |
| `version` ✱ | `"mobilize.v1"` | Lets us change the format without breaking older runs. |
| `run_id` | string | Analysis run this came from, so call outcomes can be joined back. |
| `query` | string | The user's original goal. |
| `notes` | string | Free text for anything that doesn't fit. Shown to the user, not read aloud on calls. |

### `policy`: the source document

| Field | Type | Notes |
| --- | --- | --- |
| `id` ✱ | string | Stable ID (e.g. the graph's document `id`). |
| `title` ✱ | string | Official title, shown in the UI. |
| `spoken_title` ✱ | string | **How a person would say it on the phone**, under ~10 words. Agents read this aloud. |
| `citation` | string | e.g. `Notice PIH 2018-18`, `24 CFR 5.233`. |
| `jurisdiction` ✱ | `{name, level}` | `level`: `federal`, `state` or `local`. |
| `issuing_agency`, `document_type`, `status`, `source_url`, `effective_date` | string | As in the policy graph. |
| `synthetic` ✱ | bool | `true` for fixture or demo data; the UI labels it. |

### `change`: what we want changed

| Field | Type | Notes |
| --- | --- | --- |
| `summary` ✱ | string | **One or two plain sentences** a caller can say out loud. The single most important field. |
| `barrier` ✱ | string | What goes wrong today, in plain language. Used for personas' personal stories. |
| `evidence_quote` | string | Exact quote from the source that creates the barrier. |
| `proposed_text` | string | The amendment or redline. Shown in the UI and given to the agents as background. |
| `justification` | string | Why the change helps. |
| `safeguards`, `uncertainties` | string[] | Agents use safeguards to answer "does this weaken oversight?". |

### `impact`

| Field | Type | Notes |
| --- | --- | --- |
| `estimated_annual_savings` | number \| null | **`null` unless actually measured.** Agents say "not yet estimated" when null. |
| `savings_basis` | string | How the number was computed, if there is one. |
| `affected_groups` ✱ | string[] | Who feels the barrier (3–6 short phrases). Mobilize generates one constituent persona per group, so make them distinct. |

### `people`: who Mobilize may call

Only include people the analysis thinks are relevant, ordered most relevant first. Mobilize builds:
- for each `official`, constituent callers from that official's `state`;
- for each `lobbyist`, a pitch tailored to their `clients`.

| Field | Type | Notes |
| --- | --- | --- |
| `id` ✱ | string | Stable ID. |
| `name` ✱ | string | |
| `type` ✱ | `official` \| `lobbyist` \| `organization` | Organizations are context only; they don't get calls. |
| `title` | string | How to address them: `Senator`, `Representative`, `Secretary`… Required for officials. |
| `role` | string | Plain role, e.g. `Chair, Senate Banking Subcommittee on Housing…`. |
| `organization` | string | Chamber, agency or employer. |
| `state` | string | **Required for legislators.** Constituent personas are generated from this state. |
| `district` | string | House district, if any. |
| `clients` | string[] | **Required for lobbyists.** The pitch is tailored to these. |
| `relevance` ✱ | enum | Why they're on the list: `committee_jurisdiction`, `administers`, `authority_over_document`, `lobbied_on_document`, `represents_affected_client`, `other`. Pick the strongest one the sources support. The UI shows it, and agents won't claim more. |
| `verified_at` ✱ | string | The source date or status note, e.g. `2017 Q3 filing; historical, current role unverified`. |
| `source_url` | string | Where the role or relationship comes from. |

## Rules for producers

1. **Plain text only.** No HTML or Markdown. Keep `summary` under ~300 characters; it's spoken aloud.
2. **No invented facts.** Unknown means `null` or `""`. Mobilize never fills gaps with made-up numbers.
3. **Relevance is a claim.** Only use `lobbied_on_document` or `authority_over_document` when a source shows it (same rule as the policy graph).
4. **No private data.** Public roles and public contact info only. No tenant or constituent records.
5. Extra fields are ignored, so it's safe to add more before we bump the version.

## Go structs

```go
type MobilizeHandoff struct {
	Version string         `json:"version"` // "mobilize.v1"
	RunID   string         `json:"run_id,omitempty"`
	Query   string         `json:"query,omitempty"`
	Policy  HandoffPolicy  `json:"policy"`
	Change  HandoffChange  `json:"change"`
	Impact  HandoffImpact  `json:"impact"`
	People  []HandoffPerson `json:"people"`
	Notes   string         `json:"notes,omitempty"`
}

type HandoffPolicy struct {
	ID            string `json:"id"`
	Title         string `json:"title"`
	SpokenTitle   string `json:"spoken_title"`
	Citation      string `json:"citation,omitempty"`
	Jurisdiction  struct {
		Name  string `json:"name"`
		Level string `json:"level"` // federal | state | local
	} `json:"jurisdiction"`
	IssuingAgency string `json:"issuing_agency,omitempty"`
	DocumentType  string `json:"document_type,omitempty"`
	Status        string `json:"status,omitempty"`
	SourceURL     string `json:"source_url,omitempty"`
	EffectiveDate string `json:"effective_date,omitempty"`
	Synthetic     bool   `json:"synthetic"`
}

type HandoffChange struct {
	Summary       string   `json:"summary"`
	Barrier       string   `json:"barrier"`
	EvidenceQuote string   `json:"evidence_quote,omitempty"`
	ProposedText  string   `json:"proposed_text,omitempty"`
	Justification string   `json:"justification,omitempty"`
	Safeguards    []string `json:"safeguards"`
	Uncertainties []string `json:"uncertainties"`
}

type HandoffImpact struct {
	EstimatedAnnualSavings *float64 `json:"estimated_annual_savings"` // nil = not measured
	SavingsBasis           string   `json:"savings_basis,omitempty"`
	AffectedGroups         []string `json:"affected_groups"`
}

type HandoffPerson struct {
	ID           string   `json:"id"`
	Name         string   `json:"name"`
	Type         string   `json:"type"` // official | lobbyist | organization
	Title        string   `json:"title,omitempty"`
	Role         string   `json:"role,omitempty"`
	Organization string   `json:"organization,omitempty"`
	State        string   `json:"state,omitempty"`
	District     string   `json:"district,omitempty"`
	Clients      []string `json:"clients,omitempty"`
	Relevance    string   `json:"relevance"`
	VerifiedAt   string   `json:"verified_at"`
	SourceURL    string   `json:"source_url,omitempty"`
}
```
