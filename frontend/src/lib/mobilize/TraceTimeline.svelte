<script lang="ts">
  import { fmtDuration, type RunState } from './run';

  let { run, now }: { run: RunState; now: number } = $props();

  const LABEL = { input: 'Draft input', plan: 'Plan', persona: 'Persona', voice: 'Voice cast', assemble: 'Assemble', ready: 'Ready', error: 'Error' };
  const t0 = $derived(run.start ?? now);
  const total = $derived(Math.max((run.end ?? now) - t0, 1));
  const clock = (t: number) => new Date(t).toLocaleTimeString([], { hour12: false }) + '.' + String(t % 1000).padStart(3, '0');

  let list: HTMLDivElement;
  $effect(() => {
    void run.rows.length;
    if (list) list.scrollTop = list.scrollHeight;
  });
</script>

<div class="mz-trace" bind:this={list}>
  {#if !run.rows.length}
    <p class="mz-empty">{run.legislators.length
      ? 'Agents restored from the last run. Build again to see a fresh trace.'
      : 'Build agents to watch each step: persona synthesis, voice casting and agent assembly.'}</p>
  {:else}
    {#each run.rows as row}
      {@const end = row.end ?? now}
      {@const span = row.end !== row.start}
      <div class="mz-trow {row.status}" data-stage={row.stage}>
        <span class="mz-time">{clock(row.start)}</span>
        <span class="mz-stage"><i></i>{LABEL[row.stage]}</span>
        <span class="mz-msg" title={row.message}>{row.message}</span>
        <span class="mz-lane"><span class="mz-bar" class:open={row.end === null}
          style="left:{((row.start - t0) / total) * 100}%;width:{span ? `max(${((end - row.start) / total) * 100}%, 3px)` : '3px'}"></span></span>
        <span class="mz-dur">{span ? fmtDuration(end - row.start) : ''}</span>
      </div>
    {/each}
  {/if}
</div>
