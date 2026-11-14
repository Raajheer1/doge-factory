<script lang="ts">
  import { FlaskConical } from '@lucide/svelte';
  import type { Run } from '$lib/api';
  import { isDemo, TERMINAL_STATUSES } from '$lib/runs';

  // Pitch summary + progress shared by Audit and Redline.
  let { run }: { run: Run } = $props();

  const terminal = $derived(TERMINAL_STATUSES.includes(run.status));
  const stageLabel = $derived(run.stage === 'retrieving' ? 'Retrieving provisions' : run.stage === 'auditing_and_drafting' ? 'Auditing and drafting' : run.stage === 'done' ? 'Audit finished' : 'Getting started');
  const errors = $derived(Array.isArray(run.errors) ? run.errors : []);
  const displayDate = (v?: string) => { if (!v) return 'Unavailable'; const d = new Date(v); return Number.isNaN(d.valueOf()) ? v : d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }); };
</script>

{#if isDemo(run.id)}
  <div class="demo-banner"><FlaskConical size={16} /><span><strong>Demo problem.</strong>
    {run.id.includes('replay') ? 'A prepared audit replayed on request; it did not analyze this pitch.' : 'Prepared so every screen works without the analysis API.'}
    {run.findings[0]?.provision.synthetic === false ? 'Source text is real (HUD EIV pilot); the analysis wording is pre-written.' : ''}</span></div>
{/if}
<div class="run-summary">
  <div class="run-goal"><div class="run-goal-heading"><span>ANALYSIS GOAL</span><small>Started {displayDate(run.created_at)}</small></div><p>{run.query}</p></div>
  <div class="run-summary-bottom">
    <div class="run-progress"><div class="progress-title"><span>{terminal ? 'AUDIT STATUS' : 'IN PROGRESS'}</span><strong>{stageLabel}</strong></div>
      <div class="progress-track" role="progressbar" aria-label="Provisions processed" aria-valuemin="0" aria-valuemax={Math.max(run.retrieved, 1)} aria-valuenow={run.reviewed}><i style:width={run.retrieved ? `${Math.min(100, run.reviewed / run.retrieved * 100)}%` : '0%'}></i></div><small>{run.retrieved ? `${run.reviewed} of ${run.retrieved} provisions processed` : 'Waiting for retrieval'}</small></div>
    <div class="run-stat"><strong>{run.retrieved}</strong><span>provisions retrieved</span></div><div class="run-stat"><strong>{run.reviewed}</strong><span>processed by model</span></div><div class="run-stat"><strong>{run.findings.length}</strong><span>findings</span></div>
  </div>
</div>
{#if errors.length}
  <div class="run-errors" role="status"><div><strong>{run.status === 'failed' ? 'Audit failed' : 'Audit reported issues'}</strong>{#each errors as issue}<p>{issue}</p>{/each}</div></div>
{/if}
