// Shared journey state so the layout's sidebar and top bar reflect whichever
// page is open. The URL stays the source of truth for the run id; pages write
// what they learn here when they load.
import type { VoiceStatus } from './voice';

export type StageKey = 'audit' | 'redline' | 'mobilize';
export type PageKey = StageKey | 'queue';

export const STAGES: { key: StageKey; label: string; hint: string }[] = [
  { key: 'audit', label: 'Audit', hint: 'Find the policy in the way' },
  { key: 'redline', label: 'Redline', hint: 'Draft and approve the change' },
  { key: 'mobilize', label: 'Mobilize', hint: 'Voice agents and calls' },
];

export const journey = $state({
  stage: 'audit' as PageKey,
  runId: null as string | null,
  query: '',
  analysisDone: false,
  hasFindings: false,
  findingId: null as string | null, // finding open in Redline, kept so the sidebar can link back
  approved: false,
  agentsBuilt: false,
  health: null as VoiceStatus | null, // set by Mobilize; shown in the top bar
});

const LAST_RUN = 'doge-last-run';
export function rememberRun(id: string) { try { localStorage.setItem(LAST_RUN, id); } catch { /* storage is optional */ } }
export function lastRun(): string | null { try { return localStorage.getItem(LAST_RUN); } catch { return null; } }

/** Start fresh when a new run (or no run) is opened. */
export function enterRun(runId: string | null) {
  if (journey.runId === runId) return;
  Object.assign(journey, { runId, query: '', analysisDone: false, hasFindings: false, findingId: null, approved: false, agentsBuilt: false });
}

export const runPath = (id: string) => `/runs/${encodeURIComponent(id)}`;
export const redlinePath = (id: string, findingId?: string | null) =>
  `${runPath(id)}/redline${findingId ? `?finding=${encodeURIComponent(findingId)}` : ''}`;
export const mobilizePath = (id: string) => `${runPath(id)}/mobilize`;
