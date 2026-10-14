# Phase 5 — Backend and API, write path (complete, pending your review)

> **Nothing is deployed.** The code exists and its logic is tested locally; no AWS resource has been created.

## Scope decision made in this phase

Phase 5 delivers the **write path** — log in, submit an event, store it. The **read path** (`GET /events`, `/stats`, `/alerts`) is Phase 6. Splitting it this way keeps each phase reviewable by a teammate in one sitting, and each half is independently demonstrable: after Phase 5 you can watch an event become a `critical` alert in the database; after Phase 6 you can read it back.

## Files created

| File | What it is |
|---|---|
| `backend/src/common/responses.py` | One response shape for the whole API, including the deliberately vague 500 |
| `backend/src/common/log.py` | Structured JSON logs, and metrics via **EMF** — a specially shaped log line becomes a CloudWatch metric, so we pay for no `PutMetricData` calls |
| `backend/src/common/auth.py` | Group-based authorization; normalises the `cognito:groups` claim, which arrives as a list *or* a string depending on the path |
| `backend/src/common/validation.py` | Every field checked: shape, enum, unit match, plausible range, timestamp window. Rejects rather than repairs |
| `backend/src/common/rules.py` | The severity decision — the smallest and most important file in the project |
| `backend/src/common/keys.py` | Builds the DynamoDB item, including the sparse alert key |
| `backend/src/handlers/health.py` | `GET /health` — public, touches nothing, warms the API before the demo |
| `backend/src/handlers/auth.py` | `POST /login` via Cognito `InitiateAuth` |
| `backend/src/handlers/ingest.py` | `POST /events` and `POST /requests` |
| `backend/tests/` | 74 tests across validation, rules and keys |
| `infrastructure/terraform/lambda.tf` | Three functions, packaged by Terraform itself |
| `infrastructure/terraform/apigateway.tf` | HTTP API, Cognito JWT authorizer, CORS, throttling, access logs, four routes |
| `docs/deployment/03-deploy-backend.md` | Deploy, smoke test, and the three refusal demonstrations |
| `docs/learning/05-api-explained.md`, `06-lambda-explained.md` | HTTP/JSON/status codes, and Lambda from zero |

## Files changed

`iam.tf` (a logs-only role for health) · `cloudwatch.tf` (a fifth log group) · `variables.tf` (app version, metric namespace, throttle limits) · `outputs.tf` (API endpoint, smoke test).

## Three decisions worth defending

**The client's `severity` is discarded.** Validation strips it and `rules.classify()` computes it from the value and the room's capacity. A device that could declare itself normal could silence any alert.

**`cp-ingest` cannot read the database.** Its IAM role allows `PutItem` and nothing else. The function an attacker reaches first is the one that can do least.

**The logic imports no boto3.** Validation, rules and key building are plain Python, which is why 74 tests run in a quarter of a second with no AWS account. Code that can only be tested by deploying it does not get tested.

## Testing

| Check | Status |
|---|---|
| **74 unit tests** — validation (accept, reject, units, timestamps, service requests), severity rules (both sides of every threshold), key building (including the sparse index) | **Executed — 74 passed in 0.24s** |
| End-to-end write path in memory: the data model's worked example (58 people in A203) produces `critical`, the documented reason string, and `gsi2pk = ALERT#2026-09-22`; a value of 20 produces no alert key | **Executed — passed** |
| Terraform structural validation: 12 files, **45 resources**, 9 data sources, 11 variables; every reference resolves | **Executed — no problems** |
| `terraform validate` / `fmt` | **Not executed** — Terraform still not installed here |
| Anything against real AWS | **Not deployed** |

**One test failed on the first run and it was the test that was wrong**, not the code: I claimed 400 kWh would be critical in Library-A, but 400/210 = 1.90, below the 2.0 critical ratio. Corrected to 450 kWh with the arithmetic written into the test. Recording this because it is exactly the kind of thing the report's "Implementation Process" section should contain.

## Problems / open items

| Item | Who |
|---|---|
| Phases 4 and 5 both await a real `terraform apply` | Whoever deploys |
| **Still open:** the AWS account's plan and creation date (risk C5) | You |
| `GET /events`, `/stats`, `/alerts` return 404 until Phase 6 — by design | — |

## Next phase

**Phase 6 — Database and processing, read path.** `cp-query` and `cp-stats`, the aggregation logic behind `/stats`, the three GET routes, tests for the query builders, and the DynamoDB learning document.
