# CampusPulse 2026

A cloud-native smart campus operations platform for the fictional NorthBridge University.
Final project — **Big Data & Cloud Computing**, EPITA, 2025-2026.

**Team:** Somitha Gudivada · Meha · Madhavan · MD

> **Status: in development.** Nothing is deployed yet. No AWS resources exist. Every claim in this repository is marked *not verified* until someone has run it and captured the evidence.

---

## The problem

A campus produces a constant stream of readings — room occupancy, temperature, humidity, energy use, equipment status, student service requests. Individually none of them matter. Collectively they answer the questions the operations team actually has: *which rooms are overloaded, which buildings are burning the most energy, what is abnormal right now, which student requests are urgent.* Nobody can watch thousands of readings by hand.

CampusPulse ingests all of them, classifies each one as it arrives, and surfaces only what needs attention.

## Objectives

1. Ingest simulated campus events in near real time.
2. Persist them in a store designed around the questions we will ask.
3. Classify severity and aggregate operational statistics.
4. Enforce authentication and two distinct roles.
5. Show campus state on a dashboard.
6. Monitor, log and alarm on the system itself.
7. Stay inside a fixed 100-credit AWS budget, with evidence.

## Architecture

```text
Simulator ──HTTPS+JWT──> API Gateway ──> Lambda ×4 ──> DynamoDB
   (Python)                   │            │              │
                          JWT check    CloudWatch      PITR backup
                              │         logs/metrics
Browser ──> S3 (dashboard) ───┘
                              Cognito: users, groups ops/staff
                              IAM: one least-privilege role per function
```

Region **eu-west-3 (Paris)**. Fully serverless — no EC2, no VPC, no NAT Gateway, no load balancer.

Full detail: [`docs/architecture/02-diagram.md`](docs/architecture/02-diagram.md) · decisions and alternatives: [`01-architecture-decisions.md`](docs/architecture/01-architecture-decisions.md)

## Technology stack

| Layer | Choice |
|---|---|
| Language | Python 3.12 (backend + simulator), vanilla JS (dashboard) |
| API | Amazon API Gateway, HTTP API |
| Compute | AWS Lambda × 4 |
| Storage | Amazon DynamoDB, one table + 2 GSIs |
| Identity | Amazon Cognito user pool (Essentials tier) |
| Hosting | Amazon S3 static website |
| Observability | Amazon CloudWatch — logs, metrics, alarms, dashboard |
| Permissions | AWS IAM — one role per function |
| Deployment | Terraform + a packaging script (confirmed in Phase 4) |

## Repository structure

```text
campuspulse-2026/
├── backend/
│   ├── src/common/          campus_config.py — shared source of truth
│   ├── src/handlers/        auth · ingest · query · stats
│   └── tests/
├── simulator/               simulator.py
├── frontend/                index.html · app.js · style.css
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

Not deployable yet. Once Phase 4 is done, the deployment guide lives in `docs/deployment/`.

**New to the project or to cloud computing?** Start at [`docs/learning/00-start-here.md`](docs/learning/00-start-here.md), then follow [`docs/learning/learning-path.md`](docs/learning/learning-path.md).

Inspect the campus configuration today:

```bash
python backend/src/common/campus_config.py
```

## API

| Method | Endpoint | Role required |
|---|---|---|
| POST | `/login` | — |
| POST | `/events` | `ops` |
| GET | `/events` | `ops`, `staff` |
| GET | `/stats` | `ops`, `staff` |
| GET | `/alerts` | `ops` |
| POST | `/requests` | `ops`, `staff` |
| GET | `/health` | — |

Full contract: [`docs/architecture/05-api-contract.md`](docs/architecture/05-api-contract.md)

## Security

Three independent enforcement layers: API Gateway validates the JWT before our code runs; each Lambda checks the caller's Cognito group; IAM restricts each function to one action set on one resource. HTTPS throughout, encryption at rest by default, no credentials in this repository, every input validated at ingestion.

Threat model: `docs/security/` (Phase 7).

## Cost control

Serverless throughout, so idle costs nothing. No NAT Gateway, no RDS, no EC2, no load balancer. Log retention 7 days, TTL 30 days, budget alert configured before any other resource.

**Read [`docs/cost/01-cost-model.md`](docs/cost/01-cost-model.md) §1 before touching the account** — under the AWS Free Tier rules current since July 2025, a free-plan account closes at six months or at credit depletion, whichever comes first.

## Testing

`docs/testing/` (Phase 11). Every test is labelled **Created**, **Executed** or **Not executed**, with real output. No test result in this repository is ever invented.

## Cleanup

`docs/deployment/cleanup.md` (Phase 4), plus `terraform destroy`.

## Learning documentation

`docs/learning/` — written for teammates starting from zero. Each document defines its terms simply, then technically, then shows how our project uses them, and ends with self-check questions.

## Academic integrity

External sources, libraries and AWS documentation are cited in `REFERENCES.md`. The architecture, implementation and report are the team's own work. Nothing in this repository — screenshots, costs, test results, metrics — is fabricated; unverified claims are labelled as such.
