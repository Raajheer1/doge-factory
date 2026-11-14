<script lang="ts">
  import { Phone } from '@lucide/svelte';
  import type { AgentKind, Conversation, VoiceAgent } from '$lib/voice';
  import { FINAL_CALL_STATUSES, avatarColor, initials } from './run';

  export interface CallState { agentId: string; conversationId: string | null; data: Conversation | null; error: string }

  let { agent, call, ondial, onwatch }: {
    agent: VoiceAgent; call: CallState | null;
    ondial: (agent: VoiceAgent) => void; onwatch: (agent: VoiceAgent, conversationId: string) => void;
  } = $props();

  const KIND_LABEL: Record<AgentKind, string> = { legislator: 'Constituent → Legislator', survey: 'Constituent survey', lobbyist: 'Lobbyist pitch', generated: 'Generated caller' };
  const STATUS: Record<string, string> = { initiated: 'Ringing…', 'in-progress': 'Live', processing: 'Analyzing call…', done: 'Call complete', failed: 'Call failed' };

  type Tab = 'call' | 'persona' | 'variables' | 'payload';
  let tab = $state<Tab>('call');
  const tabs = $derived<Tab[]>(agent.persona ? ['call', 'persona', 'variables', 'payload'] : ['call', 'variables', 'payload']);
  $effect(() => { void agent.id; tab = 'call'; });

  const mine = $derived(call?.agentId === agent.id ? call : null);
  const data = $derived(mine?.data ?? null);
  const live = $derived(!!mine && !mine.error && !FINAL_CALL_STATUSES.has(data?.status ?? 'initiated'));
  const statusText = $derived(mine?.error ? 'Call failed' : !mine ? 'Ready to call' : !data ? 'Dialing…' : STATUS[data.status] ?? data.status);
  const vars = $derived(Object.entries(agent.request.dynamic_variables));
  const extracted = $derived(Object.entries(data?.data_collection ?? {}));
  const evaluation = $derived(Object.entries(data?.evaluation ?? {}));
  const speaker = (role: string) => (role === 'agent' ? agent.caller.replace(/ \(.*\)/, '') : agent.target);
</script>

<div class="mz-insp" data-kind={agent.kind}>
  <div class="mz-insp-head">
    <div class="mz-kind">{agent.archetype || KIND_LABEL[agent.kind]}</div>
    <div class="mz-insp-title">
      <span class="mz-avatar lg" style="background:{agent.persona ? avatarColor(agent.caller) : 'var(--k)'}">{initials(agent.caller)}</span>
      <div class="mz-min"><strong>{agent.caller}</strong><small>calls {agent.target}</small></div>
      <button class="primary-button mz-call" disabled={live} onclick={() => ondial(agent)}><Phone size={14} />{live ? 'On call' : 'Call'}</button>
    </div>
    <div class="mz-tabs" role="tablist">
      {#each tabs as t}<button role="tab" aria-selected={tab === t} class:on={tab === t} onclick={() => (tab = t)}>{t[0].toUpperCase() + t.slice(1)}</button>{/each}
    </div>
  </div>

  <div class="mz-insp-body">
    {#if tab === 'call'}
      <div class="mz-callcard">
        <div class="mz-orb" class:live class:done={data?.status === 'done'}></div>
        <strong>{statusText}</strong>
        <small class="mz-mono">{mine?.conversationId ? `${mine.conversationId.slice(0, 20)}…${data?.duration ? ` · ${data.duration}s` : ''}` : agent.request.to_number}</small>
        {#if mine?.error}<p class="mz-error">{mine.error}</p>{/if}
        {#if agent.conversations.length > 1}
          <div class="mz-history">{#each agent.conversations as id, i}<button class:on={mine?.conversationId === id} onclick={() => onwatch(agent, id)}>Call {i + 1}</button>{/each}</div>
        {/if}
      </div>
      {#if data?.transcript.length}
        <div><div class="mini-label">TRANSCRIPT</div>
          <div class="mz-transcript">{#each data.transcript as turn}
            <div class="mz-turn" class:user={turn.role !== 'agent'}>
              <span class="mz-who">{turn.role === 'agent' ? 'AI' : 'You'}</span>
              <div><small>{speaker(turn.role)} · {turn.at ?? 0}s</small><p>{turn.message}</p></div>
            </div>{/each}</div></div>
      {:else if mine}
        <p class="mz-muted mz-center">{live ? 'The transcript streams in once you pick up.' : 'No transcript.'}</p>
      {/if}
      {#if data?.summary}<div><div class="mini-label">SUMMARY</div><p class="mz-prose">{data.summary}</p></div>{/if}
      {#if extracted.length}
        <div><div class="mini-label">EXTRACTED</div><div class="mz-table">{#each extracted as [k, v]}<div><span>{k}</span><span>{v ?? '—'}</span></div>{/each}</div></div>
      {/if}
      {#if evaluation.length}
        <div><div class="mini-label">EVALUATION</div><div class="mz-table">{#each evaluation as [k, v]}<div><span>{k}</span><span><b class="mz-result {v}">{v}</b></span></div>{/each}</div></div>
      {/if}
    {:else if tab === 'persona' && agent.persona}
      <div><div class="mini-label">BACKGROUND</div><p class="mz-prose">{agent.persona.background}</p></div>
      <div><div class="mini-label">PERSONAL IMPACT</div><p class="mz-prose">{agent.persona.personal_impact}</p></div>
      <div><div class="mini-label">PROFILE</div><dl class="mz-kv">
        <dt>Age</dt><dd>{agent.persona.age}</dd><dt>Occupation</dt><dd>{agent.persona.occupation}</dd>
        <dt>Voice</dt><dd>{agent.voice} · {agent.persona.gender}, {agent.persona.age_band.replace('_', ' ')}</dd>
        <dt>Synthetic</dt><dd>{agent.persona.synthetic ? 'Yes. Generated, not a real constituent.' : 'No'}</dd></dl></div>
    {:else if tab === 'variables'}
      <div><div class="mini-label">BUILT ON</div><dl class="mz-kv">
        <dt>Template</dt><dd>{agent.template}</dd><dt>Agent ID</dt><dd class="mz-mono">{agent.payload.agent_id}</dd>
        <dt>Voice ID</dt><dd class="mz-mono">{agent.voice_id}</dd></dl></div>
      <div><div class="mini-label">DYNAMIC VARIABLES · {vars.length}</div>
        <dl class="mz-kv mz-vars">{#each vars as [k, v]}<dt>{`{{${k}}}`}</dt><dd>{v}</dd>{/each}</dl></div>
    {:else}
      <div><div class="mini-label">POST /v1/convai/twilio/outbound-call</div><pre class="mz-pre">{JSON.stringify(agent.payload, null, 2)}</pre></div>
    {/if}
  </div>
</div>
