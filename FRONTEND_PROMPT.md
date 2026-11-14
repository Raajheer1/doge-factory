# DOGE Factory frontend — build prompt

Build a polished, local demo frontend for DOGE Factory. The backend is a separate Go Echo service. Build the frontend as a separate project; do not modify or implement the backend. This is an early proof of concept: **do not create, add, or maintain tests**. Keep the implementation focused and easy to run.

## Product and demo flow

A user types a goal such as “Optimize healthcare in Iowa.” The backend retrieves a bounded set of policy provisions, evaluates them for potential barriers to innovation, and drafts potential amendments. The frontend shows progress, presents findings with evidence and proposed changes, lets the user select and approve a finding, and requests a mobilization handoff.

The product is about **removing unnecessary policy barriers to innovation**. It should not imply that technology or automation must be mandated, or that all human review is bad. Present findings and amendments as proposals for review, not confirmed legal conclusions. Do not invent fiscal savings or claim complete coverage of all laws.

The demo should feel like one clear journey:

1. Enter a goal and start analysis.
2. See progress as the backend retrieves and analyzes provisions.
3. Browse findings and inspect the source passage, problem, proposed change, rationale, safeguards, uncertainties, amendment, and Gherkin.
4. Review the selected proposal and approve it for mobilization.
5. Request the handoff and display its actual returned status and contents. **The current backend simulates this; no calls are placed.** Never represent a simulated handoff as a real call.

Aim for a professional, confident policy-workbench experience: clear hierarchy, legible text, a responsive layout, good empty/loading/error states, keyboard accessibility, and useful visual distinction between original and proposed text. Prefer clarity over dashboard clutter or unnecessary animation. Use realistic product copy and clearly identify synthetic demo data when the API marks it synthetic.

## Stack and setup

- Use SvelteKit with TypeScript, Vite, Tailwind CSS, and DaisyUI. Use current stable compatible versions; consult official documentation as needed.
- Use npm or yarn, whichever is quickest in the environment. Keep dependencies modest.
- Assume the Go API runs locally at `http://127.0.0.1:8080`. Make the API base URL configurable with `VITE_API_BASE_URL`; provide a sensible local default and `.env.example`.
- The backend currently allows browser CORS from `http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:3000`, and `http://127.0.0.1:3000`. Run the frontend on one of those origins or use a local Vite proxy. Do not expose AI Gateway or HydraDB credentials to the browser.
- Document install and run commands and required configuration in the frontend README.
- Use the existing backend contract below. Do not assume unimplemented endpoints, fields, streaming, or real outreach.

## Screens and interactions

### Start and progress

- Provide a prominent natural-language input and an example prompt. Validate empty input and cap it at 2,000 characters, matching the API.
- Submit once, prevent accidental duplicate submissions while pending, then poll the returned `status_url`. Render meaningful progress using `status`, `stage`, `retrieved`, and `reviewed`. A reasonable polling interval is 1–2 seconds; stop when the run reaches a terminal status and stop on component teardown.
- Explain that the analysis considers a bounded set of provisions. Distinguish no matching provisions from analyzed provisions that produced no findings, and show `errors` for partial or failed runs. Do not label `reviewed` as human review: it counts provisions processed by the model.
- Handle backend unavailability, invalid responses, and network failures with clear recovery actions. Retain or restore a run through its ID when practical. `GET /api/runs` can list saved runs.

### Findings and proposal review

- Present findings in a scannable list. Make the current selection obvious. Each finding has a policy title, citation, jurisdiction, and source URL if supplied.
- Display the source passage and full original provision, the identified barrier, desired change, and justification. Show safeguards and uncertainties; they may be empty arrays.
- When present, display `comparison_analysis` and `comparison_evidence` with each peer jurisdiction, citation, source link, exact passage, and optional context. A difference across jurisdictions is a signal for review, not proof that another approach is effective or legally equivalent. These fields are absent if no comparison was supported.
- Show a legible before/after comparison of `provision.text` and `amendment`. The backend does not return a diff; a small client-side diff is optional, but do not claim word-level changes are authoritative if they are inferred. The full proposed amendment must remain visible.
- Render `gherkin` as readable preformatted text, preserving line breaks. Clearly label it as a behavioral scenario accompanying the proposed amendment.
- If `provision.synthetic` is true, visibly label the source and outputs as synthetic demo data. For missing citation, URL, or dates, say the information is unavailable; never fabricate it.
- Keep review simple: the user selects one finding and explicitly approves it for the mobilization handoff. The current API supports one selected finding per run, not editing, comments, multiple approvals, or version history.

### Mobilization

- After review succeeds, offer a clear “Prepare mobilization” action. Show the returned status, message, and the approved proposal being handed off.
- Current response status is `simulated`: explicitly state that **no calls were placed**. Do not fabricate lawmakers, constituents, organizations, contact details, call progress, recordings, or outcomes.
- Design the presentation so the real calling service can be integrated later, but do not invent its API now. If the endpoint errors, explain the handoff failed and allow retry.

## Current API contract

All paths are relative to the configured backend base URL. Requests and responses are JSON, except where noted. IDs are opaque strings. Error responses commonly contain `{"error":"..."}`; the UI should also handle non-JSON and network errors.

### Create a run

`POST /api/runs`

```json
{"query":"Optimize healthcare in Iowa"}
```

Success: HTTP `202`:

```json
{"id":"opaque-run-id","status":"queued","status_url":"/api/runs/opaque-run-id"}
```

Invalid or missing `query` returns HTTP `400`. Use the returned `status_url` for polling against the configured base URL.

### Get a run

`GET /api/runs/:id`

Representative response:

```json
{
  "id": "opaque-run-id",
  "query": "Optimize healthcare in Iowa",
  "status": "completed",
  "stage": "done",
  "retrieved": 1,
  "reviewed": 1,
  "findings": [
    {
      "id": "opaque-finding-id",
      "provision": {
        "id": "opaque-provision-id",
        "title": "Example provision",
        "citation": "Example citation",
        "jurisdiction": "Iowa",
        "topic": "healthcare",
        "text": "Original provision text.",
        "source_url": "https://example.org/source",
        "effective_date": "2025-01-01",
        "related_context": [],
        "synthetic": true
      },
      "source_passage": "Original provision text.",
      "barrier": "Why the provision might restrict innovation.",
      "desired_change": "The desired policy change.",
      "justification": "Why the proposed change could help.",
      "safeguards": ["Preserve review and appeal."],
      "uncertainties": ["Additional legal context may be needed."],
      "comparison_analysis": "A peer jurisdiction uses a different approach; further review is needed.",
      "comparison_evidence": [{"id":"peer-1","jurisdiction":"Example state","citation":"Example citation","source_url":"https://example.org/peer-source","source_passage":"Exact peer provision language.","context":"Optional context."}],
      "amendment": "Proposed replacement text.",
      "gherkin": "Scenario: Example\n  Given ...\n  When ...\n  Then ..."
    }
  ],
  "errors": [],
  "created_at": "2026-01-01T00:00:00Z",
  "selected_finding_id": "opaque-finding-id"
}
```

`source_url`, `effective_date`, `related_context`, and `selected_finding_id` can be absent. Handle empty or missing optional arrays defensively. Actual statuses are `queued`, `running`, `completed`, `completed_with_errors`, and `failed`; stages currently include `queued`, `retrieving`, `auditing_and_drafting`, and `done`. Findings may appear while a run is running, but approval is available only after `completed` or `completed_with_errors`. A missing run returns `404`.

### List runs

`GET /api/runs` returns a JSON array of run objects in unspecified order. Sort client-side if showing history.

### Approve a finding

`POST /api/runs/:id/review`

```json
{"finding_id":"opaque-finding-id"}
```

Success: HTTP `200` with `{"selected_finding_id":"...","status":"approved"}`. An invalid finding or run returns `404`; an unfinished run returns `409`. Selecting a new finding replaces the previously selected one.

### Prepare mobilization

`POST /api/runs/:id/mobilize`

The request does not need a JSON body. If a finding has not been approved, the endpoint returns `409`. Current success response:

```json
{
  "status": "simulated",
  "message": "Handoff prepared; no calls were placed.",
  "run_id": "opaque-run-id",
  "query": "Optimize healthcare in Iowa",
  "finding": {"id": "opaque-finding-id"}
}
```

The actual `finding` contains the complete finding object described above. Treat the response as the source of truth; future backend versions may add real calling statuses, but none are supported yet.

### Health

`GET /health` returns `{"status":"ok"}` when the HTTP service is running. It does not confirm that HydraDB or the AI Gateway is available.

## Implementation expectations

- Use clear typed API models and a small shared API client. Treat backend data and errors as untrusted input; avoid unsafe HTML rendering.
- Provide useful loading, empty, partial-success, and failure states. Keep the reviewer’s selected finding visible and recoverable during polling.
- Make long policy text readable and usable on smaller screens. Ensure buttons, inputs, and focus states are accessible.
- The backend currently stores runs locally and can mark interrupted runs failed after restart. Reflect returned state instead of assuming runs resume.
- Keep synthetic, simulated, and incomplete information visibly labeled. No invented call metrics, legal conclusions, savings, or jurisdictional comparisons.
- Do not add tests or test frameworks. Run an appropriate build or type check if available and report the result and any integration limitations.
