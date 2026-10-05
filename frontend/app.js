/*
 * CampusPulse 2026 - dashboard logic.
 *
 * Plain JavaScript, no framework, no build step. Roughly 250 lines, which any
 * teammate can read in one sitting.
 *
 * WHAT IT DOES
 *   1. signs in through POST /login and keeps the token
 *   2. every 10s calls GET /stats, GET /alerts and GET /events
 *   3. renders tiles, bars, an alerts list and a table
 *   4. stops polling when nobody is looking - see POLLING AND COST below
 *
 * WHERE THE TOKEN LIVES, AND THE TRADE-OFF
 *   sessionStorage. It survives a page refresh (so an accidental F5 mid-demo
 *   does not log you out) and is cleared when the tab closes. The safer
 *   alternative is a plain variable, which no script could ever read back but
 *   which loses the session on every refresh.
 *   The real mitigations are elsewhere: the token lasts one hour, this page
 *   loads no third-party scripts at all, and we never put a secret inside a
 *   JWT. Written up in docs/security/01-threat-model.md under T1.
 *
 * POLLING AND COST
 *   Polling is a cost decision as much as a UX one. A tab left open overnight
 *   at 10-second intervals would make roughly 17,000 requests a day against a
 *   pay-per-request API. So: polling pauses when the tab is hidden, and pauses
 *   again after 15 idle minutes with a visible notice. The brief asks for cost
 *   awareness; this is what it looks like in code.
 */

"use strict";

const CONFIG = window.CAMPUSPULSE_CONFIG || {};
const API = (CONFIG.API_URL || "").replace(/\/$/, "");
const POLL_MS = (CONFIG.POLL_SECONDS || 10) * 1000;
const IDLE_MS = (CONFIG.IDLE_PAUSE_MINUTES || 15) * 60 * 1000;

const TOKEN_KEY = "campuspulse.token";
const ROLE_KEY = "campuspulse.role";
const USER_KEY = "campuspulse.user";

const SEVERITY_MARK = { critical: "!!", warning: "!", normal: "" };

let timer = null;
let lastInteraction = Date.now();
let paused = false;

const $ = (id) => document.getElementById(id);

/* ───────────────────────── storage ───────────────────────── */
// Wrapped in try/catch: a private window or blocked site data makes these
// throw, and a dashboard that cannot remember a token should still work.
function store(key, value) {
  try { sessionStorage.setItem(key, value); } catch (e) { /* ignore */ }
}
function recall(key) {
  try { return sessionStorage.getItem(key); } catch (e) { return null; }
}
function forget() {
  [TOKEN_KEY, ROLE_KEY, USER_KEY].forEach((k) => {
    try { sessionStorage.removeItem(k); } catch (e) { /* ignore */ }
  });
}

/* ───────────────────────── HTTP ───────────────────────── */
/**
 * One place where every API call goes, so authentication, error shapes and
 * the 401 response are handled once rather than in five places.
 */
async function api(path, options = {}) {
  const token = recall(TOKEN_KEY);
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(API + path, { ...options, headers });

  if (response.status === 401) {
    // The token expired or was rejected. Nothing else will work either.
    forget();
    showLogin("Your session expired. Please sign in again.");
    throw new Error("unauthenticated");
  }

  let body = {};
  try { body = await response.json(); } catch (e) { /* empty body */ }
  return { status: response.status, body };
}

/* ───────────────────────── views ───────────────────────── */
function showLogin(message) {
  stopPolling();
  $("dash-view").hidden = true;
  $("session").hidden = true;
  $("login-view").hidden = false;
  if (message) {
    $("login-error").textContent = message;
    $("login-error").hidden = false;
  }
}

function showDashboard() {
  $("login-view").hidden = true;
  $("dash-view").hidden = false;
  $("session").hidden = false;
  $("who").textContent = `${recall(USER_KEY)} · ${recall(ROLE_KEY)}`;
  // Staff get a 403 on /alerts, so the panel is removed rather than left
  // showing an error. The role decides the UI; the API decides the data.
  $("alerts-card").hidden = recall(ROLE_KEY) !== "ops";
}

function banner(text, isError) {
  const el = $("banner");
  if (!text) { el.hidden = true; return; }
  el.textContent = text;
  el.classList.toggle("is-error", Boolean(isError));
  el.hidden = false;
}

/* ───────────────────────── login ───────────────────────── */
$("login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = $("login-btn");
  $("login-error").hidden = true;
  button.disabled = true;
  button.textContent = "Signing in…";

  try {
    const response = await fetch(`${API}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: $("username").value.trim(),
        password: $("password").value,
      }),
    });
    const body = await response.json();

    if (response.status !== 200) {
      // Deliberately shows the server's message unchanged: it says
      // "Incorrect username or password" for both wrong-password and
      // unknown-user, so this form cannot be used to discover accounts.
      $("login-error").textContent = body.message || "Sign in failed";
      $("login-error").hidden = false;
      return;
    }

    store(TOKEN_KEY, body.id_token);
    store(ROLE_KEY, body.role);
    store(USER_KEY, body.username);
    $("password").value = "";
    showDashboard();
    await refresh();
    startPolling();
  } catch (err) {
    $("login-error").textContent =
      "Could not reach the API. Check the endpoint in config.js and your network.";
    $("login-error").hidden = false;
  } finally {
    button.disabled = false;
    button.textContent = "Sign in";
  }
});

$("logout").addEventListener("click", () => {
  forget();
  location.reload();
});
$("refresh").addEventListener("click", () => {
  lastInteraction = Date.now();
  if (paused) startPolling();
  refresh();
});

/* ───────────────────────── rendering ───────────────────────── */
const escape = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function renderTiles(stats) {
  $("kpi-events").textContent = stats.total_events ?? 0;
  $("kpi-alerts").textContent = stats.alert_count ?? 0;
  $("kpi-critical").textContent = (stats.events_by_severity || {}).critical ?? 0;
  $("kpi-urgent").textContent = stats.urgent_requests ?? 0;

  const top = stats.top_energy_building;
  const kwh = top ? (stats.energy_kwh_by_building || {})[top] : null;
  $("kpi-energy").textContent = top ? `${top} · ${kwh} kWh` : "no data";
}

/** Occupancy: magnitude per room, with status colour only when over capacity. */
function renderOccupancy(rows) {
  const host = $("occupancy-body");
  if (!rows || !rows.length) {
    host.innerHTML = '<p class="muted">No occupancy readings yet.</p>';
    return;
  }
  host.innerHTML = rows.slice(0, 12).map((row) => {
    const pct = row.load_pct ?? 0;
    // Over 120% is critical, over 100% a warning - the same thresholds the
    // server applies, so the bar and the alert can never disagree.
    const state = pct > 120 ? "critical" : pct > 100 ? "warning" : "normal";
    const width = Math.min(pct, 100);
    const label = state === "normal" ? "" :
      ` <span class="sev status-${state}">${state}</span>`;
    return `
      <div class="bar-row">
        <div class="bar-head">
          <span class="bar-name">${escape(row.building)} / ${escape(row.room)}${label}</span>
          <span class="bar-value">${row.value} of ${row.capacity ?? "?"} · ${pct}%</span>
        </div>
        <div class="bar-track" role="img"
             aria-label="${escape(row.room)} at ${pct} percent of capacity">
          <div class="bar-fill ${state === "normal" ? "" : "is-" + state}"
               style="width:${width}%"></div>
        </div>
      </div>`;
  }).join("");
}

/** Energy: one series, one hue, every bar directly labelled. */
function renderEnergy(byBuilding) {
  const host = $("energy-body");
  const entries = Object.entries(byBuilding || {}).sort((a, b) => b[1] - a[1]);
  if (!entries.length) {
    host.innerHTML = '<p class="muted">No energy readings yet.</p>';
    return;
  }
  const max = entries[0][1] || 1;
  host.innerHTML = entries.map(([building, kwh]) => `
    <div class="bar-row">
      <div class="bar-head">
        <span class="bar-name">${escape(building)}</span>
        <span class="bar-value">${kwh} kWh</span>
      </div>
      <div class="bar-track" role="img" aria-label="${escape(building)}: ${kwh} kilowatt hours">
        <div class="bar-fill" style="width:${Math.round((kwh / max) * 100)}%"></div>
      </div>
    </div>`).join("");
}

function renderAlerts(payload) {
  const host = $("alerts-body");
  const alerts = payload.alerts || [];
  $("alerts-count").textContent = alerts.length
    ? `${payload.critical_count || 0} critical · ${payload.warning_count || 0} warning`
    : "";

  if (!alerts.length) {
    host.innerHTML = '<p class="muted">Nothing abnormal. All readings within range.</p>';
    return;
  }
  host.innerHTML = alerts.slice(0, 25).map((a) => `
    <div class="alert">
      <span class="alert-mark status-${escape(a.severity)}" aria-hidden="true">${SEVERITY_MARK[a.severity] || "!"}</span>
      <div class="alert-main">
        <div class="alert-where">
          ${escape(a.building)} / ${escape(a.room)}
          <span class="sev status-${escape(a.severity)}">${escape(a.severity)}</span>
        </div>
        <div class="alert-reason">${escape(a.reason || a.event_type)}</div>
        <div class="alert-time">${escape(a.timestamp)}</div>
      </div>
    </div>`).join("");
}

function renderEvents(payload) {
  const rows = payload.events || [];
  $("events-count").textContent = rows.length ? `${rows.length} most recent` : "";
  $("events-body").innerHTML = rows.length
    ? rows.map((e) => `
        <tr>
          <td>${escape((e.timestamp || "").slice(11, 19))}</td>
          <td>${escape(e.building)} / ${escape(e.room)}</td>
          <td>${escape(e.event_type)}</td>
          <td class="num">${escape(e.value)} ${escape(e.unit)}</td>
          <td><span class="sev status-${escape(e.severity)}">${escape(e.severity)}</span></td>
        </tr>`).join("")
    : '<tr><td colspan="5" class="muted">No events yet. Start the simulator.</td></tr>';
}

/* ───────────────────────── refresh ───────────────────────── */
async function refresh() {
  const isOps = recall(ROLE_KEY) === "ops";
  try {
    // One round trip each, in parallel. Promise.all means the slowest call
    // sets the refresh time, not the sum of all three.
    const calls = [api("/stats"), api("/events?limit=50")];
    if (isOps) calls.push(api("/alerts?limit=25"));
    const [stats, events, alerts] = await Promise.all(calls);

    if (stats.status === 200) {
      renderTiles(stats.body);
      renderOccupancy(stats.body.current_occupancy);
      renderEnergy(stats.body.energy_kwh_by_building);
      if (stats.body.truncated) {
        banner("Showing a partial day: more events than the statistics window covers.");
      } else {
        banner(null);
      }
    }
    if (events.status === 200) renderEvents(events.body);
    if (alerts && alerts.status === 200) renderAlerts(alerts.body);

    $("updated").textContent = `Updated ${new Date().toLocaleTimeString()}`;
  } catch (err) {
    if (err.message !== "unauthenticated") {
      banner("Could not reach the API. Retrying on the next refresh.", true);
    }
  }
}

/* ───────────────────────── polling ───────────────────────── */
function startPolling() {
  stopPolling();
  paused = false;
  $("poll-state").textContent = `Auto-refresh every ${POLL_MS / 1000}s`;
  timer = setInterval(() => {
    if (document.hidden) return;                 // nobody is looking
    if (Date.now() - lastInteraction > IDLE_MS) { // nobody is there at all
      pausePolling();
      return;
    }
    refresh();
  }, POLL_MS);
}

function stopPolling() {
  if (timer) clearInterval(timer);
  timer = null;
}

function pausePolling() {
  stopPolling();
  paused = true;
  $("poll-state").textContent = "Auto-refresh paused to save cost — press Refresh to resume";
}

["click", "keydown", "mousemove"].forEach((evt) =>
  window.addEventListener(evt, () => { lastInteraction = Date.now(); }, { passive: true }));

document.addEventListener("visibilitychange", () => {
  if (!document.hidden && !paused && recall(TOKEN_KEY)) refresh();
});

/* ───────────────────────── start ───────────────────────── */
(function init() {
  if (!API || API.includes("REPLACE_WITH")) {
    showLogin("config.js has no API endpoint yet — see docs/deployment/04-deploy-dashboard.md");
    $("login-btn").disabled = true;
    return;
  }
  if (recall(TOKEN_KEY)) {
    // A refresh mid-session returns straight to the dashboard. If the stored
    // token has since expired, the first call gets a 401 and api() sends us
    // back to the login view.
    showDashboard();
    refresh();
    startPolling();
  } else {
    showLogin();
  }
})();
