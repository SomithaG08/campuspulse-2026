/*
 * CampusPulse 2026 - student page logic (student.html).
 *
 * Uses only the routes a student may call:
 *   GET  /stats     free rooms and building comfort (no personal data)
 *   POST /requests  report a problem
 *   GET  /requests  the student's OWN requests (the API decides whose)
 */

"use strict";

const PRIORITY_STATE = { 3: "critical", 2: "warning", 1: "normal" };
let layoutLoaded = false;

/** Availability in words, so the colour never carries the meaning alone. */
function availability(pct) {
  if (pct === null || pct === undefined) return { word: "no data", state: "" };
  if (pct >= 100) return { word: "full", state: "critical" };
  if (pct >= 80) return { word: "busy", state: "warning" };
  return { word: "space available", state: "normal" };
}

function renderRooms(rows) {
  const host = $("rooms-body");
  if (!rows || !rows.length) {
    host.innerHTML = '<p class="muted">No occupancy readings yet today.</p>';
    $("kpi-free").textContent = "–";
    $("kpi-full").textContent = "–";
    return;
  }
  // Most free seats first - that is the question a student is asking.
  const sorted = rows.slice().sort((a, b) =>
    ((b.capacity || 0) - b.value) - ((a.capacity || 0) - a.value));
  $("kpi-free").textContent = rows.filter((r) => (r.load_pct ?? 100) < 100).length;
  $("kpi-full").textContent = rows.filter((r) => (r.load_pct ?? 0) >= 100).length;

  host.innerHTML = sorted.map((row) => {
    const pct = row.load_pct;
    const a = availability(pct);
    const free = row.capacity ? Math.max(row.capacity - row.value, 0) : "?";
    return `
      <div class="bar-row">
        <div class="bar-head">
          <span class="bar-name">${escape(row.building)} / ${escape(row.room)}
            <span class="sev status-${a.state}">${a.word}</span></span>
          <span class="bar-value">${free} free seats of ${row.capacity ?? "?"}</span>
        </div>
        <div class="bar-track" role="img" aria-label="${escape(row.room)}: ${pct ?? 0} percent full">
          <div class="bar-fill ${a.state === "normal" ? "" : "is-" + a.state}" style="width:${Math.min(pct ?? 0, 100)}%"></div>
        </div>
      </div>`;
  }).join("");
}

function renderComfort(avgTemp) {
  const host = $("comfort-body");
  const entries = Object.entries(avgTemp || {});
  if (!entries.length) {
    host.innerHTML = '<p class="muted">No temperature readings yet today.</p>';
    return;
  }
  host.innerHTML = entries.map(([building, t]) => {
    const word = t < 18 ? "cold" : t > 26 ? "warm" : "comfortable";
    const state = word === "comfortable" ? "normal" : "warning";
    return `
      <div class="bar-row">
        <div class="bar-head">
          <span class="bar-name">${escape(building)}</span>
          <span class="bar-value">${t} °C · <span class="sev status-${state}">${word}</span></span>
        </div>
      </div>`;
  }).join("");
}

function renderMine(payload) {
  const host = $("mine-body");
  const rows = payload.requests || [];
  $("kpi-mine").textContent = rows.length;
  $("mine-count").textContent = rows.length ? `${rows.length} sent` : "";
  if (!rows.length) {
    host.innerHTML = '<p class="muted">You have not reported anything yet.</p>';
    return;
  }
  host.innerHTML = rows.map((r) => {
    const state = PRIORITY_STATE[r.priority] || "warning";
    return `
      <div class="alert">
        <div class="alert-main">
          <div class="alert-where">
            ${escape(r.building)} / ${escape(r.room)}
            <span class="sev status-${state}">${escape(r.priority_label)}</span>
          </div>
          <div class="alert-reason">${escape(r.message)}</div>
          <div class="alert-time">Sent ${escape((r.timestamp || "").replace("T", " ").slice(0, 16))} UTC · received by operations</div>
        </div>
      </div>`;
  }).join("");
}

/** Room picker built from the campus layout the API returns, so it can never
 *  offer a room the validator would reject. */
function fillLayout(layout) {
  if (layoutLoaded || !layout) return;
  const building = $("req-building");
  const room = $("req-room");
  building.innerHTML = Object.keys(layout)
    .map((b) => `<option value="${escape(b)}">${escape(b)}</option>`).join("");
  const fillRooms = () => {
    room.innerHTML = (layout[building.value] || [])
      .map((r) => `<option value="${escape(r)}">${escape(r)}</option>`).join("");
  };
  building.addEventListener("change", fillRooms);
  fillRooms();
  layoutLoaded = true;
}

$("request-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = $("req-btn");
  const result = $("req-result");
  result.hidden = true;
  button.disabled = true;
  button.textContent = "Sending…";
  try {
    const { status, body } = await api("/requests", {
      method: "POST",
      body: JSON.stringify({
        building: $("req-building").value,
        room: $("req-room").value,
        priority: Number($("req-priority").value),
        message: $("req-message").value.trim(),
      }),
    });
    if (status === 201) {
      result.textContent = Number($("req-priority").value) === 3
        ? "Sent. Urgent requests are emailed to the operations team immediately."
        : "Sent. Campus operations can see it now.";
      result.className = "form-result ok";
      $("req-message").value = "";
      refresh();
    } else {
      result.textContent = body.message || "Could not send the request.";
      result.className = "form-result error";
    }
    result.hidden = false;
  } catch (err) {
    if (err.message !== "unauthenticated") {
      result.textContent = "Could not reach the API. Please try again.";
      result.className = "form-result error";
      result.hidden = false;
    }
  } finally {
    button.disabled = false;
    button.textContent = "Send request";
  }
});

async function refresh() {
  try {
    const [stats, mine] = await Promise.all([api("/stats"), api("/requests?limit=20")]);
    if (stats.status === 200) {
      fillLayout(stats.body.layout);
      renderRooms(stats.body.current_occupancy);
      renderComfort(stats.body.avg_temperature_c);
      banner(null);
    } else if (stats.status === 403) {
      banner("This account is not in the student group.", true);
    }
    if (mine.status === 200) renderMine(mine.body);
    $("updated").textContent = `Updated ${new Date().toLocaleTimeString()}`;
  } catch (err) {
    if (err.message !== "unauthenticated") {
      banner("Could not reach the API. Retrying on the next refresh.", true);
    }
  }
}

if (requireRole("student")) {
  refresh();
  startPolling(refresh);
}
