// Run access for the pages: demo ids are served from built-in fixtures,
// everything else goes to the Go analysis API (lib/api.ts).
import { approve, createRun, getRun, listRuns, mobilize, type Collection, type Handoff, type Run } from './api';
import { approveDemo, getDemoRun, isDemo, listDemoRuns, startDemoReplay } from './demoRuns';

export { isDemo };

export async function loadRun(id: string): Promise<Run> {
  if (!isDemo(id)) return getRun(`/api/runs/${encodeURIComponent(id)}`);
  const run = getDemoRun(id);
  if (!run) throw new Error('This demo problem no longer exists.');
  return run;
}

/** Real runs (if the API is up) plus demo problems. `apiOnline` is false when the Go API is unreachable. */
export async function loadQueue(): Promise<{ runs: Run[]; apiOnline: boolean }> {
  let real: Run[] = [];
  let apiOnline = true;
  try { real = await listRuns(); } catch { apiOnline = false; }
  const runs = [...real, ...listDemoRuns()].sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''));
  return { runs, apiOnline };
}

export async function approveFinding(runId: string, findingId: string) {
  if (isDemo(runId)) { approveDemo(runId, findingId); return findingId; }
  return approve(runId, findingId);
}

export async function loadHandoff(runId: string): Promise<Handoff> {
  if (!isDemo(runId)) return mobilize(runId);
  const run = getDemoRun(runId);
  const finding = run?.findings.find((f) => f.id === run.selected_finding_id);
  if (!run || !finding) throw new Error('Approve a proposal for this demo problem first.');
  return { status: 'simulated', message: 'Demo problem: handoff prepared in the browser.', run_id: run.id, query: run.query, finding };
}

export class AnalysisOfflineError extends Error {}

/** Start a real analysis. Throws AnalysisOfflineError when the Go API is unreachable,
 * so the page can offer a demo replay instead of silently substituting one. */
export async function startRun(query: string, collection: Collection): Promise<string> {
  try {
    return (await createRun(query, collection)).id;
  } catch (e) {
    if (e instanceof Error && e.message.startsWith('Could not connect')) throw new AnalysisOfflineError(e.message);
    throw e;
  }
}

/** Replay a prepared demo audit for this pitch; only on the user's explicit request. */
export const startDemoRun = (query: string) => startDemoReplay(query);

export const TERMINAL_STATUSES = ['completed', 'completed_with_errors', 'failed'];

/** Poll a run until it finishes. Returns a stop function (use as an $effect cleanup). */
export function watchRun(id: string, onRun: (run: Run) => void, onError: (message: string) => void): () => void {
  let stopped = false;
  let timer: ReturnType<typeof setTimeout> | undefined;
  const tick = async () => {
    try {
      const run = await loadRun(id);
      if (stopped) return;
      onRun(run);
      if (!TERMINAL_STATUSES.includes(run.status)) timer = setTimeout(tick, 1500);
    } catch (e) {
      if (!stopped) onError(e instanceof Error ? e.message : 'Unable to load this run.');
    }
  };
  void tick();
  return () => { stopped = true; clearTimeout(timer); };
}
