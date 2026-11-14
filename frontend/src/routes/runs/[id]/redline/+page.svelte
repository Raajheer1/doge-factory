<script lang="ts">
  import { untrack } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/state';
  import { ArrowLeft, ArrowRight, ArrowUpRight, Check, CircleAlert, FlaskConical, LoaderCircle, ShieldCheck } from '@lucide/svelte';
  import type { Run } from '$lib/api';
  import RunHeader from '$lib/RunHeader.svelte';
  import { approveFinding, TERMINAL_STATUSES, watchRun } from '$lib/runs';
  import { enterRun, journey, mobilizePath, redlinePath, rememberRun, runPath } from '$lib/journey.svelte';

  const runId = $derived(page.params.id ?? '');
  const requested = $derived(page.url.searchParams.get('finding'));
  let run = $state<Run | null>(null);
  let error = $state('');
  let actionError = $state('');
  let actionBusy = $state(false);

  const selected = $derived(run ? run.findings.find((f) => f.id === requested) ?? run.findings.find((f) => f.id === run?.selected_finding_id) ?? run.findings[0] ?? null : null);
  const canApprove = $derived(!!run && ['completed', 'completed_with_errors'].includes(run.status));
  const approved = $derived(!!selected && run?.selected_finding_id === selected.id);
  const list = (v: unknown): string[] => (Array.isArray(v) ? v.filter((x): x is string => typeof x === 'string') : []);
  const displayDate = (v?: string) => { if (!v) return 'Unavailable'; const d = new Date(v); return Number.isNaN(d.valueOf()) ? v : d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }); };

  $effect(() => {
    const id = runId;
    return untrack(() => {
      run = null; error = ''; actionError = '';
      enterRun(id);
      journey.stage = 'redline';
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
  $effect(() => { journey.findingId = selected?.id ?? null; });

  async function approveAndMobilize() {
    if (!run || !selected || actionBusy) return;
    actionBusy = true; actionError = '';
    try {
      if (run.selected_finding_id !== selected.id) {
        await approveFinding(run.id, selected.id);
        run.selected_finding_id = selected.id;
      }
      journey.approved = true;
      await goto(mobilizePath(run.id));
    } catch (e) { actionError = e instanceof Error ? e.message : 'Approval failed.'; }
    finally { actionBusy = false; }
  }
</script>

<svelte:head><title>DOGE Factory — Redline</title></svelte:head>

<div class="page-heading">
  <div><div class="eyebrow"><span></span> STEP 2 · REDLINE</div><h1>Draft the change, <em>then approve it.</em></h1>
    <p>Compare the original provision with the proposed amendment and check its safeguards before mobilizing.</p></div>
  <a class="back-link" href={runPath(runId)}><ArrowLeft size={14} /> Back to audit</a>
</div>

{#if error}<div class="alert-error" role="alert"><CircleAlert size={18} /><div><strong>Something needs attention</strong><p>{error}</p></div></div>{/if}
{#if !run && !error}<div class="loading-panel"><LoaderCircle class="spin" size={20} /> Loading redline…</div>{/if}

{#if run}
  <RunHeader {run} />
  {#if !selected}
    <div class="empty-state"><h3>No barriers to redline yet</h3><p>Redlines are available once the audit finds a barrier.</p><a class="back-link" href={runPath(run.id)}>Back to audit</a></div>
  {:else}
    <div class="workspace">
      <div class="findings-column">
        <div class="column-heading"><div><span class="mini-label">BARRIERS</span><h3>Redlines <span>{run.findings.length}</span></h3></div></div>
        <p class="column-desc">Pick the barrier to redline.</p>
        <div class="finding-list">{#each run.findings as finding, index}
          <a class="finding-card" class:selected-card={selected.id === finding.id} href={redlinePath(run.id, finding.id)} data-sveltekit-replacestate data-sveltekit-noscroll>
            <div class="finding-top"><span>BARRIER {String(index + 1).padStart(2, '0')}</span>{#if run.selected_finding_id === finding.id}<span class="approved-small"><Check size={12} /> APPROVED</span>{/if}</div>
            <strong>{finding.provision.title}</strong><span class="finding-citation">{finding.provision.citation || 'Citation unavailable'}</span>
          </a>{/each}</div>
        <div class="list-foot"><span class="tiny-spark">✳</span> Redlines are proposals for review, not legal conclusions.</div>
      </div>

      <div class="detail-column">
        <div class="detail-header"><div><div class="mini-label">REDLINE</div><h3>{selected.provision.title}</h3>
          <div class="detail-meta"><span>{selected.provision.jurisdiction || 'Jurisdiction unavailable'}</span><span>·</span><span>{selected.provision.citation || 'Citation unavailable'}</span><span>·</span><span>Effective {displayDate(selected.provision.effective_date)}</span></div></div>
          <span class="proposal-pill">FOR REVIEW</span></div>
        {#if selected.provision.synthetic}<div class="synthetic-banner"><FlaskConical size={17} /><span><strong>Synthetic demo data.</strong> This source and its generated outputs are synthetic.</span></div>{/if}
        <div class="detail-body">
          <div class="compare-heading first"><div><span class="mini-label">THE REDLINE</span><h4>Original &amp; proposed text</h4><p>The full provision beside the drafted amendment.</p></div></div>
          <div class="comparison"><div class="text-block original"><div class="text-label"><span></span> ORIGINAL PROVISION</div><p>{selected.provision.text}</p></div>
            <div class="text-block proposed"><div class="text-label"><span></span> PROPOSED AMENDMENT</div><p>{selected.amendment}</p></div></div>
          <div class="insight-grid"><div><span class="number-icon">01</span><h4>Potential barrier</h4><p>{selected.barrier}</p></div><div><span class="number-icon green">02</span><h4>Desired change</h4><p>{selected.desired_change}</p></div></div>
          <div class="rationale"><h4>Why this change?</h4><p>{selected.justification}</p></div>
          <div class="source-line evidence"><span class="mini-label">EVIDENCE</span>{#if selected.provision.source_url && /^https?:\/\//i.test(selected.provision.source_url)}<a href={selected.provision.source_url} target="_blank" rel="noopener noreferrer">View source <ArrowUpRight size={14} /></a>{:else}<span>Source URL unavailable</span>{/if}</div>
          <div class="passage"><div class="passage-label">SOURCE PASSAGE</div><p>{selected.source_passage || 'Source passage unavailable.'}</p></div>
          <div class="considerations"><div><h4><ShieldCheck size={17} /> Safeguards</h4>{#if list(selected.safeguards).length}<ul>{#each list(selected.safeguards) as item}<li>{item}</li>{/each}</ul>{:else}<p>None provided.</p>{/if}</div>
            <div><h4><CircleAlert size={17} /> Uncertainties</h4>{#if list(selected.uncertainties).length}<ul>{#each list(selected.uncertainties) as item}<li>{item}</li>{/each}</ul>{:else}<p>None provided.</p>{/if}</div></div>
          <details class="scenario"><summary><span class="mini-label">BEHAVIORAL SCENARIO</span> Gherkin accompanying the amendment</summary><pre>{selected.gherkin || 'No scenario provided.'}</pre></details>
        </div>
        <div class="review-panel">
          <div><span class="mini-label">NEXT · MOBILIZE</span><h4>{approved ? 'Redline approved for mobilization' : 'Ready to move this redline forward?'}</h4>
            <p>{approved ? 'Continue to build voice agents for this redline.' : canApprove ? 'Approving selects this redline for outreach. You can change it later.' : 'Approval is available once the audit finishes.'}</p></div>
          <button class="primary-button" disabled={!canApprove || actionBusy} onclick={approveAndMobilize}>
            {#if actionBusy}<LoaderCircle class="spin" size={16} /> Approving…{:else}{approved ? 'Continue to Mobilize' : 'Approve & mobilize'} <ArrowRight size={17} />{/if}
          </button>
        </div>
        {#if actionError}<div class="action-error" role="alert">{actionError} Please try again.</div>{/if}
      </div>
    </div>
  {/if}
{/if}
