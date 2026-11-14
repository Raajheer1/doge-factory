-- confidence.v1: how likely a proposed change is to happen, rescored after every call.
-- See docs/confidence.md.

create table public.call_reads (
  conversation_id text primary key,  -- joins calls.conversation_id
  run_key text not null,
  run_id text,
  policy_id text,
  person_id text,
  reached boolean not null,
  position text not null,
  commitment text not null,
  sentiment double precision not null,
  engagement double precision not null,
  read_confidence double precision not null,
  objections jsonb not null default '[]',
  evidence jsonb not null default '[]',
  rationale text,
  model text,
  read_at timestamptz not null default now()
);

create table public.confidence_scores (
  run_key text not null,
  seq integer not null,
  version text not null default 'confidence.v1',
  run_id text,
  policy_id text not null,
  policy_title text,
  jurisdiction text,
  score double precision not null,
  band text not null,
  delta double precision not null default 0,
  support double precision,
  coverage jsonb not null default '{}',
  factors jsonb not null default '[]',
  targets jsonb not null default '[]',
  objections jsonb not null default '[]',
  trigger jsonb not null default '{}',
  snapshot jsonb not null,
  computed_at timestamptz not null default now(),
  primary key (run_key, seq)
);

create index call_reads_run_key on public.call_reads (run_key);
create index confidence_scores_policy_id on public.confidence_scores (policy_id);

-- The latest score per run: what a consumer reads for "where do we stand now".
create view public.latest_confidence with (security_invoker = true) as
  select distinct on (run_key) * from public.confidence_scores order by run_key, seq desc;

alter table public.call_reads enable row level security;
alter table public.confidence_scores enable row level security;
