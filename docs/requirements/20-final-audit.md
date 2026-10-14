# Final Requirement Audit

> **12 October 2026:** the five review corrections (VPC, backup, team email alerts, admin/student pages, two Lambdas) are implemented — see `21-professor-corrections.md`. Rows marked *(re-capture)* need fresh evidence from the corrected deployment.

Every requirement in the brief, mapped to evidence. **Four status words only:**

| Status | Means |
|---|---|
| **Complete** | Built and verified; evidence exists in the repository |
| **Partial** | Some of it exists; the gap is named |
| **Not implemented** | We did not build it |
| **Not verified** | It exists in code or configuration but nobody has observed it working |

**Revised 11 October 2026.** The first version of this audit was written before deployment and said "nothing is deployed". That is no longer true: the system was deployed to eu-west-3 on 5 October 2026 and the evidence is in `docs/evidence/` (API test run 45/45 on 2026-10-05T13:04Z, 401/403 screenshots, dashboard, CloudWatch, IAM simulation, budget, credits). Every row below was re-checked against that evidence. A row is **Complete** only if a file in `docs/evidence/` (or a test run) shows it.

---

## §4 Functional requirements

| # | Requirement | Status | Evidence |
|---|---|---|---|
| F1 | Real-time or near-real-time ingestion | **Complete** | `simulator.py` → `POST /events`; API tests T4 (live run 2026-10-05, `api-test-results.json`); `dashboard-live.png` |
| F2 | User-facing API or web interface | **Complete** | 7 routes in `apigateway.tf`; API tests 45/45; `dashboard-live.png` |
| F3 | Persistent storage | **Complete** | DynamoDB table + 2 GSIs, TTL, PITR (`verify-deployment.png`); API test T7 writes then reads back |
| F4 | Data processing / analytics | **Complete** | `rules.py`, `aggregate.py`, 52 unit tests; live `/stats` on `dashboard-live.png`. *Known flaw: energy totals — see note E1 below* |
| F5 | Auth + authorization, ≥2 roles | **Complete** (re-capture) | Cognito groups `admin`/`student` (renamed after the review); role matrix unit-tested (`test_api_router.py`); `auth-401.png`, `auth-403-200.png` from 5 Oct; API tests T2/T3/T8 |
| F6 | Monitoring, logging, observability | **Complete** | `cloudwatch-dashboard.png`; 4 alarms in `alarms.tf` |
| F7 | Dashboard / visual output | **Complete** (re-capture) | Two pages after the review: `admin.html`, `student.html`; `dashboard-live.png` is the 5 Oct single dashboard |

## §6 Architecture requirements

| # | Requirement | Status | Evidence |
|---|---|---|---|
| A1 | Scalability | **Partial** | Analysis with the ~1,000 writes/s per-partition ceiling and its fix. **Gap: no load test; only default-rate latency measured** |
| A2 | High availability | **Complete** | Managed multi-AZ services; the `api` Lambda in two AZ subnets; stateless compute; single-region stated plainly |
| A3 | Security | **Partial** | JWT authorizer, group checks, least-privilege IAM demonstrated (`auth-*.png`, `iam-simulate.png`); **private-subnet VPC with a table-only endpoint** (Oct 2026). **Gap: the pages are served over HTTP from the S3 website endpoint (API is HTTPS)** |
| A4 | Cost optimization | **Partial** | Budget exists (`budget.png`), credits recorded (`credits.png`). **Gap: figures are account-wide; CampusPulse-only cost not isolated** |
| A5 | Observability | **Complete** | `cloudwatch-dashboard.png`, structured logs, EMF metrics, troubleshooting runbook |
| A6 | Disaster recovery | **Partial → Complete once the drill runs** | PITR + **AWS Backup daily/weekly in a separate vault** + S3 versioning (Oct 2026); `restore-drill.sh` measures the RTO. **Gap until it is run: RTO unmeasured** |

## §7 Implementation requirements

| # | Requirement | Status | Evidence |
|---|---|---|---|
| I1 | Containerized **or** serverless backend | **Complete** | 2 Lambda functions grouped by business domain: Public Auth Gateway (`auth`, outside VPC) and Protected Campus Operations Platform (`api`, inside private VPC); 5 Oct screenshot shows the earlier 5 |
| I2 | Working API or web interface | **Complete** | API tests 45/45; `dashboard-live.png` |
| I3 | Configured cloud networking | **Complete** (re-capture) | **VPC added after the review**: 2 private subnets, SG, DynamoDB gateway endpoint, flow logs (`vpc.tf`, AD-10) |
| I4 | Reproducible deployment | **Partial** | Terraform + scripts + runbook; one member deployed. **Not verified: a second member redeploying from the guide alone** |
| I5 | Monitoring visualization | **Complete** | `cloudwatch-dashboard.png` (6 widgets) |
| I6 | ≥1 security mechanism demonstrated | **Complete** | `auth-401.png`, `auth-403-200.png` |
| I7 | Simulated data generation | **Complete** | `simulator.py`, 18 tests, 1000 events through the real validator |

## §8 Cost constraints

| # | Requirement | Status | Evidence |
|---|---|---|---|
| C1 | Use free tier / low cost | **Complete** | Nothing bills by the hour. No EC2, RDS, NAT Gateway, load balancer |
| C2 | Budget / billing alert with evidence | **Complete** | `budget.tf`; `budget.png` ($10 monthly, alerts at 50/80/forecast-100 %) |
| C3 | Stop/delete unused resources | **Complete (procedure)** | `cleanup.md`, `terraform destroy` — to be run after grading |
| C4 | Avoid expensive services | **Complete** | Forbidden list; `verify-deployment.sh` checks none are running |
| C5 | Cost estimate table | **Partial** | Table exists; DynamoDB and S3 prices still marked `unverified` |
| C6 | Justify non-free resources | **Complete** | DynamoDB on-demand and PITR, AD-4 and report §7 |

## §9 Architecture diagram

| # | Requirement | Status |
|---|---|---|
| D1-D7 | Components, flows, layers, networking, security zones, external sources, monitoring/backup | **Complete** — ASCII + Mermaid + slide 3 |
| D8 | Understandable without the code | **Not verified** |
| — | Exported as PDF/image for submission | **Not verified** — check before submitting |

## §10 Report

| Section | Status |
|---|---|
| All eleven required sections | **Complete** |
| No open placeholders | **Complete** — none remain in `implementation-report.md` |
| §11.6 what the team learned, §12 contribution table | **Complete** — filled by the team |
| Delivered as PDF | **Not verified** |

## §11 Presentation

| # | Requirement | Status |
|---|---|---|
| P1 | Presentation | **Complete (content)** — `CampusPulse_2026_Final_Presentation.pptx` (15 slides) + `05-final-speaking-script.md` for the 10-minute slot. **Not verified:** timed rehearsal |
| P2-P7 | Overview, architecture, demo, security/scalability, cost, lessons | **Complete** |
| P8 | All members participate and can explain | **Not verified** — rehearsal |
| — | Backup demo video | **Not verified** |

## §13 Submission

| # | Deliverable | Status |
|---|---|---|
| S1 | Architecture diagram as PDF/image | **Not verified** |
| S2 | Report as PDF | **Not verified** |
| S3 | Repository link | **Complete** — `github.com/SomithaG08/campuspulse-2026` (branch `develop`) |
| S4 | Deployment guide / scripts | **Complete** |
| S5 | Demo evidence | **Complete** — `docs/evidence/` |
| S6 | Presentation slides | **Partial** — final deck is in the project root but **not yet committed**; the old `docs/presentation/CampusPulse-2026.pptx` is deleted locally but the deletion is not committed |

## §15 Optional features

| Feature | Status |
|---|---|
| Anomaly detection | **Partial** — threshold rules; no statistical model, by choice |
| Email alerting | **Complete** — all 7 alarms email the team's school addresses via SNS (Oct 2026, AD-13) |
| Infrastructure as Code | **Complete** — Terraform; Cognito groups added back as code in Oct 2026 (import once) |
| CI/CD | **Not implemented** — out of scope by choice |
| Container orchestration | **Not implemented** — out of scope by choice |
| Multi-cloud comparison | **Not implemented** |
| ML forecasting | **Not implemented** — deliberately avoided |

## §16 Academic integrity

| # | Requirement | Status |
|---|---|---|
| X1 | Sources cited | **Complete** — `REFERENCES.md` |
| X2 | Work is the team's own | **Complete** — AI assistance disclosed in the report |
| X3 | Nothing fabricated | **Complete** — corrections of October 2026 removed claims that were not true (HTTPS everywhere, RPO ≈ 0, provider "removed" a resource) |

---

## Open technical note

**E1 — energy totals.** Each energy event is compared with the building's `energy_baseline_kwh`, but `/stats` *sums* every energy reading of the day. Because the simulator sends energy readings at random times, the daily total depends on how many readings happened to be sent, not on real consumption, and it is compared mentally with a per-reading baseline. Either define each reading as "kWh in the last hour" and send exactly one per building per hour, or report the average reading per building. Not yet changed — needs a team decision because it changes the `/stats` contract and the dashboard.

---

## Remaining manual tasks — only things that genuinely need a human

1. **Rotate the AWS access key** that was stored in `CLI-Keys.txt` and in the PowerShell transcript; delete those local copies.
2. **Commit** the final deck, the speaking script and these corrections; push to `develop`.
3. Run `terraform import` for the two Cognito groups (commands in `cognito.tf`), then `terraform plan` — expect at most an in-place update of the two groups (description/precedence), and **no destroy or create**.
4. **Rehearse a PITR restore and time it** (`docs/learning/19-disaster-recovery.md` §5) → fills the RTO.
5. Decide on note E1 (energy totals).
6. Export diagram and report as PDF; record the backup demo video; time a rehearsal.
7. After grading: `terraform destroy`, confirm nothing remains, watch the credit balance for 24 hours.
