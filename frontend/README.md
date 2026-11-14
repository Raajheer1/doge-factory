# DOGE Factory frontend

A local SvelteKit policy workbench for the separate DOGE Factory Go API. It does not contain or modify the backend.

## Run locally

1. Start the Go API at `http://127.0.0.1:8080`.
2. Run `npm install`.
3. Optionally copy `.env.example` to `.env` and set `VITE_API_BASE_URL` to the API origin.
4. Run `npm run dev` and open `http://127.0.0.1:5173`.

The default frontend origin is allowed by the current backend CORS configuration. The browser connects directly to the configured API; no AI Gateway or HydraDB credentials belong in this project. The health endpoint only indicates that the HTTP service is running, not that upstream services are available.

Run `npm run check` for type checking and `npm run build` for a production build. Runs are stored by the backend; the frontend remembers the most recently opened run in browser storage and offers backend run history. Mobilization is currently simulated by the API and places no calls.
