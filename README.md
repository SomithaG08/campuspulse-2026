# CampusPulse 2026

A cloud-native smart campus operations platform for the fictional NorthBridge University.
Final project — **Big Data & Cloud Computing**, EPITA, 2025-2026.

**Team:** Somitha Gudivada · Meha · Madhavan · MD

> **12 October 2026 — review corrections implemented:** VPC (private subnets, DynamoDB gateway endpoint), backups (AWS Backup + PITR + S3 versioning), alerts emailed to the team's school addresses, separate **admin** and **student** pages, and **two Lambda functions grouped by business domain** (`auth` public identity gateway outside VPC, `api` private campus operations inside VPC). Summary: [`docs/requirements/21-professor-corrections.md`](docs/requirements/21-professor-corrections.md) · upgrade steps: [`docs/deployment/06-apply-corrections.md`](docs/deployment/06-apply-corrections.md).

> **Status: deployed and tested** in AWS eu-west-3 (Paris) on 5 October 2026. Evidence (live API test run 45/45, auth 401/403 screenshots, dashboard, CloudWatch, IAM simulation, budget) is in [`docs/evidence/`](docs/evidence/). Requirement-by-requirement status: [`docs/requirements/20-final-audit.md`](docs/requirements/20-final-audit.md).

---

## The problem

A campus produces a constant stream of readings — room occupancy, temperature, humidity, energy use, equipment status, student service requests. Individually none of them matter. Collectively they answer the questions the operations team actually has: *which rooms are overloaded, which buildings are burning the most energy, what is abnormal right now, which student requests are urgent.* Nobody can watch thousands of readings by hand.

CampusPulse ingests all of them, classifies each one as it arrives, and surfaces only what needs attention.

## Objectives

1. Ingest simulated campus events in near real time.
2. Persist them in a store designed around the questions we will ask.
3. Classify severity and aggregate operational statistics.
4. Enforce authentication and two distinct roles: administrator and student.
5. Show campus state on two pages: an admin dashboard and a student page.
6. Monitor, log and alarm on the system itself.
7. Stay inside a fixed 100-credit AWS budget, with evidence.

## Architecture

```text
Simulator ──HTTPS+JWT──> API Gateway ──/login──> auth Lambda ──> Cognito (admin / student)
   (Python)                   │  (JWT check)       (outside VPC, no data access)
Browser ──HTTPS+JWT───────────┘
 admin.html / student.html    └──other routes──> api Lambda ── VPC private subnets (2 AZs)
   (loaded from S3, no data)                       │  SG: out 443 to DynamoDB only
                                                   └──> DynamoDB gateway endpoint ──> DynamoDB
                                                                                  ├─ PITR 35 d
                                                                                  └─ AWS Backup daily/weekly
CloudWatch logs · metrics · 7 alarms ──> SNS ──> team @epita.fr inboxes
```

Region **eu-west-3 (Paris)**. Serverless, with the data function inside a VPC that has **no internet gateway and no NAT Gateway** — DynamoDB is reached through a free gateway endpoint.

Full detail: [`docs/architecture/02-diagram.md`](docs/architecture/02-diagram.md) · decisions and alternatives: [`01-architecture-decisions.md`](docs/architecture/01-architecture-decisions.md)

## Technology stack

| Layer | Choice |
|---|---|
| Language | Python 3.12 (backend + simulator), vanilla JS (dashboard) |
| API | Amazon API Gateway, HTTP API |
| Compute | AWS Lambda × 2 — `api` (router, in the VPC), `auth` (login) |
| Network | Amazon VPC: 2 private subnets, security group, DynamoDB gateway endpoint, flow logs |
| Storage | Amazon DynamoDB, one table + 3 GSIs |
| Backup | DynamoDB PITR + AWS Backup (daily, weekly) + S3 versioning |
| Alerts | CloudWatch alarms → SNS → team school email |
| Identity | Amazon Cognito user pool (Essentials tier) |
| Hosting | Amazon S3 static website — sign-in, admin and student pages |
| Observability | Amazon CloudWatch — logs, metrics, alarms, dashboard |
| Permissions | AWS IAM — one role per function, plus backup and flow-log roles |
| Deployment | Terraform (packages the Lambda zip itself) + `scripts/deploy-dashboard.sh` |

## Repository structure

```text
campuspulse-2026/
├── backend/
│   ├── src/common/          campus_config.py — shared source of truth
│   ├── src/handlers/        api (router) · auth · ingest · query · stats · requests · health
│   └── tests/
├── simulator/               simulator.py
├── frontend/                index.html (sign-in) · admin.html · student.html · app.js · admin.js · student.js · style.css
├── infrastructure/terraform/
├── docs/
│   ├── requirements/        requirements matrix · scope · risks · DoD · team
│   ├── architecture/        decisions · diagram · services · data model · API · data flow
│   ├── learning/            beginner documentation
│   ├── cost/                cost model and free-tier analysis
│   ├── deployment/ security/ testing/ evidence/ report/ presentation/
└── README.md
```

## Scale guardrails — deliberate limits

This is a course prototype. It is built to be **correct, explainable and demonstrable**, not large. These numbers are a design decision, not a shortcoming, and they are defended in `docs/requirements/02-scope.md`:

| Dimension | Limit | Why |
|---|---|---|
| Buildings | 5 | Enough variety for per-building statistics to mean something |
| Rooms | 11 | Enough for occupancy and alerting to be interesting |
| Event types | 6 | Covers every question the spec asks |
| Simulator rate | seconds between events, not milliseconds | Protects the credit budget |
| Total events | tens of thousands over the project | Far inside every free-tier allowance |
| Data retention | 30 days, then automatic deletion | Storage stays trivial; restores stay fast |
| Regions | 1 | We do not claim disaster recovery we have not built |
| Optional features | none until the core works end to end | Scope discipline |

**Anything that would make this bigger needs a reason tied to a graded requirement.** "It would be more impressive" is not one — a small system explained precisely scores better than a large one explained vaguely.

## Getting started

Deploy with the step-by-step runbook in [`docs/deployment/05-runbook.md`](docs/deployment/05-runbook.md) (Terraform, then Cognito users, then the dashboard). Run the unit tests first: `cd backend && pytest tests/` and `cd simulator && pytest tests/` (161 tests, no AWS needed).

**New to the project or to cloud computing?** Start at [`docs/learning/00-start-here.md`](docs/learning/00-start-here.md), then follow [`docs/learning/learning-path.md`](docs/learning/learning-path.md).

Inspect the campus configuration today:

```bash
python backend/src/common/campus_config.py
```

## API

| Method | Endpoint | Role required |
|---|---|---|
| POST | `/login` | — |
| POST | `/events` | `admin` |
| GET | `/events` | `admin` |
| GET | `/stats` | `admin`, `student` |
| GET | `/alerts` | `admin` |
| POST | `/requests` | `admin`, `student` |
| GET | `/requests` | `admin` (all), `student` (own only) |
| GET | `/health` | — |

Full contract: [`docs/architecture/05-api-contract.md`](docs/architecture/05-api-contract.md)

## Security

Four independent enforcement layers: API Gateway validates the JWT before our code runs; each route checks the caller's Cognito group (`admin`/`student`); IAM restricts each function to named actions on named resources; and the data function sits in private subnets whose only route leads to our table. The API is HTTPS-only; encryption at rest by default; no credentials in this repository; every input validated at ingestion.

**Known gap:** the dashboard page is served from the S3 *website* endpoint, which is HTTP only. The fix (CloudFront in front of the bucket) is listed as future work.

Threat model: [`docs/security/01-threat-model.md`](docs/security/01-threat-model.md).

## Cost control

Serverless throughout, so idle costs nothing. The VPC uses a free gateway endpoint instead of a NAT Gateway. No RDS, no EC2, no load balancer. Log retention 7 days, TTL 30 days, budget alert configured before any other resource.

**Read [`docs/cost/01-cost-model.md`](docs/cost/01-cost-model.md) §1 before touching the account** — under the AWS Free Tier rules current since July 2025, a free-plan account closes at six months or at credit depletion, whichever comes first.

## Testing

161 unit tests (143 backend + 18 simulator), executed locally; 45 API checks executed against the live deployment on 2026-10-05 (the suite now has 50 checks for the admin/student version) (`docs/evidence/api-test-results.json`). Plan and results: [`docs/testing/01-test-plan.md`](docs/testing/01-test-plan.md).

## Cleanup

[`docs/deployment/cleanup.md`](docs/deployment/cleanup.md), plus `terraform destroy`.

## Learning documentation

`docs/learning/` — written for teammates starting from zero. Each document defines its terms simply, then technically, then shows how our project uses them, and ends with self-check questions.

## Academic integrity

External sources, libraries and AWS documentation are cited in `REFERENCES.md`. The architecture, implementation and report are the team's own work. Nothing in this repository — screenshots, costs, test results, metrics — is fabricated; unverified claims are labelled as such.
