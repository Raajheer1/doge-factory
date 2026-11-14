-- Finished Mobilize calls, linked to the run, person and policy they came from.
create table public.calls (
  conversation_id text primary key,
  elevenlabs_agent_id text,
  agent_name text,
  -- what the call was for
  run_id text,
  query text,
  policy_id text,
  policy_title text,
  jurisdiction text,
  person_id text,
  target text,
  target_role text,
  archetype text,
  caller text,
  goal text,
  -- how it went
  started_at timestamptz,
  duration_secs integer,
  status text,
  termination_reason text,
  call_successful text,
  summary text,
  data_collection jsonb not null default '{}'::jsonb,
  evaluation jsonb not null default '{}'::jsonb,
  elevenlabs_sentiment jsonb,
  turns integer,
  agent_words integer,
  user_words integer,
  transcript jsonb not null default '[]'::jsonb,
  transcript_text text,
  -- what we told the agent (persona, variables, opening line) and the raw ElevenLabs record
  context jsonb not null default '{}'::jsonb,
  raw jsonb,
  -- free space for downstream scores (sentiment, confidence, ...)
  analysis jsonb not null default '{}'::jsonb,
  saved_at timestamptz not null default now()
);

-- One row per spoken turn, for per-utterance scoring.
create table public.call_turns (
  conversation_id text not null references public.calls(conversation_id) on delete cascade,
  turn_index integer not null,
  role text not null,
  at_secs real,
  message text not null,
  analysis jsonb not null default '{}'::jsonb,
  primary key (conversation_id, turn_index)
);

create index calls_run_id_idx on public.calls (run_id);
create index calls_person_id_idx on public.calls (person_id);
create index calls_policy_id_idx on public.calls (policy_id);
create index calls_started_at_idx on public.calls (started_at);

-- Server-side writes use the secret key, which bypasses RLS; no public access.
alter table public.calls enable row level security;
alter table public.call_turns enable row level security;
