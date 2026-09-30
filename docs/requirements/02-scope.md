# Project Scope — CampusPulse 2026

## 1. The use case we chose

**A campus operations monitoring and alerting platform.**

Simulated IoT devices across NorthBridge University (occupancy, temperature, humidity, energy meters, equipment status) and student service requests send events to a cloud API. The platform stores them, classifies them by severity, aggregates them, and shows the campus operations team a dashboard answering: which rooms are occupied or overloaded, which buildings consume the most energy, what is abnormal right now, and which student requests are urgent.

The PDF (§4) offers six example use cases and explicitly allows a *hybrid dashboard combining several of the above*. That is what we build — one ingestion path, one storage model, one dashboard, several event types. This is deliberate: one coherent pipeline is easier to build, demo and defend than several half-built ones.

## 2. What we WILL build

**Data generation**
- A Python simulator representing campus IoT devices and student requests
- Multiple buildings and rooms, six event types, normal and abnormal values, configurable rate (`--interval`) and volume (`--number-of-events`)

**Ingestion and API**
- A REST API over HTTPS with the endpoints in PDF Appendix B: `POST /events`, `GET /events`, `GET /stats`, `POST /login`, `GET /alerts` (plus a small endpoint for staff service requests)
- Serverless backend: API Gateway invoking Lambda functions

**Storage**
- DynamoDB for events, with a key design that supports "recent events for a building" queries without full-table scans
- S3 for the static dashboard and for backup exports

**Processing**
- Severity classification at write time (threshold rules: occupancy over room capacity, temperature/humidity out of range, energy spike, equipment failure, urgent request)
- Aggregation at read time for `/stats`: current occupancy, average temperature, energy per building, event counts by type and by severity, alert count

**Access control**
- Two roles — `ops` and `staff` — with different permitted endpoints
- Token-based login; every protected endpoint checks the token and the role

**Dashboard**
- A single static page: KPI tiles, recent events table, alerts panel, occupancy and energy views
- Calls the same API the simulator writes to

**Operations**
- CloudWatch logs for every function, custom metrics, a dashboard, and alarms
- A budget/billing alert
- A backup and restore procedure that we actually rehearse once
- A deployment guide complete enough for a teammate to reproduce the stack from zero

**Documentation**
- Beginner learning docs (`docs/learning/`), file-by-file explanations, a glossary, a troubleshooting runbook, a learning path and presentation scripts, because several teammates start from zero cloud knowledge and PDF §11 requires all members to explain the system

## 3. What we will NOT build

| Not building | Why |
|---|---|
| Real IoT hardware or MQTT brokers | The PDF asks for *simulated* sources (§4, §7). An IoT Core broker adds cost and a large learning surface for no extra marks |
| Machine learning / forecasting | Optional (§15). Adds complexity we cannot defend well in an oral exam. Threshold rules are explainable by every team member |
| Kubernetes / ECS / EKS | Optional (§15). Cluster costs money and time; serverless already satisfies "containerized **or** serverless" (§7) |
| RDS or any always-on database | DynamoDB on-demand costs nothing when idle; RDS free tier still burns credits 24/7 |
| NAT Gateway | ~$0.045/hour plus data charges — roughly $32/month for nothing we need. This single line protects the 100 credits |
| Load balancer (ALB/NLB) | Always-on hourly cost; API Gateway already provides a managed, scaling HTTPS entry point |
| Always-on EC2 | Only if the account check forces us off serverless; then one t2/t3.micro, stopped when not in use |
| CI/CD pipeline | Optional (§15). Not graded separately; costs team time better spent on evidence collection |
| Multi-region deployment | We will not claim DR capabilities we have not implemented. Single-region, honestly documented |
| A production-grade frontend framework build | A small dependency-free page is faster, fails less on demo day, and is explainable by beginners |
| Multi-cloud implementation | Optional (§15). At most a short written comparison in the report's trade-offs section |

## 4. Optional features: the rule we follow

**No optional feature starts before the core pipeline works end to end and is demonstrable.**

Ranked by grade value per hour of risk, if time remains after Phase 12:
1. **Infrastructure as Code (Terraform)** — highest value: it satisfies "reproducible deployment" (§7) more convincingly than a manual guide, and is named in §5 and §15. Decision deferred to Phase 4 because it depends on whether our account lets us create IAM roles.
2. **SNS email alerting** — cheap, demos beautifully (an alert email arriving live during the presentation), small code surface.
3. **Statistical anomaly detection** (rolling mean ± k·σ per room) — only if someone on the team can explain it under questioning.

Everything else stays out.

## 5. Why this scope is realistic

- **The PDF sets the bar honestly:** §7 — *"The prototype does not need to be large, but it must be coherent, functional, and aligned with the proposed architecture."* Coherence is the graded property, not size.
- **Grade weighting rewards it:** Architecture 25% + Report 20% + Security 15% + Presentation 15% = **75% of the grade is design, explanation and evidence**, not lines of code. Implementation completeness is 25%, and a small working system scores that fully; a large broken one scores poorly on both.
- **Serverless removes the two biggest student time sinks:** server administration and networking debugging. No SSH, no OS patching, no NAT, no load-balancer health checks.
- **Everything idles at zero cost.** With 100 credits and no hourly resources, the financial risk is close to nil as long as the forbidden list above is respected.
- **Beginners can own real components.** The simulator, the dashboard, the test suite and the evidence collection are each a genuine, explainable contribution that does not require deep AWS knowledge — which is what §11 and §16 demand.

## 6. Success in one sentence

A teammate who has never used AWS can open the dashboard, start the simulator, watch an abnormal event become an alert, show the log line that proves it, explain why each service is there, and say what it costs.
