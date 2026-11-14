<script lang="ts">
  import { page } from '$app/state';
  import AutopilotView from '$lib/autopilot/AutopilotView.svelte';
</script>

<svelte:head><title>DOGE Factory — Autopilot</title></svelte:head>

{#key page.params.id}
  <AutopilotView runId={page.params.id ?? ''} live={page.url.searchParams.get('live') === '1'} />
{/key}
