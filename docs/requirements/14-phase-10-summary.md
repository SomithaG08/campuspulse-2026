# Phase 10 — Monitoring and Observability (complete, pending your review)

> **Nothing deployed.** Alarms and the dashboard are defined in Terraform; none has ever evaluated against real data.

## What we built

Four alarms, one dashboard, the troubleshooting runbook, and the monitoring learning document.

## Files created

| File | What it is |
|---|---|
| `infrastructure/terraform/alarms.tf` | 4 alarms, 1 dashboard (6 widgets), optional SNS email behind a variable |
| `docs/learning/20-troubleshooting.md` | Every failure mode the brief lists — 400/401/403/429/500, Lambda, DynamoDB, dashboard, login, simulator, deployment, Terraform — each with cause, where to look, fix, and how to verify |
| `docs/learning/09-cloudwatch-monitoring.md` | For MD — logs vs metrics vs alarms, why structured JSON, EMF, p95, free-tier budget, and how to produce alarm evidence |

## Files changed

`variables.tf` (alarm thresholds + `alarm_email`) · `outputs.tf` (dashboard URL, alarm names).

## The four alarms

| Alarm | Fires when | Watches |
|---|---|---|
| `ingest-errors` | ≥ 1 Lambda error in 5 min | the system |
| `api-5xx` | ≥ 1 server error in 5 min | the front door |
| `alert-burst` | ≥ 20 alerts in 5 min | **the campus** |
| `invocation-ceiling` | ≥ 2000 invocations in 5 min | **the budget** |

Three infrastructure, one domain, one of them explicitly a cost control. Well inside the free allowance: 4 of 10 alarms, 1 of 3 dashboards, 3 of 10 custom metrics.

## Decisions worth defending

**Two thresholds are labelled as guesses, in the code.** A threshold invented before a system has run is a guess; they are variables so a real run can correct them, and the report records both numbers. That is a better story than a figure that was always mysteriously right.

**`treat_missing_data = "notBreaching"`.** Without it, a quiet period leaves alarms grey at `INSUFFICIENT_DATA`. A console full of grey alarms teaches everyone to ignore alarms, which is worse than having none.

**Email is opt-in.** Set `alarm_email` and you get SNS; leave it empty and alarms simply change state, which is enough to demonstrate. The optional feature from the scope document is available without being imposed.

**Metrics are split by severity only.** Every distinct dimension combination is a separate custom metric against a 10-metric allowance — splitting by building would be five per counter, by room eleven. A cost decision inside a monitoring decision.

## Testing

| Check | Status |
|---|---|
| Terraform structural validation: 13 files, **61 resources**, 4 alarms, 1 dashboard; every reference resolves | **Executed — no problems** |
| Dashboard JSON built with `jsonencode` rather than hand-written | **By construction** |
| 131 unit tests | **Executed — still passing** |
| Any alarm actually evaluating, firing, or recovering | **Not verified — nothing deployed** |
| `terraform validate` | **Not executed** |

## Problems / open items

| Item | Who |
|---|---|
| **The alarm evidence the report needs does not exist yet**: drive `alert-burst` into ALARM deliberately (`--force-alert --interval 0.5 -n 30`) and screenshot it. An alarm that has never fired is an untested alarm | MD, after deployment |
| Tune `alarm_alert_burst` and `alarm_invocation_ceiling` from a real run, and record both values | MD |
| **Still open:** the AWS account's plan and creation date (risk C5) | You |

## Next phase

**Phase 11 — Testing.** The test plan, API-level tests against a deployed stack (auth, authorization, ingestion, invalid input, alerts, statistics), and the testing learning document. Every test labelled **Created / Executed / Not executed** with real output.

Phase 11 is the first phase that genuinely cannot be completed without a deployment — API tests need an API. The plan and the scripts can be written now; the results have to be real.
