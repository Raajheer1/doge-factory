<script lang="ts">
  import { Check, Inbox, Layers3, Lock, ShieldCheck, Zap } from '@lucide/svelte';
  import { STAGES, autopilotPath, journey, mobilizePath, redlinePath, runPath, type StageKey } from '$lib/journey.svelte';

  const order: string[] = STAGES.map((s) => s.key);
  const currentIndex = $derived(order.indexOf(journey.stage));
  // The /mobilize demo sandbox has no run: only Mobilize is live.
  const sandbox = $derived(!journey.runId && journey.stage === 'mobilize');

  function href(key: StageKey): string | null {
    const id = journey.runId;
    if (key === 'audit') return id ? runPath(id) : '/';
    if (sandbox) return key === 'mobilize' ? '/mobilize' : null;
    if (!id) return null;
    if (key === 'redline') return journey.hasFindings ? redlinePath(id, journey.findingId) : null;
    return journey.approved ? mobilizePath(id) : null;
  }

  function lockedReason(key: StageKey): string {
    if (sandbox) return 'Not used in the demo';
    if (!journey.runId) return 'Pitch a product first';
    if (key === 'redline') return journey.analysisDone ? 'No barriers in this run' : 'Audit still running';
    return 'Approve a redline first';
  }
</script>

<aside class="sidebar">
  <a class="brand" href="/" aria-label="DOGE Factory home">
    <span class="brand-mark"><Layers3 size={19} strokeWidth={2.2} /></span>
    <span>DOGE<span class="brand-light">FACTORY</span><small>AI POLICY FACTORY</small></span>
  </a>

  <div class="side-section">{journey.runId ? 'THIS RUN' : sandbox ? 'DEMO SANDBOX' : 'HOW IT WORKS'}</div>
  <ol class="stepper">
    {#each STAGES as stage, i}
      {@const link = href(stage.key)}
      {@const current = stage.key === journey.stage}
      {@const done = journey.stage === 'autopilot' ? (stage.key === 'audit' && journey.analysisDone || stage.key === 'redline' && journey.approved) : !current && i < currentIndex && !!link && !!journey.runId}
      {#if link}
        <li><a class="step" class:current class:done href={link} aria-current={current ? 'step' : undefined}>
          <span class="step-dot">{#if done}<Check size={11} strokeWidth={3} />{:else}{i + 1}{/if}</span>
          <span class="step-text"><strong>{stage.label}</strong><small>{stage.key === 'mobilize' && journey.agentsBuilt ? 'Agents built · place calls' : stage.hint}</small></span>
        </a></li>
      {:else}
        <li><span class="step locked" aria-disabled="true" title={lockedReason(stage.key)}>
          <span class="step-dot"><Lock size={10} /></span>
          <span class="step-text"><strong>{stage.label}</strong><small>{lockedReason(stage.key)}</small></span>
        </span></li>
      {/if}
    {/each}
  </ol>

  {#if journey.runId}
    <div class="side-section">AUTOMATION</div>
    <a class="side-link" class:side-current={journey.stage === 'autopilot'} href={autopilotPath(journey.runId)} aria-current={journey.stage === 'autopilot' ? 'page' : undefined}><Zap size={17} /> Autopilot</a>
  {/if}

  <div class="side-section">WORKSPACE</div>
  <a class="side-link" class:side-current={journey.stage === 'queue'} href="/runs" aria-current={journey.stage === 'queue' ? 'page' : undefined}>
    <Inbox size={17} /> Problem queue
  </a>

  <div class="side-bottom">
    <div class="side-note"><span class="note-icon"><ShieldCheck size={17} /></span>
      <div><strong>Built for thoughtful review</strong><p>Findings and redlines are proposals, personas are synthetic, and calls only ring allowlisted numbers.</p></div>
    </div>
  </div>
</aside>
