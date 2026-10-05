# Test Plan — CampusPulse 2026

Status words, used exactly as the brief requires and nowhere loosely:

| Word | Meaning |
|---|---|
| **Executed** | It ran, and the output is in the repository |
| **Created, not executed** | The test exists but has never run against the thing it tests |
| **Not created** | We have not written it |

**No test result in this project is ever invented.** Where there is no result, the table says so.

---

## 1. What we test, and where

```text
          ┌──────────────────────────────────────────────┐
          │  API tests        tests/api/                 │  needs a deployment
          │  does the DEPLOYED system behave?            │
          ├──────────────────────────────────────────────┤
          │  Unit tests       backend/tests, simulator/  │  needs nothing
          │  is the LOGIC right?                         │
          └──────────────────────────────────────────────┘
```

Two layers, deliberately. The unit tests prove the thinking; the API tests prove the wiring. A system can pass every unit test and still return 500 because an IAM policy is wrong — and it can be perfectly deployed while classifying a critical event as normal. Neither layer substitutes for the other.

## 2. Unit tests — **Executed**

```bash
cd backend && python -m pytest tests -q          # 113
cd .. && python -m pytest simulator/tests -q     # 18
python -m pytest backend/tests simulator/tests -q  # 131 total
```

**Result: 131 passed, 0 failed, 1.0 s.** No AWS account, no network, no credentials.

| Suite | Count | Covers |
|---|---|---|
| `test_validation.py` | 30 | Accepting valid events; rejecting missing fields, wrong units, non-numeric and implausible values, bad timestamps, unknown rooms; service requests |
| `test_rules.py` | 37 | Both sides of every severity threshold in the data model, the documented worked example, per-building energy baselines |
| `test_keys.py` | 7 | Key construction, chronological ordering, TTL, and the sparse alerts index |
| `test_queries.py` | 24 | All five access patterns, parameter parsing, pagination tokens, **and that no builder can produce a `Scan`** |
| `test_aggregate.py` | 15 | Every `/stats` field, Decimal handling, newest-first occupancy |
| `test_generator.py` | 18 | 1000 generated events through the real validator; `--force-alert` always critical; CLI cost guard rails |

Two of these are design guarantees rather than ordinary tests: `test_no_builder_can_produce_a_scan` and `test_generated_events_always_pass_server_validation`.

## 3. API tests — **Created, not executed**

`tests/api/run_api_tests.py` — 45 checks, zero dependencies.

```bash
export CAMPUSPULSE_API=https://xxxx.execute-api.eu-west-3.amazonaws.com
export OPS_USER=... OPS_PASSWORD=... STAFF_USER=... STAFF_PASSWORD=...
python tests/api/run_api_tests.py
```

Exits 0 or 1, and writes `docs/evidence/api-test-results.json` — **that file is the report's evidence**, generated, never retyped.

| Group | Checks | What it proves |
|---|---|---|
| **T1 Reachability** | 2 | The API answers; cold-start latency is recorded |
| **T2 Authentication** | 8 | Both roles can log in; wrong password and unknown user are both 401 **with the same message**, so the form cannot be used to discover accounts |
| **T3 Authorization** | 8 | No token → 401. Staff → **403** on `POST /events` and `GET /alerts`, **200** on `/events` and `/stats`. Malformed token → 401 |
| **T4 Ingestion** | 7 | A valid event stores; an over-capacity event **is reclassified critical although the client said normal**; the alert carries a readable reason; staff can raise a service request |
| **T5 Invalid input** | 11 | Eight malformed payloads and two bad query parameters all return 400 with a usable message and a `request_id` |
| **T6 Queries and stats** | 6 | Newest-first ordering, building filter, alerts contain only abnormal events, every documented `/stats` field present |
| **T7 Integration** | 3 | The one critical event from T4 appears in `/alerts`, in `/events`, and in the statistics count |

**T3 and T4.4 are the two that matter most.** T3 is the two-role requirement demonstrated rather than asserted; T4.4 is the integrity control — a device cannot declare itself normal.

### Has this suite ever run?

**Against AWS: no.** Nothing is deployed.

**Against a local stand-in: yes** — 45 passed, 0 failed. A throwaway HTTP server built on the project's *real* validation, rules, key-building and aggregation modules was run on a laptop, and the suite was executed against it. That server was scratch, kept outside the repository, and is not part of the system.

**What that does and does not prove.** It proves the **test suite itself is correct** — the assertions, the ordering, the auth handling, the JSON shapes — so nobody deploys and then spends an afternoon debugging the tests instead of the system. It proves **nothing** about AWS: not IAM, not the Cognito pool, not API Gateway routing, not DynamoDB. `docs/evidence/api-test-results.json` is currently a placeholder saying exactly this, and a real run overwrites it.

## 4. Not created

| Test | Why not |
|---|---|
| Load / performance testing | Out of scope. We record observed latency from the API tests instead of claiming a throughput figure |
| Browser UI tests | The dashboard was verified by rendering and inspecting it; automated UI testing is disproportionate for one page |
| Chaos / failure injection | Out of scope |
| Penetration testing | Explicitly not claimed — see the threat model |

Saying so is the point. A test plan that lists only what exists implies the rest was considered and found unnecessary; this one says which is which.

## 5. What must still be executed

| # | Step | Owner |
|---|---|---|
| 1 | Deploy, then run `run_api_tests.py` and commit the generated JSON | Madhavan |
| 2 | Record real latency from the T1/T4/T6 lines (cold start vs warm) | Madhavan |
| 3 | Drive `alert-burst` into ALARM deliberately and screenshot it | MD |
| 4 | Re-run the suite a second time, on a different day, from a clean state | Madhavan |
| 5 | A teammate who did not write the deployment guide deploys from it | anyone but the author |

Step 5 is the real test of requirement I4, and the only way to find out whether the guide is complete.
