// Folds the pipeline's trace events into the state the graph and trace render.
import type { PipelineEvent, Persona, Stage, VoiceAgent } from '$lib/voice';

export type NodeState = 'pending' | 'running' | 'done' | 'error';
export interface PersonaSlot { state: NodeState; persona?: Persona; voice?: string }
export interface TraceRow { stage: Stage | 'error'; start: number; end: number | null; message: string; status: string }
export interface RunState {
  phase: 'idle' | 'running' | 'done' | 'error';
  n: number; start: number | null; end: number | null;
  inputState: NodeState; synthState: NodeState;
  personas: PersonaSlot[];
  legislators: VoiceAgent[]; survey: VoiceAgent | null; lobbyist: VoiceAgent | null;
  rows: TraceRow[];
}

export const FINAL_CALL_STATUSES = new Set(['done', 'failed']);

export function emptyRun(n = 0): RunState {
  return {
    phase: 'idle', n, start: null, end: null, inputState: 'pending', synthState: 'pending',
    personas: [], legislators: [], survey: null, lobbyist: null, rows: [],
  };
}

export function allAgents(r: RunState): VoiceAgent[] {
  return [...r.legislators, r.survey, r.lobbyist].filter((a): a is VoiceAgent => !!a);
}

/** Rebuild a finished run from agents saved by the API. */
export function restoreRun(agents: VoiceAgent[]): RunState {
  const r = emptyRun();
  for (const a of agents) {
    if (a.kind === 'legislator' || a.kind === 'generated') {
      r.legislators.push(a);
      if (a.persona) r.personas.push({ state: 'done', persona: a.persona, voice: a.voice });
    } else r[a.kind] = a;
  }
  if (agents.length) Object.assign(r, { n: r.legislators.length, phase: 'done', inputState: 'done', synthState: 'done' });
  return r;
}

/** Mutates `r` (a $state proxy) with one pipeline event. */
export function applyEvent(r: RunState, ev: PipelineEvent) {
  const t = Date.parse(ev.t);
  r.start ??= t;

  if (ev.status === 'error') {
    const open = r.rows.find((row) => row.end === null);
    if (open) Object.assign(open, { end: t, status: 'error', message: ev.message });
    else r.rows.push({ stage: 'error', start: t, end: t, message: ev.message, status: 'error' });
    r.phase = 'error';
    r.synthState = 'error';
    const slot = r.personas.find((p) => p.state === 'running');
    if (slot) slot.state = 'error';
    return;
  }

  if (ev.stage === 'persona' && ev.status === 'running') {
    r.rows.push({ stage: 'persona', start: t, end: null, message: ev.message, status: 'running' });
    r.personas[ev.data!.index - 1] = { state: 'running' };
    r.synthState = 'running';
  } else if (ev.stage === 'persona') {
    const open = r.rows.find((row) => row.stage === 'persona' && row.end === null);
    if (open) Object.assign(open, { end: t, message: ev.message, status: ev.data?.skipped ? 'error' : 'done' });
    r.personas[ev.data!.index - 1] = ev.data!.skipped ? { state: 'error' } : { state: 'running', persona: ev.data!.persona };
  } else {
    r.rows.push({ stage: ev.stage, start: t, end: t, message: ev.message, status: ev.status });
  }

  if (ev.stage === 'input') r.inputState = 'done';
  if (ev.stage === 'plan') r.n = ev.data!.targets.length; // one generated agent per person
  if (ev.stage === 'voice') {
    const slot = r.personas.find((p) => p.persona && !p.voice);
    if (slot) {
      slot.voice = ev.message.match(/voice (\w+)/)?.[1];
      slot.state = 'done';
    }
  }
  if (ev.agent) {
    if (ev.agent.kind === 'legislator' || ev.agent.kind === 'generated') r.legislators.push(ev.agent);
    else r[ev.agent.kind] = ev.agent;
    if (r.personas.length === r.n && r.personas.every((p) => p.state === 'done' || p.state === 'error')) r.synthState = 'done';
  }
  if (ev.stage === 'ready') {
    r.phase = 'done';
    r.synthState = r.personas.some((p) => p.state === 'error') ? 'error' : 'done';
    r.end = t;
  }
}

export const fmtDuration = (ms: number) => (ms < 1000 ? `${Math.round(ms)}ms` : `${(ms / 1000).toFixed(1)}s`);
export const initials = (name: string) =>
  name.replace(/\(.*\)/, '').trim().split(/\s+/).map((w) => w[0]).slice(0, 2).join('').toUpperCase();
export const avatarColor = (name: string) => `hsl(${[...name].reduce((h, c) => (h * 31 + c.charCodeAt(0)) % 360, 7)} 32% 44%)`;
