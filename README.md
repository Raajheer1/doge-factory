# DOGE Factory

> **Department of Government Efficiency / Engineering Factory**

DOGE Factory is an autonomous regulatory refactoring platform that helps governments identify policy written for a paper-and-people era, modernize it for responsible automation, and build the case for legislative action.

## The problem

Government policy is often *human-native*, rather than *AI-native*. Federal, state, and local statutes can explicitly require manual review, paper records, wet signatures, or other human-in-the-loop processes—even when technology can perform the same work more quickly, consistently, and affordably.

These requirements can:

- Preserve expensive administrative bottlenecks.
- Block adoption of safe, compliant automation.
- Protect entrenched manual intermediaries.
- Shift avoidable costs onto taxpayers.

The bottleneck to government efficiency is not always the technology. Often, it is the law.

## What we’re building

DOGE Factory ingests municipal, state, and federal codes to identify provisions that unnecessarily mandate manual work. It produces proposed, reviewable legislative redlines and a localized fiscal-impact brief to help policymakers modernize policy while preserving oversight, due process, privacy, and compliance.

**We turn legacy, human-only laws into AI-native policy—clearing the path for accountable public-sector modernization.**

## How it works

### 1. Audit

Scans statutes and regulations to isolate mandatory human bottlenecks, paper-era requirements, and automation barriers—then estimates their potential fiscal impact.

### 2. Redline

Translates legacy, paper-bound provisions into reviewable, AI-native legislative amendments designed to preserve the policy’s original safeguards without requiring unnecessary manual labor.

### 3. Mobilize

Packages the legislative redline, fiscal ROI memo, and stakeholder context for the lawmakers and committees positioned to act.

## Example outcome

For a given code section, DOGE Factory can help a policy team answer:

1. **What does this law require people to do manually?**
2. **Is that requirement necessary for the policy objective or legal safeguard?**
3. **What is a legally actionable amendment?**
4. **What could modernization save taxpayers and constituents?**
5. **Who has the authority to move the change forward?**

## Principles

- **Human accountability:** Automation should strengthen—not remove—appropriate oversight and appeal processes.
- **Legislative precision:** Recommendations are specific, traceable, and suitable for expert legal review.
- **Measurable impact:** Fiscal claims should be transparent, localized, and evidence-backed.
- **Public interest first:** Modernization must protect privacy, equity, due process, and public trust.

## Status

Early-stage concept and product development. The [housing policy graph guide](docs/housing-policy-graph.md) covers the HydraDB-backed fixture, setup, and tests.

## Disclaimer

DOGE Factory is a policy-analysis and drafting-support tool. Its output is not legal advice and should be reviewed by qualified legal, policy, security, and subject-matter experts before use.

## Voice agents

The Mobilize step's calling agents live in `voice_agents/`. See [docs/voice-agents.md](docs/voice-agents.md).

### Run the policy workbench locally

Set `HYDRADB_API_KEY` and `AI_GATEWAY_API_KEY` in the root `.env`. The Go server reads environment variables; it does not load `.env` automatically. In a terminal at the repository root, export the variables and start the server:

```sh
set -a
source .env
set +a
go run ./cmd/server
```

In a second terminal, run `cd frontend`, `npm install` (first run), and `npm run dev`. Open http://127.0.0.1:5173. Choose **Healthcare** or **Housing**, enter a goal, and start an analysis. You can close or refresh the page while it runs; the backend continues processing. Open **Saved runs** in the sidebar to revisit a result, including after restarting the services.

The Go server saves runs, findings, errors, and the approved finding in `data/runs.json` (relative to the directory where the server is started). This file is local, gitignored, and intended for a single server process. Set `RUNS_FILE` to use another path. Keep the backend running until an analysis finishes: if it stops or restarts during a run, that run is marked failed on startup, with any partial results retained; it does not automatically resume.

The frontend defaults to the Go API at `http://127.0.0.1:8080`; set `VITE_API_BASE_URL` in `frontend/.env` before starting Vite if needed. The default HydraDB database is `doge-factory`; set `HYDRADB_DATABASE_ID` to override it. Analysis requires an AI Gateway account with access and credits. Results are limited to the selected collection and are drafts for review; stored source snapshots may be incomplete or outdated.
