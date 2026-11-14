<script lang="ts">
  import { page } from '$app/state';
  import MobilizeView from '$lib/mobilize/MobilizeView.svelte';
</script>

<svelte:head><title>DOGE Factory — Mobilize</title></svelte:head>
{#key page.params.id}<MobilizeView runId={page.params.id ?? null} />{/key}
