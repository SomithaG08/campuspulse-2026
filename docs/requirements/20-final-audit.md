# Final Requirement Audit

Every requirement in the brief, mapped to evidence. **Four status words only:**

| Status | Means |
|---|---|
| **Complete** | Built and verified; evidence exists in the repository |
| **Partial** | Some of it exists; the gap is named |
| **Not implemented** | We did not build it |
| **Not verified** | It exists in code or configuration but nobody has observed it working |

**Everything that depends on a deployment is currently Not verified**, because nothing is deployed. That is stated once here rather than repeated fifty times, and it is the single thing that changes most of this table.

---

## §4 Functional requirements

| # | Requirement | Status | Evidence |
|---|---|---|---|
| F1 | Real-time or near-real-time ingestion | **Not verified** | `simulator/simulator.py`, `handlers/ingest.py`, 18 simulator tests |
| F2 | User-facing API or web interface | **Not verified** | 7 endpoints in `apigateway.tf`; `frontend/` rendered and inspected |
| F3 | Persistent storage | **Not verified** | `dynamodb.tf` — table, 2 GSIs, TTL, PITR |
| F4 | Data processing / analytics | **Complete (logic)**, Not verified (deployed) | `common/rules.py`, `common/aggregate.py`, 52 tests |
| F5 | Auth + authorization, ≥2 roles | **Not verified** | `cognito.tf`, `common/auth.py`, permission matrix, API tests T3 |
| F6 | Monitoring, logging, observability | **Not verified** | `common/log.py`, `alarms.tf` — 4 alarms, 1 dashboard |
| F7 | Dashboard / visual output | **Not verified** | `frontend/` — rendered light and dark, no console errors |

## §6 Architecture requirements

| # | Requirement | Status | Evidence |
|---|---|---|---|
| A1 | Scalability | **Partial** | Analysis written with the ~1,000 writes/sec ceiling and its fix named. **Gap: no measured numbers** |
| A2 | High availability | **Complete (design + honesty)** | Managed services, multi-AZ by default, stateless compute; single-region stated plainly |
| A3 | Security | **Complete (design), Not verified (runtime)** | Threat model; IAM audited against actual code calls — exact match |
| A4 | Cost optimization | **Partial** | Cost model with sources; several figures still `unverified`; **budget not yet created** |
| A5 | Observability | **Not verified** | 4 alarms, 1 dashboard, troubleshooting runbook |
| A6 | Disaster recovery | **Partial** | PITR configured, procedure documented. **Gap: no restore performed, RTO unmeasured** |

## §7 Implementation requirements

| # | Requirement | Status | Evidence |
|---|---|---|---|
| I1 | Containerized **or** serverless backend | **Not verified** | 5 Lambda functions in `lambda.tf` |
| I2 | Working API or web interface | **Not verified** | API + dashboard |
| I3 | Configured cloud networking | **Complete (as equivalent concepts)** | No VPC by design; trust zones in the diagram; `11-networking-explained.md` |
| I4 | Reproducible deployment | **Partial** | Terraform + scripts + runbook. **Gap: nobody has deployed from the guide** |
| I5 | Monitoring visualization | **Not verified** | CloudWatch dashboard, 6 widgets |
| I6 | ≥1 security mechanism demonstrated | **Not verified** | Three layers; the 401/403/200 demonstration is scripted but not run |
| I7 | Simulated data generation | **Complete** | `simulator.py`, 18 tests, 1000 events through the real validator |

## §8 Cost constraints

| # | Requirement | Status | Evidence |
|---|---|---|---|
| C1 | Use free tier / low cost | **Complete (design)** | Nothing bills by the hour. No EC2, RDS, NAT Gateway, load balancer |
| C2 | **Budget / billing alert with evidence** | **Not implemented yet** | `budget.tf` exists; **no account has one — mandatory** |
| C3 | Stop/delete unused resources | **Complete (procedure)** | `cleanup.md`, `terraform destroy` |
| C4 | Avoid expensive services | **Complete** | Forbidden list in the cost warning; verification script checks none are running |
| C5 | Cost estimate table | **Partial** | Table exists; some rows `unverified` pending `verify-prices.sh` |
| C6 | Justify non-free resources | **Complete** | DynamoDB on-demand and PITR, justified in AD-4 and §7 of the report |

## §9 Architecture diagram

| # | Requirement | Status |
|---|---|---|
| D1-D7 | Components, flows, layers, networking, security zones, external sources, monitoring/backup | **Complete** — ASCII + Mermaid + all 10 connections explained |
| D8 | Understandable without the code | **Not verified** — needs the least technical teammate to confirm |
| — | **Exported as PDF/image for submission** | **Not implemented** |

## §10 Report

| Section | Status |
|---|---|
| All eleven required sections | **Complete (structure and content)** |
| Delivered as PDF | **Not implemented** |
| Free of invented results | **Complete** — 51 placeholders mark what is missing |
| §11.6 what the team learned | **Not implemented** — each member writes their own |
| Contribution table | **Not implemented** |

## §11 Presentation

| # | Requirement | Status |
|---|---|---|
| P1 | 15-minute presentation | **Partial** — 17 slides + script; **never timed** |
| P2-P7 | Overview, architecture, demo, security/scalability, cost, lessons | **Complete (content)** |
| P8 | **All members participate and can explain** | **Not verified** — never rehearsed |
| — | Backup demo video | **Not implemented** |

## §13 Submission

| # | Deliverable | Status |
|---|---|---|
| S1 | Architecture diagram as PDF/image | **Not implemented** (source exists) |
| S2 | Report as PDF | **Not implemented** (source exists) |
| S3 | Repository link | **Not implemented** — repo not yet pushed |
| S4 | Deployment guide / scripts | **Complete** |
| S5 | Demo evidence | **Not implemented** — checklist ready, nothing collected |
| S6 | Presentation slides | **Complete** — `CampusPulse-2026.pptx` |

## §15 Optional features

| Feature | Status |
|---|---|
| Anomaly detection | **Partial** — threshold rules; no statistical model, by choice |
| Email alerting | **Partial** — SNS behind `alarm_email`, off by default |
| Infrastructure as Code | **Complete** — 61 resources in Terraform |
| CI/CD | **Not implemented** — out of scope by choice |
| Container orchestration | **Not implemented** — out of scope by choice |
| Multi-cloud comparison | **Not implemented** |
| ML forecasting | **Not implemented** — deliberately avoided |

## §16 Academic integrity

| # | Requirement | Status |
|---|---|---|
| X1 | Sources cited | **Complete** — `REFERENCES.md` with dates |
| X2 | Work is the team's own | **Complete** — AI assistance disclosed in the report's references |
| X3 | Nothing fabricated | **Complete** — no invented screenshot, cost, test result or metric anywhere |

---

## Score against the grading criteria

| Criterion | Weight | Where it stands |
|---|---|---|
| Architecture quality | 25% | **Strong.** Diagram, nine justified decisions, scalability and DR reasoning, limits stated |
| Implementation completeness | 25% | **Built, unproven.** Everything exists; nothing is deployed. **This is where the remaining risk is concentrated** |
| Security and cloud practices | 15% | **Strong.** Audited IAM, threat model, three enforcement layers — needs the 401/403/200 evidence |
| Technical report | 20% | **Strong structure, 51 gaps.** Fills quickly once evidence exists |
| Presentation | 15% | **Ready, unrehearsed.** Deck, script, demo runbook, Q&A all written |

**The single highest-value hour you can spend is deploying.** It converts most "Not verified" rows to "Complete" at once, and unblocks about forty of the report's placeholders.

---

## Remaining manual tasks — only things that genuinely need a human

### Before anything else (5 minutes)

1. **Check the AWS account's plan and creation date** in the Billing console. On the free plan it closes at six months or credit depletion. Record it in `docs/evidence/cost/`.

### Deployment (about 90 minutes, follow `docs/deployment/05-runbook.md`)

2. `terraform init && validate && plan && apply` — **you are the first to run validate**; expect to fix something.
3. **Verify the budget exists and screenshot it** — mandatory, requirement C2.
4. Create the three Cognito users and set permanent passwords.
5. Run `scripts/verify-deployment.sh`, screenshot the output.
6. Run `scripts/deploy-dashboard.sh`.
7. Run `python tests/api/run_api_tests.py` and **commit the generated JSON**.
8. Run `scripts/verify-prices.sh` and replace the `unverified` rows in the cost model.

### Evidence (about 1 hour — `docs/evidence/CHECKLIST.md`)

9. Dashboard with data · a red alert · the DynamoDB item · the matching log line.
10. **Staff token: 403 on `/alerts`, 200 on `/events`.** The two-role evidence.
11. **Drive an alarm into ALARM deliberately** and screenshot it.
12. **Perform a restore and time it.** That number fills the RTO blank.
13. `aws iam simulate-principal-policy` for `cp-ingest` — machine-generated least-privilege proof.
14. Credit balance, dated, at start and end.

### Writing (only you can)

15. Fill the report's **51 placeholders**.
16. **§11.6** — each member, two or three sentences, own words.
17. **§12 contribution table** — what actually happened.
18. Slide 10's dashboard screenshot; slide 12's cost figure.

### Submission

19. `git init`, commit, push. Record the URL.
20. Export the diagram as PDF/image; export the report as PDF.
21. **Record the backup demo video** the day before; store it locally on two laptops.

### Rehearsal

22. **Time a full run-through.** 14 minutes is an estimate.
23. Each member takes the quiz in `21-team-quiz.md` and answers the Q&A cold.
24. **Have a teammate deploy from the guide alone** — the only real test of requirement I4.

### Afterwards

25. `terraform destroy`, confirm nothing remains, watch the credit balance for 24 hours.

---

## Phase 16 — what this phase produced

| File | What it is |
|---|---|
| `docs/requirements/20-final-audit.md` | This document |
| `docs/learning/21-team-quiz.md` | 32 questions with answers, for the oral exam |

**Verification performed:** every requirement in the brief's §4, §6, §7, §8, §9, §10, §11, §13, §15 and §16 is represented above, each with one of the four status words and a pointer to its evidence. No requirement is marked Complete on the strength of a deployment that has not happened.
