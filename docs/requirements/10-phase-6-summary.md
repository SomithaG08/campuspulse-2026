# Phase 6 — Database and Processing, read path (complete, pending your review)

> **Nothing is deployed.** The backend is now complete in code and its logic is tested locally; no AWS resource has been created.

## What we built

The read half of the system. **All seven endpoints in the API contract now exist.**

## Files created

| File | What it is |
|---|---|
| `backend/src/common/queries.py` | All five access patterns as pure functions, plus parameter parsing and opaque pagination tokens |
| `backend/src/common/aggregate.py` | The `/stats` response computed in one pass over a day's events |
| `backend/src/handlers/query.py` | `GET /events` and `GET /alerts` |
| `backend/src/handlers/stats.py` | `GET /stats` |
| `backend/tests/test_queries.py` | 24 tests, including the guarantee that no builder can produce a `Scan` |
| `backend/tests/test_aggregate.py` | 15 tests, one per `/stats` field |
| `docs/learning/07-dynamodb-explained.md` | Key design, Query vs Scan, the sparse index, pagination, TTL, and our design's ceiling |

## Files changed

`lambda.tf` (two more functions) · `apigateway.tf` (two integrations, three routes, two permissions) · `03-deploy-backend.md` (read-path verification) · both component READMEs.

## Four decisions worth defending

**Filtering by building switches index, it does not filter.** A `FilterExpression` runs after the read, so you pay to read everything and discard most of it. `GET /events?building=X` queries GSI1 instead. The one place we do use a filter is severity on the alerts index — acceptable precisely because that index is already tiny.

**Aggregation happens on read, not on write.** Running counters in the database would make `/stats` a single tiny read, and at large scale that is right. At a few hundred events a day, read-time aggregation has no counter that can drift out of sync with reality, and a new statistic is a change to one pure function rather than a backfill. The scalability section says what we would do at a thousand times the volume.

**The API returns a fixed field list, not the raw item.** `pk`, `sk`, `gsi1pk` and `expires_at` never leave the system, so the storage design can change without breaking the dashboard.

**`/stats` reports its own ceiling.** It pages through at most ten pages and then sets `truncated: true`. A day with tens of thousands of events would be summarised from its most recent slice only — stated in the response and in the docs rather than hidden.

## Testing

| Check | Status |
|---|---|
| **113 unit tests** — validation, severity rules, keys, query builders, aggregation | **Executed — 113 passed in 0.48s** |
| `test_no_builder_can_produce_a_scan` — every access pattern supplies a partition key | **Executed — passed.** The read roles are not granted `dynamodb:Scan` either, so a future `Scan` would fail loudly rather than work slowly |
| Terraform structural validation: 12 files, **54 resources**; all seven contract routes present (`GET /health`, `POST /login`, `POST /events`, `POST /requests`, `GET /events`, `GET /alerts`, `GET /stats`) | **Executed — no problems** |
| `terraform validate` | **Not executed** — Terraform still not installed here |
| Anything against real AWS | **Not deployed** |

## Problems / open items

| Item | Who |
|---|---|
| Phases 4-6 all await a real `terraform apply` | Whoever deploys |
| **Still open:** the AWS account's plan and creation date (risk C5) | You |
| `aggregate.summarise` holds a day of items in memory; the stats function has 512 MB and a 15 s timeout, which is ample at our scale but is the first thing to revisit if volume grows | — |

## Next phase

**Phase 7 — Authentication and security.** The threat model, a review of every IAM policy against what the code actually calls, the Cognito user and group setup documented end to end, log-redaction verification, and the security learning documents (`08-cognito-authentication.md`, `10-iam-security.md`).

Phase 7 is mostly review and documentation rather than new code — the security *mechanisms* were built into Phases 4-6 by design, because security added at the end is security that does not work.
