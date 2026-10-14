# Phase 9 — Dashboard (complete, pending your review)

> **Nothing deployed.** The page was rendered and inspected locally against mock data; it has never talked to a real API.

## What we built

The dashboard — and with it, **the system exists end to end**: simulator → API → Lambda → DynamoDB → dashboard.

## Files created

| File | What it is |
|---|---|
| `frontend/index.html` | Sign-in, five KPI tiles, alerts panel, occupancy bars, energy bars, events table |
| `frontend/style.css` | All styling, dark mode included; colour assigned by job |
| `frontend/app.js` | ~250 lines: login, parallel polling, rendering, error handling, idle pause |
| `frontend/config.js` | API endpoint and polling settings, rewritten at deploy time |
| `scripts/deploy-dashboard.sh` | Builds into `frontend/.build/` and syncs to S3 — the repo's `config.js` keeps its placeholder, so a deploy never dirties `git status` |
| `docs/deployment/04-deploy-dashboard.md` | Deploy, verify, troubleshoot |
| `docs/learning/15-frontend-explained.md` | For MD — frontend vs backend trust, the colour method, the token trade-off, the polling cost argument |

## Decisions worth defending

**No framework, no build step.** Three files a teammate can read. Nothing to install, nothing to break on demo day.

**The page decides nothing that matters.** Hiding the alerts panel from `staff` is a convenience; the security control is the API returning 403. A user who edits the page in developer tools still gets nothing.

**Colour is assigned by the job it does.** Sequential blue for magnitude (energy, occupancy under capacity), the reserved status palette for state. Status colours are never reused as series colours, and every coloured mark carries a written severity word plus a glyph — so colour never carries meaning alone. Verified with a palette validator in both modes: worst adjacent CVD separation ΔE 11.3, worst normal-vision ΔE 27.6.

**Polling is a cost control.** Ten-second polling with a tab open all day is ~17,000 requests. It stops when the tab is hidden and pauses after 15 idle minutes with a visible notice.

**The token is in `sessionStorage`, and the trade-off is written down** rather than glossed: it survives a refresh but is readable by any script on the page, so the mitigations are a one-hour lifetime and zero third-party scripts.

## Testing

| Check | Status |
|---|---|
| Rendered in a real browser with mock data, light and dark, 1280px and 390px | **Executed** |
| Console errors | **Executed — none in either mode** |
| Horizontal overflow | **Executed — none at 1280px or 390px** |
| Logged-out view shows login and not the dashboard; logged-in shows the reverse | **Executed — passed after the fix below** |
| `node --check` on `app.js` and `config.js`; HTML tag balance; every id referenced by JS exists | **Executed — passed** |
| `bash -n` on the deploy script | **Executed — passed** |
| 131 backend + simulator tests | **Executed — still passing** |
| Against a real API | **Not executed — nothing deployed** |

**A real bug, found by looking at the rendered page:** the sign-in form was visible *underneath* the dashboard despite `hidden` being set correctly. The browser's stylesheet says `[hidden] { display: none }`, but our `.login-view { display: grid }` overrode it. One-line fix, `[hidden] { display: none !important; }`.

Worth recording in the report's Implementation Process section **because of how it was found**: no test would have caught it — the elements existed, the JavaScript ran cleanly, the attribute was set. Some bugs only exist visually, which is why rendering and looking is a verification step and not a nicety.

## Problems / open items

| Item | Who |
|---|---|
| Phases 4-9 all await a real `terraform apply` | Whoever deploys |
| **Still open:** the AWS account's plan and creation date (risk C5) | You |
| Tooltips are not implemented; values are printed directly on every bar instead, which suits five bars | — |

## Next phase

**Phase 10 — Monitoring and observability.** CloudWatch alarms with thresholds chosen from observed behaviour rather than guessed, a CloudWatch dashboard, the troubleshooting runbook (`20-troubleshooting.md`), and the monitoring learning document.

That one genuinely benefits from a deployed system — alarm thresholds invented before anything has run are guesses. It can be written now and tuned after deployment, but deploying first would make it better.
