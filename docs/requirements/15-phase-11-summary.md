# Phase 11 — Testing (complete, pending your review)

> **The API tests have never run against AWS**, because nothing is deployed. What they *have* done is described precisely below — and the evidence file in the repo is a placeholder that says so.

## What we built

The second testing layer: 45 API checks against a deployed stack, the test plan, and the testing learning document.

## Files created

| File | What it is |
|---|---|
| `tests/api/run_api_tests.py` | 45 checks in 7 groups, zero dependencies, exits 0/1, writes the evidence JSON |
| `docs/testing/01-test-plan.md` | Both layers, every group's status, and what is deliberately *not* tested |
| `docs/learning/17-testing-explained.md` | For Madhavan — why two layers, why boundary values, why most tests assert failure |
| `docs/evidence/api-test-results.json` | **Placeholder**, explicitly marked as not a real run |
| `docs/testing/README.md` | Index |

## The suite

| Group | Checks | Proves |
|---|---|---|
| T1 Reachability | 2 | The API answers; cold-start latency recorded |
| T2 Authentication | 8 | Both roles log in; **wrong password and unknown user return the same message**, so the form cannot be used to discover accounts |
| T3 Authorization | 8 | Staff get **403** on `POST /events` and `GET /alerts`, **200** on `/events` and `/stats` |
| T4 Ingestion | 7 | **An over-capacity event is reclassified `critical` although the client sent `normal`** |
| T5 Invalid input | 11 | Eight bad payloads and two bad parameters, all 400 with a usable message |
| T6 Queries and stats | 6 | Ordering, building filter, alerts-only, every documented field |
| T7 Integration | 3 | One critical event traced into `/alerts`, `/events` and the statistics |

T3 is the two-role requirement demonstrated rather than asserted. T4.4 is the integrity control: a device cannot declare itself normal.

## Testing — including the testing of the tests

| Check | Status |
|---|---|
| 131 unit tests | **Executed — 131 passed in ~1 s** |
| API suite against **AWS** | **Not executed — nothing deployed** |
| API suite against a **local stand-in** built on the project's real validation, rules, keys and aggregate modules | **Executed — 45 passed, 0 failed** |
| Suite exits 2 with a clear message when unconfigured | **Executed — verified** |
| `docs/evidence/api-test-results.json` | Deliberately replaced with a placeholder so mock output cannot be mistaken for real evidence |

**Why the local run was worth doing, and what it is not.** It proves the **test suite itself is correct** — assertions, ordering, token handling, JSON shapes — so nobody deploys and then spends an afternoon debugging the tests instead of the system. It proves **nothing** about IAM, Cognito, API Gateway or DynamoDB. The stand-in server was scratch, kept outside the repository, and is not a project component.

That distinction is the whole point of this phase: it is the difference between "our tests pass" and "our tests pass against the thing we are claiming works".

## Problems / open items

| Item | Who |
|---|---|
| Deploy, run the suite, commit the generated JSON | Madhavan |
| Record real cold-start vs warm latency from the T1/T4/T6 lines | Madhavan |
| Drive `alert-burst` into ALARM and screenshot it | MD |
| Run the suite a second time, another day, from a clean state | Madhavan |
| **A teammate who did not write the deployment guide deploys from it** — the only real test of requirement I4 | anyone but the author |
| **Still open:** the AWS account's plan and creation date (risk C5) | You |

## Next phase

**Phase 12 — Deployment and verification.** This is the phase that cannot be faked: it is where everything written since Phase 4 meets a real AWS account. The deliverable is an ordered deployment runbook (budget first), an evidence checklist naming every screenshot the report needs, and a demo-day smoke test.

After Phase 12 the remaining work is the report (13-14), the presentation (15) and the final audit (16) — all of which depend on evidence that only a deployment can produce.
