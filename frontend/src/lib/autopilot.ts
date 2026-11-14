// Autopilot: drives one run from audit to a placed call without clicks, and
// records every step as a timestamped event. The same log renders the live view
// and replays an old run, so "what happened" is exactly what was shown.
import type { Finding, Handoff, Run } from './api';
import { approveFinding, loadHandoff, loadRun, TERMINAL_STATUSES } from './runs';
import { getConversation, placeCall, runPipeline, type VoiceAgent } from './voice';
import { FINAL_CALL_STATUSES } from './mobilize/run';

export type APStage = 'audit' | 'select' | 'redline' | 'handoff' | 'mobilize' | 'call' | 'done';
export interface APEvent { t: number; stage: APStage; status: 'running' | 'progress' | 'done' | 'error'; message: string; data?: Record<string, any> }

export const AP_STAGES: { key: APStage; label: string }[] = [
  { key: 'audit', label: 'Audit policy' },
  { key: 'select', label: 'Pick the barrier' },
  { key: 'redline', label: 'Redline & approve' },
  { key: 'handoff', label: 'Hand off to Mobilize' },
  { key: 'mobilize', label: 'Build voice agents' },
  { key: 'call', label: 'Place the call' },
];

export const PERSONAS = 2; // kept small so a run stays cheap

const key = (runId: string) => `doge-autopilot:${runId}`;
export function loadLog(runId: string): APEvent[] {
  try { return JSON.parse(localStorage.getItem(key(runId)) || '[]'); } catch { return []; }
}
function saveLog(runId: string, events: APEvent[]) {
  try { localStorage.setItem(key(runId), JSON.stringify(events)); } catch { /* storage is optional */ }
}
export function hasLog(runId: string): boolean { return loadLog(runId).length > 0; }
export function clearLog(runId: string) { try { localStorage.removeItem(key(runId)); } catch { /* optional */ } }
/** Append one event to a run's log (e.g. when the user stops autopilot). */
export function appendEvent(runId: string, e: APEvent) { saveLog(runId, [...loadLog(runId), e]); }
export const isFinished = (events: APEvent[]) => events.some((e) => (e.stage === 'done') || e.status === 'error');

export class Stopped extends Error {}

export interface Controls { paused: () => boolean; stopped: () => boolean }

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

const findingSummary = (f: Finding) => ({
  id: f.id, title: f.title || f.provision.title, citation: f.provision.citation, jurisdiction: f.provision.jurisdiction,
  barrier: f.barrier, source_passage: f.source_passage, source_url: f.provision.source_url,
});

const handoffSummary = (h: Handoff) => ({
  spoken_title: h.policy?.spoken_title ?? h.finding.provision.title,
  summary: h.change?.summary ?? h.finding.desired_change,
  affected_groups: h.impact?.affected_groups ?? [],
  people: (h.people ?? []).map((p) => ({ name: p.name, type: p.type, title: p.title, state: p.state, organization: p.organization, clients: p.clients, relevance: p.relevance })),
  version: h.version ?? 'legacy',
  notes: h.notes ?? '',
});

const agentSummary = (a: VoiceAgent) => ({ id: a.id, kind: a.kind, caller: a.caller, target: a.target, voice: a.voice, persona: a.persona ? { name: a.persona.name, age: a.persona.age, occupation: a.persona.occupation, personal_impact: a.persona.personal_impact } : null });

/** Run the whole journey for `runId`, appending to its log through `emit`. */
export async function runAutopilot(runId: string, emit: (e: APEvent) => void, ctl: Controls, onRosterBuilt?: () => void) {
  // A rerun starts a fresh log, but never redials a call that was already placed.
  const priorCall = [...loadLog(runId)].reverse().find((e) => e.stage === 'call' && e.data?.conversation_id)?.data?.conversation_id as string | undefined;
  const events: APEvent[] = [];
  saveLog(runId, events);
  const log = (stage: APStage, status: APEvent['status'], message: string, data?: Record<string, any>) => {
    const e = { t: Date.now(), stage, status, message, data };
    events.push(e); saveLog(runId, events); emit(e);
  };
  // Waits that honour Pause and Stop between steps.
  const gate = async (ms = 0) => {
    const end = Date.now() + ms;
    while (ctl.paused() || Date.now() < end) {
      if (ctl.stopped()) throw new Stopped();
      await sleep(200);
    }
    if (ctl.stopped()) throw new Stopped();
  };

  // 1. Audit: poll the analysis run until it finishes.
  log('audit', 'running', 'Searching the policy graph and auditing candidate provisions');
  let run: Run;
  let lastSeen = '';
  for (;;) {
    await gate();
    run = await loadRun(runId);
    const seen = `${run.retrieved}/${run.reviewed}/${run.findings.length}`;
    if (seen !== lastSeen) {
      lastSeen = seen;
      log('audit', 'progress', `${run.reviewed} of ${run.retrieved} provisions reviewed · ${run.findings.length} barrier${run.findings.length === 1 ? '' : 's'} found`,
        { query: run.query, collection: run.collection, retrieved: run.retrieved, reviewed: run.reviewed, findings: run.findings.map(findingSummary) });
    }
    if (TERMINAL_STATUSES.includes(run.status)) break;
    await gate(1500);
  }
  if (!run.findings.length) {
    log('audit', 'error', run.status === 'failed' ? 'The audit failed; nothing to redline.' : 'No barriers found for this pitch.', { errors: run.errors });
    return;
  }
  log('audit', 'done', `Audit complete: ${run.findings.length} barrier${run.findings.length === 1 ? '' : 's'} in ${run.reviewed} provisions`);

  // 2. Pick the top-ranked finding (search ranks the most relevant first).
  await gate(1200);
  const finding = run.findings.find((f) => f.id === run.selected_finding_id) ?? run.findings[0];
  log('select', 'done', `Selected ${finding.provision.citation || finding.provision.title}`, { finding: findingSummary(finding), alternatives: run.findings.length - 1 });

  // 3. Redline, then approve.
  await gate(1500);
  log('redline', 'progress', 'Drafted amendment', {
    original: finding.diff?.original || finding.provision.text, proposed: finding.amendment,
    desired_change: finding.desired_change, safeguards: finding.safeguards ?? [],
  });
  await gate(2500);
  await approveFinding(runId, finding.id);
  log('redline', 'done', 'Redline approved for mobilization');

  // 4. Handoff (mobilize.v1 with people from the graph).
  await gate(1000);
  log('handoff', 'running', 'Preparing the mobilize.v1 handoff');
  const handoff = await loadHandoff(runId);
  const summary = handoffSummary(handoff);
  log('handoff', 'done', `${summary.people.filter((p) => p.type !== 'organization').length} people to mobilize`, summary);

  // 5. Build voice agents.
  await gate(1500);
  log('mobilize', 'running', `Generating ${PERSONAS} constituent personas and voice agents`);
  try { localStorage.setItem('doge-agents-run', runId); } catch { /* optional */ }
  const agents: VoiceAgent[] = [];
  await runPipeline({ personas: PERSONAS, source: 'claude', handoff }, (ev) => {
    if (ev.status === 'error') log('mobilize', 'error', ev.message);
    else if (ev.stage === 'persona' && ev.status === 'done') log('mobilize', 'progress', ev.message, { persona: ev.data?.persona });
    else if (ev.stage === 'assemble' && ev.agent) { agents.push(ev.agent); log('mobilize', 'progress', ev.message, { agent: agentSummary(ev.agent) }); }
    else if (ev.stage === 'input') log('mobilize', 'progress', ev.message, { input: ev.data });
  });
  if (!agents.length) { log('mobilize', 'error', 'No agents were built.'); return; }
  onRosterBuilt?.();
  log('mobilize', 'done', `${agents.length} agents ready`, { agents: agents.map(agentSummary) });

  // 6. Call: the first constituent → legislator agent rings the allowlisted number.
  await gate(2000);
  const caller = agents.find((a) => a.kind === 'legislator') ?? agents[0];
  log('call', 'running', `${caller.caller} is calling as a constituent of ${caller.target}`, { agent: agentSummary(caller), to: caller.request.to_number });
  const conversation_id = priorCall ?? (await placeCall(caller.id)).conversation_id;
  if (priorCall) log('call', 'progress', 'Reattached to the call placed earlier; not redialing', { conversation_id });
  let lastTurns = -1;
  let status = 'initiated';
  for (;;) {
    await gate(2500);
    const convo = await getConversation(conversation_id);
    if (convo.transcript.length !== lastTurns || convo.status !== status) {
      lastTurns = convo.transcript.length; status = convo.status;
      log('call', 'progress', `Call ${convo.status} · ${convo.transcript.length} turns`, { conversation_id, status: convo.status, transcript: convo.transcript, summary: convo.summary, duration: convo.duration });
    }
    if (FINAL_CALL_STATUSES.has(convo.status)) break;
  }
  log('call', 'done', status === 'failed' ? 'The call failed.' : 'Call finished');
  log('done', 'done', 'Autopilot finished: pitch → policy → redline → agents → call');
}
