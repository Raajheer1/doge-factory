# DOGE Factory frontend

A local SvelteKit policy workbench for the separate DOGE Factory Go API. It does not contain or modify the backend.

## Run locally

1. Start the Go API at `http://127.0.0.1:8080`.
2. Run `npm install`.
3. Optionally copy `.env.example` to `.env` and set `VITE_API_BASE_URL` to the API origin.
4. Run `npm run dev` and open `http://127.0.0.1:5173`.

The default frontend origin is allowed by the current backend CORS configuration. The browser connects directly to the configured API; no AI Gateway or HydraDB credentials belong in this project. The health endpoint only indicates that the HTTP service is running, not that upstream services are available.

Run `npm run check` for type checking and `npm run build` for a production build. Runs are stored by the backend; the frontend remembers the most recently opened run in browser storage and offers backend run history. Mobilization is currently simulated by the API and places no calls.

## Journey and routes

One run moves through three stages, tracked by the sidebar stepper (`src/lib/shell/Sidebar.svelte`, state in `src/lib/journey.svelte.ts`):

| Stage | Route | Primary action |
| --- | --- | --- |
| 1 Audit | `/` (pitch), then `/runs/[id]` (barriers found) | Redline this barrier |
| 2 Redline | `/runs/[id]/redline?finding=<id>` | Approve & mobilize |
| 3 Mobilize | `/runs/[id]/mobilize` (shows the analysis handoff, builds agents, places calls) | Build voice agents, Call |

The shared shell (sidebar, top bar, footer) lives in `src/routes/+layout.svelte`.

`/runs` is the **problem queue**: real runs from the Go API plus built-in demo problems (`src/lib/demoRuns.ts`, ids starting `demo-`), so every screen can be clicked through without the analysis API. When the Go API is offline, the pitch page says so and offers a clearly labeled demo audit; it never substitutes one silently. Pages load runs through `src/lib/runs.ts`, which routes demo ids to the fixtures.

`/mobilize` is a demo sandbox using the Kentucky fixture, with no analysis run needed.

## Mobilize page

`/mobilize` builds persona voice agents from an approved proposal and can place real calls through the Python Mobilize API (`voice-agents console`, default `http://127.0.0.1:8000`, configurable with `VITE_VOICE_API_BASE_URL`). Calls only ring numbers in that service's `ALLOWED_TO_NUMBERS`. See `docs/voice-agents.md`.
