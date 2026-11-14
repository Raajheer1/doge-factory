<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { ArrowLeft, ArrowRight, CheckCircle2, CircleAlert, FlaskConical, Hammer, LoaderCircle, PhoneCall } from '@lucide/svelte';
  import type { Handoff } from '$lib/api';
  import ExpandableText from '$lib/ExpandableText.svelte';
  import { loadHandoff } from '$lib/runs';
  import { getConversation, getDemoInput, getStatus, listAgents, placeCall, runPipeline, type DemoInput, type VoiceAgent, type VoiceStatus } from '$lib/voice';
  import { FINAL_CALL_STATUSES, allAgents, applyEvent, emptyRun, fmtDuration, restoreRun } from '$lib/mobilize/run';
  import AgentGraph from '$lib/mobilize/AgentGraph.svelte';
  import TraceTimeline from '$lib/mobilize/TraceTimeline.svelte';
  import AgentInspector, { type CallState } from '$lib/mobilize/AgentInspector.svelte';
  import { enterRun, journey, redlinePath } from '$lib/journey.svelte';
  import './mobilize.css';

  // null = demo sandbox (/mobilize) with the Kentucky fixture as input.
  let { runId }: { runId: string | null } = $props();

  // The Mobilize API keeps one roster; remember which run it was built for so
  // another run's page doesn't show it.
  const ROSTER_KEY = 'doge-agents-run';
  const rosterOwner = () => { try { return localStorage.getItem(ROSTER_KEY); } catch { return null; } };
  const setRosterOwner = (id: string) => { try { localStorage.setItem(ROSTER_KEY, id); } catch { /* optional */ } };

  let status = $state<VoiceStatus | null>(null);
  let demo = $state<DemoInput | null>(null);
  let handoff = $state<Handoff | null>(null);
  let loadError = $state('');
  let handoffError = $state('');
  let buildError = $state('');
  let count = $state(3);
  let source = $state<'sample' | 'claude'>('sample');
  let run = $state(emptyRun());
  let selectedId = $state<string | null>(null);
  let call = $state<CallState | null>(null);
  let now = $state(Date.now());
  let ticker: ReturnType<typeof setInterval> | undefined;
  let poll: ReturnType<typeof setTimeout> | undefined;
  let disposed = false;

  const agents = $derived(allAgents(run));
  const selected = $derived(agents.find((a) => a.id === selectedId) ?? null);
  const building = $derived(run.phase === 'running');
  const liveAgentId = $derived(call && !call.error && !FINAL_CALL_STATUSES.has(call.data?.status ?? 'initiated') ? call.agentId : null);
  const finding = $derived(handoff?.finding ?? null);
  const proposalTitle = $derived(finding?.provision.title ?? demo?.policy.title ?? '');
  const jurisdiction = $derived(finding?.provision.jurisdiction || demo?.policy.state || '');
  // A handoff with people gets one generated agent per person instead of the fixed set.
  const people = $derived(handoff?.people ?? []);
  const campaign = $derived(source === 'claude' && people.length > 0);
  const official = $derived(handoff?.people?.find((p) => p.type === 'official' && p.state));
  const lobbyist = $derived(handoff?.people?.find((p) => p.type === 'lobbyist' && p.clients?.length));
  // A campaign targets everyone in the handoff; otherwise the first official, else the demo target.
  const target = $derived(campaign ? `${people.length} people` : official ? `${official.title || ''} ${official.name}`.trim() : demo ? `${demo.legislator.title} ${demo.legislator.name}` : '');
  const sourceLabel = $derived(campaign ? status?.planner_model ?? 'Planner' : source === 'claude' ? status?.persona_model ?? 'Claude' : 'Sample library');
  const planned = $derived(campaign ? people.length : count);
  const totalCalls = $derived(agents.reduce((sum, a) => sum + a.conversations.length, 0));

  $effect(() => { journey.agentsBuilt = agents.length > 0; });

  onMount(async () => {
    enterRun(runId);
    journey.stage = 'mobilize';
    if (runId) source = 'claude'; // sample personas are written for the Kentucky demo
    try {
      [status, demo] = await Promise.all([getStatus(), getDemoInput()]);
      journey.health = status;
      if (rosterOwner() === (runId ?? 'demo')) run = restoreRun(await listAgents());
    } catch (e) { loadError = e instanceof Error ? e.message : 'Could not load the Mobilize API.'; }
    if (runId) {
      try {
        handoff = await loadHandoff(runId);
        Object.assign(journey, { query: handoff.query, analysisDone: true, hasFindings: true, approved: true });
      } catch (e) { handoffError = e instanceof Error ? e.message : 'Could not load the approved proposal.'; }
    }
  });
  onDestroy(() => { disposed = true; clearInterval(ticker); clearTimeout(poll); journey.health = null; });

  async function build() {
    if (building || (runId && !handoff)) return;
    buildError = '';
    clearTimeout(poll);
    call = null;
    selectedId = null;
    run = { ...emptyRun(planned), phase: 'running' };
    setRosterOwner(runId ?? 'demo');
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
    if (!window.confirm(`Place a real call to ${agent.request.to_number}? The caller is synthetic; verify the target, consent and applicable disclosure requirements first.`)) return;
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
    let failures = 0;
    const tick = async () => {
      if (disposed || call?.conversationId !== conversationId) return;
      try {
        const data = await getConversation(conversationId);
        if (disposed || call?.conversationId !== conversationId) return;
        call.data = data;
        failures = 0;
      } catch {
        if (disposed || call?.conversationId !== conversationId) return;
        if (++failures >= 5) { call.error = 'Could not load the call status. Select the call again to retry.'; return; }
      }
      if (!FINAL_CALL_STATUSES.has(call.data?.status ?? '')) poll = setTimeout(tick, 2000);
    };
    void tick();
  }
</script>

      <div class="page-heading">
        <div><div class="eyebrow"><span></span> STEP 3 · MOBILIZE</div><h1>Turn the proposal into <em>a conversation.</em></h1>
          <p>Build persona voice agents from the approved proposal, watch every step, then call from any of them.</p></div>
        {#if runId}<a class="back-link" href={redlinePath(runId, finding?.id)}><ArrowLeft size={14} /> Back to redline</a>
        {:else}<a class="back-link" href="/"><ArrowLeft size={14} /> Start with a pitch</a>{/if}
      </div>

      {#if loadError}<div class="alert-error" role="alert"><CircleAlert size={18} /><div><strong>Mobilize API unavailable</strong><p>{loadError}</p></div></div>{/if}

      <section class="mz-input">
        <div class="mz-card">
          <div class="section-kicker">{runId ? 'APPROVED REDLINE' : 'DEMO PROPOSAL'}</div>
          {#if finding}
            <h2>{finding.provision.title}</h2>
            <p class="mz-meta">{finding.provision.jurisdiction || 'Jurisdiction unavailable'} · {finding.provision.citation || 'Citation unavailable'}</p>
            {#if handoff?.query}<details class="mz-goal"><summary>View analysis goal</summary><p>{handoff.query}</p></details>{/if}
            {#if finding.provision.synthetic}<div class="synthetic-banner"><FlaskConical size={17} /><span><strong>Synthetic demo data.</strong> This source and its generated outputs are synthetic.</span></div>{/if}
            <div class="mz-input-grid">
              <div><div class="mini-label">POTENTIAL BARRIER</div><ExpandableText text={finding.barrier}/></div>
              <div><div class="mini-label">DESIRED CHANGE</div><ExpandableText text={finding.desired_change}/></div>
            </div>
            {#if handoff}
              <div class="mz-handoff">
                <div class="mz-handoff-title"><CheckCircle2 size={16} /><span class="mini-label">ANALYSIS HANDOFF</span><span class="mz-pill">{handoff.status.replaceAll('_', ' ').toUpperCase()}</span></div>
                <p>{handoff.message}</p>
                {#if handoff.status === 'simulated'}<p class="mz-note">The analysis API simulated this handoff and placed no calls. Calls below are placed by the Mobilize service, to allowlisted numbers only.</p>{/if}
                <details><summary>View complete returned handoff</summary><pre class="mz-pre">{JSON.stringify(handoff, null, 2)}</pre></details>
              </div>
            {/if}
          {:else if runId && !handoffError}
            <p class="mz-muted"><LoaderCircle class="spin" size={15} /> Loading the approved proposal…</p>
          {:else if runId && handoffError}
            <p class="mz-error">{handoffError}</p><p class="mz-note">An approved handoff is required to build agents for this run. Return to the redline and try again.</p>
          {:else if demo}
            <h2>{demo.policy.title}</h2>
            <p class="mz-meta">{demo.policy.state} · demo input</p>
            <p class="mz-prose">{demo.policy.summary}</p>
            <a class="mz-link" href="/">Pitch a product to mobilize a real proposal <ArrowRight size={14} /></a>
          {/if}
        </div>
        {#if people.length}
          <div class="mz-card">
            <div class="section-kicker">CALL TARGETS <span class="mz-pill">{people.length} FROM THE GRAPH</span></div>
            <dl class="mz-kv">
              {#each people as p}<dt>{p.type}</dt><dd>{p.title ? `${p.title} ` : ''}{p.name}<small>{p.relevance.replaceAll('_', ' ')}{p.clients?.length ? ` · for ${p.clients.join(', ')}` : ''}</small></dd>{/each}
              <dt>Every call rings</dt><dd>{status?.allowed_numbers.join(', ') || demo?.to_number}</dd>
            </dl>
            <p class="mz-note">In Live mode, each person gets a purpose-built agent. Every call rings your phone and you play them.</p>
          </div>
        {:else if demo}
          <div class="mz-card">
            <div class="section-kicker">CALL ROLES <span class="mz-pill">LOCAL DEMO</span></div>
            <dl class="mz-kv">
              <dt>Legislator</dt><dd>{target}<small>{official ? `${official.district || official.state} · source status: ${official.verified_at}` : 'Demo placeholder'}</small></dd>
              <dt>Lobbyist</dt><dd>{lobbyist?.name || demo.lobbyist.name}<small>{lobbyist ? `${lobbyist.organization || lobbyist.clients?.join(', ')} · source status: ${lobbyist.verified_at}` : 'Demo placeholder'}</small></dd>
              <dt>Dialed number</dt><dd>{demo.to_number}<small>{status?.allowed_numbers.includes(demo.to_number) ? 'Allowlisted' : 'Not allowlisted; calls will be blocked'}</small></dd>
            </dl>
            <p class="mz-note">These are roles for the demonstration, not the numbers being dialed. Missing roles use placeholders; verify sourced roles before any outreach.</p>
          </div>
        {/if}
      </section>

      <section class="mz-build">
        <div class="section-heading mz-build-head">
          <div><div class="section-kicker">BUILD VOICE AGENTS</div><h2>Agent graph</h2><p>Each persona becomes a caller built on an ElevenLabs agent template. Select one to call.</p></div>
          <div class="mz-controls">
            {#if campaign}<div class="mz-field"><span>Agents</span><output class="mz-fixed">{people.length}, one per person</output></div>
            {:else}<div class="mz-field"><span>Personas</span>
              <div class="mz-stepper"><button aria-label="Fewer personas" disabled={building} onclick={() => (count = Math.max(1, count - 1))}>−</button><output>{count}</output><button aria-label="More personas" disabled={building} onclick={() => (count = Math.min(status?.max_personas ?? 4, count + 1))}>+</button></div></div>{/if}
            <div class="mz-seg" role="radiogroup" aria-label="Persona source">
              <button role="radio" aria-checked={source === 'sample'} class:on={source === 'sample'} disabled={building} onclick={() => (source = 'sample')} title="Pre-written personas, no API cost">Sample</button>
              <button role="radio" aria-checked={source === 'claude'} class:on={source === 'claude'} disabled={building} onclick={() => (source = 'claude')} title="Generate agents live with a model; uses API credits">Live</button>
            </div>
            <button class="primary-button" disabled={building || !demo || (!!runId && !handoff)} onclick={build}>
              {#if building}<LoaderCircle class="spin" size={16} /> Building…{:else}<Hammer size={16} /> Build voice agents{/if}
            </button>
          </div>
        </div>
        {#if source === 'sample' && finding}<p class="mz-note warn">Sample personas were written for the Kentucky permit demo. Use Claude to fit them to this proposal.</p>{/if}
        {#if buildError}<div class="action-error" role="alert">{buildError}</div>{/if}

        <div class="mz-workspace" id="calls">
          <div class="mz-card mz-graph-card">
            <div class="mz-card-bar">
              <span class="mini-label">AGENT GRAPH</span>
              {#if run.start}<span class="mz-runmeta"><span class="status-dot" class:active-dot={building}></span>{building ? 'Building' : run.phase === 'error' ? 'Failed' : 'Complete'} · {fmtDuration((run.end ?? now) - run.start)} · {run.rows.length} events · {agents.length} agents</span>{/if}
            </div>
            {#if demo}
              <AgentGraph {run} {planned} {campaign} {sourceLabel} {proposalTitle} {jurisdiction} {target} {selectedId} {liveAgentId} onselect={select} />
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
              <div class="mz-placeholder"><PhoneCall size={22} /><strong>No agents yet</strong><p>Build voice agents to turn this proposal into persona callers, then select one to place a call.</p></div>
            {/if}
          </aside>
        </div>

        <div class="mz-card mz-trace-card">
          <div class="mz-card-bar"><span class="mini-label">TRACE</span><span class="mz-runmeta">Every pipeline step, with timing</span></div>
          <TraceTimeline {run} {now} />
        </div>
      </section>
