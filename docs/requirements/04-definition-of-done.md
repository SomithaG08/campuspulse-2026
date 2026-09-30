# Definition of Done — CampusPulse 2026

The project is complete when **every line below is true and verified by a person**, not when the code exists.

Status vocabulary used across this project (and in the Phase 16 audit) — no other words:
**Complete** · **Partial** · **Not implemented** · **Not verified**

---

## 1. Working system (maps to "Implementation Completeness", 25%)

- [ ] The simulator runs from a clean checkout with documented commands and produces valid events
- [ ] `POST /events` accepts a valid event over HTTPS and rejects an invalid one with a 400 and a useful message
- [ ] The event is persisted and readable afterwards through `GET /events`
- [ ] `GET /stats` returns aggregated values that a human has manually checked against the stored data at least once
- [ ] `GET /alerts` returns only abnormal events, verified by injecting one normal and one abnormal event
- [ ] `POST /login` returns a token for a valid user and fails cleanly for an invalid one
- [ ] The dashboard loads in a browser and displays live data from the deployed API
- [ ] An abnormal event submitted during a run appears as an alert on the dashboard **without a manual step**
- [ ] The whole flow has been executed end to end at least twice, on different days, from a clean state

## 2. Two roles, actually enforced (maps to "Security and Cloud Practices", 15%)

- [ ] Two users exist with different roles (`ops`, `staff`)
- [ ] A protected endpoint returns **401** without a token
- [ ] A protected endpoint returns **403** for a token whose role is not permitted — demonstrated, with the response captured
- [ ] Passwords are never stored or logged in plaintext (log inspection performed and recorded)
- [ ] Each Lambda has its own least-privilege IAM policy, or any forced exception is documented honestly
- [ ] No credential, key or token exists anywhere in the Git repository (repo scanned before submission)
- [ ] Secrets management is documented and implemented: configuration comes from environment variables or Parameter Store, never from hard-coded values
- [ ] Encryption at rest and in transit is verified in the console, not assumed
- [ ] A threat model table exists covering at minimum: unauthorized access, credential compromise, malicious event submission, excessive permissions, data exposure, API abuse, misconfiguration — each marked *Implemented* / *Configured* / *Planned*

## 3. Cloud architecture qualities (maps to "Architecture Quality", 25%)

- [ ] An architecture diagram exists showing components, flows, compute/storage/processing layers, network and security boundaries, IAM boundaries, external sources, monitoring and backup
- [ ] Someone outside the team could follow the diagram without reading code (tested on the least technical teammate)
- [ ] Scalability: written analysis naming the real limits of the services we use, supported by at least one measured observation from a high-rate simulator run
- [ ] High availability: written analysis of what is genuinely redundant and what is not — single-region stated plainly
- [ ] Disaster recovery: backup mechanism enabled, **a restore actually performed once**, RPO and RTO stated with the reasoning behind the numbers
- [ ] Every AWS service in the architecture has a written answer to: what it is, why it is there, what it costs, what breaks without it

## 4. Observability

- [ ] Every Lambda writes structured logs, visible in CloudWatch
- [ ] At least one custom metric is published and graphed
- [ ] At least two alarms exist, and **one has been deliberately triggered** with the ALARM state captured
- [ ] A CloudWatch dashboard shows system state at a glance
- [ ] A troubleshooting runbook covers 400 / 401 / 403 / 500, Lambda failure, empty database, empty dashboard, login failure, simulator connection failure, deployment failure

## 5. Cost control

- [ ] A budget or billing alert is configured, with a screenshot
- [ ] The alert has been received or its configuration verified
- [ ] A cost estimate table exists with, per service: free-tier allowance, our expected usage, expected charge, and the pricing page it came from
- [ ] No hourly-billed resource is running that is not justified in writing
- [ ] Credit consumption has been checked and recorded at least twice during the project
- [ ] A cleanup procedure exists and has been rehearsed at least once

## 6. Reproducible deployment

- [ ] A deployment guide exists with complete, copy-pasteable commands and no unexplained placeholders
- [ ] **A teammate who did not write it deployed the stack from scratch using only that guide** and reported the outcome
- [ ] Prerequisites, region, and account assumptions are stated explicitly
- [ ] A cleanup/teardown path is documented and tested

## 7. Testing (maps to the report's Testing section)

- [ ] Unit tests exist for validation and the severity rules
- [ ] API tests exist for each endpoint, including failure cases
- [ ] Authentication and authorization tests exist
- [ ] Every test in the report is labelled **Created** / **Executed** / **Not executed** with real output, never invented
- [ ] Test output is stored in the repo as evidence

## 8. Documentation and learning (enables "Presentation", 15%)

- [ ] `README.md` covers overview, architecture, stack, install, deploy, API, tests, security, monitoring, cost, cleanup
- [ ] Every important source file has a learning document explaining it at beginner and technical level
- [ ] The learning documents match the code as it actually is (Phase 13 audit passed)
- [ ] The glossary covers every term used in the report and slides
- [ ] A learning path exists taking a zero-knowledge teammate to "can explain the project"
- [ ] Each major component has a 20-60 second spoken explanation written down
- [ ] Every team member has taken the final quiz and can answer the architecture questions

## 9. Submission package (PDF §13)

- [ ] Architecture diagram exported as PDF or image
- [ ] Implementation report exported as PDF, all eleven required sections present
- [ ] Source code repository link recorded and the repo is accessible
- [ ] Deployment guide / scripts included
- [ ] Demo evidence collected: screenshots, logs, endpoint URLs, and a backup video
- [ ] Presentation slides finished
- [ ] Contribution table filled with what each member actually did
- [ ] References list complete, no fabricated citations

## 10. Presentation readiness (15%)

- [ ] The deck fits in 15 minutes, verified by a timed rehearsal
- [ ] Every member has a speaking part and has rehearsed it
- [ ] The demo has been rehearsed against the deployed system, not against a local mock
- [ ] The offline backup video exists on a local drive
- [ ] The team has rehearsed answers to likely questions: why this architecture, what happens if Lambda fails, how does it scale, how is the API protected, how do you control cost, what is your RPO/RTO, what would you do differently

---

## The three rules that override everything

1. **Nothing is "done" because it was written — only because it was run and observed.**
2. **No invented evidence.** If it cannot be shown, it is written as *Not verified yet*.
3. **If a teammate cannot explain a component, that component is not finished.**
