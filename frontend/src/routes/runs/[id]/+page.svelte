<script lang="ts">
  import { untrack } from 'svelte';
  import { page } from '$app/state';
  import { ArrowLeft, ArrowRight, Check, CircleAlert, FilePenLine, FileSearch, LoaderCircle } from '@lucide/svelte';
  import type { Run } from '$lib/api';
  import RunHeader from '$lib/RunHeader.svelte';
  import { TERMINAL_STATUSES, watchRun } from '$lib/runs';
  import { enterRun, journey, mobilizePath, redlinePath, rememberRun } from '$lib/journey.svelte';

  const runId = $derived(page.params.id ?? '');
  let run = $state<Run | null>(null);
  let error = $state('');
  let retry = $state(0);
  const terminal = $derived(!!run && TERMINAL_STATUSES.includes(run.status));

  $effect(() => {
    const id = runId;
    void retry;
    return untrack(() => {
      run = null; error = '';
      enterRun(id);
      journey.stage = 'audit';
      rememberRun(id);
      return watchRun(id, (next) => {
        run = next;
        Object.assign(journey, {
          query: next.query, analysisDone: TERMINAL_STATUSES.includes(next.status),
          hasFindings: next.findings.length > 0, approved: !!next.selected_finding_id,
        });
      }, (message) => (error = message));
    });
  });
</script>

<svelte:head><title>DOGE Factory — Audit</title></svelte:head>

<div class="page-heading">
  <div><div class="eyebrow"><span></span> STEP 1 · AUDIT</div><h1>Policy in the way of <em>your pitch.</em></h1>
    <p>{run ? `“${run.query}”` : 'Loading your audit…'}</p></div>
  <a class="back-link" href="/runs"><ArrowLeft size={14} /> Problem queue</a>
</div>

{#if error}<div class="alert-error" role="alert"><CircleAlert size={18} /><div><strong>Something needs attention</strong><p>{error}</p></div><button onclick={() => retry++}>Retry</button></div>{/if}
{#if !run && !error}<div class="loading-panel"><LoaderCircle class="spin" size={20} /> Loading audit…</div>{/if}

{#if run}
  <RunHeader {run} />
  {#if run.coverage}<div class="scope-note">{run.coverage}</div>{/if}
  {#if run.findings.length}
    <div class="section-heading"><div><div class="section-kicker">BARRIERS FOUND · {run.findings.length}</div><h2>Provisions that may block your pitch</h2>
      <p>Each is a proposal for review, not a legal conclusion. Open one to redline it.</p></div></div>
    <div class="barrier-list">
      {#each run.findings as finding, index}
        <a class="barrier-card" href={redlinePath(run.id, finding.id)}>
          <div class="finding-top"><span>BARRIER {String(index + 1).padStart(2, '0')} · {finding.provision.jurisdiction || 'Jurisdiction unavailable'}</span>
            {#if run.selected_finding_id === finding.id}<span class="approved-small"><Check size={12} /> APPROVED</span>{/if}</div>
          <strong>{finding.provision.title}</strong>
          <span class="finding-citation">{finding.provision.citation || 'Citation unavailable'}{finding.provision.synthetic ? ' · synthetic' : ''}</span>
          <p>{finding.barrier}</p>
          <span class="barrier-cta"><FilePenLine size={14} /> {run.selected_finding_id === finding.id ? 'View redline' : 'Redline this barrier'} <ArrowRight size={14} /></span>
        </a>
      {/each}
    </div>
    {#if run.selected_finding_id}
      <div class="review-panel stage-cta"><div><span class="mini-label">NEXT · MOBILIZE</span><h4>A redline is approved for this run</h4><p>Build voice agents to rally support for it.</p></div>
        <a class="primary-button" href={mobilizePath(run.id)}>Continue to Mobilize <ArrowRight size={17} /></a></div>
    {/if}
  {:else if run.status === 'failed'}
    <div class="empty-state"><CircleAlert size={24}/><h3>Analysis did not complete</h3><p>Review the errors above, then start a new analysis if needed.</p><a class="back-link" href="/">Start a new analysis</a></div>
  {:else if terminal}
    <div class="empty-state"><FileSearch size={24} /><h3>{run.retrieved === 0 ? 'No matching provisions found' : 'No findings to review'}</h3>
      <p>{run.status === 'completed_with_errors' ? 'Some provisions could not be analyzed; review the errors above. ' : ''}The search covered a limited set of sources. No findings does not establish that no relevant policy exists.</p><a class="back-link" href="/">Try another analysis</a></div>
  {:else if !terminal}
    <div class="empty-state"><LoaderCircle class="spin" size={24} /><h3>Auditing the policy</h3><p>Barriers appear here as provisions are analyzed.</p></div>
  {/if}
{/if}
