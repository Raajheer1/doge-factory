# Confidence scores (`confidence.v1`)

How likely a proposed change is to actually happen, scored twice: **before calls**, from
what we expect each person's stance to be, and **after calls**, from how the conversations
actually went. Built for a downstream software factory (8090) to rank and filter proposals,
and for us to watch the score move as agents are built and calls come in.

## How a score is made

1. **Baseline.** When Mobilize builds agents for a `mobilize.v1` handoff with people, the run
   gets a baseline from path difficulty alone (`voice_agents/confidence.py`, `PATH`):
   guidance 55, regulation/rule 45, ordinance 40, statute 32, otherwise 40. Measured savings
   add 4; each open uncertainty in the change takes off 2 (at most 8).
2. **Expected stances (before calls).** While writing each agent's call plan, the planner
   also gives where it expects that person to stand (`expected_position`, `expected_reason`),
   judged from their role, authority and interests. Each one rescores the run as its agent
   is built.
3. **Read each call (after calls).** When a call finishes, a small model (`CONFIDENCE_MODEL`, default
   `gpt-6-luna`) reads the transcript into facts: reached, position, commitment, sentiment
   (-1 to 1), engagement, how clear the read is, objections and up to 3 verbatim quotes. The
   model never picks the score.
4. **Rescore in code.** For each reached person (their latest call counts), and for each
   person not reached yet from their expected stance:

   ```
   stance  = 0.55·sentiment + 0.45·position + commitment bonus      (clamped to -1..1)
   weight  = leverage(relevance) · read confidence  # a call
   stance  = position(expected)                     # not reached yet
   weight  = leverage(relevance) · 0.2              # a guess counts a fifth of a clear call
   support = Σ stance·weight / Σ weight
   pull    = Σ weight / (Σ weight + 0.6)          # few calls barely move the score
   score   = prior + support·pull·(95 − prior)    # or ·(prior − 5) when support < 0
   ```

   Sentiment carries the most weight while there are only a few calls. Leverage by relevance:
   authority over the document 1.0, administers 0.9, committee jurisdiction 0.75, lobbied on
   the document 0.55, represents an affected client 0.45, other 0.3. Commitment bonus: will
   consider 0.1, follow-up 0.2, committed 0.35. A reached person's call replaces their
   expected stance; people with neither have no effect but count against coverage.

Bands: likely ≥ 75, promising ≥ 55, toss-up ≥ 40, uphill ≥ 25, otherwise long shot.

This is a ranked score, not a calibrated probability: there is no history of outcomes yet.
Once outcomes are recorded, the weights above are what gets fitted. Party control, session
calendar and bill history are not inputs yet.

## The snapshot

One snapshot per scoring event: `seq` 0 is the baseline, then one per planned agent and one
per read call. `phase` is `before_calls` until the first call is read, then `after_calls`.

| Field | Meaning |
|---|---|
| `version` | `confidence.v1` |
| `run_id`, `policy_id`, `policy_title`, `citation`, `jurisdiction`, `change`, `synthetic` | What is being scored, from the handoff |
| `score`, `band`, `delta`, `phase` | 0–100, its band, the change from the previous snapshot, and `before_calls` or `after_calls` |
| `factors[]` | `{key, label, points, detail}`: `path` (the prior), `expected` (points from expected stances) and `calls` (points from calls) |
| `support`, `evidence_pull` | The weighted stance (-1..1) and how much of it is applied (0..1) |
| `coverage` | `{people, called, reached}` |
| `objections[]` | Every objection heard so far |
| `targets[]` | Per person: `leverage`, `called`, `reached`, `source` (`call`, `expected` or null), `stance`, `weight`, `points` (their share of the shift), `expected` (`{position, reason}`), and from their latest call `position`, `commitment`, `sentiment`, `engagement`, `read_confidence`, `objections`, `evidence`, `rationale`, `conversation_id` |
| `trigger` | `{type: baseline|plan|call, summary, conversation_id?, person_id?}` |
| `weights`, `reader_model`, `computed_at`, `seq` | How it was computed |

## Where to read it

- **Supabase** (`supabase/migrations/20261114210000_create_confidence_scores.sql`):
  - `confidence_scores`: every snapshot, keyed by `(run_key, seq)`, with the full snapshot in
    `snapshot` and the main fields (including `phase`) as columns.
  - `latest_confidence`: the newest snapshot per run. For the before-calls score, take a run's
    last `before_calls` row.
  - `call_reads`: one row per read call; joins `calls` on `conversation_id`.
  Row level security is on with no policies, so read with the secret key server-side.
- **Mobilize API:** `GET /api/confidence?run=<run_id>` returns `{key, current, before, after,
  history, reading}`: `before` and `after` are the last snapshot of each phase. Without `run`,
  it is the run built last. `reading` lists calls still being read.
- **Local:** `call_logs/confidence/<run_id>.json` holds the handoff, the expected stances,
  every read and the history. It is the source of truth; Supabase is a copy.

The Mobilize page and Autopilot show the before and after scores side by side, the score's
history (planned agents, then calls) and each person's stance, expected or from their call,
polling every 2 seconds.
