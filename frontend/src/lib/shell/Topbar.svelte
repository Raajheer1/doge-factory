<script lang="ts">
  import { STAGES, journey, runPath } from '$lib/journey.svelte';

  const stageLabel = $derived(journey.stage === 'queue' ? 'Problem queue' : STAGES.find((s) => s.key === journey.stage)?.label ?? '');
  const shortQuery = $derived(journey.query.length > 48 ? journey.query.slice(0, 47) + '…' : journey.query);
</script>

<header class="topbar">
  <nav class="breadcrumb" aria-label="Breadcrumb">
    <a href="/">DOGE Factory</a>
    {#if journey.runId && shortQuery}<span>/</span><a href={runPath(journey.runId)} title={journey.query}>{shortQuery}</a>{/if}
    <span>/</span><strong>{stageLabel}</strong>
  </nav>
  <div class="top-right">
    {#if journey.health}
      {@const h = journey.health}
      <span class="health"><i class:ok={h.elevenlabs_key}></i>ELEVENLABS</span>
      <span class="health"><i class:ok={h.phone_number}></i>PHONE</span>
      <span class="health"><i class:ok={h.allowed_numbers.length > 0}></i>DIALS {h.allowed_numbers.join(', ') || 'NOBODY'}</span>
      <span class="top-divider"></span>
    {/if}
    <span class="demo-dot"></span> LOCAL DEMO <span class="top-divider"></span><span class="top-avatar">DF</span>
  </div>
</header>
