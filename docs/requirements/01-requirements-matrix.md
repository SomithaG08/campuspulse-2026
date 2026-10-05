# Requirements Matrix — CampusPulse 2026

**Source of truth:** `Cloud_Computing_Final_Project_2026_S2.pdf` (Big Data & Cloud Computing, EPITA, 2025-2026).
**Status rule:** nothing in this file is marked done. Phase 1 is planning only. Status is tracked in `docs/requirements/04-definition-of-done.md` and in the final audit (Phase 16).

Legend for **Mandatory?**: **M** = explicitly required by the PDF · **O** = listed in PDF §15 as optional.

---

## A. Functional requirements (PDF §4)

| # | Requirement | M/O | How we will satisfy it | Planned component | Evidence to produce |
|---|---|---|---|---|---|
| F1 | Real-time or near-real-time ingestion from simulated campus sources | M | Python simulator POSTs JSON events over HTTPS at a configurable interval; each event is stored within seconds | `simulator/simulator.py` → API Gateway → Lambda `ingest` | Terminal recording of simulator output + matching items in DynamoDB + CloudWatch log lines with timestamps |
| F2 | User-facing service via API or web interface | M | REST API (`/events`, `/stats`, `/alerts`, `/login`) plus a static single-page dashboard | API Gateway + Lambda + S3-hosted dashboard | Live API calls in the demo; dashboard screenshots; endpoint URL in the report |
| F3 | Persistent storage for events, users, operational records | M | DynamoDB table for events (on-demand billing), second table or Cognito for users | DynamoDB `campuspulse-events` | Console screenshot of items; `GET /events` response |
| F4 | Data processing / analytics (aggregation, filtering, anomaly detection or reporting) | M | Threshold rules at ingest (severity classification) + aggregation on read (`/stats`: occupancy, avg temperature, energy per building, counts by type and severity) | Lambda `ingest` rules module + Lambda `stats` | Unit tests on the rules module; `/stats` response before vs after injecting abnormal events |
| F5 | Authentication and authorization for **at least two roles** | M | Two roles: `ops` (full read + admin views) and `staff` (limited read + submit service request). Login returns a signed token; Lambda checks role per endpoint | Cognito user pool **if available in our account**, otherwise Lambda-based JWT with hashed passwords (decision blocked on account check — see `05-aws-account-verification.md`) | Demo: staff token rejected with 403 on an ops-only endpoint; screenshot of both logins |
| F6 | Monitoring, logging, observability | M | CloudWatch Logs for every Lambda, custom metrics for ingested events and alerts, at least two alarms (Lambda errors, alert-rate spike) | CloudWatch Logs + Metrics + Alarms | Log screenshots, metric graph, alarm in ALARM state triggered deliberately |
| F7 | Dashboard / API endpoint / visual output of system state and processed results | M | Dashboard page: recent events table, occupancy per room, active alerts, energy per building, campus KPI tiles | `frontend/` static site on S3 | Screenshots + live demo |

## B. Cloud architecture requirements (PDF §6)

| # | Requirement | M/O | How we will satisfy it | Planned component | Evidence to produce |
|---|---|---|---|---|---|
| A1 | **Scalability** — behaviour under more devices, events, users, data | M | Serverless: Lambda concurrency scales per request, API Gateway absorbs burst, DynamoDB on-demand scales partitions. Written analysis of limits (Lambda concurrency quota, DynamoDB partition throughput, item-size limits) | Architecture doc + report §Scalability | Load observation: run simulator at high rate, show latency/throughput from CloudWatch. Numbers must be measured, not claimed |
| A2 | **High availability** — redundancy or continuity | M | All services used are AWS-managed and multi-AZ by default within one region; backend is stateless; failed invocations retried; explicit statement that we are single-region | Architecture doc + report | Written justification referencing AWS docs; no unverified multi-region claim |
| A3 | **Security** — IAM, secure networking, encryption, protected API, secrets, threat mitigation | M | Least-privilege IAM per Lambda; HTTPS-only API; encryption at rest (DynamoDB/S3 default) and in transit; no secrets in code (env vars / Parameter Store); input validation; threat model table | IAM policies, API authorizer, `docs/security/` | Policy JSON in repo, 403/401 demo, threat model table in report |
| A4 | **Cost optimization** — evidence of staying in free tier / low cost | M | Serverless-only, no NAT Gateway, no RDS, no load balancer, no always-on EC2. Cost estimate table + AWS Budgets alert | `docs/cost/` + AWS Budgets | Budget/billing alert screenshot, cost estimate table, credit consumption screenshot |
| A5 | **Observability** — monitoring, logging, metrics, alarms, troubleshooting | M | Same as F6 plus a troubleshooting runbook | CloudWatch + `docs/learning/20-troubleshooting.md` | Alarm evidence + runbook |
| A6 | **Disaster recovery** — backup policy, RPO, RTO, restore procedure | M | DynamoDB point-in-time recovery (PITR) and/or scheduled export to S3; documented RPO/RTO with justification; **restore actually rehearsed once** | DynamoDB PITR / S3 export + `docs/` DR procedure | Screenshot of PITR enabled + evidence of an executed restore test |

## C. Implementation requirements (PDF §7)

| # | Requirement | M/O | How we will satisfy it | Planned component | Evidence to produce |
|---|---|---|---|---|---|
| I1 | At least one containerized **or** serverless backend service | M | Serverless: several Lambda functions | `backend/src/` | Deployed function ARNs, invocation logs |
| I2 | Working API or web interface | M | Same as F2 | API Gateway + dashboard | Demo |
| I3 | Configured cloud networking environment | M | Serverless managed endpoints + IAM/resource policies as the network boundary; VPC concepts documented and justified (why no NAT Gateway). **If the account requires EC2 instead, a VPC with public/private subnets and security groups is built** | `docs/learning/11-networking-explained.md` (+ Terraform/VPC only if needed) | Diagram with security zones; console screenshots of whatever is actually configured |
| I4 | Reproducible deployment process or detailed deployment guide | M | Scripted deployment (Terraform **or** shell + AWS CLI, decided in Phase 4 after the account check) plus a step-by-step guide with complete commands | `infrastructure/` + `docs/deployment/` | A teammate redeploys from a clean state and reports success |
| I5 | Monitoring or logging visualization | M | CloudWatch dashboard with 4-6 widgets | CloudWatch dashboard | Screenshot |
| I6 | At least one security mechanism implemented and demonstrated | M | Token-based auth + role check on endpoints (demonstrated live), plus least-privilege IAM | Auth module | 401/403 demo |
| I7 | Simulated campus data generation | M | `simulator.py` with `--interval` and `--number-of-events`, multiple buildings/rooms, normal + abnormal events, severities | `simulator/` | Demo run |

## D. Cost constraints (PDF §8)

| # | Requirement | M/O | How we will satisfy it | Planned component | Evidence to produce |
|---|---|---|---|---|---|
| C1 | Use free tier / equivalent low-cost services | M | Lambda, API Gateway, DynamoDB on-demand, S3, CloudWatch, IAM (+ Cognito if available) | Whole architecture | Cost table |
| C2 | Create a budget or billing alert, include evidence | M | AWS Budgets alert at a low threshold of the 100 credits, email notification | AWS Budgets | Screenshot of the budget and of the alert email |
| C3 | Stop or delete unused resources after testing | M | `docs/deployment/cleanup.md` + a teardown command | Cleanup script | Screenshot of empty resource list after teardown rehearsal |
| C4 | Avoid expensive managed services unless unavoidable | M | No RDS, NAT Gateway, ALB/NLB, EKS, Kinesis, OpenSearch | Architecture | Trade-off section in report |
| C5 | Cost estimation table in the report | M | Per-service table: free-tier allowance, our expected usage, expected charge, assumption source | `docs/cost/` | Table with cited AWS pricing pages |
| C6 | Explain and justify any non-free resource | M | Section listing anything that consumes credits and why | Report | Written justification |

## E. Architecture design deliverable (PDF §9)

| # | Requirement | M/O | How we will satisfy it | Planned component | Evidence to produce |
|---|---|---|---|---|---|
| D1 | Components and responsibilities | M | Labelled diagram + per-service responsibility table | `docs/architecture/` | Diagram PDF/PNG |
| D2 | Communication flows between services | M | Numbered arrows, each explained in prose | Same | Diagram + flow narrative |
| D3 | Compute, storage, data-processing layers shown | M | Layered diagram | Same | Diagram |
| D4 | Networking config (VPC, subnets, security groups or equivalent) | M | Explicit network/trust boundaries drawn; equivalent-concept mapping explained for serverless | Same | Diagram + text |
| D5 | Security zones and IAM boundaries | M | Zones: public internet / API edge / compute / data; IAM role per component | Same | Diagram |
| D6 | External integrations and simulated data sources | M | Simulator and browser clients drawn as external actors | Same | Diagram |
| D7 | Monitoring, logging, backup components | M | CloudWatch and backup path drawn | Same | Diagram |
| D8 | Understandable without reading the source code | M | Diagram reviewed by the least technical teammate before submission | — | Review confirmation |

## F. Implementation report (PDF §10) — all sections mandatory

| # | Section | M/O | Owner artefact | Evidence to produce |
|---|---|---|---|---|
| R1 | Introduction: problem, objectives, use case, team organization | M | `docs/report/` | Real team names and real task split |
| R2 | System architecture + diagram + justification | M | " | Diagram + justification of every service choice |
| R3 | Technology stack | M | " | Versions and libraries listed |
| R4 | Implementation process: workflow, config decisions, issues encountered | M | " | Real issues logged as they happen during Phases 4-12 |
| R5 | Security design: threat analysis, IAM, networking, encryption, API protection, secrets | M | " | Threat model table + policy excerpts |
| R6 | Scalability strategy | M | " | Measured numbers where possible |
| R7 | Cost analysis: assumptions, estimates, billing alert evidence, optimizations | M | " | Screenshots |
| R8 | Observability: logs, metrics, dashboards, alarms, troubleshooting | M | " | Screenshots |
| R9 | Disaster recovery: backups, restore procedure, RPO, RTO | M | " | Restore test evidence |
| R10 | Testing and evaluation: functional, API, ingestion tests, monitoring evidence, performance | M | " | Test output captured verbatim, never fabricated |
| R11 | Lessons learned: challenges, trade-offs, limitations, future improvements | M | " | Written at the end, from the real log |
| R12 | Report delivered as **PDF** | M | Export step in `docs/deployment/` | Final PDF |
| R13 | Contribution table per team member (PDF §16) | M | Report appendix | Filled by the team, not invented |

## G. Presentation (PDF §11)

| # | Requirement | M/O | How we will satisfy it | Evidence |
|---|---|---|---|---|
| P1 | 15-minute technical presentation + Q&A | M | ~15 slides with speaker notes, rehearsed and timed | Timed rehearsal |
| P2 | System overview and use case | M | Slides 1-3 | Slides |
| P3 | Architecture explanation | M | Slides 4-6 | Slides |
| P4 | Implementation demo or deployment evidence | M | Live demo + recorded backup video | Demo script + video |
| P5 | Security and scalability discussion | M | Slides | Slides |
| P6 | Cost-control explanation | M | Slide with budget screenshot | Slides |
| P7 | Challenges and lessons learned | M | Slides | Slides |
| P8 | **All members participate and can explain architecture + implementation** | M | Per-member speaking section + learning docs + quiz | Rehearsal, quiz results |

## H. Submission (PDF §13)

| # | Deliverable | M/O | Where it comes from | Status check |
|---|---|---|---|---|
| S1 | Architecture diagram (PDF or image) | M | `docs/architecture/` | Exported file exists |
| S2 | Implementation report (PDF) | M | `docs/report/` | Exported file exists |
| S3 | Source code repository link | M | Git repo (to be created by SaSo) | URL recorded |
| S4 | Deployment guide or reproducible scripts | M | `docs/deployment/` + `infrastructure/` | Redeploy rehearsal passed |
| S5 | Demo evidence (screenshots, logs, endpoints, or short video) | M | `docs/evidence/` | Files collected |
| S6 | Presentation slides | M | `docs/presentation/` | File exists |

## I. Academic integrity (PDF §16)

| # | Requirement | M/O | How we will satisfy it |
|---|---|---|---|
| X1 | External sources, code, templates cited | M | `REFERENCES.md` maintained continuously; AWS docs cited with URLs |
| X2 | Architecture, implementation and report are the team's own work | M | The team makes the design decisions; generated drafts are reviewed, edited and understood before submission |
| X3 | No fabricated screenshots, tests, costs or results | M | Every placeholder written as `[INSERT SCREENSHOT HERE]` until real evidence exists |

## J. Optional features (PDF §15) — deferred, not in scope for now

| # | Feature | Decision |
|---|---|---|
| O1 | Basic anomaly detection | Partially covered by threshold rules (F4). No statistical model. |
| O2 | Automatic email alerting (SNS) | Deferred. Candidate for after the core works. |
| O3 | Infrastructure as Code (Terraform/CloudFormation) | Decided in Phase 4 — see scope doc. Strong grade value, moderate risk. |
| O4 | CI/CD pipeline | Out of scope. |
| O5 | Container orchestration (ECS/EKS/K8s) | Out of scope — cost and complexity. |
| O6 | Multi-cloud comparison | Out of scope (a short written comparison may appear in the report's trade-offs). |
| O7 | ML forecasting | Out of scope — explicitly avoided as unjustified complexity. |

---

## Open decisions — RESOLVED in Phase 2 (2026-09-22)

The team confirmed the AWS account is a standard account created with a school email address, carrying 100 credits, with full service access (not a restricted Learner Lab). That resolves all four.

| ID | Decision | Resolution |
|---|---|---|
| OD-1 | Cognito vs. custom JWT auth | **Cognito user pool, Essentials tier** — see `docs/architecture/01-architecture-decisions.md` AD-3 |
| OD-2 | Terraform vs. CLI deployment | **Terraform for infrastructure + a shell script for Lambda code**, confirmed in Phase 4 — AD-9 |
| OD-3 | Region | **eu-west-3 (Paris)** — AD-1 |
| OD-4 | Any EC2/VPC needed? | **No.** Fully serverless; no VPC — AD-7 |

One new constraint emerged from verifying the current AWS Free Tier: on the Free plan an account **closes** at six months or at credit depletion, whichever comes first. See risk **C5** and `docs/cost/01-cost-model.md` §1.

## Team

Somitha Gudivada · Meha · Madhavan · MD — ownership in `06-team-assignment.md`.
