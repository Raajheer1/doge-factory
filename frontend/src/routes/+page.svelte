<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { ArrowRight, CircleAlert, FilePenLine, FileSearch, FlaskConical, HeartPulse, House, Library, LoaderCircle, Megaphone, RotateCcw, Search, Sparkles, Zap } from '@lucide/svelte';
  import type { Collection, Run } from '$lib/api';
  import { hasLog } from '$lib/autopilot';
  import { AnalysisOfflineError, loadQueue, startDemoRun, startRun } from '$lib/runs';
  import { enterRun, journey, lastRun, mobilizePath, redlinePath, rememberRun, runPath } from '$lib/journey.svelte';

  const COLLECTIONS: { key: Collection; label: string; hint: string }[] = [
    { key: 'other', label: 'Problem library', hint: 'Identity, benefits, procurement & more' },
    { key: 'healthcare', label: 'Healthcare', hint: 'Health & healthcare policy' },
    { key: 'housing', label: 'Housing', hint: 'Housing & assistance policy' },
  ];
  const EXAMPLES: Record<Collection, string[]> = {
    other: ['AI identity verification for private car sales in Kentucky, no notary visit', 'Payroll-connected income verification for public housing agencies'],
    healthcare: ['Optimize healthcare in Iowa'],
    housing: ['Reduce housing assistance paperwork'],
  };

  let query = $state('');
  let collection = $state<Collection>('other');
  let autopilot = true;
  let busy = $state(false);
  let error = $state('');
  let recent = $state<Run[]>([]);
  let continueId = $state<string | null>(null);
  let apiOnline = $state(true);
  let offline = $state(false); // the last pitch couldn't reach the analysis API

  onMount(async () => {
    enterRun(null);
    journey.stage = 'audit';
    continueId = lastRun();
    const queue = await loadQueue();
    apiOnline = queue.apiOnline;
    recent = queue.runs.slice(0, 4);
  });

  async function start(event: SubmitEvent) {
    event.preventDefault();
    autopilot = (event.submitter as HTMLButtonElement | null)?.value !== 'manual';
    if (busy) return;
    const text = query.trim();
    if (!text) { error = 'Describe what you are building to start.'; return; }
    if (new TextEncoder().encode(text).length > 2000) { error = 'Keep the pitch under 2,000 characters.'; return; }
    busy = true; error = ''; offline = false;
    try {
      const id = await startRun(text, collection);
      rememberRun(id);
      await goto(autopilot ? `${runPath(id)}/autopilot?live=1` : runPath(id));
    } catch (e) {
      if (e instanceof AnalysisOfflineError) offline = true;
      else error = e instanceof Error ? e.message : 'Unable to start the audit.';
    }
    finally { busy = false; }
  }

  async function runDemo() {
    const id = startDemoRun(query.trim());
    rememberRun(id);
    await goto(runPath(id));
  }

  const continueRun = $derived(recent.find((r) => r.id === continueId));
</script>

<svelte:head><title>DOGE Factory — Audit</title><meta name="description" content="Pitch a product, find the policy in the way, and mobilize support to change it." /></svelte:head>

<div class="page-heading">
  <div><div class="eyebrow"><span></span> STEP 1 · AUDIT</div><h1>Pitch a product. <em>Find the policy in the way.</em></h1>
    <p>Describe what you want to build. We audit the policy that may block it, redline a fix, and help you mobilize support.</p></div>
  <div class="heading-badge"><Sparkles size={15} /> FROM IDEA TO ACTION</div>
</div>

<section class="goal-card" aria-labelledby="goal-title">
  <div class="goal-intro"><div><div class="section-kicker">YOUR PITCH</div><h2 id="goal-title">What are you building?</h2>
    <p>A product, service or outcome. Plain language is best.</p></div><div class="goal-icon"><Search size={21} /></div></div>
  <form onsubmit={start}>
    <fieldset class="collection-picker">
      <legend>Policy collection <span>Choose one</span></legend>
      <div class="collection-options">
        {#each COLLECTIONS as c}
          <label class:collection-selected={collection === c.key} class="collection-option">
            <input type="radio" name="collection" value={c.key} bind:group={collection} />
            <span class="collection-icon">{#if c.key === 'healthcare'}<HeartPulse size={18} />{:else if c.key === 'housing'}<House size={18} />{:else}<Library size={18} />{/if}</span>
            <span class="collection-copy"><strong>{c.label}</strong><small>{c.hint}</small></span>
            <span class="collection-indicator" aria-hidden="true"></span>
          </label>
        {/each}
      </div>
    </fieldset>
    <label class="sr-only" for="goal">What are you building?</label>
    <div class="input-wrap"><Search size={19} />
      <input id="goal" maxlength="2000" bind:value={query} placeholder={`e.g. ${EXAMPLES[collection][0]}`} />
      <button class="ghost-button" name="mode" value="manual" disabled={busy}>Step through</button>
      <button class="primary-button" name="mode" value="autopilot" disabled={busy}>{#if busy}<LoaderCircle class="spin" size={17} /> Starting{:else}<Zap size={16} /> Run on autopilot{/if}</button>
    </div>
    <div class="input-meta"><span class="examples">Try: {#each EXAMPLES[collection] as ex}<button type="button" class="example" onclick={() => (query = ex)}>“{ex}”</button>{/each}</span><span>{query.length} / 2,000</span></div>
  </form>
  <div class="scope-note"><span class="scope-dot"></span> Analysis considers a bounded set of retrieved provisions, not all applicable laws.
    {#if !apiOnline}<span class="offline-note">· Analysis API offline</span>{/if}</div>
</section>

{#if offline}
  <div class="alert-error" role="alert"><CircleAlert size={18} /><div><strong>The analysis API isn't reachable</strong>
    <p>Start the Go API and try again, or replay a prepared demo audit. The demo is clearly labeled and won't analyze your pitch.</p></div>
    <button onclick={runDemo}><FlaskConical size={14} /> Run demo audit</button></div>
{/if}
{#if error}<div class="alert-error" role="alert"><CircleAlert size={18} /><div><strong>Something needs attention</strong><p>{error}</p></div></div>{/if}

{#if continueRun}
  <a class="continue-card" href={continueRun.selected_finding_id ? mobilizePath(continueRun.id) : continueRun.findings.length ? redlinePath(continueRun.id) : runPath(continueRun.id)}>
    <RotateCcw size={16} /><span><small>CONTINUE WHERE YOU LEFT OFF</small><strong>{continueRun.query}</strong></span><ArrowRight size={16} />
  </a>
{/if}

<section class="welcome-section">
  <div class="section-heading"><div><div class="section-kicker">HOW IT WORKS</div><h2>Audit, redline, mobilize</h2><p>Every run moves through the same three steps; the sidebar tracks where you are.</p></div></div>
  <div class="welcome-grid">
    <div><span class="welcome-icon"><FileSearch size={19} /></span><strong>Audit</strong><p>We retrieve relevant provisions and flag the ones that may block your product.</p></div>
    <div><span class="welcome-icon"><FilePenLine size={19} /></span><strong>Redline</strong><p>Compare the original text with a drafted amendment, check its safeguards, and approve it.</p></div>
    <div><span class="welcome-icon"><Megaphone size={19} /></span><strong>Mobilize</strong><p>Build synthetic constituent, survey and lobbyist voice agents and call to build support.</p></div>
  </div>
</section>

{#if recent.length}
  <section class="welcome-section">
    <div class="section-heading"><div><div class="section-kicker">PROBLEM QUEUE</div><h2>Pick up a queued problem</h2></div><a class="back-link" href="/runs">See all <ArrowRight size={14} /></a></div>
    <div class="recent-grid">
      {#each recent as r}
        <a class="finding-card" href={r.selected_finding_id ? mobilizePath(r.id) : r.findings.length ? redlinePath(r.id) : runPath(r.id)}>
          <div class="finding-top"><span>{r.status.replaceAll('_', ' ').toUpperCase()}</span>{#if r.selected_finding_id}<span class="approved-small">APPROVED</span>{/if}</div>
          <strong>{r.query}</strong><span class="finding-citation">{r.findings.length} finding{r.findings.length === 1 ? '' : 's'}{r.id.startsWith('demo-') ? ' · demo' : ''}{hasLog(r.id) ? ' · autopilot recorded' : ''}</span>
        </a>
      {/each}
    </div>
  </section>
{/if}
