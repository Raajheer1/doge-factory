<script lang="ts">
  export let text = '';
  export let limit = 320;

  $: cut = text.length > limit ? (text.lastIndexOf(' ', limit) > 0 ? text.lastIndexOf(' ', limit) : limit) : text.length;
  $: preview = text.slice(0, cut);
  $: remainder = text.slice(cut).trimStart();
</script>

<div class="expandable-text">
  <p>{preview}{remainder ? '…' : ''}</p>
  {#if remainder}
    <details><summary>Read more</summary><p>{remainder}</p></details>
  {/if}
</div>

<style>
  .expandable-text p { white-space: pre-wrap; overflow-wrap: anywhere; }
  details { margin-top: 7px; }
  summary { color: #397b53; cursor: pointer; font-size: 11px; font-weight: 700; width: fit-content; }
  summary:focus-visible { outline: 3px solid #8ebba4; outline-offset: 3px; }
  details p { margin-top: 8px !important; }
</style>
