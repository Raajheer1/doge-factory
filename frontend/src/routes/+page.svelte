<script lang="ts">
  import { goto } from '$app/navigation';
  import { ArrowRight, CircleAlert, HeartPulse, House, Library, LoaderCircle, Search, Sparkles } from '@lucide/svelte';
  import type { Collection } from '$lib/api';
  import { startRun } from '$lib/runs';
  import { enterRun, journey, rememberRun, runPath } from '$lib/journey.svelte';

  let query = $state('');
  let collection = $state<Collection>('housing');
  let busy = $state(false);
  let error = $state('');
  const examples: Record<Collection, string> = {
    healthcare: 'Optimize healthcare in Iowa',
    housing: 'Identify barriers to income verification in Texas LIHTC housing',
    other: 'AI identity verification for private car sales in Kentucky',
  };
  $effect(() => { enterRun(null); journey.stage = 'audit'; });

  async function start() {
    if (busy) return;
    const goal = query.trim();
    if (!goal) { error = 'Enter a policy goal to start an analysis.'; return; }
    if (new TextEncoder().encode(goal).length > 2000) { error = 'The goal exceeds the 2,000-byte limit. Shorten it and try again.'; return; }
    busy = true; error = '';
    try {
      const id = await startRun(goal, collection);
      rememberRun(id);
      await goto(runPath(id));
    } catch (e) { error = e instanceof Error ? e.message : 'Unable to start the analysis.'; }
    finally { busy = false; }
  }
</script>

<svelte:head><title>DOGE Factory — Policy workbench</title><meta name="description" content="Explore policy barriers and review proposed amendments." /></svelte:head>
<div class="page-heading"><div><div class="eyebrow"><span></span> POLICY WORKBENCH</div><h1>Make room for <em>better policy.</em></h1><p>Find opportunities to remove barriers to innovation, and move promising ideas forward.</p></div><div class="heading-badge"><Sparkles size={15}/> FROM IDEA TO ACTION</div></div>
<section class="goal-card" aria-labelledby="goal-title">
  <div class="goal-intro"><div><div class="section-kicker">01 / DEFINE YOUR GOAL</div><h2 id="goal-title">What would you like to improve?</h2><p>Describe an outcome. We’ll look for policy provisions that may be getting in the way.</p></div><div class="goal-icon"><Search size={21}/></div></div>
  <form onsubmit={(e) => { e.preventDefault(); void start(); }}>
    <fieldset class="collection-picker"><legend>Policy collection <span>Choose one</span></legend><div class="collection-options">
      <label class:collection-selected={collection === 'healthcare'} class="collection-option"><input type="radio" name="collection" value="healthcare" bind:group={collection}/><span class="collection-icon"><HeartPulse size={18}/></span><span class="collection-copy"><strong>Healthcare</strong><small>Health &amp; healthcare policy</small></span><span class="collection-indicator" aria-hidden="true"></span></label>
      <label class:collection-selected={collection === 'housing'} class="collection-option"><input type="radio" name="collection" value="housing" bind:group={collection}/><span class="collection-icon"><House size={18}/></span><span class="collection-copy"><strong>Housing</strong><small>Housing &amp; assistance policy</small></span><span class="collection-indicator" aria-hidden="true"></span></label>
      <label class:collection-selected={collection === 'other'} class="collection-option"><input type="radio" name="collection" value="other" bind:group={collection}/><span class="collection-icon"><Library size={18}/></span><span class="collection-copy"><strong>Problem library</strong><small>Identity, benefits, procurement &amp; more</small></span><span class="collection-indicator" aria-hidden="true"></span></label>
    </div></fieldset>
    <label class="sr-only" for="goal">Policy goal</label><div class="input-wrap"><Search size={19}/><textarea id="goal" rows="3" maxlength="2000" bind:value={query} placeholder={'e.g. ' + examples[collection]}></textarea><button class="primary-button" disabled={busy}>{#if busy}<LoaderCircle class="spin" size={17}/> Starting{:else}Analyze goal <ArrowRight size={17}/>{/if}</button></div>
    <div class="input-meta"><span>Try: <button type="button" class="example" onclick={() => query = examples[collection]}>“{examples[collection]}”</button></span><span>{new TextEncoder().encode(query).length} / 2,000 bytes</span></div>
  </form>
  <div class="scope-note"><span class="scope-dot"></span> Analysis searches a bounded set of sources. Runs are saved locally and continue while the backend is running; find them in Problem queue.</div>
</section>
{#if error}<div class="alert-error" role="alert"><CircleAlert size={18}/><div><strong>Could not start analysis</strong><p>{error}</p></div><button onclick={start}>Try again</button></div>{/if}
