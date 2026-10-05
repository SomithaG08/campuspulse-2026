# Phase 8 — Simulator (complete, pending your review)

> **Still nothing deployed.** The simulator runs and is tested locally in `--dry-run`; it has never sent a request to a real API.

## What we built

The data source. `simulator/simulator.py` — 1 file, no dependencies, 16 tests.

## Files created

| File | What it is |
|---|---|
| `simulator/simulator.py` | Device login with token refresh, realistic per-type generation, `--interval`, `-n/--number-of-events`, `--anomaly-rate`, `--force-alert`, `--dry-run`, `--seed` |
| `simulator/tests/test_generator.py` | 18 tests, including 1000 generated events run through the backend's real validator |
| `simulator/tests/conftest.py` | Import paths |
| `simulator/requirements.txt` | Deliberately empty, with the reasoning |
| `docs/learning/14-simulator-explained.md` | For Madhavan — what it generates, the time-of-day curve, the guard rails, the token, and why zero dependencies |
| `simulator/README.md` | Quick reference |

## Four decisions worth defending

**It imports the backend's `campus_config.py` and `rules.py`.** Not a copy — the same files. Room capacities, energy baselines and thresholds exist in exactly one place, so the simulator and the server cannot disagree. Two import lines close the integration risk that breaks most team projects.

**Zero dependencies.** `urllib` instead of `requests`. Slightly clumsier code in exchange for "no pip install" — four laptops, nothing to break on demo day. For a tool whose only job is to work during a live demonstration, that trade is the right way round.

**Credentials come from the environment, never from arguments.** A password passed as a flag lands in shell history and the process list.

**A time-of-day occupancy curve** rather than random numbers: empty overnight, filling from 8, peaks late morning and mid afternoon, a lunch dip. Noise looks like a toy; a daily rhythm looks like a system, and the professor will be looking at that dashboard.

## Cost guard rails, each with a test

`--interval` below 0.5 s refused · `-n` above 10,000 refused · `--anomaly-rate` outside 0–1 refused · no API URL unless `--dry-run`.

## Testing

| Check | Status |
|---|---|
| **131 tests total** (113 backend + 18 simulator) | **Executed — 131 passed in 1.0s** |
| 1000 generated events through the backend's **real** validator | **Executed — zero rejections.** The simulator cannot produce an event the API refuses |
| `--force-alert` always yields `critical`, over 300 events | **Executed — passed** |
| Every building/room/unit valid; all six types appear; ids unique; same seed reproduces the run | **Executed — passed** |
| `--dry-run` end to end at several seeds | **Executed — output as expected** |
| Against a real API | **Not executed — nothing deployed** |

**Two things the tests caught, both worth recording for the report's Implementation Process section:**

1. **`--force-alert` was unreliable.** The anomalous occupancy range (105–145 % of capacity) straddles the 120 % critical threshold, so a forced event sometimes produced only a warning. A demo alert that sometimes lands as something milder is a demo that sometimes does not land. Forced events now use ranges comfortably past critical, verified over 300 runs.
2. **A test assumption of mine was wrong, and the investigation was useful.** `anomaly_rate=0` still produced warnings. Cause: a routine priority-2 service request maps to `warning` in the data model — severity for a request comes from the requester's chosen priority, not from a sensor being out of range. That is correct behaviour, so the test was split: no *sensor* alerts at zero anomaly rate, and routine requests are never *critical*.

## Problems / open items

| Item | Who |
|---|---|
| Phases 4-8 all await a real `terraform apply` | Whoever deploys |
| **Still open:** the AWS account's plan and creation date (risk C5) | You |
| In `--dry-run` all events share one timestamp because pacing is skipped; harmless, and real runs are spaced by `--interval` | — |

## Next phase

**Phase 9 — Dashboard.** `frontend/index.html`, `app.js`, `style.css`: login form, KPI tiles, recent events, the alerts panel, occupancy and energy views, polling every 10 s. No framework, no build step. Plus the frontend learning document and the S3 upload step in the deployment guide.

After Phase 9 the whole system exists end to end, and the remaining phases are monitoring, testing, deployment evidence, the report and the presentation.
