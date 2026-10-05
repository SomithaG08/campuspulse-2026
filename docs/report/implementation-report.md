# CampusPulse 2026
## A Cloud-Native Smart Campus Operations Platform

**Implementation Report**

Big Data & Cloud Computing — Final Project S2 2026
EPITA, Academic Year 2025-2026

**Team:** Somitha Gudivada · Meha · Madhavan · MD
**Cloud provider:** Amazon Web Services · **Region:** eu-west-3 (Paris)
**Repository:** `https://github.com/SomithaG08/campuspulse-2026`
**Deployed API:** `https://wsjs04q4yi.execute-api.eu-west-3.amazonaws.com/`

---

## 1. Introduction

### 1.1 Problem definition

A university campus continuously produces operational data: how full each room is, how warm, how humid, how much electricity each building draws, whether equipment has failed, and what students are asking for. Individually none of these readings matters. Collectively they answer the questions a campus operations team actually has — and no person can watch thousands of readings to find the handful that need action.

NorthBridge University needs a platform that collects this data, decides automatically which readings are abnormal, and presents only those to the people who can act. The brief sets five operational questions the platform must answer: which rooms are occupied or overloaded, which buildings consume the most energy, whether temperature/humidity/equipment events are unusual, which student requests are urgent, and what the overall state of the campus is.

### 1.2 Objectives

1. Ingest simulated campus events in near real time.
2. Persist them in a store designed around the questions we will ask.
3. Classify severity on arrival and aggregate operational statistics.
4. Enforce authentication and two distinct roles.
5. Present campus state on a dashboard.
6. Monitor, log and alarm on the system itself.
7. Remain inside a fixed 100-credit AWS budget, with evidence.

### 1.3 Selected use case

The brief offers six example use cases and permits a hybrid. We built **a campus operations monitoring and alerting platform**: one ingestion path, one storage model, one dashboard, six event types.

This was a deliberate narrowing. One coherent pipeline is easier to build, demonstrate and defend than several partial ones, and the brief states the bar explicitly: *"The prototype does not need to be large, but it must be coherent, functional, and aligned with the proposed architecture."* Coherence is the graded property, not size.

### 1.4 Team organization

Each member owns one area end to end — building it, writing its learning documentation, and presenting it. The areas were chosen to be independently explainable: the simulator can be understood without IAM, and vice versa.

| Member | Area | Components |
|---|---|---|
| Somitha Gudivada | Architecture and ingestion | `cp-ingest`, `cp-stats`, severity rules, shared campus configuration |
| Meha | Identity and security | Cognito, `cp-auth`, IAM policies, threat model |
| Madhavan | Data generation and testing | Simulator, test suites, demo script |
| MD | Interface and observability | Dashboard, `cp-query`, CloudWatch alarms and dashboard, evidence |

Two rules governed the split: **you write the documentation for what you own**, because writing the explanation is how you discover whether you understand it; and **nobody presents a component they did not build**.

---

## 2. System Architecture

### 2.1 Overview

```text
   EXTERNAL                          AWS — eu-west-3 (Paris)
 ..............   .........................................................
 : Simulator  :   :  ZONE A — PUBLIC EDGE                                 :
 : (Python)   :---1-> API Gateway (HTTP API) ── JWT authorizer ──2── 401   :
 :            :   :        │ 3                                            :
 : Browser    :---1->      ▼                                              :
 : (dashboard):   :  ZONE B — COMPUTE (one IAM role per function)         :
 :............:   :   cp-auth  cp-ingest  cp-query  cp-stats  cp-health    :
                  :      │4        │5         │6        │6                :
                  :      ▼         ▼          ▼         ▼                 :
                  :  ZONE C — DATA                                        :
                  :   Cognito          DynamoDB (+2 GSI, TTL, PITR)       :
                  :                                                       :
                  :  CROSS-CUTTING: CloudWatch (logs/metrics/alarms), IAM  :
                  :.......................................................:
```

Full diagram, including the Mermaid source and an explanation of all ten numbered connections: `docs/architecture/02-diagram.md`.

`[INSERT ARCHITECTURE DIAGRAM — exported PDF/PNG, required by §13]`

### 2.2 Components and responsibilities

| Component | Responsibility |
|---|---|
| Simulator | Represents campus IoT devices; authenticates and POSTs events |
| API Gateway (HTTP API) | Single public HTTPS entry point; validates every JWT before our code runs; CORS; throttling |
| `cp-auth` | Exchanges credentials for a token via Cognito |
| `cp-ingest` | Validates, classifies severity, writes to DynamoDB |
| `cp-query` | Reads recent events and alerts |
| `cp-stats` | Aggregates a day's events into operational statistics |
| `cp-health` | Unauthenticated liveness check; warms the API before a demo |
| DynamoDB | Stores events; two secondary indexes; TTL; point-in-time recovery |
| Cognito | Users, passwords, tokens, and the `ops`/`staff` groups |
| S3 | Serves the dashboard's static files — no campus data |
| CloudWatch | Logs, metrics, four alarms, one dashboard |
| IAM | One least-privilege role per function |

### 2.3 Justification of design choices

Nine decisions are recorded in `docs/architecture/01-architecture-decisions.md`, each with the alternatives considered and what the choice costs us. The four that shaped the system most:

**Serverless rather than servers.** Campus events arrive in bursts and the system is idle between them — the worst possible fit for hourly billing and the best possible fit for per-request billing. With 100 non-renewable credits, "costs nothing while idle" is the most valuable property available. It also removes the heaviest beginner topics: no OS patching, no web-server configuration, no NAT Gateway, no load-balancer health checks. *Cost to us:* cold starts of 1-3 seconds, and a design that does not lift to another cloud unchanged.

**HTTP API rather than REST API.** $1.00 per million requests against $3.50, a built-in JWT authorizer that matches our auth model exactly, and CORS as a single setting rather than per-method configuration. *Cost to us:* no API keys or usage plans — which we do not need, since the simulator authenticates with a real token like any other client.

**Four small Lambdas rather than one.** This is what makes least privilege concrete: `cp-ingest` is the internet-facing function and it can write but **cannot read the database**; `cp-query` and `cp-stats` can read but cannot write. A flaw in the exposed function yields "can add junk events", not "can read every student service request".

**DynamoDB on-demand rather than provisioned.** The published free tier covers *provisioned* capacity (25 WCU/25 RCU), so on-demand request charges come from credits — a few cents at our volume. We accepted that cost to avoid the one failure mode that would ruin a live demonstration: a throttled write while the examiner is watching. The scalability narrative is also stronger and truer.

### 2.4 Data model

One DynamoDB table. Partition key `DAY#<date>`, sort key `<timestamp>#<event_id>`.

Two secondary indexes: **GSI1** keyed by building and date, and **GSI2** — a **sparse index** containing only alerts, because `cp-ingest` writes its key attribute only when severity is not `normal`. `GET /alerts` therefore reads an index that physically contains alerts, instead of reading the day and discarding the ~95% that are normal.

**There is no `Scan` anywhere in the system.** The design rule is enforced three ways: by key design, by a unit test (`test_no_builder_can_produce_a_scan`), and by IAM — no role is granted `dynamodb:Scan`, so a future `Scan` would fail loudly rather than work slowly.

Full schema, thresholds and all five access patterns: `docs/architecture/04-data-model.md`.

### 2.5 Scalability, availability and the honest limits

Covered in §6 and §9. The short version: Lambda and DynamoDB scale horizontally and automatically; we are **single-region**, with no failover, and we say so rather than claiming multi-region capability we have not built.

---

## 3. Technology Stack

| Layer | Technology | Version/notes |
|---|---|---|
| Backend language | Python | 3.12 (Lambda runtime) |
| Frontend | HTML, CSS, vanilla JavaScript | No framework, no build step |
| Simulator | Python | 3.9+, **standard library only** |
| API | Amazon API Gateway | HTTP API (v2) |
| Compute | AWS Lambda | 5 functions |
| Storage | Amazon DynamoDB | on-demand, 1 table + 2 GSIs |
| Identity | Amazon Cognito | user pool, **Essentials** tier |
| Static hosting | Amazon S3 | static website hosting |
| Observability | Amazon CloudWatch | logs, metrics (EMF), 4 alarms, 1 dashboard |
| Permissions | AWS IAM | 5 roles |
| Infrastructure as Code | Terraform | ≥1.5, AWS provider ~>5.0 |
| Testing | pytest, plus a dependency-free API suite | 131 unit + 45 API checks |
| Version control | Git | |

**Libraries:** `boto3` (AWS SDK, already present in the Lambda runtime, so nothing is vendored), `pytest` (tests only). The deployment package therefore contains only our own code — a few kilobytes, which keeps cold starts short.

**Two deliberate absences.** The simulator and the API test suite use **no third-party libraries at all**, so any teammate can run them immediately and nothing can fail on demo day because a dependency would not install. The dashboard has **no build step**, for the same reason.

---

## 4. Implementation Process

### 4.1 Workflow

The project ran in numbered phases, each ending with a written summary recording what was built, what was tested, what was *not* verified, and what remained open. Those summaries are in `docs/requirements/` and are the raw material for this section.

| Phase | Output |
|---|---|
| 1 | Requirements matrix, scope, risk register, definition of done |
| 2 | Architecture decisions, diagram, frozen data model and API contract, cost model |
| 3 | Repository structure, shared campus configuration |
| 4 | Infrastructure as Terraform, cost warning, deployment guide |
| 5-6 | Backend: shared modules, five handlers, the API |
| 7 | Security audit and threat model |
| 8 | Simulator |
| 9 | Dashboard |
| 10 | Alarms, dashboard, troubleshooting runbook |
| 11 | Test plan and API test suite |
| 12 | Deployment runbook, verification scripts, evidence checklist |
| 13 | Documentation audit |

Two rules were applied throughout: **the data model and API contract were frozen in Phase 2** and every component coded against those documents; and **documentation was updated in the phase that changed the code**, not at the end.

### 4.2 Configuration decisions

| Decision | Value | Reason |
|---|---|---|
| Region | `eu-west-3` | European university, personal data stays in the EU; lowest latency from campus |
| Log retention | **7 days, set explicitly** | The default is "never expire", which quietly accrues storage cost |
| Log groups | **Created by Terraform, not by Lambda** | A group Lambda creates for itself inherits that "never expire" default |
| Token lifetime | 60 minutes | A stolen token is briefly useful |
| Cognito tier | **Essentials** | Free tier is 10,000 MAU on Lite/Essentials; **Plus has no free tier at all** |
| Simulator auth | Ordinary user, not machine-to-machine | M2M token requests have no free tier and are billed per request |
| TTL | 30 days | Storage stays trivial; smaller table restores faster, improving RTO |
| `treat_missing_data` | `notBreaching` | Otherwise quiet periods leave alarms grey, and grey alarms teach people to ignore alarms |
| Throttling | 20/s steady, 40 burst | A budget control as much as a security one |

### 4.3 Technical issues encountered

These are real, recorded as they happened. They are the honest content of this section.

**1. `--force-alert` was unreliable.** The simulator's anomalous occupancy range (105-145% of capacity) straddles the 120% critical threshold, so a forced event sometimes produced only a *warning*. A demo alert that sometimes lands as something milder is a demo that sometimes does not land. Forced events now use ranges comfortably past critical, verified over 300 generated events.

**2. A test assumption was wrong, and the investigation was useful.** A test asserted that with the anomaly rate at zero no alerts would appear; it failed. The cause was not a bug: a routine priority-2 service request maps to `warning` in our data model, because a request's severity comes from the priority the requester chose, not from a sensor being out of range. The test was split in two to reflect the real behaviour.

**3. The dashboard rendered the login form underneath the dashboard.** The `hidden` attribute was set correctly, but the browser's own stylesheet rule `[hidden] { display: none }` is beaten by any explicit `display:` rule — and `.login-view { display: grid }` silently cancelled it. The fix was one line. It is recorded because of *how* it was found: by rendering the page and looking at it. No test would have caught it — the elements existed, the JavaScript ran cleanly, the attribute was set. **Some classes of bug only exist visually.**

**4. A documentation audit found nine inconsistencies.** A script that resolves every file path cited in the documentation and compares quoted figures against reality found two references to files that had never been written, four stale resource counts, and three glossary gaps. All were fixed. The lesson: documentation drift is mechanical and should be checked mechanically.

**5. Pricing pages could not be read programmatically.** AWS renders its regional price tables in JavaScript, so several figures could not be verified from the published pages. Rather than quoting plausible numbers, those figures were **tagged `[unverified]` in the cost model** with a script (`scripts/verify-prices.sh`) to resolve them from the AWS Price List API. See §7.

**6. `aws_cognito_user_pool_group` was removed in AWS provider v5.100.0.** The Terraform configuration originally used this resource to create the `ops` and `staff` Cognito groups. Running `terraform validate` produced: *"An argument named group_name is not expected here."* The resource was removed from the provider in hashicorp/aws v5.100.0. The fix: removed both `aws_cognito_user_pool_group` blocks from `cognito.tf` and created the groups post-deployment via AWS CLI (`aws cognito-idp create-group`). This approach is now documented in `docs/deployment/03-deploy-backend.md`.

**7. Cognito requires email as the username.** The user pool was configured with `username_attributes = ["email"]`, so `admin-create-user` calls using display names (e.g. `ops-user`) failed with *"Username should be an email."* All users were re-created with their email addresses as the username (`ops@northbridge.edu`, `staff@northbridge.edu`, `admin@northbridge.edu`).

**8. PowerShell's `curl` alias differs from Unix `curl`.** On Windows, `curl` is an alias for `Invoke-WebRequest` and does not accept `-s` (silent). Smoke tests used `Invoke-RestMethod -Uri <url>` instead.

---

## 5. Security Design

### 5.1 The model in one paragraph

Data crosses a trust boundary in exactly three places, each with an independent control: **API Gateway's JWT authorizer** decides whether we know who you are (401); **the Lambda's group check** decides whether your role permits this route (403); and **IAM** decides whether that function may touch that resource at all (`AccessDenied`). Defeating one leaves the other two standing.

### 5.2 Threat analysis

Seven threats, each control marked **Implemented** (code exists and is tested), **Configured** (infrastructure declares it), or **Planned** (designed, not built). Full table: `docs/security/01-threat-model.md`.

| Threat | Principal controls | Status |
|---|---|---|
| Unauthorized access | JWT validated at the edge before our code runs; 60-minute tokens; HTTPS only | Configured |
| Credential compromise | **No AWS credentials in the code at all**; passwords handled only by Cognito; identical error for wrong-password and unknown-user; `.gitignore` written before the first commit | Implemented |
| Malicious event submission | Every field validated for type, enum, length, unit and plausibility; 4 KB body cap; timestamp window; **the client's `severity` is discarded and recomputed** | Implemented |
| Excessive permissions | One role per function, each scoped to one action set on one named ARN; no `Action:"*"`; `dynamodb:Scan` granted to nobody | Configured |
| Data exposure | Encryption at rest and in transit; the API returns an explicit field list so internal keys never leave; vague 500s; no credential material logged | Implemented |
| API abuse / cost attack | Throttling; invalid tokens rejected at the edge so they invoke no Lambda; `limit` capped; budget alert | Configured |
| Misconfiguration | All infrastructure in Terraform; S3 public-ACL blocks retained; retention set explicitly; no public sign-up | Configured |

**Residual risks, accepted and stated:** a stolen token works until it expires (one hour); a flood of *valid* requests consumes credits up to the throttle ceiling. Mitigations for both are designed but not built.

### 5.3 IAM strategy

| Function | AWS calls it makes | Policy grants |
|---|---|---|
| `cp-health` | none | logs only |
| `cp-auth` | `initiate_auth` | `cognito-idp:InitiateAuth` on our pool |
| `cp-ingest` | `put_item` | `dynamodb:PutItem` on one table — **cannot read** |
| `cp-query`, `cp-stats` | `query` | `dynamodb:Query` on the table and indexes — **cannot write** |

Audited in Phase 7 by listing every AWS call in the code and comparing it with every action granted: **exact match, no excess, no gaps**. `logs:CreateLogGroup` is deliberately withheld so a function cannot create a log group with "never expire" retention — a trade-off accepted knowingly, since all groups are created by Terraform.

**An honest caveat.** The human who runs `terraform apply` uses a broad, near-administrator IAM user. That is a convenience for a course project. It is a *different claim* from runtime least privilege, and this report does not use one to imply the other.

`[INSERT SCREENSHOT: aws iam simulate-principal-policy for cp-ingest — PutItem allowed, Query and Scan implicitDeny]`

### 5.4 Secure networking

**There is no VPC, and that is a decision.** All services used are AWS-managed with no server of ours inside a network we own, so our boundary is IAM plus the JWT authorizer rather than a subnet. The equivalent-concepts mapping (public subnet → API Gateway, security group → Lambda resource policy, and so on) is in `docs/learning/11-networking-explained.md`.

The cost consequence is the headline: a private-subnet design requires a **NAT Gateway**, roughly **$32 per month** for a component that would do nothing for us — about a third of our entire budget, spent on idling.

### 5.5 Encryption, API protection and secrets

Encryption at rest is enabled by default on DynamoDB and S3; everything in transit is HTTPS, with no plaintext listener to downgrade to. The API is protected by the JWT authorizer, per-route role checks, stage throttling and input validation.

**Secrets:** there are none in the repository. Functions assume IAM roles and receive temporary, auto-rotated credentials; configuration arrives through environment variables set by Terraform. A repository-wide scan for access-key patterns, private-key headers and hardcoded password literals found nothing, and a review of all twelve logging calls confirmed no password, token or authorization header is ever logged.

**The public S3 bucket is a deliberate, bounded exposure:** it contains only the page shell — HTML, CSS, JavaScript — and no campus data. Every value the page displays comes from the API, which refuses without a token. The bucket policy permits `s3:GetObject` only.

`[INSERT SCREENSHOT: 401 without a token]` · `[INSERT SCREENSHOT: 403 with a staff token on /alerts]` · `[INSERT SCREENSHOT: 200 with the same staff token on /events]`

---

## 6. Scalability Strategy

### 6.1 How each component scales

| Component | Mechanism | Practical limit |
|---|---|---|
| API Gateway | Managed; absorbs bursts | Account-level request quotas |
| Lambda | A new execution environment per concurrent request | Account concurrency quota (1,000 by default) |
| DynamoDB on-demand | Partitions split automatically | **~1,000 writes/sec per partition** — see below |
| Cognito | Managed | 10,000 MAU free; far beyond our users |
| S3 | Managed | Effectively unlimited for static files |

### 6.2 Behaviour as load grows

**More sensors** — more rows in the campus configuration. No architectural change; occupancy and energy remain per-room and per-building.

**More events** — Lambda scales horizontally and statelessness is what makes that free: no instance holds anything another would need, so AWS can run many without coordination. DynamoDB on-demand absorbs the writes until the partition limit below.

**More dashboard users** — each browser polls three endpoints every 10 seconds. A hundred concurrent viewers would be ~30 requests/second, above our 20/s throttle; the fix is to raise the throttle or increase the polling interval, both single-value changes.

**More stored data** — TTL bounds the table at 30 days. Query cost does not grow with table size because every access pattern supplies a partition key.

### 6.3 The design's real ceiling, and the fix

All of one day's writes land in a single partition, `DAY#<date>`, and a DynamoDB partition sustains roughly **1,000 write units per second**. That is far beyond our prototype and it is a genuine ceiling.

**The fix, designed but not implemented:** shard the partition key — `DAY#2026-10-05#0` through `#9` — distributing writes across ten partitions and querying all ten in parallel. It touches `keys.py` and `queries.py` only.

A second ceiling: `/stats` aggregates at read time and pages through at most ten pages, reporting `truncated: true` beyond that. At very high volume the answer is to maintain counters on write via DynamoDB Streams, so `/stats` reads pre-computed aggregates instead of raw events.

### 6.4 Measurements

Numbers, not theory. Recorded from the API test suite and the CloudWatch dashboard:

| Measurement | Value |
|---|---|
| Cold-start latency (first `/health` after idle) | 315 ms |
| Warm `POST /events` latency | 95 ms |
| Warm `GET /stats` latency | 95 ms |
| Lambda `Duration` p95 under simulator load | `[MEASURED: ___ ms — read from CloudWatch dashboard]` |
| Observed behaviour at a higher simulator rate | No throttling or errors observed at 1 event/5s (simulator default) |

`[INSERT SCREENSHOT: CloudWatch latency widget]`

---

## 7. Cost Analysis

### 7.1 The account model — and a scheduled risk

The AWS Free Tier changed on 15 July 2025. For an account created in 2026:

- **$100 in credits at sign-up**, plus up to $100 more earned by using certain services.
- **Credits expire 12 months** from account creation.
- On the **free plan**, the account ends at **six months from sign-up, or when the credits are depleted — whichever comes first.** AWS then closes the account; data is retained 90 days and is recoverable only by upgrading to the paid plan.
- Over 30 services retain an always-free monthly allowance on both plans.

*Sources: [AWS Free Tier FAQs](https://aws.amazon.com/free/free-tier-faqs/), [the July 2025 announcement](https://aws.amazon.com/about-aws/whats-new/2025/07/aws-free-tier-credits-month-free-plan/), consulted 2026-09-22.*

**This is a project risk with a date on it**, tracked as C5 in the risk register. Account plan: `[INSERT: Free or Paid — check AWS Console → Billing → Account]`. Created: `[INSERT DATE]`. Six-month boundary: `[INSERT DATE]`.

Joining an AWS Organisation or setting up Control Tower expires the credits immediately; neither was done.

### 7.2 Per-service allowances and our usage

| Service | Free allowance | Source | Our usage |
|---|---|---|---|
| Lambda | 1M requests + 400,000 GB-s per month, not time-limited | **verified** | « 100k requests total |
| API Gateway (HTTP) | 1M calls/month for 12 months; then $1.00/M | **verified** | « 100k calls |
| DynamoDB | 25 GB storage, 25 WCU, 25 RCU — stated for **provisioned** capacity | **verified** | on-demand; storage « 1 GB |
| DynamoDB on-demand requests | — | **unverified** (~$0.625/M writes, $0.125/M reads, N. Virginia) | ~100k writes ≈ **$0.06** |
| Cognito | 10,000 MAU on Lite/Essentials, not time-limited; **no free tier on Plus** | **verified** | ~6 users |
| CloudWatch | 5 GB logs, 10 custom metrics, 10 alarms, 3 dashboards | **verified** | 3 metrics, 4 alarms, 1 dashboard |
| S3 | figures could not be read from the pricing page | **unverified** | < 1 MB static files |
| IAM | free | **verified** | 5 roles |

**Why some rows say "unverified":** AWS renders its regional price tables in JavaScript, so those figures could not be read from the published pages. We flagged them rather than quoting plausible numbers. `scripts/verify-prices.sh` resolves them from the AWS Price List API; run it and replace these rows.

`[INSERT: verified figures from scripts/verify-prices.sh]`

### 7.3 Estimated and actual cost

**Estimate: well under $5 of the 100 credits**, dominated by DynamoDB on-demand requests and point-in-time recovery.

**Actual:** $145.61 (credit balance before deployment) → `[INSERT: credit balance after deployment — check AWS Console → Billing]` = `[INSERT: actual consumption]`

`[INSERT SCREENSHOT: credit balance, dated]`

### 7.4 Cost optimization decisions

| Decision | Saves |
|---|---|
| **No NAT Gateway** (no VPC) | ~$32/month |
| No EC2, no RDS, no load balancer | all hourly billing |
| HTTP API rather than REST API | 3.5× per request |
| Log retention 7 days, set explicitly | unbounded log storage growth |
| TTL 30 days | unbounded table growth |
| Cognito Essentials, not Plus | Plus has no free tier |
| Ordinary user auth for the simulator, not M2M | M2M tokens have no free tier |
| EMF metrics rather than `PutMetricData` | per-call metric charges |
| Dashboard polling pauses when hidden and after 15 idle minutes | ~17,000 requests/day from a forgotten tab |
| Simulator refuses `--interval` below 0.5 s | runaway request loops |

**Nothing in this architecture bills by the hour.** That single property is the cost model.

### 7.5 Billing alert

A budget is created by Terraform with alerts at 50%, 80% and forecast 100%, with `include_credit = false` — without that flag a cost budget reads $0.00 on a credit-funded account right up until the credits are gone.

`[INSERT SCREENSHOT: the budget in the Budgets console — mandatory, §8]`

---

## 8. Observability

### 8.1 Logs

Every function emits structured JSON with a `request_id` that also appears in the API Gateway access log — so one identifier ties the error response, the function log and the access log together. Retention is 7 days.

```json
{"level":"INFO","request_id":"a1b2c3","event_id":"evt-42","building":"Library-A",
 "room":"A203","severity":"critical","reason":"occupancy 58 exceeds 120% of capacity 45","latency_ms":41}
```

### 8.2 Metrics

Three custom metrics — `EventsIngested`, `AlertsRaised`, `StatsRequested` — published using **Embedded Metric Format**, so a specially shaped log line becomes a metric with no `PutMetricData` call. Dimensions are limited to severity: every distinct dimension combination is a separate custom metric against a 10-metric free allowance.

### 8.3 Alarms

| Alarm | Fires at | Watches |
|---|---|---|
| `ingest-errors` | ≥1 Lambda error in 5 min | the system |
| `api-5xx` | ≥1 server error in 5 min | the front door |
| `alert-burst` | ≥20 alerts in 5 min | **the campus** |
| `invocation-ceiling` | ≥2000 invocations in 5 min | **the budget** |

Two thresholds began as explicit estimates and are variables for that reason. Initial values: 20 and 2000. Tuned values after observation: initial values retained — no runaway invocations observed during testing.

`[INSERT SCREENSHOT: an alarm in ALARM state, triggered deliberately]`

### 8.4 Dashboard and troubleshooting

One CloudWatch dashboard, six widgets: the top row answers *is it working?*, the bottom row *what is it doing?* Latency is shown as p95 rather than an average, because an average hides a slow tail.

A troubleshooting runbook (`docs/learning/20-troubleshooting.md`) covers every failure mode in the brief with cause, where to look, fix and how to verify.

`[INSERT SCREENSHOT: CloudWatch dashboard with real data]`

---

## 9. Disaster Recovery

### 9.1 Backup

**DynamoDB point-in-time recovery**, enabled in Terraform. It continuously records changes and permits restoring to **any second within 35 days** — not a nightly snapshot. A restore creates a new table and never overwrites the original, which makes rehearsing it safe.

Also protective: all infrastructure and code is in Git, so the entire stack is rebuildable with `terraform apply`. Cognito users are not backed up — there are three, recreated by two CLI commands.

### 9.2 RPO and RTO

| | Value | Basis |
|---|---|---|
| **RPO** | ≈ 0, bounded by PITR granularity | A property of the service: restore to any second |
| **RTO** | Target < 60 minutes. **Measured: `[MEASURED: ___ minutes — from restore rehearsal]`** | From the restore rehearsal |

**The RTO is deliberately left blank until measured.** Writing a number we have not observed would be inventing evidence.

### 9.3 Restore procedure

`restore-table-to-point-in-time` to a new table name → verify the data → repoint the functions' `TABLE_NAME` → delete the test table. Full commands in `docs/learning/19-disaster-recovery.md`.

`[INSERT SCREENSHOT: restore in progress]` · `[INSERT SCREENSHOT: restored table containing data]`

### 9.4 Continuity, and what we do not claim

The likeliest disasters here are a person deleting something and **the account closing at the six-month free-plan boundary** — the second being a disaster with a date on it, mitigated by keeping everything reproducible from Git and exporting evidence out of AWS as it is collected.

**We do not claim:** multi-region deployment, automated failover, or survival of a full region failure. We are single-region. Recovery is a human running documented commands.

---

## 10. Testing and Evaluation

Status words are used strictly: **Executed** means it ran and the output is in the repository; **Created, not executed** means the test exists but has never run against the thing it tests.

### 10.1 Unit tests — **Executed**

**131 passed, 0 failed, approximately 1 second.** No AWS account, no network.

| Suite | Count | Covers |
|---|---|---|
| `test_validation.py` | 30 | Accepting valid events; rejecting every category of invalid one |
| `test_rules.py` | 37 | Both sides of every severity threshold |
| `test_keys.py` | 7 | Key construction, ordering, TTL, the sparse index |
| `test_queries.py` | 24 | All five access patterns; **that no builder can produce a `Scan`** |
| `test_aggregate.py` | 15 | Every `/stats` field |
| `test_generator.py` | 18 | **1000 generated events through the real validator** |

They run without AWS because the logic in `common/` imports no `boto3` — a deliberate split, since code that can only be tested by deploying it does not get tested.

### 10.2 API tests — **Executed against live AWS deployment 2026-10-05**

45 checks across seven groups, zero dependencies: reachability, authentication, authorization, ingestion, invalid input, queries and statistics, and one end-to-end integration path.

**Result: 45 passed, 0 failed** — from `docs/evidence/api-test-results.json`, generated not retyped.

The two most important checks: **T3** (a staff token receives 403 on `POST /events` and `GET /alerts`, 200 on `/events` and `/stats`) is the two-role requirement demonstrated rather than asserted; **T4.4** (an over-capacity event returns `critical` although the client sent `normal`) is the integrity control.

### 10.3 Deployment verification — **Executed**

`scripts/verify-deployment.sh` performs ~22 checks that the deployment matches the design: table active and on-demand, both indexes, TTL enabled, **PITR enabled**, both Cognito groups, all five functions, no log group set to never-expire, four alarms, a budget — and **no EC2, no RDS, no NAT Gateway running**.

`[INSERT SCREENSHOT: verification script output]`

### 10.4 Not tested, and why

Load and performance testing (out of scope — we report observed latency instead of claiming throughput), automated browser tests (the dashboard was verified by rendering and inspecting it), chaos testing, and penetration testing. Stating these is deliberate: a test plan listing only what exists implies everything else was considered unnecessary.

---

## 11. Lessons Learned

### 11.1 Technical challenges

The eight issues in §4.3 — the unreliable demo flag, the wrong test assumption, the invisible CSS bug, the documentation drift, the unreadable pricing pages, the Cognito provider version incompatibility, the email-as-username requirement, and the PowerShell curl alias.

The common thread: **each was found by a check, not by thinking harder.** A test caught the demo flag. Rendering the page caught the CSS. A script caught the documentation drift. Running `terraform validate` caught the provider issue. The pricing pages were caught by trying to verify rather than assuming.

### 11.2 Trade-offs

| We chose | Over | Because | It cost us |
|---|---|---|---|
| Serverless | Containers / EC2 | Zero idle cost on a fixed budget | Cold starts; vendor lock-in |
| On-demand DynamoDB | Provisioned (free tier) | No throttling during a live demo | A few cents |
| Thresholds | Machine learning | Every member can explain and defend them | No adaptive detection |
| No framework | React or similar | Nothing to install, nothing to break | Manual DOM work |
| Local Terraform state | S3 backend with locking | Fewer resources, fewer failure modes | Only one person can apply |
| Four small Lambdas | One function | Genuine least privilege | More deployment wiring |

### 11.3 Limitations

Single-region, no failover. Threshold-based detection only. One partition per day caps throughput at roughly 1,000 writes/second. `/stats` aggregates at read time and truncates beyond ten pages. Tokens cannot be revoked before they expire. The deployment identity is broad. No CI/CD.

**Every one of these is stated in the documentation where it is relevant**, rather than being discovered by an examiner.

### 11.4 What we would do differently

Deploy earlier. A great deal was built and tested before anything existed in AWS, and while the logic was genuinely verifiable locally, the deployment-shaped problems — IAM, CORS, token wiring — can only be found by deploying. A thin end-to-end slice in week one would have de-risked the rest.

### 11.5 Future improvements

In the order we would actually do them: SNS email alerting (small, demos well); statistical anomaly detection using a rolling mean and standard deviation per room; pre-aggregated counters via DynamoDB Streams; a CI/CD pipeline; an S3 data lake with Athena for historical analytics; and multi-region DR — which would be the largest change and the first thing a real campus would require.

### 11.6 What the team learned

**Somitha Gudivada:** `[2-3 sentences in your own words about what you learned from the architecture and ingestion work]`

**Meha:** `[2-3 sentences in your own words about what you learned from the identity and security work]`

**Madhavan:** `[2-3 sentences in your own words about what you learned from the simulator and testing work]`

**MD:** `[2-3 sentences in your own words about what you learned from the dashboard and observability work]`

---

## 12. Team Contributions

| Member | Components built | Documentation written | Other | Share |
|---|---|---|---|---|
| Somitha Gudivada | `cp-ingest`, `cp-stats`, `common/rules.py`, `common/validation.py`, `common/aggregate.py`, campus configuration | Architecture decisions, data model, ingestion explainer, §4.3 issues | Terraform deployment, AWS account setup, git branching | 25% |
| Meha | `cp-auth`, `common/auth.py`, Cognito Terraform (`cognito.tf`), IAM policies (`iam.tf`) | Threat model, Cognito explainer, IAM explainer, security section | IAM audit, security review | 25% |
| Madhavan | `simulator/simulator.py`, simulator tests, `tests/api/run_api_tests.py` | Simulator explainer, test plan, demo runbook | API test execution, demo preparation | 25% |
| MD | `frontend/` (index.html, app.js, style.css, config.js), `cp-query`, CloudWatch alarms (`alarms.tf`), CloudWatch dashboard (`cloudwatch.tf`) | Frontend explainer, CloudWatch explainer, troubleshooting runbook, evidence checklist | Dashboard deployment, evidence collection | 25% |

*Adjust percentages and details to reflect what actually happened.*

---

## 13. References

Full list with dates: `REFERENCES.md` in the repository.

**Course material:** Cloud Computing Final Project brief, S2 2026, Big Data & Cloud Computing, EPITA; course slides and labs.

**AWS documentation and pricing** (all consulted 2026-09-22): [Free Tier](https://aws.amazon.com/free/) · [Free Tier FAQs](https://aws.amazon.com/free/free-tier-faqs/) · [Free Tier credits announcement](https://aws.amazon.com/about-aws/whats-new/2025/07/aws-free-tier-credits-month-free-plan/) · [Lambda pricing](https://aws.amazon.com/lambda/pricing/) · [API Gateway pricing](https://aws.amazon.com/api-gateway/pricing/) · [DynamoDB pricing](https://aws.amazon.com/dynamodb/pricing/) · [Cognito pricing](https://aws.amazon.com/cognito/pricing/) · [CloudWatch pricing](https://aws.amazon.com/cloudwatch/pricing/) · [S3 pricing](https://aws.amazon.com/s3/pricing/)

**Libraries:** `boto3` (Apache-2.0), `pytest` (MIT).

**AI assistance.** The team used an AI assistant during planning and drafting. The architecture decisions, implementation and report are the team's own: every generated draft was reviewed, edited and verified by the member who owns that component, and no member presents a component they did not build and cannot explain. Factual claims about AWS pricing and free-tier limits were checked against the AWS pages cited above rather than accepted from the assistant, and figures that could not be verified are marked as unverified in §7.

---

## Appendix A — Repository structure

```text
campuspulse-2026/
├── backend/src/common/      shared logic: config, validation, rules, keys, queries, aggregate
├── backend/src/handlers/    health, auth, ingest, query, stats
├── backend/tests/           113 unit tests
├── simulator/               simulator.py + 18 tests
├── frontend/                index.html, style.css, app.js, config.js
├── infrastructure/terraform/ 13 files, 61 resources
├── tests/api/               45 API checks
├── scripts/                 deploy-dashboard, verify-deployment, verify-prices, smoke-test
└── docs/                    requirements · architecture · learning · security · testing · cost · deployment · evidence
```

## Appendix B — API summary

| Method | Endpoint | Role |
|---|---|---|
| POST | `/login` | — |
| GET | `/health` | — |
| POST | `/events` | `ops` |
| GET | `/events` | `ops`, `staff` |
| GET | `/stats` | `ops`, `staff` |
| GET | `/alerts` | `ops` |
| POST | `/requests` | `ops`, `staff` |

## Appendix C — Example event

```json
{ "event_id": "evt-2026-0042", "building": "Library-A", "room": "A203",
  "event_type": "occupancy", "value": 58, "unit": "people",
  "severity": "normal", "timestamp": "2026-09-22T14:05:00Z" }
```

Stored as `critical` — room A203 holds 45, so 58 is 129% of capacity. The client's `severity` is discarded by design.
