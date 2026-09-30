# Risk Register — CampusPulse 2026

Severity = impact if it happens. Likelihood = our honest estimate for a student team.
Every risk has an owner-to-be-named and a mitigation that is an action, not a hope.

## 1. Technical risks

| ID | Risk | Likelihood | Severity | Mitigation | Early warning sign |
|---|---|---|---|---|---|
| T1 | ~~The school account blocks a service we designed around~~ **RESOLVED 2026-09-22**: standard account, full service access | — | — | Closed. The fallback designs stay documented in case a service is later restricted | — |
| T2 | Resources exist only in the console, so a mistake or a wipe means rebuilding by hand | Medium | High | Everything redeployable from Terraform + scripts; never let the only copy of anything live in the console | A resource nobody can recreate |
| T3 | Wrong DynamoDB key design forces table scans and a rewrite later | Medium | Medium | Decide access patterns in Phase 2 *before* creating the table; write the query list first, key design second | `/stats` or `/events` needs a Scan |
| T4 | CORS blocks the dashboard from calling the API | High | Low | Known, standard problem. Enable CORS at API Gateway and in Lambda responses from the first deploy; test the dashboard against the real API early, not on demo day | Browser console: "blocked by CORS policy" |
| T5 | Lambda cold starts make the demo look slow | Medium | Low | Warm the API with one call before the demo; keep the deployment package small; mention cold starts honestly in the scalability section — the professor will likely ask | First request takes 1-3 s |
| T6 | Clock/timestamp confusion between simulator, Lambda and DynamoDB | Medium | Low | Standardise on UTC ISO-8601 everywhere, as in the PDF's example event | Dashboard shows events in the wrong order |

## 2. Cost risks

| ID | Risk | Likelihood | Severity | Mitigation | Early warning sign |
|---|---|---|---|---|---|
| C1 | **An hourly resource is left running** (NAT Gateway, EC2, ALB, RDS) and eats the 100 credits | Medium | Critical | Forbidden-services list in the scope doc; budget alert configured in Phase 4 *before* any other resource; teardown rehearsal; a "what is running?" check at the end of every work session | Credit balance drops while nobody is working |
| C2 | A runaway simulator loop generates millions of requests | Low | High | Default `--interval` of seconds, not milliseconds; a hard `--number-of-events` cap in the code; CloudWatch alarm on invocation count | Invocation graph spikes |
| C3 | CloudWatch log retention left at "never expire" quietly accrues storage cost | Medium | Low | Set log group retention to 7 days at creation | Growing log storage in the cost report |
| C4 | We claim "free" without checking, and the report is wrong | Medium | Medium | Every cost claim in the report cites the AWS pricing or free-tier page it came from, with the date checked | An unsourced "this is free" sentence |
| **C5** | **The AWS account closes mid-project.** Under the Free Tier rules in force since July 2025, a Free-plan account ends at **6 months after sign-up or when the credits are depleted, whichever comes first** — AWS then closes it and the resources and data become inaccessible (retained 90 days, recoverable only by upgrading to the Paid plan) | Medium | **Critical** | Confirm the account's plan and creation date **now**; put the six-month date in the team calendar; keep everything reproducible from code so the stack can be rebuilt in a different account if needed; export the evidence (screenshots, logs, exported data) out of AWS as it is collected rather than leaving it only in the console | The six-month date falling anywhere near the submission or presentation |
| C6 | Joining an AWS Organization or setting up Control Tower **expires the credits immediately** and force-upgrades the account | Low | Critical | Simply do not do either. Written into the deployment guide as a prohibition | An invitation to join an Organization |

## 3. Security risks

| ID | Risk | Likelihood | Severity | Mitigation | Early warning sign |
|---|---|---|---|---|---|
| S1 | **AWS credentials committed to the public Git repo** | Medium | Critical | `.gitignore` before the first commit; credentials only in environment variables / AWS CLI profiles; scan the repo before submission; never paste keys into docs or slides | Any `AKIA...` string anywhere in the repo |
| S2 | The ingestion endpoint is left completely open and gets abused | Medium | High | Require an API key or token on `POST /events`; API Gateway throttling and usage plan; input validation rejecting oversized or malformed payloads | Unexpected invocations in CloudWatch |
| S3 | Over-permissive IAM (`Action: "*"`) used to "make it work" and never fixed | High | High | Write per-function least-privilege policies from the start; a security review task in Phase 7 that re-reads every policy; document any forced exception (e.g. a lab-provided shared role) honestly | A policy with a wildcard |
| S4 | Passwords stored or logged in plaintext | Low | Critical | Cognito if available; otherwise hashed with a vetted library, never logged; log redaction check in Phase 7 | A password visible in CloudWatch Logs |
| S5 | Screenshots in the report leak account IDs, endpoint URLs or tokens | Medium | Medium | Redaction checklist applied when evidence is collected, not at the end | Raw account number visible in an image |

## 4. Integration risks

| ID | Risk | Likelihood | Severity | Mitigation |
|---|---|---|---|---|
| N1 | Components built separately do not fit together (simulator payload ≠ API schema ≠ dashboard expectation) | High | High | The event schema is frozen in Phase 2 and written into `docs/architecture/data-model.md`; every component is coded against that one document; one shared example event used in all tests |
| N2 | Auth is bolted on last and breaks the working dashboard | Medium | Medium | Design the token flow in Phase 2 and stub it in Phase 5, even though it is implemented in Phase 7 |
| N3 | Everyone works in one AWS account and overwrites each other's resources | Medium | Medium | Name-prefix convention per person for experiments; only one person runs the "official" deploy |

## 5. Demo risks

| ID | Risk | Likelihood | Severity | Mitigation |
|---|---|---|---|---|
| M1 | **The venue's Wi-Fi fails or AWS is unreachable during the presentation** | Medium | Critical | Record a full demo video in advance (PDF §13 accepts video as evidence) and carry it offline; screenshots in the slides as a second fallback |
| M2 | The lab session/credentials expire minutes before the demo | Medium | Critical | Re-deploy and smoke-test the morning of the presentation; a one-command smoke test in the repo |
| M3 | Live typing errors during the demo | High | Low | A written demo script with exact commands, copy-pasteable, rehearsed at least twice |
| M4 | The alert we want to show does not fire on cue | Medium | Medium | A dedicated `--force-alert` mode in the simulator that reliably produces an abnormal event |

## 6. Documentation risks

| ID | Risk | Likelihood | Severity | Mitigation |
|---|---|---|---|---|
| G1 | Docs drift from the code and we defend a system that no longer exists | High | High | Doc update is part of each phase's definition of done, not a final step; Phase 13 is a full documentation audit |
| G2 | The report contains invented results (costs, tests, screenshots) | Medium | Critical | Hard rule: placeholders `[INSERT SCREENSHOT HERE]` until real evidence exists; test results copied verbatim from actual runs; this is an academic-integrity matter (§16), not a style preference |
| G3 | Evidence is collected only at the end and half of it is impossible to reproduce | High | Medium | `docs/evidence/` from Phase 4 onward: screenshot as you go, with a date and what it shows |

## 7. Team knowledge risks

| ID | Risk | Likelihood | Severity | Mitigation |
|---|---|---|---|---|
| K1 | **One person builds everything and the others cannot answer questions** — directly penalised by §11 ("all team members must participate and be able to explain") | High | Critical | Every teammate owns at least one component *and* writes its learning doc; the final quiz is taken by everyone; rehearsal with cross-questions |
| K2 | Beginners stall because the vocabulary is unfamiliar | High | Medium | `docs/learning/` with two-level explanations (simple + technical), a glossary, and a step-by-step learning path |
| K3 | Uneven contribution creates a dishonest contribution table | Medium | High | Track tasks as they are done; the table records what actually happened |
| K4 | Deadline compression — everything left to the last week | High | High | Phase order is itself the schedule; the core pipeline (Phases 4-9) must be working well before evidence, report and rehearsal begin |

## Top five to watch

1. **C5** — the account closing at the six-month mark, or when credits run out
2. **C1** — an hourly resource draining the credits
3. **S1** — credentials in a public repository
4. **K1** — teammates unable to explain the system at the oral
5. **M1** — the live demo failing at the venue
