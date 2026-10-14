/*
 * CampusPulse 2026 - shared page logic (loaded by all three pages).
 *
 * THE PAGES (professor's review, October 2026: one page per role)
 *   index.html    sign in, then go to the page for your role
 *   admin.html    administrators - full operations view       (admin.js)
 *   student.html  students - free rooms, report an issue,     (student.js)
 *                 follow your own requests
 *
 * This file holds what every page needs: the API helper, where the token is
 * kept, the sign-in form, the page guard and polling. Plain JavaScript, no
 * framework, no build step.
 *
 * THE PAGE GUARD IS CONVENIENCE, NOT SECURITY
 *   A student who opens admin.html is sent to student.html - but even if they
 *   edited the JavaScript to stay, every admin call would get a 403 from the
 *   API. The role decides the UI; the API decides the data.
 *
 * WHERE THE TOKEN LIVES, AND THE TRADE-OFF
 *   sessionStorage: survives a refresh, cleared when the tab closes. The
 *   token lasts one hour, the pages load no third-party scripts, and no
 *   secret is ever inside a JWT. Threat model T1.
 *
 * POLLING AND COST
 *   Polling pauses when the tab is hidden and after 15 idle minutes. A tab
 *   left open overnight would otherwise make ~17,000 requests a day.
 */

"use strict";

const CONFIG = window.CAMPUSPULSE_CONFIG || {};
const API = (CONFIG.API_URL || "").replace(/\/$/, "");
const POLL_MS = (CONFIG.POLL_SECONDS || 10) * 1000;
const IDLE_MS = (CONFIG.IDLE_PAUSE_MINUTES || 15) * 60 * 1000;

const TOKEN_KEY = "campuspulse.token";
const ROLE_KEY = "campuspulse.role";
const USER_KEY = "campuspulse.user";

const PAGE_FOR_ROLE = { admin: "admin.html", student: "student.html" };

const $ = (id) => document.getElementById(id);

/* ───────────────────────── storage ───────────────────────── */
// try/catch: a private window or blocked site data makes these throw.
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
async function api(path, options = {}) {
  const token = recall(TOKEN_KEY);
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(API + path, { ...options, headers });

  if (response.status === 401) {
    // Expired or rejected token: nothing else will work either.
    forget();
    location.replace("index.html?expired=1");
    throw new Error("unauthenticated");
  }

  let body = {};
  try { body = await response.json(); } catch (e) { /* empty body */ }
  return { status: response.status, body };
}

/* ───────────────────────── helpers ───────────────────────── */
const escape = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function banner(text, isError) {
  const el = $("banner");
  if (!el) return;
  if (!text) { el.hidden = true; return; }
  el.textContent = text;
  el.classList.toggle("is-error", Boolean(isError));
  el.hidden = false;
}

function configMissing() {
  return !API || API.includes("REPLACE_WITH");
}

/* ───────────────────────── page guard ───────────────────────── */
/**
 * Call at the top of admin.js / student.js. Sends a signed-out visitor to the
 * sign-in page and a visitor with the other role to their own page.
 */
function requireRole(role) {
  const token = recall(TOKEN_KEY);
  const actual = recall(ROLE_KEY);
  if (!token) { location.replace("index.html"); return false; }
  if (actual !== role) {
    location.replace(PAGE_FOR_ROLE[actual] || "index.html");
    return false;
  }
  $("who").textContent = `${recall(USER_KEY)} · ${actual}`;
  $("logout").addEventListener("click", () => { forget(); location.replace("index.html"); });
  return true;
}

/* ───────────────────────── polling ───────────────────────── */
function startPolling(refresh) {
  let timer = null;
  let lastInteraction = Date.now();
  let paused = false;
  const state = $("poll-state");

  function start() {
    if (timer) clearInterval(timer);
    paused = false;
    if (state) state.textContent = `Auto-refresh every ${POLL_MS / 1000}s`;
    timer = setInterval(() => {
      if (document.hidden) return;                  // nobody is looking
      if (Date.now() - lastInteraction > IDLE_MS) { // nobody is there at all
        clearInterval(timer);
        timer = null;
        paused = true;
        if (state) state.textContent = "Auto-refresh paused to save cost — press Refresh to resume";
        return;
      }
      refresh();
    }, POLL_MS);
  }

  ["click", "keydown", "mousemove"].forEach((evt) =>
    window.addEventListener(evt, () => { lastInteraction = Date.now(); }, { passive: true }));
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && !paused) refresh();
  });
  const button = $("refresh");
  if (button) {
    button.addEventListener("click", () => {
      lastInteraction = Date.now();
      if (paused) start();
      refresh();
    });
  }
  start();
}

/* ───────────────────────── sign-in page ───────────────────────── */
function initLoginPage() {
  const form = $("login-form");
  const error = $("login-error");

  if (configMissing()) {
    error.textContent = "config.js has no API endpoint yet — see docs/deployment/04-deploy-dashboard.md";
    error.hidden = false;
    $("login-btn").disabled = true;
    return;
  }
  if (new URLSearchParams(location.search).has("expired")) {
    error.textContent = "Your session expired. Please sign in again.";
    error.hidden = false;
  }
  // Already signed in: go straight to the right page.
  const role = recall(ROLE_KEY);
  if (recall(TOKEN_KEY) && PAGE_FOR_ROLE[role]) {
    location.replace(PAGE_FOR_ROLE[role]);
    return;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = $("login-btn");
    error.hidden = true;
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
        // Same message for wrong password and unknown user (no enumeration).
        error.textContent = body.message || "Sign in failed";
        error.hidden = false;
        return;
      }
      if (!PAGE_FOR_ROLE[body.role]) {
        error.textContent = "This account has no CampusPulse role yet. Ask an administrator to add it to the admin or student group.";
        error.hidden = false;
        return;
      }

      store(TOKEN_KEY, body.id_token);
      store(ROLE_KEY, body.role);
      store(USER_KEY, body.username);
      $("password").value = "";
      location.replace(PAGE_FOR_ROLE[body.role]);
    } catch (err) {
      error.textContent = "Could not reach the API. Check the endpoint in config.js and your network.";
      error.hidden = false;
    } finally {
      button.disabled = false;
      button.textContent = "Sign in";
    }
  });
}

if ($("login-form")) initLoginPage();
