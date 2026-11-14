<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/state';
  import { mobilizePath } from '$lib/journey.svelte';
  import MobilizeView from '$lib/mobilize/MobilizeView.svelte';

  // Old links used /mobilize?run=<id>; send them to the run's Mobilize page.
  const legacyRun = page.url.searchParams.get('run');
  onMount(() => { if (legacyRun) void goto(mobilizePath(legacyRun), { replaceState: true }); });
</script>

<!-- Demo sandbox: Mobilize with the Kentucky fixture, no analysis run needed. -->
<svelte:head><title>DOGE Factory — Mobilize demo</title></svelte:head>
{#if !legacyRun}<MobilizeView runId={null} />{/if}
