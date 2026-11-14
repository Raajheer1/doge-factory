# Voice Agents (Mobilize)

Voice agents that make calls on behalf of a policy change. There is one ElevenLabs
agent per **call type**, not one per persona. Each call fills in the persona, policy
details, and voice at dial time.

## Architecture

```
HydraDB: legislators, districts, policies, lobbyists, personas
        │
        ├─ persona generator (voice_agents/personas.py, Claude)
        │     district profile + policy → synthetic persona + voice_id → written back to DB
        │
        ▼
call builder (voice_agents/agents.py)  →  CallRequest (agent type + variables + voice)
        │
        ▼
ElevenLabs outbound call (voice_agents/calls.py)  →  Twilio number  →  phone
        │
        ▼
post-call analysis (data_collection fields)  →  written back to DB
```

## Agents

| Type | ElevenLabs agent | Caller → callee |
|---|---|---|
| `legislator` | `agent_5501m7ck1rtnf0wt4z429ddj3130` | constituent persona → legislator's office |
| `survey` | `agent_2801m7cp2e12e5d89y6drn7g8arm` | DOGE Factory → constituent |
| `lobbyist` | `agent_5901m7cp2pj8frcaj8hh7sg83ajj` | DOGE Factory → lobbyist |

The prompts live in ElevenLabs. The `{{placeholders}}` in each prompt must match
`required_variables` in `voice_agents/agents.py`. Every agent allows a per-call override of
`tts.voice_id` and `agent.first_message`.

## Database contract

These are the fields the call layer reads. The names are suggestions; the builders in
`agents.py` do the mapping.

**Policy**: `title`, `summary`, `fiscal_impact`, `state`, `pain_point` (what residents
personally run into), `key_legislators` (who can move it).

**Legislator**: `title` ("Senator"), `name`, `district`, plus `district_profile`
(free text: demographics, industries, towns), which is the input to persona generation.

**Lobbyist**: `name`, `firm`, `client_name`, `client_benefit` (why the policy serves the client).

**Persona**: `name`, `age`, `gender` (female|male|neutral), `age_band`
(young|middle_aged|old), `occupation`, `background`, `personal_impact`, `voice_id`,
`synthetic` (must be `true` for generated personas, so they never mix with real
constituent data).

**Call outcomes** (from ElevenLabs post-call analysis, keyed by `conversation_id`):

| Agent | Fields |
|---|---|
| legislator | `office_position` (supportive/undecided/opposed/no_answer), `commitment`, `staffer_contact`, `objections` |
| survey | `aware_of_issue`, `personal_experience`, `support_score` (1-5, 0 = no answer), `concerns`, `willing_to_contact_rep`, `do_not_call` |
| lobbyist | `interest_level` (high/medium/low/declined), `objections`, `next_step`, `follow_up_contact` |

## Calling from another language (e.g. Go)

All the call layer sends is one HTTP request. `voice-agents preview <type>` prints the
exact JSON body:

```
POST https://api.elevenlabs.io/v1/convai/twilio/outbound-call
xi-api-key: $ELEVENLABS_API_KEY
{ agent_id, agent_phone_number_id, to_number,
  conversation_initiation_client_data: { dynamic_variables, conversation_config_override } }
```

Results come from `GET /v1/convai/conversations/{conversation_id}`, under
`analysis.data_collection_results`.

## Running the demo

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
cp .env.example .env            # add ELEVENLABS_API_KEY (+ ANTHROPIC_API_KEY for personas)
.venv/bin/voice-agents preview legislator   # inspect the payload, no call
.venv/bin/voice-agents call legislator      # dials the number in fixtures/demo.json
.venv/bin/voice-agents persona              # generate a persona for the demo district
.venv/bin/voice-agents call legislator --persona generated_persona.json
.venv/bin/voice-agents result <conversation_id>
.venv/bin/pytest
```

`place_call` only dials numbers listed in `ALLOWED_TO_NUMBERS`.

## Disclosure

Each prompt checks a `disclose_ai` variable, which defaults to `false` for the internal
demo, where every call goes to a team member. Set it to `true` before calling anyone
outside the team. Robocall rules (the FCC's 2024 ruling on AI voices under the TCPA) and
some state laws require disclosure.

## Placeholders

The figures in `voice_agents/fixtures/demo.json` are invented: $2.1M, $800, "13th District",
"Senator Smith", and "Bluegrass Strategies". Replace them with real DOGE Factory output.

## Mobilize page (frontend `/mobilize`)

The SvelteKit frontend's **Mobilize** page turns an approved proposal into
persona voice agents and lets you call from any of them. It talks to two
backends: the Go API for the approved proposal, and this Python package for
building agents and placing calls.

```bash
pip install -e ".[console]"
voice-agents console            # Mobilize API on http://127.0.0.1:8000
cd frontend && npm run dev      # open http://127.0.0.1:5173/mobilize
```

- **Input:** approve a finding in Policy analysis, then choose *Prepare
  mobilization → Open Mobilize*. The page loads the Go handoff
  (`POST /api/runs/:id/mobilize`) and sends it with the pipeline request, and
  `input_from_handoff` maps the finding onto the agents' policy variables.
  Legislator, lobbyist and district aren't in the handoff yet, so they are demo
  placeholders. Opened without a run, the page uses `fixtures/demo.json`.
- **Agent graph:** proposal → persona synthesis → personas → voice agents,
  streamed from `POST /api/pipeline` (server-sent events). Source is **Sample**
  (pre-written Kentucky personas, no API cost) or **Claude** (Haiku, each
  persona told to differ from the ones before it).
- **Trace:** every pipeline step with real timing.
- **Inspector:** persona, dynamic variables and the outbound-call payload, plus
  **Call**, with live transcript, extracted fields and evaluation.

Agents are saved to `console_agents.json` (gitignored), and each build replaces
the previous roster. Calls still go through `place_call`, so
`ALLOWED_TO_NUMBERS` applies. Set `VITE_VOICE_API_BASE_URL` in
`frontend/.env` if the API isn't on port 8000.
