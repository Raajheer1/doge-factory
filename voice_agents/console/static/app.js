/* Mobilize console: agent graph + trace timeline + inspector. No build step. */

const ICON = {
  file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/>',
  landmark: '<path d="M3 22h18M6 18v-7M10 18v-7M14 18v-7M18 18v-7M12 2l8 5H4z"/>',
  map: '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z"/><circle cx="12" cy="10" r="3"/>',
  briefcase: '<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>',
  target: '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
  sparkles: '<path d="M12 3l1.9 5.8L20 10l-6.1 1.2L12 17l-1.9-5.8L4 10l6.1-1.2z"/><path d="M19 17v4M17 19h4"/>',
  mic: '<rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10a7 7 0 0 0 14 0M12 17v5"/>',
  phone: '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7a2 2 0 0 1-.5 2.1L8 9.8a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.7.7a2 2 0 0 1 1.7 2z"/>',
  check: '<path d="M20 6L9 17l-5-5"/>',
  chevron: '<path d="M9 18l6-6-6-6"/>',
  clipboard: '<rect x="8" y="2" width="8" height="4" rx="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>',
  dollar: '<path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>',
  graph: '<circle cx="5" cy="12" r="2"/><circle cx="19" cy="5" r="2"/><circle cx="19" cy="19" r="2"/><path d="M7 12h4l6-6M11 12l6 6"/>',
};
const icon = (name) => `<svg viewBox="0 0 24 24">${ICON[name]}</svg>`;

const KIND = {
  legislator: { label: "Constituent → Legislator", icon: "landmark" },
  survey: { label: "Constituent survey", icon: "clipboard" },
  lobbyist: { label: "Lobbyist pitch", icon: "briefcase" },
};
const STAGE_COLOR = {
  input: "var(--text-3)", persona: "var(--accent)", voice: "var(--survey)",
  assemble: "var(--ok)", ready: "var(--text-2)", error: "var(--err)",
};
const STAGE_LABEL = { input: "Draft input", persona: "Persona", voice: "Voice cast", assemble: "Assemble", ready: "Ready", error: "Error" };
const FINAL = new Set(["done", "failed"]);

const state = {
  status: null, input: null,
  count: 3, source: "sample",
  run: emptyRun(),
  selected: null, tab: "call",
  call: null, // { agentId, convId, data, error }
  poll: null, ticker: null,
  seen: new Set(), // node keys already animated in
};

function emptyRun() {
  return {
    phase: "idle", // idle | running | done | error
    n: 0, start: null, end: null,
    inputState: "pending", synthState: "pending",
    personas: [], // { state, persona, voice }
    legislators: [], survey: null, lobbyist: null,
    rows: [], // trace rows { stage, start, end, msg, status }
  };
}

const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const initials = (name) => name.replace(/\(.*\)/, "").trim().split(/\s+/).map((w) => w[0]).slice(0, 2).join("").toUpperCase();
const hue = (s) => [...s].reduce((h, c) => (h * 31 + c.charCodeAt(0)) % 360, 7);
const avatar = (name, color) =>
  `<div class="avatar" style="background:${color || `hsl(${hue(name)} 52% 54%)`}">${esc(initials(name))}</div>`;
const appear = (key) => (state.seen.has(key) ? "" : (state.seen.add(key), "appear"));
const allAgents = () => [...state.run.legislators, state.run.survey, state.run.lobbyist].filter(Boolean);
const fmtSecs = (ms) => (ms < 1000 ? `${Math.round(ms)}ms` : `${(ms / 1000).toFixed(1)}s`);

async function api(path, opts = {}) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || res.statusText);
  return body;
}

/* ================= Header + sidebar ================= */

function renderHealth() {
  const s = state.status;
  const pill = (ok, label) => `<span class="pill"><i class="${ok ? "ok" : ""}"></i>${esc(label)}</span>`;
  $("#health").innerHTML = [
    pill(s.elevenlabs_key, "ElevenLabs"),
    pill(s.phone_number, "Twilio number"),
    pill(s.allowed_numbers.length, s.allowed_numbers.length ? `Dials ${s.allowed_numbers.join(", ")}` : "No numbers allowed"),
  ].join("");
}

function renderSourceHint() {
  $("#source-hint").textContent = state.source === "claude"
    ? `Generates each persona live with ${state.status?.persona_model ?? "Claude"}. Uses API credits.`
    : "Pre-written personas. Free, paced so the flow is watchable.";
}

function renderContext() {
  const d = state.input;
  const { policy: p, legislator: l, lobbyist: lb } = d;
  const item = (ic, title, sub, body, open = false) => `
    <details class="ctx" ${open ? "open" : ""}>
      <summary><span class="ic">${icon(ic)}</span>
        <span style="min-width:0"><div class="t">${esc(title)}</div><div class="s">${esc(sub)}</div></span>
        <span class="chev">${icon("chevron")}</span></summary>
      <div class="body">${body}</div>
    </details>`;
  $("#context").innerHTML = [
    item("file", "Policy", p.title, `<p>${esc(p.summary)}</p><p><b>Pain point:</b> ${esc(p.pain_point)}</p>`, true),
    item("dollar", "Fiscal impact", p.fiscal_impact, `<p>${esc(p.fiscal_impact)}</p>`),
    item("landmark", "Target legislator", `${l.title} ${l.name}`, `<p>${esc(l.district)}</p>`),
    item("map", "District profile", l.district, `<p>${esc(d.district_profile)}</p>`),
    item("briefcase", "Lobbyist", `${lb.name} · ${lb.firm}`, `<p><b>Client:</b> ${esc(lb.client_name)}</p><p>${esc(lb.client_benefit)}</p>`),
    item("target", "Asks", "What each call is trying to get",
      `<p><b>Legislator:</b> ${esc(d.asks.legislator)}</p><p><b>Lobbyist:</b> ${esc(d.asks.lobbyist)}</p>`),
  ].join("");
}

/* ================= Graph ================= */

function stateBadge(s) {
  if (s === "done") return `<span class="state done">${icon("check")}</span>`;
  if (s === "running") return '<span class="state running"></span>';
  if (s === "live") return '<span class="state live"></span>';
  return "";
}

function renderGraph() {
  const r = state.run;
  const n = r.phase === "idle" && !r.legislators.length ? state.count : r.n;
  const last = n + 3; // label row + n persona rows + survey + lobbyist
  const p = state.input.policy;
  const l = state.input.legislator;
  const doneCount = r.personas.filter((x) => x.state === "done").length;
  const sourceLabel = state.source === "claude" ? state.status?.persona_model : "Sample library";

  const html = [
    '<div class="col-label" style="grid-column:1">Input</div>',
    '<div class="col-label" style="grid-column:2">Synthesis</div>',
    '<div class="col-label" style="grid-column:3">Personas</div>',
    '<div class="col-label" style="grid-column:4">Voice agents</div>',
    `<div class="node span ${r.inputState}" id="n-input" style="grid-column:1;grid-row:2/${last + 1}">
      ${stateBadge(r.inputState)}
      <div class="node-head"><span class="ic">${icon("file")}</span>
        <div style="min-width:0"><div class="name">Draft output</div><div class="sub">${esc(p.title)}</div></div></div>
      <div class="tags"><span class="tag">${icon("landmark")}${esc(l.title)} ${esc(l.name)}</span>
        <span class="tag">${esc(p.state)}</span><span class="tag">${icon("dollar")}fiscal brief</span></div>
    </div>`,
    `<div class="node span ${r.synthState}" id="n-synth" style="grid-column:2;grid-row:2/${n + 2}">
      ${stateBadge(r.synthState)}
      <div class="node-head"><span class="ic">${icon("sparkles")}</span>
        <div style="min-width:0"><div class="name">Persona synthesis</div><div class="sub">${esc(sourceLabel)}</div></div></div>
      <div class="tags"><span class="tag">${doneCount}/${n} personas</span><span class="tag">diverse by role, age, gender</span></div>
      <div class="progress"><i style="width:${n ? (doneCount / n) * 100 : 0}%"></i></div>
    </div>`,
  ];

  for (let i = 0; i < n; i++) {
    const slot = r.personas[i] || { state: "pending" };
    const ps = slot.persona;
    html.push(`<div class="node ${slot.state} ${ps ? appear(`p:${ps.name}`) : ""}" id="n-p${i}" style="grid-column:3;grid-row:${i + 2}">
      ${stateBadge(slot.state)}
      <div class="node-head">${ps ? avatar(ps.name) : `<span class="ic">${icon("sparkles")}</span>`}
        <div style="min-width:0"><div class="name">${ps ? esc(ps.name) : `Persona ${i + 1}`}</div>
        <div class="sub">${ps ? `${ps.age} · ${esc(ps.occupation)}` : slot.state === "running" ? "Drafting…" : "Waiting"}</div></div></div>
      ${ps ? `<div class="tags"><span class="tag">${icon("mic")}${esc(slot.voice || "casting…")}</span>
        <span class="tag">${esc(ps.gender)} · ${esc(ps.age_band.replace("_", " "))}</span></div>` : ""}
    </div>`);
  }

  const agentNode = (a, id, row, kind, placeholder) => {
    const live = a && state.call?.agentId === a.id && !FINAL.has(state.call.data?.status ?? "initiated");
    const st = a ? (live ? "live" : "done") : "";
    const cls = a ? `clickable ${appear(`a:${a.id}`)} ${state.selected === a.id ? "selected" : ""}` : "pending";
    return `<div class="node ${cls}" id="${id}" data-kind="${kind}" ${a ? `data-id="${a.id}"` : ""} style="grid-column:4;grid-row:${row}">
      ${stateBadge(st)}
      <div class="kind">${KIND[kind].label}</div>
      <div class="node-head">${a ? avatar(a.caller, kind === "legislator" ? null : `var(--${kind})`) : `<span class="ic">${icon(KIND[kind].icon)}</span>`}
        <div style="min-width:0"><div class="name">${a ? esc(a.caller) : placeholder}</div>
        <div class="sub">${a ? `→ ${esc(a.target)}` : "Not built yet"}</div></div></div>
      ${a ? `<div class="tags"><span class="tag">${icon("mic")}${esc(a.voice)}</span>
        <span class="tag">${Object.keys(a.request.dynamic_variables).length} vars</span>
        ${a.conversations.length ? `<span class="tag">${icon("phone")}${a.conversations.length}</span>` : ""}</div>` : ""}
    </div>`;
  };
  for (let i = 0; i < n; i++) html.push(agentNode(r.legislators[i], `n-a${i}`, i + 2, "legislator", "Constituent caller"));
  html.push(agentNode(r.survey, "n-survey", n + 2, "survey", "Survey caller"));
  html.push(agentNode(r.lobbyist, "n-lobbyist", n + 3, "lobbyist", "Lobbyist caller"));

  $("#graph").innerHTML = html.join("");
  requestAnimationFrame(drawEdges);
}

function drawEdges() {
  const r = state.run;
  const n = r.phase === "idle" && !r.legislators.length ? state.count : r.n;
  const edgeState = (s) => (s === "running" ? "active" : s === "done" || s === "error" ? "done" : "");
  const edges = [["n-input", "n-synth", edgeState(r.synthState === "pending" ? r.inputState === "done" ? "running" : "" : "done")]];
  for (let i = 0; i < n; i++) {
    const slot = r.personas[i];
    edges.push(["n-synth", `n-p${i}`, edgeState(slot?.state)]);
    edges.push([`n-p${i}`, `n-a${i}`, r.legislators[i] ? "done" : slot?.state === "done" ? "active" : ""]);
  }
  const orgReady = r.personas.length === n && r.personas.every((p) => p.state === "done") && r.phase === "running";
  edges.push(["n-input", "n-survey", r.survey ? "done" : orgReady ? "active" : ""]);
  edges.push(["n-input", "n-lobbyist", r.lobbyist ? "done" : orgReady && r.survey ? "active" : ""]);

  const graph = $("#graph");
  const pos = (el) => ({ x: el.offsetLeft + graph.offsetLeft, y: el.offsetTop + graph.offsetTop, w: el.offsetWidth, h: el.offsetHeight });
  const paths = edges.map(([from, to, cls]) => {
    const a = document.getElementById(from);
    const b = document.getElementById(to);
    if (!a || !b) return "";
    const A = pos(a), B = pos(b);
    const x1 = A.x + A.w, y1 = A.y + A.h / 2, x2 = B.x, y2 = B.y + B.h / 2;
    const dx = (x2 - x1) / 2;
    return `<path class="${cls}" d="M${x1},${y1} C${x1 + dx},${y1} ${x2 - dx},${y2} ${x2},${y2}"/>`;
  });
  $("#edges").innerHTML = paths.join("");
}

/* ================= Trace ================= */

function renderTrace() {
  const r = state.run;
  if (!r.rows.length) {
    $("#trace").innerHTML = `<div class="empty">${r.legislators.length
      ? "Agents restored from the last run. Run the pipeline again to see a fresh trace."
      : "Run the pipeline to watch each step: persona synthesis, voice casting and agent assembly."}</div>`;
    $("#trace-meta").innerHTML = "";
    $("#run-meta").innerHTML = "";
    return;
  }
  const t0 = r.start;
  const t1 = r.end ?? Date.now();
  const total = Math.max(t1 - t0, 1);
  $("#trace").innerHTML = r.rows.map((row) => {
    const end = row.end ?? Date.now();
    const left = ((row.start - t0) / total) * 100;
    const width = ((end - row.start) / total) * 100;
    const span = row.end !== row.start;
    const clock = new Date(row.start).toLocaleTimeString([], { hour12: false }) + "." + String(row.start % 1000).padStart(3, "0");
    return `<div class="trow ${row.status}" style="--c:${STAGE_COLOR[row.stage]}">
      <span class="time">${clock}</span>
      <span class="stage-pill"><i></i>${STAGE_LABEL[row.stage]}</span>
      <span class="msg" title="${esc(row.msg)}">${esc(row.msg)}</span>
      <span class="lane"><span class="bar ${row.end == null ? "open" : ""}" style="left:${left}%;width:${span ? `max(${width}%,3px)` : "3px"}"></span></span>
      <span class="dur">${span ? fmtSecs(end - row.start) : ""}</span>
    </div>`;
  }).join("");
  const el = $("#trace");
  el.scrollTop = el.scrollHeight;
  const meta = `<span><b>${fmtSecs(total)}</b> elapsed</span><span><b>${r.rows.length}</b> events</span>
    <span><b>${allAgents().length}</b> agents</span>`;
  $("#trace-meta").innerHTML = meta;
  $("#run-meta").innerHTML = `<span>${r.phase === "running" ? "Running…" : r.phase === "error" ? "Failed" : "Completed"}</span>` + meta;
}

/* ================= Pipeline events ================= */

function handleEvent(ev) {
  const r = state.run;
  const t = Date.parse(ev.t);
  r.start ??= t;

  if (ev.status === "error") {
    const open = r.rows.find((x) => x.end == null);
    if (open) Object.assign(open, { end: t, status: "error", msg: ev.message });
    else r.rows.push({ stage: "error", start: t, end: t, msg: ev.message, status: "error" });
    r.phase = "error";
    r.synthState = "error";
    const slot = r.personas.find((p) => p.state === "running");
    if (slot) slot.state = "error";
    return;
  }

  if (ev.stage === "persona" && ev.status === "running") {
    r.rows.push({ stage: "persona", start: t, end: null, msg: ev.message, status: "running" });
    r.personas[ev.data.index - 1] = { state: "running" };
    r.synthState = "running";
  } else if (ev.stage === "persona") {
    const open = r.rows.find((x) => x.stage === "persona" && x.end == null);
    if (open) Object.assign(open, { end: t, msg: ev.message, status: "done" });
    r.personas[ev.data.index - 1] = { state: "running", persona: ev.data.persona };
  } else {
    r.rows.push({ stage: ev.stage, start: t, end: t, msg: ev.message, status: ev.status });
  }

  if (ev.stage === "input") r.inputState = "done";
  if (ev.stage === "voice") {
    const slot = r.personas.find((p) => p.persona && !p.voice);
    slot.voice = ev.message.match(/voice (\w+)/)?.[1];
    slot.state = "done";
  }
  if (ev.agent) {
    const a = ev.agent;
    if (a.kind === "legislator") r.legislators.push(a);
    else r[a.kind] = a;
    if (r.personas.length === r.n && r.personas.every((p) => p.state === "done")) r.synthState = "done";
  }
  if (ev.stage === "ready") {
    r.phase = "done";
    r.end = t;
  }
}

async function runPipeline() {
  const btn = $("#run");
  btn.disabled = true;
  btn.classList.add("busy");
  $("#run span").textContent = "Running…";
  stopPolling();
  state.call = null;
  state.selected = null;
  state.run = { ...emptyRun(), phase: "running", n: state.count };
  state.seen.clear();
  renderAll();
  state.ticker = setInterval(renderTrace, 120);

  try {
    const res = await fetch("/api/pipeline", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ personas: state.count, source: state.source }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const parts = buf.split("\n\n");
      buf = parts.pop();
      for (const part of parts) {
        if (!part.startsWith("data: ")) continue;
        handleEvent(JSON.parse(part.slice(6)));
        renderGraph();
        renderTrace();
      }
    }
  } catch (err) {
    handleEvent({ t: new Date().toISOString(), stage: "error", status: "error", message: err.message });
  } finally {
    clearInterval(state.ticker);
    const r = state.run;
    r.end ??= Date.now();
    if (r.phase === "running") r.phase = "done";
    btn.disabled = false;
    btn.classList.remove("busy");
    $("#run span").textContent = "Run pipeline";
    renderAll();
    if (r.phase === "done" && r.legislators[0]) select(r.legislators[0].id);
  }
}

/* ================= Inspector ================= */

function renderInspector() {
  const a = allAgents().find((x) => x.id === state.selected);
  if (!a) return renderRunSummary();
  const kind = KIND[a.kind];
  const tabs = ["call", ...(a.persona ? ["persona"] : []), "variables", "payload"];
  if (!tabs.includes(state.tab)) state.tab = "call";
  const calling = state.call?.agentId === a.id && !FINAL.has(state.call.data?.status ?? "initiated") && !state.call.error;

  $("#inspector").innerHTML = `
    <div class="insp-head" data-kind="${a.kind}">
      <div class="kind">${kind.label}</div>
      <div class="insp-title">
        ${avatar(a.caller, a.kind === "legislator" ? null : `var(--${a.kind})`)}
        <div style="min-width:0"><div class="name">${esc(a.caller)}</div><div class="sub">calls ${esc(a.target)}</div></div>
        <button class="call-btn" id="dial" ${calling ? "disabled" : ""}>${icon("phone")}${calling ? "On call" : "Call"}</button>
      </div>
      <div class="tabs">${tabs.map((t) => `<button data-tab="${t}" class="${t === state.tab ? "on" : ""}">${t[0].toUpperCase() + t.slice(1)}</button>`).join("")}</div>
    </div>
    <div class="insp-body" id="insp-body">${tabBody(a)}</div>`;
  $("#dial").onclick = () => dial(a);
  document.querySelectorAll(".tabs button").forEach((b) => (b.onclick = () => { state.tab = b.dataset.tab; renderInspector(); }));
  document.querySelectorAll(".history button").forEach((b) => (b.onclick = () => watch(a.id, b.dataset.conv)));
}

function tabBody(a) {
  if (state.tab === "persona") {
    const p = a.persona;
    return `<div><div class="section-label">Background</div><p class="prose">${esc(p.background)}</p></div>
      <div><div class="section-label">Personal impact</div><p class="prose">${esc(p.personal_impact)}</p></div>
      <div><div class="section-label">Profile</div><dl class="kv">
        <dt>Age</dt><dd>${p.age}</dd><dt>Occupation</dt><dd>${esc(p.occupation)}</dd>
        <dt>Voice</dt><dd>${esc(a.voice)} · ${esc(p.gender)}, ${esc(p.age_band.replace("_", " "))}</dd>
        <dt>Synthetic</dt><dd>${p.synthetic ? "Yes, generated, not a real constituent" : "No"}</dd></dl></div>`;
  }
  if (state.tab === "variables") {
    return `<div><div class="section-label">Built on</div><dl class="kv"><dt>Template</dt><dd>${esc(a.template)}</dd>
        <dt>Agent ID</dt><dd class="mono">${esc(a.payload.agent_id)}</dd><dt>Voice ID</dt><dd class="mono">${esc(a.voice_id)}</dd></dl></div>
      <div><div class="section-label">Dynamic variables · ${Object.keys(a.request.dynamic_variables).length}</div>
      <dl class="kv vars">${Object.entries(a.request.dynamic_variables).map(([k, v]) => `<dt>{{${esc(k)}}}</dt><dd>${esc(v)}</dd>`).join("")}</dl></div>`;
  }
  if (state.tab === "payload") {
    return `<div><div class="section-label">POST /v1/convai/twilio/outbound-call</div>
      <pre>${esc(JSON.stringify(a.payload, null, 2))}</pre></div>`;
  }
  return callBody(a);
}

function callBody(a) {
  const c = state.call?.agentId === a.id ? state.call : null;
  const d = c?.data;
  const live = c && !c.error && !FINAL.has(d?.status ?? "initiated");
  const status = c?.error ? "Call failed" : !c ? "Ready to call" : !d ? "Dialing…" : {
    initiated: "Ringing…", "in-progress": "Live", processing: "Analyzing call…", done: "Call complete", failed: "Call failed",
  }[d.status] ?? d.status;
  const sub = c?.convId ? `${c.convId.slice(0, 18)}…${d?.duration ? ` · ${d.duration}s` : ""}` : esc(a.request.to_number);
  const history = a.conversations.length > 1
    ? `<div class="history">${a.conversations.map((id, i) => `<button data-conv="${id}" class="${c?.convId === id ? "on" : ""}">Call ${i + 1}</button>`).join("")}</div>` : "";

  const transcript = d?.transcript?.length
    ? `<div><div class="section-label">Transcript</div><div class="transcript">${d.transcript.map((t) => `
        <div class="turn ${t.role === "agent" ? "agent" : "user"}">
          <div class="who">${t.role === "agent" ? "AI" : "You"}</div>
          <div><div class="meta">${t.role === "agent" ? esc(a.caller.replace(/ \(.*\)/, "")) : esc(a.target)} · ${t.at ?? 0}s</div>
          <div class="text">${esc(t.message)}</div></div></div>`).join("")}</div></div>`
    : c ? `<p class="prose" style="text-align:center;color:var(--text-3)">${live ? "Transcript streams in once you pick up." : "No transcript."}</p>` : "";

  const dc = Object.entries(d?.data_collection ?? {});
  const evals = Object.entries(d?.evaluation ?? {});
  const extracted = dc.length || evals.length || d?.summary ? `
    ${d.summary ? `<div><div class="section-label">Summary</div><p class="prose">${esc(d.summary)}</p></div>` : ""}
    ${dc.length ? `<div><div class="section-label">Extracted</div><div class="extract">${dc.map(([k, v]) =>
      `<div class="row"><span class="k">${esc(k)}</span><span>${esc(v ?? "—")}</span></div>`).join("")}</div></div>` : ""}
    ${evals.length ? `<div><div class="section-label">Evaluation</div><div class="extract">${evals.map(([k, v]) =>
      `<div class="row"><span class="k">${esc(k)}</span><span><span class="result ${esc(v)}">${esc(v)}</span></span></div>`).join("")}</div></div>` : ""}` : "";

  return `<div class="callcard">
      <div class="orb ${live ? "live" : d?.status === "done" ? "done" : ""}"></div>
      <div class="call-status">${status}</div>
      <div class="call-sub">${sub}</div>
      ${c?.error ? `<div class="call-error">${esc(c.error)}</div>` : ""}
      ${history}
    </div>${transcript}${extracted}`;
}

function renderRunSummary() {
  const r = state.run;
  const agents = allAgents();
  if (!agents.length) {
    $("#inspector").innerHTML = `<div class="placeholder"><div class="ring">${icon("graph")}</div>
      <div style="color:var(--text);font-weight:600">No agents yet</div>
      <div>Run the pipeline to turn the Draft output into persona voice agents. Then select one to inspect it and place a call.</div></div>`;
    return;
  }
  const calls = agents.reduce((s, a) => s + a.conversations.length, 0);
  $("#inspector").innerHTML = `<div class="insp-body">
    <div class="section-label">Run summary</div>
    <div class="summary-grid">
      <div class="stat"><b>${agents.length}</b><span>voice agents</span></div>
      <div class="stat"><b>${r.legislators.length}</b><span>personas</span></div>
      <div class="stat"><b>${r.start && r.end ? fmtSecs(r.end - r.start) : "—"}</b><span>build time</span></div>
      <div class="stat"><b>${calls}</b><span>calls placed</span></div>
    </div>
    <div class="placeholder" style="padding:28px 12px"><div class="ring">${icon("phone")}</div>
      <div>Select an agent in the graph to see its persona, variables and payload, and to call ${esc(state.status.allowed_numbers[0] ?? "")}.</div></div>
  </div>`;
}

function select(id) {
  state.selected = id;
  state.tab = "call";
  const a = allAgents().find((x) => x.id === id);
  if (state.call?.agentId !== id) {
    stopPolling();
    state.call = null;
    if (a?.conversations.length) watch(a.id, a.conversations.at(-1));
  }
  renderGraph();
  renderInspector();
}

/* ================= Calls ================= */

async function dial(a) {
  stopPolling();
  state.call = { agentId: a.id, convId: null, data: null, error: null };
  state.tab = "call";
  renderInspector();
  renderGraph();
  try {
    const res = await api(`/api/agents/${a.id}/call`, { method: "POST" });
    a.conversations.push(res.conversation_id);
    watch(a.id, res.conversation_id);
  } catch (err) {
    state.call.error = err.message;
    renderInspector();
    renderGraph();
  }
}

function stopPolling() {
  clearTimeout(state.poll);
  state.poll = null;
}

function watch(agentId, convId) {
  stopPolling();
  state.call = { agentId, convId, data: null, error: null };
  renderInspector();
  const tick = async () => {
    if (state.call?.convId !== convId) return;
    try {
      state.call.data = await api(`/api/conversations/${convId}`);
    } catch {
      // The conversation can 404 for a moment right after dialing.
    }
    if (state.selected === agentId && state.tab === "call") $("#insp-body").innerHTML = callBody(allAgents().find((x) => x.id === agentId));
    renderGraph();
    if (!FINAL.has(state.call.data?.status)) state.poll = setTimeout(tick, 2000);
    else if (state.selected === agentId) renderInspector();
  };
  tick();
}

/* ================= Wire up ================= */

function renderAll() {
  renderGraph();
  renderTrace();
  renderInspector();
}

function setCount(n) {
  state.count = Math.min(Math.max(n, 1), state.status.max_personas);
  $("#count").textContent = state.count;
  if (state.run.phase !== "running" && !allAgents().length) renderGraph();
}

$("#minus").onclick = () => setCount(state.count - 1);
$("#plus").onclick = () => setCount(state.count + 1);
$("#source").addEventListener("click", (e) => {
  const btn = e.target.closest("button");
  if (!btn) return;
  state.source = btn.dataset.source;
  document.querySelectorAll("#source button").forEach((b) => b.classList.toggle("on", b === btn));
  renderSourceHint();
  renderGraph();
});
$("#run").onclick = runPipeline;
$("#graph").addEventListener("click", (e) => {
  const node = e.target.closest(".node[data-id]");
  if (node) select(node.dataset.id);
});
window.addEventListener("resize", () => requestAnimationFrame(drawEdges));

(async () => {
  const [status, input, agents] = await Promise.all([api("/api/status"), api("/api/input"), api("/api/agents")]);
  Object.assign(state, { status, input });
  renderHealth();
  renderSourceHint();
  renderContext();
  // Restore the last run's agents into the graph.
  const r = state.run;
  for (const a of agents) {
    if (a.kind === "legislator") {
      r.legislators.push(a);
      r.personas.push({ state: "done", persona: a.persona, voice: a.voice });
    } else r[a.kind] = a;
  }
  if (r.legislators.length) Object.assign(r, { n: r.legislators.length, phase: "done", inputState: "done", synthState: "done" });
  renderAll();
})();
