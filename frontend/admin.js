/*
 * CampusPulse 2026 - administrator page logic (admin.html).
 *
 * Every 10 s, in parallel: GET /stats, GET /events, GET /alerts, GET /requests.
 * All four are admin routes (stats is shared with students).
 */

"use strict";

const SEVERITY_MARK = { critical: "!!", warning: "!", normal: "" };
const PRIORITY_STATE = { 3: "critical", 2: "warning", 1: "normal" };

function renderTiles(stats, requests) {
  $("kpi-events").textContent = stats.total_events ?? 0;
  $("kpi-alerts").textContent = stats.alert_count ?? 0;
  $("kpi-critical").textContent = (stats.events_by_severity || {}).critical ?? 0;
  $("kpi-urgent").textContent = requests ? (requests.urgent_count ?? 0) : (stats.urgent_requests ?? 0);

  const top = stats.top_energy_building;
  const kwh = top ? (stats.energy_kwh_by_building || {})[top] : null;
  $("kpi-energy").textContent = top ? `${top} · ${kwh} kWh` : "no data";
}

/** Occupancy: magnitude per room, status colour only when over capacity. */
function renderOccupancy(rows) {
  const host = $("occupancy-body");
  if (!rows || !rows.length) {
    host.innerHTML = '<p class="muted">No occupancy readings yet.</p>';
    return;
  }
  host.innerHTML = rows.slice(0, 12).map((row) => {
    const pct = row.load_pct ?? 0;
    // Same thresholds as the server (>100% warning, >120% critical).
    const state = pct > 120 ? "critical" : pct > 100 ? "warning" : "normal";
    const label = state === "normal" ? "" : ` <span class="sev status-${state}">${state}</span>`;
    return `
      <div class="bar-row">
        <div class="bar-head">
          <span class="bar-name">${escape(row.building)} / ${escape(row.room)}${label}</span>
          <span class="bar-value">${row.value} of ${row.capacity ?? "?"} · ${pct}%</span>
        </div>
        <div class="bar-track" role="img" aria-label="${escape(row.room)} at ${pct} percent of capacity">
          <div class="bar-fill ${state === "normal" ? "" : "is-" + state}" style="width:${Math.min(pct, 100)}%"></div>
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

/** Student requests: urgent first, then newest. Shows who raised each one. */
function renderRequests(payload) {
  const host = $("requests-body");
  const rows = (payload.requests || []).slice()
    .sort((a, b) => (b.priority - a.priority) || String(b.timestamp).localeCompare(String(a.timestamp)));
  $("requests-count").textContent = rows.length
    ? `${payload.urgent_count || 0} urgent · ${rows.length} today` : "";
  if (!rows.length) {
    host.innerHTML = '<p class="muted">No student requests today.</p>';
    return;
  }
  host.innerHTML = rows.slice(0, 30).map((r) => {
    const state = PRIORITY_STATE[r.priority] || "warning";
    return `
      <div class="alert">
        <span class="alert-mark status-${state}" aria-hidden="true">${r.priority === 3 ? "!!" : r.priority === 2 ? "!" : "·"}</span>
        <div class="alert-main">
          <div class="alert-where">
            ${escape(r.building)} / ${escape(r.room)}
            <span class="sev status-${state}">${escape(r.priority_label)}</span>
          </div>
          <div class="alert-reason">${escape(r.message)}</div>
          <div class="alert-time">${escape((r.timestamp || "").slice(11, 16))} UTC · ${escape(r.requested_by || "unknown")}</div>
        </div>
      </div>`;
  }).join("");
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

async function refresh() {
  try {
    const [stats, events, alerts, requests] = await Promise.all([
      api("/stats"), api("/events?limit=50"), api("/alerts?limit=25"), api("/requests?limit=100"),
    ]);
    const requestsBody = requests.status === 200 ? requests.body : null;

    if (stats.status === 200) {
      renderTiles(stats.body, requestsBody);
      renderOccupancy(stats.body.current_occupancy);
      renderEnergy(stats.body.energy_kwh_by_building);
      banner(stats.body.truncated
        ? "Showing a partial day: more events than the statistics window covers." : null);
    } else if (stats.status === 403) {
      banner("This account is not in the admin group.", true);
    }
    if (events.status === 200) renderEvents(events.body);
    if (alerts.status === 200) renderAlerts(alerts.body);
    if (requestsBody) renderRequests(requestsBody);

    $("updated").textContent = `Updated ${new Date().toLocaleTimeString()}`;
  } catch (err) {
    if (err.message !== "unauthenticated") {
      banner("Could not reach the API. Retrying on the next refresh.", true);
    }
  }
}

if (requireRole("admin")) {
  refresh();
  startPolling(refresh);
}
