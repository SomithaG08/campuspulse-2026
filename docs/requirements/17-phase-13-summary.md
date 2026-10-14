# Phase 13 — Documentation Audit (complete, pending your review)

> This phase was a mechanical check of the documentation against the code, then fixing what it found. Not a read-through — a script.

## What the audit checked

A script that: resolves every repo-relative file path cited in any `.md`; compares quoted counts (tests, Terraform resources, alarms, routes) against reality; re-runs the data model's worked example through the live rules module to confirm the quoted reason string still matches; compares the API contract's endpoints against the routes actually declared in Terraform; and checks the glossary for terms the other documents lean on.

## What it found — nine real problems

| Finding | Fix |
|---|---|
| `docs/architecture/networking.md` cited **twice**, never written | Written as `docs/learning/11-networking-explained.md`; both references repointed |
| `docs/architecture/data-model.md` cited in the risk register — wrong filename | Corrected to `04-data-model.md` |
| `02-deploy-foundation.md` told you to expect **26 resources**; the stack is now 61 | Corrected, with the stage-by-stage figure kept as a parenthetical |
| `03-deploy-backend.md` said **~19 resources** without saying "in addition to" | Corrected |
| Glossary missing **EMF**, though two documents rely on it | Added |
| Glossary missing **p95**, used in the monitoring doc | Added |
| Glossary said we have **three alarms**; there are four | Corrected |
| Nine learning documents the brief lists did not exist | Four written (below); five mapped to where that content already lives |

**What it confirmed as still true:** every other cited path resolves; all seven contract endpoints are declared as routes and no route is undocumented; every event type and unit in the data model matches `campus_config.py`; and the worked example still produces exactly `occupancy 58 exceeds 120% of capacity 45` from the live code.

**Note on the phase summaries:** these quote 26, 45 and 54 resources. Those were correct *for that phase* and are historical records, so they were deliberately left alone. Only forward-looking instructions were corrected.

## Files created

| File | Why it was needed |
|---|---|
| `docs/learning/11-networking-explained.md` | Required by spec §18, cited twice, never written. VPC, subnets, security groups, what our stack would look like with them, the NAT Gateway cost argument, and the honest "is no VPC less secure?" |
| `docs/learning/12-serverless-explained.md` | The term is used throughout and was never defined. Includes what serverless *costs* us and when it is the wrong choice |
| `docs/learning/13-big-data-and-analytics.md` | **Required by spec §29** and the single most likely oral question in this module. Where each Big Data idea lives in our code, why thresholds instead of ML, and precisely what changes at 1000× |
| `docs/learning/19-disaster-recovery.md` | Required by spec §21. RPO/RTO with reasons, PITR, the restore procedure — **and an RTO left as a blank until it is measured** |
| `docs/learning/README.md` | Index with owners, plus a table mapping the brief's remaining topics to where that content actually lives |

## Decisions worth defending

**Five of the brief's listed documents were deliberately not written.** Cloud basics, AWS basics, project architecture, data flow and costs are already covered properly — in `00-start-here.md`, `03-services-explained.md`, `01-architecture-decisions.md`, `06-data-flow.md` and `01-cost-model.md`. Creating near-duplicate files would produce two versions of each fact, which disagree by submission week. The index says where each topic lives instead.

**The DR document leaves RTO blank on purpose.** It gets filled from the restore rehearsal in Phase 12. Writing a number now would be inventing evidence, which is the one thing this project does not do.

## Testing

| Check | Status |
|---|---|
| Audit script across all documentation | **Executed — 9 problems found, all fixed** |
| Re-run after fixes: dead references | **Executed — none remain** |
| Worked example re-checked against live code | **Executed — still exact** |
| Contract endpoints vs declared routes | **Executed — all seven match, none undocumented** |
| 131 unit tests | **Executed — still passing** |

## Problems / open items

| Item | Who |
|---|---|
| The audit is a one-off script, not saved as a repeatable check. Re-run it after any large documentation change | — |
| RTO in `19-disaster-recovery.md` stays blank until the restore is rehearsed | MD |
| **Still open:** the AWS account's plan and creation date (risk C5) | You |

## Next phase

**Phase 14 — The academic report.** All eleven sections the spec requires, assembled from what this project has actually produced — with `[INSERT SCREENSHOT HERE]` wherever real evidence is still missing, and no invented results anywhere.
