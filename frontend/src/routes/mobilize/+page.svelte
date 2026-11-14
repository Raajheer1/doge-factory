<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { page } from '$app/state';
  import { ArrowLeft, CircleAlert, FileSearch, FlaskConical, Hammer, Layers3, LoaderCircle, Megaphone, PhoneCall, ShieldCheck } from '@lucide/svelte';
  import { mobilize, type Handoff } from '$lib/api';
  import { getConversation, getDemoInput, getStatus, listAgents, placeCall, runPipeline, type DemoInput, type VoiceAgent, type VoiceStatus } from '$lib/voice';
  import { FINAL_CALL_STATUSES, allAgents, applyEvent, emptyRun, fmtDuration, restoreRun } from '$lib/mobilize/run';
  import AgentGraph from '$lib/mobilize/AgentGraph.svelte';
  import TraceTimeline from '$lib/mobilize/TraceTimeline.svelte';
  import AgentInspector, { type CallState } from '$lib/mobilize/AgentInspector.svelte';
  import '../app.css';
  import './mobilize.css';

  const runId = page.url.searchParams.get('run');

  let status = $state<VoiceStatus | null>(null);
  let demo = $state<DemoInput | null>(null);
  let handoff = $state<Handoff | null>(null);
  let loadError = $state('');
  let handoffError = $state('');
  let buildError = $state('');
  let count = $state(3);
  let source = $state<'sample' | 'claude'>(runId ? 'claude' : 'sample');
  let run = $state(emptyRun());
  let selectedId = $state<string | null>(null);
  let call = $state<CallState | null>(null);
  let now = $state(Date.now());
  let ticker: ReturnType<typeof setInterval> | undefined;
  let poll: ReturnType<typeof setTimeout> | undefined;

  const agents = $derived(allAgents(run));
  const selected = $derived(agents.find((a) => a.id === selectedId) ?? null);
  const building = $derived(run.phase === 'running');
  const liveAgentId = $derived(call && !call.error && !FINAL_CALL_STATUSES.has(call.data?.status ?? 'initiated') ? call.agentId : null);
  const finding = $derived(handoff?.finding ?? null);
  const proposalTitle = $derived(finding?.provision.title ?? demo?.policy.title ?? '');
  const jurisdiction = $derived(finding?.provision.jurisdiction || demo?.policy.state || '');
  const target = $derived(demo ? `${demo.legislator.title} ${demo.legislator.name}` : '');
  const sourceLabel = $derived(source === 'claude' ? status?.persona_model ?? 'Claude' : 'Sample library');
  const totalCalls = $derived(agents.reduce((sum, a) => sum + a.conversations.length, 0));

  onMount(async () => {
    try {
      [status, demo] = await Promise.all([getStatus(), getDemoInput()]);
      run = restoreRun(await listAgents());
    } catch (e) { loadError = e instanceof Error ? e.message : 'Could not load the Mobilize API.'; }
    if (runId) {
      try { handoff = await mobilize(runId); }
      catch (e) { handoffError = e instanceof Error ? e.message : 'Could not load the approved proposal.'; }
    }
  });
  onDestroy(() => { clearInterval(ticker); clearTimeout(poll); });

  async function build() {
    if (building) return;
    buildError = '';
    clearTimeout(poll);
    call = null;
    selectedId = null;
    run = { ...emptyRun(count), phase: 'running' };
    ticker = setInterval(() => (now = Date.now()), 120);
    try {
      await runPipeline({ personas: count, source, handoff }, (ev) => applyEvent(run, ev));
    } catch (e) {
      buildError = e instanceof Error ? e.message : 'The pipeline failed.';
      run.phase = 'error';
    } finally {
      clearInterval(ticker);
      now = Date.now();
      run.end ??= now;
      if (run.phase === 'running') run.phase = 'done';
      if (run.phase === 'done' && run.legislators[0]) select(run.legislators[0].id);
    }
  }

  function select(id: string) {
    selectedId = id;
    const agent = agents.find((a) => a.id === id);
    if (call?.agentId !== id) {
      clearTimeout(poll);
      call = null;
      if (agent?.conversations.length) watch(agent, agent.conversations.at(-1)!);
    }
  }

  async function dial(agent: VoiceAgent) {
    clearTimeout(poll);
    call = { agentId: agent.id, conversationId: null, data: null, error: '' };
    try {
      const res = await placeCall(agent.id);
      agent.conversations.push(res.conversation_id);
      watch(agent, res.conversation_id);
    } catch (e) {
      if (call) call.error = e instanceof Error ? e.message : 'The call could not be placed.';
    }
  }

  function watch(agent: VoiceAgent, conversationId: string) {
    clearTimeout(poll);
    call = { agentId: agent.id, conversationId, data: null, error: '' };
    const tick = async () => {
      if (call?.conversationId !== conversationId) return;
      try { call.data = await getConversation(conversationId); } catch { /* The conversation can 404 right after dialing. */ }
      if (!FINAL_CALL_STATUSES.has(call.data?.status ?? '')) poll = setTimeout(tick, 2000);
    };
    void tick();
  }
</script>

<svelte:head><title>DOGE Factory — Mobilize</title></svelte:head>
<div class="app-shell">
  <aside class="sidebar">
    <a class="brand" href="/" aria-label="DOGE Factory home"><span class="brand-mark"><Layers3 size={19} strokeWidth={2.2} /></span><span>DOGE<span class="brand-light">FACTORY</span><small>POLICY WORKBENCH</small></span></a>
    <div class="side-section">WORKSPACE</div>
    <a class="side-link" href="/"><FileSearch size={17} /> Policy analysis</a>
    <div class="side-active"><Megaphone size={17} /> Mobilize <span class="side-dot"></span></div>
    <div class="side-bottom"><div class="side-note"><span class="note-icon"><ShieldCheck size={17} /></span><div><strong>Synthetic callers</strong><p>Personas are generated. Calls only ring allowlisted numbers.</p></div></div></div>
  </aside>
  <main>
    <header class="topbar">
      <div class="breadcrumb">Workspace <span>/</span> <strong>Mobilize</strong></div>
      <div class="top-right">
        {#if status}
          <span class="mz-health"><i class:ok={status.elevenlabs_key}></i>ElevenLabs</span>
          <span class="mz-health"><i class:ok={status.phone_number}></i>Phone number</span>
          <span class="mz-health"><i class:ok={status.allowed_numbers.length > 0}></i>Dials {status.allowed_numbers.join(', ') || 'nobody'}</span>
        {/if}
      </div>
    </header>

    <div class="content">
      <div class="page-heading">
        <div><div class="eyebrow"><span></span> MOBILIZE</div><h1>Turn a proposal into <em>a conversation.</em></h1>
          <p>Build persona voice agents from an approved proposal, watch every step, then call from any of them.</p></div>
        <div class="heading-badge"><PhoneCall size={15} /> STEP 03 OF 03</div>
      </div>

      {#if loadError}<div class="alert-error" role="alert"><CircleAlert size={18} /><div><strong>Mobilize API unavailable</strong><p>{loadError}</p></div></div>{/if}

      <section class="mz-input">
        <div class="mz-card">
          <div class="section-kicker">01 / APPROVED PROPOSAL</div>
          {#if finding}
            <h2>{finding.provision.title}</h2>
            <p class="mz-meta">{finding.provision.jurisdiction || 'Jurisdiction unavailable'} · {finding.provision.citation || 'Citation unavailable'} · Goal: {handoff?.query}</p>
            {#if finding.provision.synthetic}<div class="synthetic-banner"><FlaskConical size={17} /><span><strong>Synthetic demo data.</strong> This source and its generated outputs are synthetic.</span></div>{/if}
            <div class="mz-input-grid">
              <div><div class="mini-label">POTENTIAL BARRIER</div><p>{finding.barrier}</p></div>
              <div><div class="mini-label">DESIRED CHANGE</div><p>{finding.desired_change}</p></div>
            </div>
          {:else if runId && !handoffError}
            <p class="mz-muted"><LoaderCircle class="spin" size={15} /> Loading the approved proposal…</p>
          {:else if demo}
            {#if handoffError}<p class="mz-error">{handoffError}</p>{/if}
            <h2>{demo.policy.title}</h2>
            <p class="mz-meta">{demo.policy.state} · demo input</p>
            <p class="mz-prose">{demo.policy.summary}</p>
            <a class="mz-link" href="/"><ArrowLeft size={14} /> Approve a finding in Policy analysis to mobilize real Draft output</a>
          {/if}
        </div>
        {#if demo}
          <div class="mz-card">
            <div class="section-kicker">CALL TARGETS <span class="mz-pill">DEMO</span></div>
            <dl class="mz-kv">
              <dt>Legislator</dt><dd>{target}<small>{finding ? `${jurisdiction}'s 13th Senate District` : demo.legislator.district}</small></dd>
              <dt>Lobbyist</dt><dd>{demo.lobbyist.name}<small>{demo.lobbyist.firm}</small></dd>
              <dt>Every call rings</dt><dd>{status?.allowed_numbers.join(', ') || demo.to_number}</dd>
            </dl>
            <p class="mz-note">Targets aren't in the Draft handoff yet, so they're placeholders. You play all of them.</p>
          </div>
        {/if}
      </section>

      <section class="mz-build">
        <div class="section-heading mz-build-head">
          <div><div class="section-kicker">02 / BUILD &amp; CALL</div><h2>Agent graph</h2><p>Each persona becomes a caller built on an ElevenLabs agent template.</p></div>
          <div class="mz-controls">
            <div class="mz-field"><span>Personas</span>
              <div class="mz-stepper"><button aria-label="Fewer personas" disabled={building} onclick={() => (count = Math.max(1, count - 1))}>−</button><output>{count}</output><button aria-label="More personas" disabled={building} onclick={() => (count = Math.min(status?.max_personas ?? 4, count + 1))}>+</button></div></div>
            <div class="mz-seg" role="radiogroup" aria-label="Persona source">
              <button role="radio" aria-checked={source === 'sample'} class:on={source === 'sample'} disabled={building} onclick={() => (source = 'sample')} title="Pre-written personas, no API cost">Sample</button>
              <button role="radio" aria-checked={source === 'claude'} class:on={source === 'claude'} disabled={building} onclick={() => (source = 'claude')} title="Generate personas live; uses API credits">Claude</button>
            </div>
            <button class="primary-button" disabled={building || !demo} onclick={build}>
              {#if building}<LoaderCircle class="spin" size={16} /> Building…{:else}<Hammer size={16} /> Build agents{/if}
            </button>
          </div>
        </div>
        {#if source === 'sample' && finding}<p class="mz-note warn">Sample personas were written for the Kentucky permit demo. Use Claude to fit them to this proposal.</p>{/if}
        {#if buildError}<div class="action-error" role="alert">{buildError}</div>{/if}

        <div class="mz-workspace">
          <div class="mz-card mz-graph-card">
            <div class="mz-card-bar">
              <span class="mini-label">AGENT GRAPH</span>
              {#if run.start}<span class="mz-runmeta"><span class="status-dot" class:active-dot={building}></span>{building ? 'Building' : run.phase === 'error' ? 'Failed' : 'Complete'} · {fmtDuration((run.end ?? now) - run.start)} · {run.rows.length} events · {agents.length} agents</span>{/if}
            </div>
            {#if demo}
              <AgentGraph {run} planned={count} {sourceLabel} {proposalTitle} {jurisdiction} {target} {selectedId} {liveAgentId} onselect={select} />
            {/if}
          </div>
          <aside class="mz-card mz-inspector">
            {#if selected}
              <AgentInspector agent={selected} {call} ondial={dial} onwatch={watch} />
            {:else if agents.length}
              <div class="mz-summary">
                <div class="mini-label">RUN SUMMARY</div>
                <div class="mz-stats">
                  <div><strong>{agents.length}</strong><span>voice agents</span></div>
                  <div><strong>{run.legislators.length}</strong><span>personas</span></div>
                  <div><strong>{run.start && run.end ? fmtDuration(run.end - run.start) : '—'}</strong><span>build time</span></div>
                  <div><strong>{totalCalls}</strong><span>calls placed</span></div>
                </div>
                <p class="mz-muted mz-center">Select an agent in the graph to inspect it and place a call.</p>
              </div>
            {:else}
              <div class="mz-placeholder"><PhoneCall size={22} /><strong>No agents yet</strong><p>Build agents to turn this proposal into persona callers, then select one to inspect it and call.</p></div>
            {/if}
          </aside>
        </div>

        <div class="mz-card mz-trace-card">
          <div class="mz-card-bar"><span class="mini-label">TRACE</span><span class="mz-runmeta">Every pipeline step, with timing</span></div>
          <TraceTimeline {run} {now} />
        </div>
      </section>
      <footer><span>DOGE FACTORY <b> / </b> MOBILIZE</span><span>Synthetic personas, real conversations.</span></footer>
    </div>
  </main>
</div>
