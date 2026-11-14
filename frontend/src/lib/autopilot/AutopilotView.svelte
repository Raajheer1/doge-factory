<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import ExpandableText from '$lib/ExpandableText.svelte';
  import { ArrowRight, Check, CircleAlert, FastForward, LoaderCircle, Pause, PhoneCall, Play, RotateCcw, Square, Zap } from '@lucide/svelte';
  import { AP_STAGES, Stopped, appendEvent, isFinished, loadLog, runAutopilot, type APEvent, type APStage } from '$lib/autopilot';
  import { enterRun, journey, mobilizePath, redlinePath } from '$lib/journey.svelte';
  import { loadRun, TERMINAL_STATUSES } from '$lib/runs';
  import type { Run } from '$lib/api';
  import './autopilot.css';

  let { runId, live }: { runId: string; live: boolean } = $props();

  let events = $state<APEvent[]>([]);
  let mode = $state<'live' | 'replay' | 'idle'>('idle');
  let paused = $state(false);
  let stopped = $state(false);
  let speed = $state(4);
  let error = $state('');
  let replayTimer: ReturnType<typeof setTimeout> | undefined;
  let recorded = $state<APEvent[]>([]);
  let actualRun = $state<Run | null>(null);
  let runError = $state('');
  let disposed = false;

  async function refreshRun() {
    try { const next = await loadRun(runId); if (!disposed) { actualRun = next; runError = ''; } }
    catch (e) { if (!disposed) runError = e instanceof Error ? e.message : 'Could not load this run.'; }
  }

  onMount(() => {
    enterRun(runId);
    journey.stage = 'autopilot';
    void refreshRun();
    recorded = loadLog(runId);
    // A live start only when asked (?live=1) and nothing was recorded yet; otherwise show the record.
    if (live && !recorded.length) startLive();
    else if (recorded.length) startReplay();
  });
  onDestroy(() => { disposed = true; stopped = true; clearTimeout(replayTimer); });

  async function startLive() {
    clearTimeout(replayTimer);
    mode = 'live'; paused = false; stopped = false; error = ''; events = [];
    try {
      await runAutopilot(runId, (e) => { events = [...events, e]; }, { paused: () => paused, stopped: () => stopped });
    } catch (e) {
      const stop = e instanceof Stopped;
      const ev: APEvent = { t: Date.now(), stage: current(), status: 'error', message: stop ? 'Stopped by you' : e instanceof Error ? e.message : 'Autopilot failed' };
      appendEvent(runId, ev);
      events = [...events, ev];
      if (!stop) error = ev.message;
    } finally {
      recorded = loadLog(runId);
      mode = 'idle';
      void refreshRun();
    }
  }

  function startReplay() {
    clearTimeout(replayTimer);
    recorded = loadLog(runId);
    mode = 'replay'; paused = false; events = [];
    step(0);
  }
  function step(i: number) {
    if (i >= recorded.length) { mode = 'idle'; return; }
    if (paused) { replayTimer = setTimeout(() => step(i), 200); return; }
    events = [...events, recorded[i]];
    const gap = i + 1 < recorded.length ? Math.min(recorded[i + 1].t - recorded[i].t, 8000) : 0;
    replayTimer = setTimeout(() => step(i + 1), gap / speed);
  }

  const byStage = $derived(Object.fromEntries(AP_STAGES.map((s) => [s.key, events.filter((e) => e.stage === s.key)])) as Record<APStage, APEvent[]>);
  function stateOf(stage: APStage): 'pending' | 'running' | 'done' | 'error' {
    const list = byStage[stage] ?? [];
    if (list.some((e) => e.status === 'error')) return 'error';
    if (list.some((e) => e.status === 'done')) return 'done';
    return list.length ? 'running' : 'pending';
  }
  function current(): APStage { return events.length ? events[events.length - 1].stage : 'audit'; }
  const lastData = (stage: APStage, k: string) => [...(byStage[stage] ?? [])].reverse().find((e) => e.data?.[k] !== undefined)?.data?.[k];

  const start = $derived(events[0]?.t ?? 0);
  const elapsed = $derived(events.length ? (events[events.length - 1].t - start) / 1000 : 0);
  const finished = $derived(isFinished(events));
  const audit = $derived([...(byStage.audit ?? [])].reverse().find((e) => e.data?.findings)?.data);
  const chosen = $derived(lastData('select', 'finding'));
  const redline = $derived((byStage.redline ?? []).find((e) => e.data?.proposed !== undefined)?.data);
  const handoff = $derived((byStage.handoff ?? []).find((e) => e.status === 'done')?.data);
  const personas = $derived((byStage.mobilize ?? []).filter((e) => e.data?.persona).map((e) => e.data!.persona));
  const agents = $derived((byStage.mobilize ?? []).filter((e) => e.data?.agent).map((e) => e.data!.agent));
  const callData = $derived([...(byStage.call ?? [])].reverse().find((e) => e.data?.transcript)?.data);
  const callAgent = $derived(lastData('call', 'agent'));
  const query = $derived(actualRun?.query ?? audit?.query ?? '');

  // Replay describes historical events; navigation reflects the current run,
  // never the progressively replayed approval state.
  $effect(() => {
    journey.query = query;
    if (actualRun) {
      journey.analysisDone = TERMINAL_STATUSES.includes(actualRun.status);
      journey.hasFindings = actualRun.findings.length > 0;
      journey.findingId = actualRun.selected_finding_id ?? null;
      journey.approved = !!actualRun.selected_finding_id;
    }
    journey.stage = 'autopilot';
  });

  const offset = (e: APEvent) => `+${((e.t - start) / 1000).toFixed(1)}s`;
  const relevanceLabel = (r: string) => r.replaceAll('_', ' ');
</script>

<section class="ap-head">
  <div>
    <div class="eyebrow"><span></span> AUTOPILOT</div>
    <h1>Autopilot <em>run.</em></h1>
    <p class="ap-meta">
      {#if mode === 'live'}<span class="ap-badge live"><Zap size={12} /> LIVE</span>
      {:else if mode === 'replay'}<span class="ap-badge replay"><FastForward size={12} /> REPLAY · {speed}×</span>
      {:else if finished}<span class="ap-badge">RECORDED RUN</span>{/if}
      {#if audit?.collection}<span>{audit.collection === 'other' ? 'Problem library' : audit.collection}</span>{/if}
      {#if events.length}<span>{elapsed.toFixed(1)}s elapsed</span>{/if}
    </p>
  </div>
  <div class="ap-controls">
    {#if mode === 'live'}
      <button class="ghost-button" onclick={() => (paused = !paused)}>{#if paused}<Play size={15} /> Resume{:else}<Pause size={15} /> Pause{/if}</button>
      <button class="ghost-button danger" onclick={() => (stopped = true)}><Square size={14} /> Stop</button>
    {:else if mode === 'replay'}
      <button class="ghost-button" onclick={() => (paused = !paused)}>{#if paused}<Play size={15} /> Play{:else}<Pause size={15} /> Pause{/if}</button>
      {#each [1, 4, 10] as s}<button class="speed" class:active={speed === s} onclick={() => (speed = s)}>{s}×</button>{/each}
    {:else}
      {#if recorded.length}<button class="ghost-button" onclick={startReplay}><RotateCcw size={15} /> Replay</button>{/if}
      <button class="primary-button" onclick={startLive}><Zap size={15} /> {recorded.length ? 'Run again live' : 'Start autopilot'}</button>
    {/if}
  </div>
</section>

{#if query}
  <section class="ap-goal" aria-label="Analysis goal"><span class="mini-label">ANALYSIS GOAL</span><ExpandableText text={query} limit={240}/></section>
{/if}

{#if runError}<div class="alert-error" role="alert"><CircleAlert size={18}/><div><strong>Could not load current run</strong><p>{runError} Recorded events may be out of date.</p></div><button onclick={refreshRun}>Retry</button></div>{/if}
{#if error}<div class="alert-error" role="alert"><CircleAlert size={18} /><div><strong>Autopilot stopped</strong><p>{error}</p></div></div>{/if}
{#if mode === 'idle' && !events.length}
  <div class="empty-state"><Zap size={22} /><h3>No autopilot record for this run yet</h3><p>Start autopilot to audit, draft and build agents. You will be asked to confirm approval and any real call.</p></div>
{/if}

<ol class="ap-timeline">
  {#each AP_STAGES as s, i}
    {@const st = stateOf(s.key)}
    {@const list = byStage[s.key] ?? []}
    <li id={`ap-${s.key}`} class={`ap-stage ${st}`}>
      <div class="ap-dot">{#if st === 'done'}<Check size={13} strokeWidth={3} />{:else if st === 'running'}<LoaderCircle class="spin" size={14} />{:else if st === 'error'}<CircleAlert size={13} />{:else}{i + 1}{/if}</div>
      <div class="ap-card">
        <div class="ap-card-head"><strong>{s.label}</strong>{#if list.length}<small>{offset(list[list.length - 1])}</small>{/if}</div>
        {#if list.length}<p class="ap-msg">{list[list.length - 1].message}</p>{/if}

        {#if s.key === 'audit' && audit}
          <div class="ap-stats"><span><b>{audit.retrieved}</b> retrieved</span><span><b>{audit.reviewed}</b> reviewed</span><span><b>{audit.findings.length}</b> barriers</span></div>
          {#if audit.findings.length}<ul class="ap-findings">{#each audit.findings as f}<li class:chosen={chosen?.id === f.id}><strong>{f.title}</strong><small>{f.citation} · {f.jurisdiction}</small></li>{/each}</ul>{/if}
        {/if}

        {#if s.key === 'select' && chosen}
          <div class="ap-quote"><small>{chosen.citation} · {chosen.jurisdiction}</small><p>“{chosen.source_passage}”</p><p class="ap-barrier">{chosen.barrier}</p></div>
        {/if}

        {#if s.key === 'redline' && redline}
          <div class="comparison"><div class="text-block"><div class="text-label"><span></span>ORIGINAL</div><p>{redline.original}</p></div>
            <div class="text-block proposed"><div class="text-label"><span></span>PROPOSED</div><p>{redline.proposed}</p></div></div>
          {#if redline.safeguards?.length}<p class="ap-small">Safeguards kept: {redline.safeguards.join(' · ')}</p>{/if}
        {/if}

        {#if s.key === 'handoff' && handoff}
          <p class="ap-spoken">“{handoff.spoken_title}”</p><p class="ap-small">{handoff.summary}</p>
          {#if handoff.affected_groups.length}<div class="ap-chips">{#each handoff.affected_groups as g}<span>{g}</span>{/each}</div>{/if}
          {#if handoff.people.length}
            <ul class="ap-people">{#each handoff.people as p}<li><span class={`ap-type ${p.type}`}>{p.type}</span><strong>{p.title ? `${p.title} ` : ''}{p.name}</strong><small>{p.state || p.organization || ''}{p.clients?.length ? ` · for ${p.clients.join(', ')}` : ''}</small><em>{relevanceLabel(p.relevance)}</em></li>{/each}</ul>
          {:else}<p class="ap-small">{handoff.notes || 'No people in the handoff; Mobilize uses demo targets.'}</p>{/if}
        {/if}

        {#if s.key === 'mobilize' && (personas.length || agents.length)}
          {#if personas.length}<ul class="ap-personas">{#each personas as p}<li><strong>{p.name}, {p.age}</strong><small>{p.occupation}</small><p>{p.personal_impact}</p></li>{/each}</ul>{/if}
          {#if agents.length}<div class="ap-chips">{#each agents as a}<span>{a.archetype ? `${a.archetype}: ` : ''}{a.caller} → {a.target}</span>{/each}</div>{/if}
        {/if}

        {#if s.key === 'call' && callAgent}
          <p class="ap-small"><PhoneCall size={13} /> {callAgent.caller} ({callAgent.archetype || callAgent.persona?.occupation || callAgent.kind}) calling {callAgent.target}{callData ? ` · ${callData.status}` : ''}{callData?.duration ? ` · ${callData.duration}s` : ''}</p>
          {#if callData?.transcript?.length}<div class="ap-transcript">{#each callData.transcript as turn}<p class={turn.role}><b>{turn.role === 'agent' ? callAgent.caller : 'You'}</b> {turn.message}</p>{/each}</div>{/if}
          {#if callData?.summary}<p class="ap-small"><b>Summary:</b> {callData.summary}</p>{/if}
        {/if}
      </div>
    </li>
  {/each}
</ol>

{#if finished}
  <div class="ap-links" aria-label="Continue reviewing this run">
    {#if chosen}<a class="ghost-button" href={redlinePath(runId, chosen.id)}>Review in Redline <ArrowRight size={14} /></a>{/if}
    {#if agents.length}<a class="ghost-button" href={mobilizePath(runId)}>Open Mobilize console <ArrowRight size={14} /></a>{/if}
  </div>
{/if}
