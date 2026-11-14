# Confidence scores (`confidence.v1`)

How likely a proposed change is to actually happen, rescored after every call. Built for a
downstream software factory (8090) to rank and filter proposals, and for us to watch a score
move as calls come in.

## How a score is made

1. **Baseline.** When Mobilize builds agents for a `mobilize.v1` handoff with people, the run
   gets a baseline from path difficulty alone (`voice_agents/confidence.py`, `PATH`):
   guidance 55, regulation/rule 45, ordinance 40, statute 32, otherwise 40. Measured savings
   add 4; each open uncertainty in the change takes off 2 (at most 8).
2. **Read each call.** When a call finishes, a small model (`CONFIDENCE_MODEL`, default
   `gpt-6-luna`) reads the transcript into facts: reached, position, commitment, sentiment
   (-1 to 1), engagement, how clear the read is, objections and up to 3 verbatim quotes. The
   model never picks the score.
3. **Rescore in code.** For each reached person (their latest call counts):

   ```
   stance  = 0.55·sentiment + 0.45·position + commitment bonus      (clamped to -1..1)
   weight  = leverage(relevance) · read confidence
   support = Σ stance·weight / Σ weight
   pull    = Σ weight / (Σ weight + 0.6)          # few calls barely move the score
   score   = prior + support·pull·(95 − prior)    # or ·(prior − 5) when support < 0
   ```

   Sentiment carries the most weight while there are only a few calls. Leverage by relevance:
   authority over the document 1.0, administers 0.9, committee jurisdiction 0.75, lobbied on
   the document 0.55, represents an affected client 0.45, other 0.3. Commitment bonus: will
   consider 0.1, follow-up 0.2, committed 0.35. People not reached have no effect yet but count
   against coverage.

Bands: likely ≥ 75, promising ≥ 55, toss-up ≥ 40, uphill ≥ 25, otherwise long shot.

This is a ranked score, not a calibrated probability: there is no history of outcomes yet.
Once outcomes are recorded, the weights above are what gets fitted. Party control, session
calendar and bill history are not inputs yet.

## The snapshot

One snapshot per scoring event (`seq` 0 is the baseline, then one per call):

| Field | Meaning |
|---|---|
| `version` | `confidence.v1` |
| `run_id`, `policy_id`, `policy_title`, `citation`, `jurisdiction`, `change`, `synthetic` | What is being scored, from the handoff |
| `score`, `band`, `delta` | 0–100, its band, and the change from the previous snapshot |
| `factors[]` | `{key, label, points, detail}`: `path` (the prior) and `stance` (points the calls added or took away) |
| `support`, `evidence_pull` | The weighted stance (-1..1) and how much of it is applied (0..1) |
| `coverage` | `{people, called, reached}` |
| `objections[]` | Every objection heard so far |
| `targets[]` | Per person: `leverage`, `called`, `reached`, `stance`, `weight`, `points` (their share of the shift), and from their latest call `position`, `commitment`, `sentiment`, `engagement`, `read_confidence`, `objections`, `evidence`, `rationale`, `conversation_id` |
| `trigger` | `{type: baseline|call, summary, conversation_id?, person_id?}` |
| `weights`, `reader_model`, `computed_at`, `seq` | How it was computed |

## Where to read it

- **Supabase** (`supabase/migrations/20261114210000_create_confidence_scores.sql`):
  - `confidence_scores`: every snapshot, keyed by `(run_key, seq)`, with the full snapshot in
    `snapshot` and the main fields as columns.
  - `latest_confidence`: the newest snapshot per run.
  - `call_reads`: one row per read call; joins `calls` on `conversation_id`.
  Row level security is on with no policies, so read with the secret key server-side.
- **Mobilize API:** `GET /api/confidence?run=<run_id>` returns `{key, current, history,
  reading}`; without `run`, the run built last. `reading` lists calls still being read.
- **Local:** `call_logs/confidence/<run_id>.json` holds the handoff, every read and the
  history. It is the source of truth; Supabase is a copy.

The Mobilize page and Autopilot show the score, its history across calls and each person's
stance, polling every 3 seconds.
