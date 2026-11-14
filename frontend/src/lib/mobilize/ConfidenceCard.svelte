<script lang="ts">
  import { onDestroy } from 'svelte';
  import { ArrowDownRight, ArrowUpRight, LoaderCircle, Minus } from '@lucide/svelte';
  import { getConfidence, type ConfidenceView } from '$lib/voice';

  // `run` is the run's key (run_id); null shows the run built last. Polls while mounted.
  let { run = null }: { run?: string | null } = $props();

  let view = $state<ConfidenceView | null>(null);
  let hover = $state<number | null>(null);
  let timer: ReturnType<typeof setTimeout> | undefined;
  let disposed = false;

  $effect(() => {
    const key = run;
    clearTimeout(timer);
    const tick = async () => {
      try { const v = await getConfidence(key); if (!disposed && key === run) view = v; } catch { /* the API may be restarting */ }
      if (!disposed && key === run) timer = setTimeout(tick, 3000);
    };
    void tick();
  });
  onDestroy(() => { disposed = true; clearTimeout(timer); });

  const cur = $derived(view?.current ?? null);
  const hist = $derived(view?.history ?? []);
  const reading = $derived((view?.reading.length ?? 0) > 0);
  const BANDS = [75, 55, 40, 25];

  // Score over each scoring event (baseline, then one per call), on a fixed 0-100 scale.
  const W = 320, H = 120, PAD = { l: 26, r: 10, t: 10, b: 18 };
  const x = (i: number) => PAD.l + (hist.length > 1 ? (i / (hist.length - 1)) * (W - PAD.l - PAD.r) : (W - PAD.l - PAD.r) / 2);
  const y = (v: number) => PAD.t + (1 - v / 100) * (H - PAD.t - PAD.b);
  const path = $derived(hist.map((h, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(h.score).toFixed(1)}`).join(''));
  const shown = $derived(hover !== null ? hist[hover] : null);

  const pct = (v: number | undefined) => (v === undefined ? '—' : `${Math.round(v * 100)}%`);
  const signed = (v: number) => `${v > 0 ? '+' : ''}${v.toFixed(1)}`;
  const label = (s?: string) => (s ?? '').replaceAll('_', ' ');
</script>

<div class="mz-conf">
  <div class="mz-card-bar">
    <span class="mini-label">CONFIDENCE THE CHANGE HAPPENS</span>
    <span class="mz-runmeta">{#if reading}<LoaderCircle class="spin" size={12} /> Reading the latest call…{:else if cur}{cur.version} · rescored after every call · {cur.reader_model}{/if}</span>
  </div>
  {#if !cur}
    <p class="mz-muted mz-conf-empty">Scores appear once agents are built in Live mode from a handoff with people. Each finished call rescores the run.</p>
  {:else}
    <div class="mz-conf-body">
      <div class="mz-conf-main">
        <div class="mz-conf-score">
          <strong>{Math.round(cur.score)}</strong><span>/ 100</span>
          <em data-band={cur.band}>{cur.band}</em>
          {#if cur.seq > 0}
            <small class="mz-conf-delta" class:up={cur.delta > 0} class:down={cur.delta < 0}>
              {#if cur.delta > 0}<ArrowUpRight size={13} />{:else if cur.delta < 0}<ArrowDownRight size={13} />{:else}<Minus size={13} />{/if}{signed(cur.delta)} last call
            </small>
          {/if}
        </div>
        <p class="mz-conf-trigger">{cur.trigger.summary}</p>

        <figure class="mz-conf-chart" aria-label="Confidence score after each call">
          <svg viewBox={`0 0 ${W} ${H}`} role="img" onmouseleave={() => (hover = null)}>
            {#each BANDS as b}<line x1={PAD.l} x2={W - PAD.r} y1={y(b)} y2={y(b)} class="grid" /><text x={PAD.l - 5} y={y(b) + 3} class="tick">{b}</text>{/each}
            <line x1={PAD.l} x2={W - PAD.r} y1={y(0)} y2={y(0)} class="axis" />
            {#if hist.length > 1}<path d={path} class="line" />{/if}
            {#each hist as h, i}
              <circle cx={x(i)} cy={y(h.score)} r={hover === i ? 5 : 4} class="dot" class:base={h.trigger.type === 'baseline'} />
              <rect x={x(i) - 14} y={PAD.t} width="28" height={H - PAD.t - PAD.b} fill="transparent" role="presentation" onmouseenter={() => (hover = i)} />
            {/each}
            <text x={PAD.l} y={H - 4} class="tick start">baseline</text>
            {#if hist.length > 1}<text x={W - PAD.r} y={H - 4} class="tick end">call {hist.length - 1}</text>{/if}
          </svg>
          {#if shown}<figcaption class="mz-conf-tip"><b>{Math.round(shown.score)}</b> {shown.band}{shown.trigger.type === 'call' ? ` (${signed(shown.delta)})` : ''}<span>{shown.trigger.summary}</span></figcaption>{/if}
        </figure>

        <dl class="mz-conf-factors">
          {#each cur.factors as f}<dt>{f.label}</dt><dd><b>{f.key === 'path' ? f.points.toFixed(0) : signed(f.points)}</b><small>{f.detail}</small></dd>{/each}
          <dt>Coverage</dt><dd><b>{cur.coverage.reached}/{cur.coverage.people}</b><small>reached of people in the handoff · {cur.coverage.called} called</small></dd>
        </dl>
      </div>

      <ul class="mz-conf-targets">
        {#each [...cur.targets].sort((a, b) => Number(b.called) - Number(a.called) || b.leverage - a.leverage) as t}
          <li class:muted={!t.reached}>
            <div class="mz-conf-who"><strong>{t.name}</strong><small>{label(t.relevance)} · leverage {t.leverage.toFixed(2)}</small></div>
            {#if t.stance !== null}
              <div class="mz-conf-stance" title={`Stance ${t.stance.toFixed(2)}`}>
                <span class="track"><span class="mid"></span><span class="fill" class:neg={t.stance < 0} style={`left:${t.stance < 0 ? 50 + t.stance * 50 : 50}%;width:${Math.abs(t.stance) * 50}%`}></span></span>
                <b>{signed(t.points)}</b>
              </div>
              <p class="mz-conf-read">{label(t.position)} · {label(t.commitment)} · sentiment {signed(t.sentiment ?? 0)} · read {pct(t.read_confidence)}</p>
              {#if t.evidence?.length}<blockquote>“{t.evidence[0]}”</blockquote>{/if}
              {#if t.objections?.length}<p class="mz-conf-obj">Objections: {t.objections.join('; ')}</p>{/if}
            {:else}
              <p class="mz-conf-read">{t.called ? 'Called, not reached; no effect yet' : 'Not called yet'}</p>
            {/if}
          </li>
        {/each}
      </ul>
    </div>
  {/if}
</div>
