<script lang="ts">
  import { onMount } from 'svelte';
  import { ArrowRight, Check, CircleAlert, FlaskConical, LoaderCircle, Megaphone, Plus, RotateCcw, Zap } from '@lucide/svelte';
  import { hasLog } from '$lib/autopilot';
  import type { Run } from '$lib/api';
  import { isDemo, loadQueue } from '$lib/runs';
  import { enterRun, journey, mobilizePath, redlinePath, runPath } from '$lib/journey.svelte';

  let runs = $state<Run[] | null>(null);
  let apiOnline = $state(true);
  let loadError = $state('');

  onMount(async () => {
    enterRun(null);
    journey.stage = 'queue';
    await refresh();
  });

  async function refresh() { ({ runs, apiOnline, loadError } = await loadQueue()); }

  const label = (r: Run) => r.selected_finding_id ? 'Redline approved · ready to mobilize'
    : ['queued', 'running'].includes(r.status) ? 'Auditing'
    : r.status === 'failed' ? 'Analysis failed'
    : r.status === 'completed_with_errors' ? `Completed with errors · ${r.findings.length} findings`
    : r.findings.length ? `${r.findings.length} barrier${r.findings.length === 1 ? '' : 's'} to redline` : 'No findings';
  const nextHref = (r: Run) => (r.status === 'failed' || ['queued', 'running'].includes(r.status) ? runPath(r.id) : r.selected_finding_id ? mobilizePath(r.id) : r.findings.length ? redlinePath(r.id) : runPath(r.id));
  const nextLabel = (r: Run) => (r.status === 'failed' || ['queued', 'running'].includes(r.status) ? 'Audit' : r.selected_finding_id ? 'Mobilize' : r.findings.length ? 'Redline' : 'Audit');
  const date = (value?: string) => { if (!value) return 'Date unavailable'; const d = new Date(value); return Number.isNaN(d.valueOf()) ? 'Date unavailable' : d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }); };
</script>

<svelte:head><title>DOGE Factory — Problem queue</title></svelte:head>

<div class="page-heading">
  <div><div class="eyebrow"><span></span> PROBLEM QUEUE</div><h1>Problems <em>in motion.</em></h1>
    <p>Every pitch you've run, and where it stands. Pick one up at its next step.</p></div>
  <a class="primary-button queue-new" href="/"><Plus size={16} /> New pitch</a>
</div>

{#if !apiOnline}
  <div class="alert-error queue-offline" role="status"><CircleAlert size={18} /><div><strong>Saved analyses unavailable</strong>
    <p>{loadError} Showing built-in demos only; your saved runs have not been deleted.</p></div><button onclick={refresh}>Retry</button></div>
{/if}

{#if !runs}
  <div class="loading-panel"><LoaderCircle class="spin" size={20} /> Loading problems…</div>
{:else}
  {#each [{ title: 'Saved analyses', items: runs.filter((r) => !isDemo(r.id)) }, { title: 'Built-in demos', items: runs.filter((r) => isDemo(r.id)) }] as group}
  <div class="section-heading"><div><h2>{group.title}</h2><p>{group.title === 'Built-in demos' ? 'Prepared examples, not analyses of your queries.' : 'Your locally saved runs.'}</p></div></div>
  {#if !group.items.length}<div class="empty-state"><p>No saved analyses yet. Start a new analysis to see it here.</p></div>{:else}
  <div class="queue">
    {#each group.items as r}
      <div class="queue-item"><a class="queue-row" href={nextHref(r)}>
        <span class="queue-state" class:approved={!!r.selected_finding_id} class:running={['queued', 'running'].includes(r.status)}>
          {#if r.selected_finding_id}<Megaphone size={15} />{:else if ['queued', 'running'].includes(r.status)}<LoaderCircle class="spin" size={15} />{:else if r.status === 'failed' || r.status === 'completed_with_errors'}<CircleAlert size={15} />{:else}<Check size={15} />{/if}
        </span>
        <span class="queue-main">
          <strong>{r.query}</strong>
          <small>{date(r.created_at)} · {r.collection === 'other' ? 'Problem library' : r.collection || 'Policy'} · {label(r)}{#if r.findings[0]} · {r.findings[0].provision.citation || r.findings[0].provision.title}{/if}</small>
        </span>
        {#if isDemo(r.id)}<span class="queue-tag"><FlaskConical size={11} /> DEMO</span>{/if}
        <span class="queue-next">{nextLabel(r)} <ArrowRight size={14} /></span>
      </a>
      <a class="ghost-button queue-ap" href={`${runPath(r.id)}/autopilot`} title={hasLog(r.id) ? 'Replay the recorded autopilot run' : 'Run this problem on autopilot'}>
        {#if hasLog(r.id)}<RotateCcw size={14} /> Replay{:else}<Zap size={14} /> Autopilot{/if}</a></div>
    {/each}
  </div>
  {/if}
  {/each}
{/if}
