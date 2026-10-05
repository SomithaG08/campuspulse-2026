# Phase 12 — Deployment and Verification (complete, pending your review)

> **This is the phase I cannot finish for you.** Everything written since Phase 4 now meets a real AWS account — or does not. What this phase produced is the procedure, the checks and the evidence list; the results have to be yours.

## What we built

The runbook, two verification scripts, and the evidence checklist.

## Files created

| File | What it is |
|---|---|
| `docs/deployment/05-runbook.md` | One ordered sequence, empty account to working demo, ~90 min, with a checkpoint and a stop condition at every stage |
| `scripts/verify-deployment.sh` | ~22 checks that what is *deployed* matches what was *designed* |
| `scripts/smoke-test.sh` | Six checks in ~15 s, to run 10 minutes before the presentation |
| `docs/evidence/CHECKLIST.md` | Every artefact the report needs, mapped to the requirement it satisfies, with a folder convention and redaction rules |

## Why two scripts rather than one

**`verify-deployment.sh`** answers *"is the deployment correct?"* — and it checks the things "apply complete" does not tell you: PITR actually on, TTL actually enabled, log retention 7 days rather than forever, both Cognito groups present, and **no EC2, no RDS, no NAT Gateway running**. That last check is unusual and deliberate: evidence of what is *not* running is what makes a low-cost claim credible.

**`smoke-test.sh`** answers *"is it working right now?"* and does one more thing — **it pays the cold start**, so the first request the examiner sees is warm. It also asserts that 58 people in A203 comes back `critical`, which means the demo's centrepiece is verified before anyone is watching.

## Decisions worth defending

**The budget is a stop condition, not a step.** No budget alert, no further deploying. A billing alert added after the resources is a smoke detector installed after the fire.

**Stage 7 is a teammate deploying from the guide alone.** That is the only honest test of "reproducible deployment" (requirement I4), and the only one that can fail usefully. Whatever they get stuck on is a documentation gap, and it belongs in the report's Implementation Process section.

**The restore must actually be performed and timed.** `R4 — elapsed restore time` turns "our RTO is about 20 minutes" into "we measured it: 18 minutes". One of those is a claim; the other is a finding.

## Testing

| Check | Status |
|---|---|
| `bash -n` on both scripts | **Executed — passed** |
| `smoke-test.sh` exits 2 with a clear message when unconfigured | **Executed — verified** |
| 131 unit tests | **Executed — still passing** |
| Either script against real AWS | **Not executed — nothing deployed** |

## Problems / open items

Everything in this phase is open until someone deploys. In order:

| # | Step | Owner |
|---|---|---|
| 1 | Record the account's plan and creation date (**risk C5**, open since Phase 2) | You |
| 2 | Stage 1-3: foundation, users, verification. 📸 budget, 📸 verification output | state owner |
| 3 | Stage 4-5: dashboard, API tests, simulator run. **Commit the real `api-test-results.json`** | Madhavan |
| 4 | Stage 6: alarm into ALARM, **restore rehearsed and timed**, credit balance | MD |
| 5 | Stage 7: a teammate deploys from the guide alone | anyone but the author |
| 6 | Record the backup demo video | Madhavan |

## Next phase

**Phase 13 — Learning documentation audit.** Re-read every learning document against the code as it now stands and fix anything that drifted; confirm each component has one; check the glossary covers every term the report and slides will use.

Phase 13 needs no deployment, so it can run in parallel with your deployment work. After it: the report (14), the presentation and demo (15), and the final requirement audit (16).
