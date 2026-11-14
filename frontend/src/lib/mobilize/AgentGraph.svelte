<script lang="ts">
  import { tick } from 'svelte';
  import { Briefcase, Check, ClipboardList, FileText, Landmark, Mic, Phone, Sparkles, Wand } from '@lucide/svelte';
  import type { AgentKind, VoiceAgent } from '$lib/voice';
  import { avatarColor, initials, type NodeState, type RunState } from './run';

  let { run, planned, campaign = false, ticking = true, targets = [], sourceLabel, proposalTitle, jurisdiction, target, selectedId, liveAgentId, onselect }: {
    run: RunState; planned: number; campaign?: boolean; ticking?: boolean; targets?: string[]; sourceLabel: string; proposalTitle: string; jurisdiction: string; target: string;
    selectedId: string | null; liveAgentId: string | null; onselect: (id: string) => void;
  } = $props();

  const KIND: Record<AgentKind, { label: string; placeholder: string; icon: typeof Landmark }> = {
    legislator: { label: 'Constituent → Legislator', placeholder: 'Constituent caller', icon: Landmark },
    survey: { label: 'Constituent survey', placeholder: 'Survey caller', icon: ClipboardList },
    lobbyist: { label: 'Lobbyist pitch', placeholder: 'Lobbyist caller', icon: Briefcase },
    generated: { label: 'Generated caller', placeholder: 'Planned caller', icon: Wand },
  };

  let canvas: HTMLDivElement;
  let edges = $state<{ d: string; cls: string }[]>([]);

  const n = $derived(run.phase === 'idle' && !run.legislators.length ? planned : run.n);
  const doneCount = $derived(run.personas.filter((p) => p.state === 'done').length);
  // A campaign builds one generated agent per person, with no fixed survey or lobbyist rows.
  const orgRows = $derived<{ kind: AgentKind; agent: VoiceAgent | null; row: number }[]>(campaign ? [] : [
    { kind: 'survey', agent: run.survey, row: n + 2 },
    { kind: 'lobbyist', agent: run.lobbyist, row: n + 3 },
  ]);

  function edgeClass(s: NodeState | undefined) {
    return s === 'running' ? 'active' : s === 'done' || s === 'error' ? 'done' : '';
  }

  function computeEdges() {
    if (!canvas) return;
    const list: [string, string, string][] = [
      ['input', 'synth', run.synthState !== 'pending' ? 'done' : run.inputState === 'done' ? 'active' : ''],
    ];
    for (let i = 0; i < n; i++) {
      const slot = run.personas[i];
      list.push(['synth', `p${i}`, edgeClass(slot?.state)]);
      list.push([`p${i}`, `a${i}`, run.legislators[i] ? 'done' : slot?.state === 'done' ? 'active' : '']);
    }
    const personasDone = run.personas.length === n && run.personas.every((p) => p.state === 'done') && run.phase === 'running';
    if (!campaign) {
      list.push(['input', 'survey', run.survey ? 'done' : personasDone ? 'active' : '']);
      list.push(['input', 'lobbyist', run.lobbyist ? 'done' : personasDone && run.survey ? 'active' : '']);
    }

    const box = canvas.getBoundingClientRect();
    const rect = (key: string) => canvas.querySelector<HTMLElement>(`[data-node="${key}"]`)?.getBoundingClientRect();
    edges = list.flatMap(([from, to, cls]) => {
      const a = rect(from), b = rect(to);
      if (!a || !b) return [];
      const x1 = a.right - box.left + canvas.scrollLeft, y1 = a.top + a.height / 2 - box.top + canvas.scrollTop;
      const x2 = b.left - box.left + canvas.scrollLeft, y2 = b.top + b.height / 2 - box.top + canvas.scrollTop;
      const dx = (x2 - x1) / 2;
      return [{ d: `M${x1},${y1} C${x1 + dx},${y1} ${x2 - dx},${y2} ${x2},${y2}`, cls }];
    });
  }

  // A ticking clock on the node being planned, so long reasoning visibly runs.
  let clock = $state(Date.now());
  $effect(() => {
    if (runningIndex < 0 || !ticking) return;
    const id = setInterval(() => (clock = Date.now()), 500);
    return () => clearInterval(id);
  });
  // Replays fold in events with their recorded times, so only a live build ticks.
  const secs = (from?: number) => (from && ticking ? `${Math.max(0, Math.round((clock - from) / 1000))}s` : '');

  // Keep the node being planned in view while the graph scrolls.
  const runningIndex = $derived(run.personas.findIndex((p) => p.state === 'running'));
  $effect(() => {
    const i = runningIndex;
    if (i < 0 || !canvas) return;
    void tick().then(() => {
      const el = canvas.querySelector<HTMLElement>(`[data-node="p${i}"]`);
      if (el) canvas.scrollTo({ top: Math.max(0, el.offsetTop - 60), behavior: 'smooth' });
    });
  });
  const tail = (s: string, n = 240) => (s.length > n ? '…' + s.slice(-n) : s);
  const thought = (text: string) => tail(text.replaceAll('**', '').trim());
  // The plan streams as JSON; show the field being written, in words.
  const FIELD: Record<string, string> = { caller_name: 'Caller', occupation: 'Occupation', caller_role: 'Who they are', background: 'Background', personal_stake: 'Why they care', goal: 'Goal', talking_points: 'Talking points', objections: 'Objections', first_message: 'Opening line' };
  function drafting(json: string): string {
    const keys = [...json.matchAll(/"(\w+)":/g)];
    const last = keys.at(-1);
    if (!last || !(last[1] in FIELD)) return '';
    const value = json.slice(last.index! + last[0].length).replace(/^[\s\[]*"?/, '').replaceAll('","', ' · ').replace(/["\]},]+\s*$/, '').replaceAll('\\"', '"');
    return `${FIELD[last[1]]}: ${tail(value, 200)}`;
  }

  $effect(() => {
    $state.snapshot(run);
    void planned; void selectedId; void liveAgentId;
    tick().then(computeEdges);
  });
</script>

<svelte:window onresize={computeEdges} />

<div class="mz-canvas" bind:this={canvas}>
  <svg class="mz-edges" aria-hidden="true">
    {#each edges as e}<path d={e.d} class={e.cls} />{/each}
  </svg>
  <div class="mz-graph">
    <div class="mz-col-label" style="grid-column:1">Input</div>
    <div class="mz-col-label" style="grid-column:2">{campaign ? 'Planning' : 'Synthesis'}</div>
    <div class="mz-col-label" style="grid-column:3">{campaign ? 'Callers' : 'Personas'}</div>
    <div class="mz-col-label" style="grid-column:4">Voice agents</div>

    <div class="mz-node {run.inputState}" data-node="input" style="grid-column:1;grid-row:2/{n + 4}">
      {@render badge(run.inputState)}
      <div class="mz-node-head"><span class="mz-ic"><FileText size={15} /></span>
        <div class="mz-min"><div class="mz-name">Approved proposal</div><div class="mz-sub">{proposalTitle}</div></div></div>
      <div class="mz-tags"><span class="mz-tag"><Landmark size={11} />{target}</span><span class="mz-tag">{jurisdiction}</span></div>
    </div>

    <div class="mz-node {run.synthState}" data-node="synth" style="grid-column:2;grid-row:2/{n + 2}">
      {@render badge(run.synthState)}
      <div class="mz-node-head"><span class="mz-ic"><Sparkles size={15} /></span>
        <div class="mz-min"><div class="mz-name">{campaign ? 'Call planner' : 'Persona synthesis'}</div><div class="mz-sub">{sourceLabel}</div></div></div>
      <div class="mz-tags"><span class="mz-tag">{doneCount}/{n} {campaign ? 'calls' : 'personas'}</span><span class="mz-tag">{campaign ? 'one per person in the handoff' : 'varied by role, age, gender'}</span></div>
      <div class="mz-progress"><i style="width:{n ? (doneCount / n) * 100 : 0}%"></i></div>
    </div>

    {#each Array(n) as _, i}
      {@const slot = run.personas[i] ?? { state: 'pending' as NodeState }}
      <div class="mz-node {slot.state}" class:mz-appear={!!slot.persona} data-node="p{i}" style="grid-column:3;grid-row:{i + 2}">
        {@render badge(slot.state)}
        <div class="mz-node-head">
          {#if slot.persona}<span class="mz-avatar" style="background:{avatarColor(slot.persona.name)}">{initials(slot.persona.name)}</span>
          {:else}<span class="mz-ic"><Sparkles size={15} /></span>{/if}
          <div class="mz-min">
            <div class="mz-name">{slot.persona?.name ?? (slot.target ?? targets[i] ? `Caller → ${slot.target ?? targets[i]}` : `Persona ${i + 1}`)}</div>
            <div class="mz-sub">{slot.persona ? `${slot.persona.age} · ${slot.persona.occupation}`
              : slot.state === 'error' ? 'Skipped'
              : slot.state === 'running' ? (slot.phase === 'writing' ? `Writing the call plan… ${secs(slot.startedAt)}` : slot.target ? `Thinking… ${secs(slot.startedAt)}` : 'Drafting…')
              : slot.archetype ?? 'Waiting'}</div>
          </div>
        </div>
        {#if slot.state === 'running' && slot.phase === 'writing' && slot.draft}<p class="mz-think">{drafting(slot.draft)}</p>
        {:else if slot.state === 'running' && slot.thinking}<p class="mz-think">{thought(slot.thinking)}</p>{/if}
        {#if slot.persona}
          <div class="mz-tags"><span class="mz-tag"><Mic size={11} />{slot.voice ?? 'casting…'}</span>
            <span class="mz-tag">{slot.persona.gender} · {slot.persona.age_band.replace('_', ' ')}</span></div>
        {/if}
      </div>
    {/each}

    {#each Array(n) as _, i}
      {@render agentNode(campaign ? 'generated' : 'legislator', run.legislators[i] ?? null, `a${i}`, i + 2)}
    {/each}
    {#each orgRows as o}
      {@render agentNode(o.kind, o.agent, o.kind, o.row)}
    {/each}
  </div>
</div>

{#snippet badge(state: NodeState | 'live')}
  {#if state === 'done'}<span class="mz-state done"><Check size={10} strokeWidth={3} /></span>
  {:else if state === 'running'}<span class="mz-state running"></span>
  {:else if state === 'live'}<span class="mz-state live"></span>{/if}
{/snippet}

{#snippet agentNode(kind: AgentKind, agent: VoiceAgent | null, key: string, row: number)}
  {@const Icon = KIND[kind].icon}
  {#if agent}
    <button class="mz-node clickable mz-appear" class:selected={selectedId === agent.id} data-node={key} data-kind={kind}
      style="grid-column:4;grid-row:{row}" onclick={() => onselect(agent.id)}>
      {@render badge(liveAgentId === agent.id ? 'live' : 'done')}
      <div class="mz-kind">{agent.archetype || KIND[kind].label}</div>
      <div class="mz-node-head">
        <span class="mz-avatar" style="background:{agent.persona ? avatarColor(agent.caller) : 'var(--k)'}">{initials(agent.caller)}</span>
        <div class="mz-min"><div class="mz-name">{agent.caller}</div><div class="mz-sub">→ {agent.target}</div></div>
      </div>
      <div class="mz-tags"><span class="mz-tag"><Mic size={11} />{agent.voice}</span>
        <span class="mz-tag">{Object.keys(agent.request.dynamic_variables).length} vars</span>
        {#if agent.conversations.length}<span class="mz-tag"><Phone size={11} />{agent.conversations.length}</span>{/if}</div>
    </button>
  {:else}
    <div class="mz-node pending" data-node={key} data-kind={kind} style="grid-column:4;grid-row:{row}">
      <div class="mz-kind">{KIND[kind].label}</div>
      <div class="mz-node-head"><span class="mz-ic"><Icon size={15} /></span>
        <div class="mz-min"><div class="mz-name">{KIND[kind].placeholder}</div><div class="mz-sub">Not built yet</div></div></div>
    </div>
  {/if}
{/snippet}
