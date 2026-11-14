<script lang="ts">
  import { onMount } from 'svelte';
  import { ArrowRight, Check, CircleAlert, FlaskConical, LoaderCircle, Megaphone, Plus, RotateCcw, Zap } from '@lucide/svelte';
  import { hasLog } from '$lib/autopilot';
  import type { Run } from '$lib/api';
  import { isDemo, loadQueue } from '$lib/runs';
  import { enterRun, journey, mobilizePath, redlinePath, runPath } from '$lib/journey.svelte';

  let runs = $state<Run[] | null>(null);
  let apiOnline = $state(true);

  onMount(async () => {
    enterRun(null);
    journey.stage = 'queue';
    ({ runs, apiOnline } = await loadQueue());
  });

  const label = (r: Run) => r.selected_finding_id ? 'Redline approved · ready to mobilize'
    : ['queued', 'running'].includes(r.status) ? 'Auditing'
    : r.status === 'failed' ? 'Failed'
    : r.findings.length ? `${r.findings.length} barrier${r.findings.length === 1 ? '' : 's'} to redline` : 'No barriers found';
  const nextHref = (r: Run) => (r.selected_finding_id ? mobilizePath(r.id) : r.findings.length ? redlinePath(r.id) : runPath(r.id));
  const nextLabel = (r: Run) => (r.selected_finding_id ? 'Mobilize' : r.findings.length ? 'Redline' : 'Audit');
</script>

<svelte:head><title>DOGE Factory — Problem queue</title></svelte:head>

<div class="page-heading">
  <div><div class="eyebrow"><span></span> PROBLEM QUEUE</div><h1>Problems <em>in motion.</em></h1>
    <p>Every pitch you've run, and where it stands. Pick one up at its next step.</p></div>
  <a class="primary-button queue-new" href="/"><Plus size={16} /> New pitch</a>
</div>

{#if !apiOnline}
  <div class="alert-error queue-offline" role="status"><CircleAlert size={18} /><div><strong>Analysis API offline</strong>
    <p>Showing built-in demo problems only. Start the Go API to see real runs; a new pitch can replay a demo audit on request.</p></div></div>
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
          {#if r.selected_finding_id}<Megaphone size={15} />{:else if ['queued', 'running'].includes(r.status)}<LoaderCircle class="spin" size={15} />{:else}<Check size={15} />{/if}
        </span>
        <span class="queue-main">
          <strong>{r.query}</strong>
          <small>{label(r)}{#if r.findings[0]} · {r.findings[0].provision.citation || r.findings[0].provision.title}{/if}</small>
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
