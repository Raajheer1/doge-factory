<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { ArrowRight, ArrowUpRight, Check, CheckCircle2, ChevronDown, CircleAlert, Clock3, FileSearch, FileText, FlaskConical, HeartPulse, House, Layers3, LoaderCircle, Megaphone, Menu, Search, ShieldCheck, Sparkles } from '@lucide/svelte';
  import { createRun, getRun, listRuns, approve, mobilize, type Run, type Handoff } from '$lib/api';
  import './app.css';

  let query = '';
  let collection: 'healthcare' | 'housing' = 'healthcare';
  let run: Run | null = null;
  let selectedId = '';
  let handoff: Handoff | null = null;
  let history: Run[] = [];
  let historyOpen = false;
  let historyError = '';
  let error = '';
  let errorAction: 'start' | 'poll' = 'start';
  let actionError = '';
  let busy = false;
  let actionBusy = false;
  let loadingRun = false;
  let statusUrl = '';
  let timer: ReturnType<typeof setTimeout> | undefined;
  let generation = 0;
  let disposed = false;
  $: selected = run?.findings.find(f => f.id === selectedId) ?? null;
  $: approved = !!run?.selected_finding_id && run.selected_finding_id === selectedId;
  $: terminal = run ? ['completed', 'completed_with_errors', 'failed'].includes(run.status) : false;
  $: canApprove = run && ['completed', 'completed_with_errors'].includes(run.status);
  $: stageLabel = run?.stage === 'retrieving' ? 'Retrieving provisions' : run?.stage === 'auditing_and_drafting' ? 'Analyzing and drafting' : run?.stage === 'done' ? 'Analysis finished' : 'Getting started';
  const rememberRun = (id: string) => { try { localStorage.setItem('doge-last-run', id); } catch { /* Storage is optional. */ } };
  const list = (value: unknown): string[] => Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];
  const displayDate = (value?: string) => { if (!value) return 'Unavailable'; const date = new Date(value); return Number.isNaN(date.valueOf()) ? value : date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }); };
  const labelStatus = (status: string) => status.replaceAll('_', ' ');
  function stopPolling() { if (timer) clearTimeout(timer); timer = undefined; }
  function acceptRun(next: Run) { run = next; if (!next.findings.some(f => f.id === selectedId)) selectedId = next.selected_finding_id && next.findings.some(f => f.id === next.selected_finding_id) ? next.selected_finding_id : (next.findings[0]?.id ?? ''); }
  async function poll(path: string, token: number) {
    try {
      const next = await getRun(path);
      if (token !== generation || disposed) return;
      acceptRun(next); if (errorAction === 'poll') error = ''; loadingRun = false;
      if (!['completed', 'completed_with_errors', 'failed'].includes(next.status)) timer = setTimeout(() => poll(path, token), 1500);
    } catch (e) { if (token === generation && !disposed) { loadingRun = false; errorAction = 'poll'; error = e instanceof Error ? e.message : 'Unable to load this run.'; } }
  }
  async function start() {
    if (busy) return;
    if (!query.trim()) { errorAction = 'start'; error = 'Enter a policy goal to start an analysis.'; return; }
    if (new TextEncoder().encode(query).length > 2000) { errorAction = 'start'; error = 'The goal exceeds the API limit of 2,000 UTF-8 bytes. Shorten it and try again.'; return; }
    busy = true; error = ''; actionError = ''; const token = generation;
    try {
      const created = await createRun(query.trim(), collection);
      if (token !== generation) return;
      stopPolling(); generation++;
      run = null; selectedId = ''; handoff = null; statusUrl = created.statusUrl; loadingRun = true;
      rememberRun(created.id);
      await poll(statusUrl, generation);
    } catch (e) { if (token === generation) { errorAction = 'start'; error = e instanceof Error ? e.message : 'Unable to start the analysis.'; } }
    finally { busy = false; }
  }
  function openRun(id: string) { stopPolling(); generation++; error = ''; actionError = ''; handoff = null; selectedId = ''; run = null; loadingRun = true; statusUrl = `/api/runs/${encodeURIComponent(id)}`; rememberRun(id); historyOpen = false; void poll(statusUrl, generation); }
  function retryRun() { if (errorAction === 'poll' && statusUrl) { loadingRun = true; error = ''; void poll(statusUrl, generation); } else void start(); }
  async function showHistory() { historyOpen = !historyOpen; if (!historyOpen) return; historyError = ''; try { history = (await listRuns()).sort((a,b) => (b.created_at || '').localeCompare(a.created_at || '')); } catch (e) { historyError = e instanceof Error ? e.message : 'Could not load saved runs.'; } }
  function selectFinding(id: string) { selectedId = id; actionError = ''; handoff = null; }
  async function approveSelected() { if (!run || !selected || actionBusy || busy) return; const token = generation; const runId = run.id; const findingId = selected.id; actionBusy = true; actionError = ''; try { const id = await approve(runId, findingId); if (token !== generation || !run || run.id !== runId) return; run = { ...run, selected_finding_id: id }; handoff = null; } catch (e) { if (token === generation && selectedId === findingId) actionError = e instanceof Error ? e.message : 'Approval failed.'; } finally { actionBusy = false; } }
  async function prepare() { if (!run || !selected || actionBusy || busy) return; const token = generation; const runId = run.id; const findingId = selected.id; actionBusy = true; actionError = ''; try { const result = await mobilize(runId); if (token === generation && selectedId === findingId) { if (result.run_id !== runId || result.finding.id !== findingId) throw new Error('The handoff response does not match the approved proposal.'); handoff = result; } } catch (e) { if (token === generation && selectedId === findingId) actionError = e instanceof Error ? e.message : 'Handoff failed.'; } finally { actionBusy = false; } }
  onMount(() => { try { const id = localStorage.getItem('doge-last-run'); if (id) openRun(id); } catch { /* The workspace works without browser storage. */ } });
  onDestroy(() => { disposed = true; generation++; stopPolling(); });
</script>

<svelte:head><title>DOGE Factory — Policy workbench</title><meta name="description" content="Explore policy barriers and review proposed amendments." /></svelte:head>
<div class="app-shell">
  <aside class="sidebar">
    <a class="brand" href="/" aria-label="DOGE Factory home"><span class="brand-mark"><Layers3 size={19} strokeWidth={2.2}/></span><span>DOGE<span class="brand-light">FACTORY</span><small>POLICY WORKBENCH</small></span></a>
    <div class="side-section">WORKSPACE</div>
    <div class="side-active"><FileSearch size={17}/> Policy analysis <span class="side-dot"></span></div>
    <a class="side-link" href={run?.selected_finding_id ? `/mobilize?run=${encodeURIComponent(run.id)}` : '/mobilize'}><Megaphone size={17}/> Mobilize</a>
    <button class="side-link" onclick={showHistory}><Clock3 size={17}/> Saved runs <ChevronDown size={14} class={historyOpen ? "rotate" : ""}/></button>
    {#if historyOpen}<div class="history-list">{#if historyError}<p>{historyError}</p><button onclick={showHistory}>Close</button>{:else if history.length === 0}<p>No saved runs yet.</p>{:else}{#each history as item}<button class:history-current={item.id === run?.id} onclick={() => openRun(item.id)}><span>{item.query}</span><small>{displayDate(item.created_at)} · {item.collection || 'policy'} · {labelStatus(item.status)} · {item.findings.length} findings</small></button>{/each}{/if}</div>{/if}
    <div class="side-bottom"><div class="side-note"><span class="note-icon"><ShieldCheck size={17}/></span><div><strong>Built for thoughtful review</strong><p>Proposals are a starting point for policy discussion.</p></div></div><div class="side-footer"><span class="avatar">DF</span><div><strong>Policy workspace</strong><small>Local demo</small></div><Menu size={17}/></div></div>
  </aside>
  <main>
    <header class="topbar"><div class="breadcrumb">Workspace <span>/</span> <strong>Policy analysis</strong></div><div class="top-right"><span class="demo-dot"></span> LOCAL DEMO <span class="top-divider"></span><span class="top-avatar">DF</span></div></header>
    <div class="content">
      <div class="page-heading"><div><div class="eyebrow"><span></span> POLICY WORKBENCH</div><h1>Make room for <em>better policy.</em></h1><p>Find opportunities to remove barriers to innovation, and move promising ideas forward.</p></div><div class="heading-badge"><Sparkles size={15}/> FROM IDEA TO ACTION</div></div>
      <section class="goal-card" aria-labelledby="goal-title"><div class="goal-intro"><div><div class="section-kicker">01 / DEFINE YOUR GOAL</div><h2 id="goal-title">What would you like to improve?</h2><p>Describe an outcome. We’ll look for policy provisions that may be getting in the way.</p></div><div class="goal-icon"><Search size={21}/></div></div>
        <form onsubmit={(e) => { e.preventDefault(); void start(); }}>
          <fieldset class="collection-picker">
            <legend>Policy collection <span>Choose one</span></legend>
            <div class="collection-options">
              <label class:collection-selected={collection === 'healthcare'} class="collection-option">
                <input type="radio" name="collection" value="healthcare" bind:group={collection} />
                <span class="collection-icon"><HeartPulse size={18}/></span>
                <span class="collection-copy"><strong>Healthcare</strong><small>Health &amp; healthcare policy</small></span>
                <span class="collection-indicator" aria-hidden="true"></span>
              </label>
              <label class:collection-selected={collection === 'housing'} class="collection-option">
                <input type="radio" name="collection" value="housing" bind:group={collection} />
                <span class="collection-icon"><House size={18}/></span>
                <span class="collection-copy"><strong>Housing</strong><small>Housing &amp; assistance policy</small></span>
                <span class="collection-indicator" aria-hidden="true"></span>
              </label>
            </div>
          </fieldset>
          <label class="sr-only" for="goal">Policy goal</label><div class="input-wrap"><Search size={19}/><input id="goal" maxlength="2000" bind:value={query} placeholder={collection === 'healthcare' ? 'e.g. Optimize healthcare in Iowa' : 'e.g. Reduce housing assistance paperwork'} /><button class="primary-button" disabled={busy || loadingRun}>{#if busy}<LoaderCircle class="spin" size={17}/> Starting{:else}Analyze goal <ArrowRight size={17}/>{/if}</button></div><div class="input-meta"><span>Try: <button type="button" class="example" onclick={() => query = collection === 'healthcare' ? 'Optimize healthcare in Iowa' : 'Reduce housing assistance paperwork'}>“{collection === 'healthcare' ? 'Optimize healthcare in Iowa' : 'Reduce housing assistance paperwork'}”</button></span><span>{query.length} / 2,000</span></div>
        </form>
        <div class="scope-note"><span class="scope-dot"></span> Analysis considers a bounded set of retrieved provisions, not all applicable laws. Runs are saved locally; you can close this page and return via Saved runs while the backend keeps running.</div>
      </section>
      {#if error}<div class="alert-error" role="alert"><CircleAlert size={18}/><div><strong>Something needs attention</strong><p>{error}</p></div><button onclick={retryRun}>Try again</button></div>{/if}
      {#if loadingRun}<div class="loading-panel"><LoaderCircle class="spin" size={20}/> Loading analysis…</div>{/if}
      {#if run}
        <section class="analysis-section"><div class="section-heading"><div><div class="section-kicker">02 / EXPLORE THE ANALYSIS</div><h2>Analysis workspace</h2><p>Review the evidence and consider each proposed change.</p></div><div class="run-status"><span class:active-dot={!terminal} class="status-dot"></span>{labelStatus(run.status)}</div></div>
          <div class="run-summary"><div class="run-goal"><span>ANALYSIS GOAL</span><strong>{run.query}</strong><small>Started {displayDate(run.created_at)}</small></div><div class="summary-divider"></div><div class="run-progress"><div class="progress-title"><span>{terminal ? 'RUN STATUS' : 'IN PROGRESS'}</span><strong>{stageLabel}</strong></div><div class="progress-track"><i class:complete={terminal} class:auditing={run.stage === 'auditing_and_drafting'}></i></div></div><div class="stat"><strong>{run.retrieved}</strong><span>provisions retrieved</span></div><div class="stat"><strong>{run.reviewed}</strong><span>processed by model</span></div></div>
          {#if run.coverage}<div class="scope-note">{run.coverage}</div>{/if}
          {#if list(run.errors).length}<div class="run-errors" role="status"><CircleAlert size={18}/><div><strong>{run.status === 'failed' ? 'Analysis failed' : 'Analysis reported issues'}</strong>{#each list(run.errors) as issue}<p>{issue}</p>{/each}</div></div>{/if}
          {#if run.status === 'failed' && !list(run.errors).length}<div class="run-errors"><CircleAlert size={18}/> This run failed. Start a new analysis to try again.</div>{/if}
          {#if run.findings.length}
            <div class="workspace"><div class="findings-column"><div class="column-heading"><div><span class="mini-label">RESULTS</span><h3>Findings <span>{run.findings.length}</span></h3></div><FileText size={19}/></div><p class="column-desc">Select a finding to explore the proposal.</p><div class="finding-list">{#each run.findings as finding, index}<button class:selected-card={selectedId === finding.id} class="finding-card" onclick={() => selectFinding(finding.id)}><div class="finding-top"><span>FINDING {String(index + 1).padStart(2, '0')}</span>{#if run.selected_finding_id === finding.id}<span class="approved-small"><Check size={12}/> APPROVED</span>{:else}<ArrowUpRight size={15}/>{/if}</div><strong>{finding.title || finding.provision.title}</strong><span class="finding-citation">{finding.provision.citation || 'Citation unavailable'}</span><div class="finding-tags"><span>{finding.provision.jurisdiction || 'Jurisdiction unavailable'}</span>{#if finding.provision.synthetic}<span class="synthetic-tag">Synthetic</span>{/if}</div></button>{/each}</div><div class="list-foot"><span class="tiny-spark">✳</span> Findings are proposals for review, not legal conclusions.</div></div>
            {#if selected}<div class="detail-column"><div class="detail-header"><div><div class="mini-label">FINDING DETAIL <span> / </span> PROPOSAL</div><h3>{selected.title || selected.provision.title}</h3><div class="detail-meta"><span>{selected.provision.jurisdiction || 'Jurisdiction unavailable'}</span><span>·</span><span>{selected.provision.citation || 'Citation unavailable'}</span><span>·</span><span>Effective {displayDate(selected.provision.effective_date)}</span></div></div><span class="proposal-pill">PROPOSAL</span></div>
              {#if selected.provision.synthetic}<div class="synthetic-banner"><FlaskConical size={17}/><span><strong>Synthetic demo data.</strong> This source and its generated outputs are synthetic.</span></div>{/if}
              <div class="detail-body"><div class="source-line"><span class="mini-label">SOURCE MATERIAL</span>{#if selected.provision.source_url && /^https?:\/\//i.test(selected.provision.source_url)}<a href={selected.provision.source_url} target="_blank" rel="noopener noreferrer">View source <ArrowUpRight size={14}/></a>{:else}<span>Source URL unavailable</span>{/if}</div><div class="passage"><div class="passage-label">SOURCE PASSAGE</div><p>{selected.source_passage || 'Source passage unavailable.'}</p></div>
                <div class="insight-grid"><div><span class="number-icon">01</span><h4>Potential barrier</h4><p>{selected.barrier}</p></div><div><span class="number-icon green">02</span><h4>Desired change</h4><p>{selected.desired_change}</p></div></div>
                <div class="rationale"><h4>Why this change?</h4><p>{selected.justification}</p></div>
                <div class="compare-heading"><div><span class="mini-label">THE PROPOSAL</span><h4>Original & proposed text</h4><p>Compare the full provision with the suggested amendment.</p></div></div><div class="comparison"><div class="text-block original"><div class="text-label"><span></span> ORIGINAL PROVISION</div><p>{selected.provision.text}</p></div><div class="text-block proposed"><div class="text-label"><span></span> PROPOSED AMENDMENT</div><p>{selected.amendment}</p></div></div>
                <div class="considerations"><div><h4><ShieldCheck size={17}/> Safeguards</h4>{#if list(selected.safeguards).length}<ul>{#each list(selected.safeguards) as item}<li>{item}</li>{/each}</ul>{:else}<p>None provided.</p>{/if}</div><div><h4><CircleAlert size={17}/> Uncertainties</h4>{#if list(selected.uncertainties).length}<ul>{#each list(selected.uncertainties) as item}<li>{item}</li>{/each}</ul>{:else}<p>None provided.</p>{/if}</div></div>
                <details class="scenario"><summary>View proposal JSON</summary><pre>{JSON.stringify({ title: selected.title || selected.provision.title, description: selected.description || selected.barrier, policy_change: selected.policy_change || selected.desired_change, diff: selected.diff || { original: selected.provision.text, proposed: selected.amendment }, lobby_targets: selected.lobby_targets || [] }, null, 2)}</pre><p>Lobbying targets require further research when this list is empty.</p></details><div class="scenario"><span class="mini-label">BEHAVIORAL SCENARIO</span><h4>Gherkin</h4><p>Scenario accompanying the proposed amendment.</p><pre>{selected.gherkin || 'No scenario provided.'}</pre></div>
              </div><div class="review-panel"><div><span class="mini-label">03 / REVIEW & HANDOFF</span><h4>{approved ? 'Proposal approved for handoff' : 'Ready to move this proposal forward?'}</h4><p>{approved ? 'You can now prepare the mobilization handoff.' : canApprove ? 'Approve this finding to prepare it for mobilization.' : 'Approval is available once the analysis finishes.'}</p></div>{#if approved}<button class="primary-button" disabled={actionBusy || busy} onclick={prepare}>{actionBusy ? 'Preparing…' : 'Prepare mobilization'} <ArrowRight size={17}/></button>{:else}<button class="primary-button" disabled={!canApprove || actionBusy || busy} onclick={approveSelected}>{actionBusy ? 'Approving…' : 'Approve proposal'} <ArrowRight size={17}/></button>{/if}</div>
              {#if actionError}<div class="action-error" role="alert">{actionError} Please try again.</div>{/if}
              {#if handoff}<div class="handoff"><div class="handoff-title"><CheckCircle2 size={20}/><div><span class="mini-label">MOBILIZATION HANDOFF</span><h4>Handoff status: {labelStatus(handoff.status)}</h4></div></div><p>{handoff.message}</p>{#if handoff.status === 'simulated'}<p class="no-calls">This handoff is simulated. No calls were placed.</p>{/if}<div class="handoff-proposal"><span>APPROVED PROPOSAL</span><strong>{handoff.finding.provision.title}</strong><p>{handoff.finding.desired_change}</p><small>Goal: {handoff.query} · Run: {handoff.run_id}</small></div><a class="primary-button handoff-open" href={`/mobilize?run=${encodeURIComponent(handoff.run_id)}`}><Megaphone size={16}/> Open Mobilize: build voice agents <ArrowRight size={16}/></a><details class="handoff-details"><summary>View complete returned handoff</summary><pre>{JSON.stringify(handoff, null, 2)}</pre></details></div>{/if}
            </div>{/if}</div>
          {:else if terminal && run.status !== 'failed'}<div class="empty-state"><FileSearch size={24}/><h3>{run.retrieved === 0 && run.status === 'completed' ? 'No matching provisions found' : 'No findings to review'}</h3><p>{run.retrieved === 0 && run.status === 'completed' ? 'The analysis did not retrieve any matching provisions. Try a different or broader goal.' : run.status === 'completed_with_errors' ? 'No findings are available. Review the issues reported above and try another analysis.' : 'The retrieved provisions did not produce any findings. Try a different goal.'}</p></div>{:else if !terminal}<div class="empty-state"><LoaderCircle class="spin" size={24}/><h3>Analysis is underway</h3><p>Findings will appear here as provisions are processed.</p></div>{/if}
        </section>
      {:else if !loadingRun}<section class="welcome-section"><div class="section-heading"><div><div class="section-kicker">02 / EXPLORE THE ANALYSIS</div><h2>Your workspace awaits</h2><p>Start with a goal to see potential opportunities for policy improvement.</p></div></div><div class="welcome-grid"><div><span class="welcome-icon"><Search size={19}/></span><strong>Discover</strong><p>Find relevant provisions within a bounded set of sources.</p></div><div><span class="welcome-icon"><FileText size={19}/></span><strong>Review</strong><p>Explore evidence, proposed amendments, and safeguards.</p></div><div><span class="welcome-icon"><ArrowRight size={19}/></span><strong>Move forward</strong><p>Approve a proposal and prepare a simulated handoff.</p></div></div></section>{/if}
      <footer><span>DOGE FACTORY <b> / </b> POLICY WORKBENCH</span><span>Thoughtful policy starts with a better question.</span></footer>
    </div>
  </main>
</div>
