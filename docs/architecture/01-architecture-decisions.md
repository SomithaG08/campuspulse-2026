# Architecture Decisions — CampusPulse 2026

Every decision below is written as: **options considered → what we chose → why → what it costs us**. This format is what you defend at the oral exam; "we used Lambda because it's serverless" is not an answer, "we used Lambda because our traffic is bursty and idle most of the day, so paying per request instead of per hour costs us nothing when nobody is sending events" is.

---

## AD-0: Overall style — serverless, not servers

**Options**
| Option | What it means | Verdict |
|---|---|---|
| EC2 + Nginx + Node/Flask | One virtual machine running our API 24/7 | **Rejected** |
| Containers on ECS/EKS | Our API in Docker, orchestrated | **Rejected** |
| Serverless: API Gateway + Lambda | AWS runs our code only when a request arrives | **Chosen** |

**Why serverless**
- **Cost shape matches our usage.** Campus events arrive in bursts during a demo and then nothing for days. An EC2 instance bills every hour whether or not anyone uses it; Lambda bills per request and costs literally nothing while idle. With a fixed 100-credit budget that runs out permanently, "costs nothing while idle" is the single most valuable property available to us.
- **It deletes the hardest beginner topics.** No SSH keys, no OS patching, no web-server config, no process manager, no NAT Gateway, no load-balancer health checks. Four teammates with mixed experience can all understand "a function runs when a request arrives".
- **The spec allows it explicitly.** §7 requires "at least one **containerized or serverless** backend service".
- **Availability and scaling come for free** — and we can say precisely why, which §6 asks for.

**What it costs us**
- Cold starts: the first request after idle takes ~1-3 s. We mitigate it in the demo and discuss it honestly in the report.
- Vendor lock-in: this design does not lift to another cloud unchanged. A real trade-off, worth one honest paragraph in "Lessons learned".
- Debugging moves to CloudWatch Logs instead of a terminal on a server.

---

## AD-1: Region — Europe (Paris) `eu-west-3`

**Options:** `us-east-1` (N. Virginia — cheapest, every service, most tutorials) · `eu-west-3` (Paris) · `eu-west-1` (Ireland).

**Chosen: `eu-west-3` (Paris).**

**Why**
- NorthBridge University is a European university and the platform processes data about identified rooms and people's service requests. Keeping personal data in the EU is the defensible choice and gives us a real GDPR/data-residency sentence in the security section rather than an invented one.
- Lowest latency from campus, which matters for a live demo over the venue's network.
- All services in this design are available there.

**What it costs us:** unit prices in `eu-west-3` are generally slightly higher than `us-east-1`. At our volumes that is cents. **We have not yet verified eu-west-3 unit prices** — the AWS pricing pages render their regional tables in JavaScript and could not be read directly. Phase 4 verifies them with `aws pricing get-products` and the cost model is corrected then if needed.

**Rule for the team: everything goes in one region. One person creates resources, everyone else reads.**

---

## AD-2: API layer — API Gateway **HTTP API**, not REST API

| | HTTP API (v2) | REST API (v1) |
|---|---|---|
| Price | **$1.00 per million** requests | $3.50 per million |
| Free tier | 1M calls/month, 12 months (legacy offer — see cost model) | 1M calls/month, 12 months (legacy offer) |
| Cognito JWT auth | **Built in** (native JWT authorizer) | Needs a Cognito authorizer or a custom Lambda authorizer |
| CORS | **Built-in setting** | Manual per-method configuration, a classic time sink |
| API keys / usage plans | Not supported | Supported |
| Request validation, WAF, caching | Limited | Yes |

**Chosen: HTTP API.** 3.5× cheaper, the built-in JWT authorizer is exactly our auth model, and built-in CORS removes risk T4 (the single most common thing that breaks student dashboards).

**What we give up:** API keys and usage plans. We do not need them — the simulator authenticates with a real Cognito token like any other client, which is a *better* security story than a shared API key. Stage-level throttling still protects us from runaway loops.

*Source: [API Gateway pricing](https://aws.amazon.com/api-gateway/pricing/) — free tier and both per-million prices confirmed on the page.*

---

## AD-3: Authentication — Amazon Cognito user pool

**Options:** Cognito user pool · our own JWT auth in Lambda with hashed passwords in DynamoDB.

**Chosen: Cognito**, now that we have confirmed the account has full service access.

**Why**
- Passwords are never stored, hashed, or handled by our code. The most dangerous thing a student project can get wrong is removed entirely — risk S4 disappears rather than being mitigated.
- Roles come from Cognito **groups** (`ops`, `staff`) which appear inside the JWT as `cognito:groups`. API Gateway validates the token's signature and expiry before our code runs; our Lambda only has to read the group claim. Two enforcement layers, both explainable.
- It is named in the spec's recommended architecture (§5).
- **Free tier: 10,000 monthly active users** for Lite/Essentials user pools, and that allowance is not limited to the first 12 months. We will have about six users.

**What it costs us:** one more service to learn, and the login flow has vocabulary (user pool, app client, ID token vs access token) that the learning docs must cover properly.

*Source: [Cognito pricing](https://aws.amazon.com/cognito/pricing/) — "10,000 MAU per month… applicable to user pools configured as Lite or Essentials"; "There is no free tier for the Plus tier". We use **Essentials**. Avoid the Plus tier: it has no free tier at all.*

**Cost trap we are avoiding:** machine-to-machine (client-credentials) token requests have **no free tier** and are billed per token request. Our simulator therefore signs in as a normal user (`device@campuspulse.local`) and reuses its token, instead of using an M2M app client.

---

## AD-4: Storage — DynamoDB, one table, **on-demand** capacity

**Options:** RDS (PostgreSQL) · DynamoDB provisioned · DynamoDB on-demand.

**RDS rejected:** a database instance bills per hour, 24/7, whether or not we use it. That is exactly the shape of spend that kills a fixed credit budget.

**Provisioned vs on-demand — this one is a genuine trade-off:**

| | Provisioned (25 RCU / 25 WCU) | On-demand |
|---|---|---|
| Free tier | **Yes** — 25 WCU, 25 RCU, 25 GB storage per month, per region | Storage counts toward the 25 GB; **requests are not in the free-tier allowance as published** |
| Behaviour under a spike | Throttles (`ProvisionedThroughputExceeded`) | Absorbs it automatically |
| Cost of our expected volume | $0 | a few cents (see cost model) |
| Scalability story at the oral | "we sized capacity manually" | "capacity scales per request, no planning" |

**Chosen: on-demand.** At ~100,000 events over the whole project the request cost is pennies, and we avoid the one failure mode guaranteed to ruin the live demo — a throttled write while the professor is watching. The scalability answer is also stronger and truer.

**We will say this explicitly in the report,** including the number, because claiming "DynamoDB is free tier" while running on-demand would be exactly the unsourced cost claim the spec warns about.

*Source: [DynamoDB pricing](https://aws.amazon.com/dynamodb/pricing/) — the free tier is stated as using **provisioned** capacity and the Standard table class: 25 WCU, 25 RCU, 25 GB storage, 2.5M stream reads per month.*

---

## AD-5: Four small Lambdas, not one big one — **SUPERSEDED by AD-11 (October 2026)**

> Kept as a record of the original reasoning. After the project review the system runs two functions; see AD-11.

| Function | Routes | IAM permission it gets |
|---|---|---|
| `cp-auth` | `POST /login` | `cognito-idp:InitiateAuth` on our user pool only |
| `cp-ingest` | `POST /events`, `POST /requests` | `dynamodb:PutItem` on the events table only |
| `cp-query` | `GET /events`, `GET /alerts` | `dynamodb:Query` on the table and its indexes only |
| `cp-stats` | `GET /stats` | `dynamodb:Query` on the table and its indexes only |

**Why split:** it is what makes least privilege real instead of rhetorical. The function that receives untrusted input from the internet **cannot read the database**, and the functions that read **cannot write**. If an attacker found an injection bug in `cp-ingest`, the blast radius is "can write items", not "can read every student request on campus". That sentence is worth marks in a security section, and it is only true because we split the functions.

**What it costs us:** four deployment packages instead of one. Shared code (validation, rules, response helpers) lives in `backend/src/common/` and is packaged into each.

---

## AD-6: Dashboard — static files on S3, no framework, no CloudFront

**Chosen:** plain HTML + CSS + vanilla JavaScript, uploaded to an S3 bucket with static website hosting.

**Why:** no build step, no `node_modules`, no framework version to break the week of the demo, and every teammate can read the code. CloudFront would add a CDN we do not need for one browser in one room.

**The security point we must make honestly:** the bucket is publicly readable **because it contains only the public page shell — HTML, CSS, JavaScript. It contains no campus data.** Every piece of data arrives in the browser from the API, and the API refuses to answer without a valid Cognito token. This goes in the threat model as a deliberate, bounded decision, not an oversight.

---

## AD-7: No VPC — **SUPERSEDED by AD-10 (October 2026)**

> Kept as a record. The review asked for a VPC, and the cost argument below turned out not to apply: a NAT Gateway is needed only for *internet* access, and a DynamoDB gateway endpoint is free. See AD-10.

There is no VPC, no subnet and no security group in this architecture, and that is a decision, not an omission.

Lambda, API Gateway, DynamoDB, Cognito and S3 are **AWS-managed services with no servers of ours inside a network we own**. Our network boundary is not a subnet — it is **IAM plus the JWT authorizer**. Traffic between AWS services stays on the AWS network and is encrypted in transit.

The spec (§9) asks the diagram to show "networking configuration including VPC, subnets, security groups, **or equivalent concepts**". Our equivalent concepts are trust zones and IAM boundaries, which the diagram draws explicitly.

**The cost consequence is the headline:** a private-subnet design needs a **NAT Gateway** to reach anything outside the VPC, billed per hour plus per GB — roughly $30-35 per month for a resource that would do nothing for us. On a 100-credit budget that one component could consume a third of the budget in a month of idling. Choosing managed services avoids it entirely.

`docs/learning/11-networking-explained.md` teaches VPC, subnets and security groups properly and shows what our architecture *would* look like on EC2, so the team can answer VPC questions at the oral even though we did not build one.

---

## AD-8: Processing — threshold rules at write time, aggregation at read time

**Write time (`cp-ingest`):** each event is compared against a rule for its type (occupancy vs room capacity, temperature/humidity bands, energy spike, equipment failure, request urgency) and gets a `severity` of `normal`, `warning` or `critical`. Anything not `normal` is also written into a sparse alerts index.

**Read time (`cp-stats`):** aggregates are computed by querying today's partition and summarising in the function — current occupancy per room, average temperature, energy per building, counts by type and severity.

**Why not a streaming pipeline (Kinesis, DynamoDB Streams + aggregator, Athena)?** Because at our volume it would be machinery no teammate could explain, and §13 of our brief is explicit that complexity must be justified. We *will* explain in the scalability section what we would change if volume grew by 1000× — that is where DynamoDB Streams and pre-aggregated counters belong, as a designed answer rather than unused code.

---

## AD-9: Deployment — decided in Phase 4, leaning Terraform

The account allows IAM role creation, so Terraform is possible. Terraform gives us `terraform apply` as the reproducibility evidence §7 asks for, and it is named in the spec's optional list (§15).

**Risk:** Terraform is a new tool for beginners and a broken state file the week before submission is a real hazard.

**Planned compromise, confirmed in Phase 4:** Terraform for the infrastructure that rarely changes (DynamoDB table, Cognito pool, IAM roles, S3 bucket, CloudWatch alarms), plus a short shell script for packaging and updating Lambda code, which is the part that changes constantly. One person owns the state file; everyone else can read the `.tf` files as documentation of what exists.

---

## AD-10: A VPC with private subnets and a free DynamoDB gateway endpoint (October 2026)

**Context.** Project review: "VPC missing". The brief (§7) asks for "a configured cloud networking environment".

**Options**
| Option | Monthly cost | Verdict |
|---|---|---|
| No VPC (AD-7) | $0 | **Rejected** by the review |
| Lambda in private subnets + NAT Gateway | ~$32 + data | **Rejected** — a third of the budget, and gives the data function internet access it does not need |
| Lambda in private subnets + interface endpoints (DynamoDB, Cognito, SNS) | ~$8 per endpoint per AZ | **Rejected** — ~$48/month for two AZs |
| **Lambda in private subnets + DynamoDB *gateway* endpoint** | **$0** | **Chosen** |

**What we built** (`infrastructure/terraform/vpc.tf`): VPC `10.20.0.0/16`; two private `/24` subnets in eu-west-3a and eu-west-3b; one route table with no `0.0.0.0/0` route; no internet gateway, no NAT; a DynamoDB gateway endpoint whose policy allows `PutItem`/`Query` on our table only; a security group with no inbound rules and outbound HTTPS to the DynamoDB prefix list only; the default security group emptied; VPC Flow Logs to CloudWatch (7 days).

**Why it is worth having even though the services are managed.** The data function can now send data to exactly one place — our table — whatever bug or stolen credential is involved. That is a property IAM alone cannot give: IAM limits *what* a function may call, the network limits *where* its packets can go.

**What it costs us.** Lambda in a VPC takes minutes to release its network interfaces on `terraform destroy`. The `auth` function cannot live inside (AD-11). Extending the system to call another AWS service from the `api` function now needs an endpoint for that service.

---

## AD-11: Two Lambda functions, grouped by business requirements and network boundaries (October 2026)

**Context.** Project review: "Group Lambda functions according to business requirements, and VPC is missing". The original version had five nano-functions (`health`, `auth`, `ingest`, `query`, `stats`) split purely by HTTP verb and technical CRUD action on the same data entity. This created function sprawl, duplicate connection overhead, and failed to reflect high-level business capabilities.

We reorganized the compute layer into **two distinct business-capability domains** aligned with our security and networking boundaries:

| Business Domain & Function | Network Boundary | Business Responsibilities & Routes | IAM Scope & Security Guarantee |
|---|---|---|---|
| **Public Identity & Access Gateway**<br/>`campuspulse-dev-auth` | **Outside the VPC** | **Identity & Access Management:** User authentication, JWT token minting, role assertion (`admin` vs `student`).<br/>Route: `POST /login` | `cognito-idp:InitiateAuth` on Cognito User Pool.<br/>**Zero database access:** Cannot read, write, or touch campus operational records. |
| **Protected Campus Operations Platform**<br/>`campuspulse-dev-api` | **Inside the VPC** (2 private subnets across 2 AZs, no internet access) | **Campus Operations & Telemetry:** Ingesting & validating sensor telemetry (`POST /events`), student facility maintenance requests (`POST /requests`, `GET /requests`), campus comfort & energy analytics (`GET /stats`), real-time operational alerts (`GET /alerts`), event auditing (`GET /events`), and system health (`GET /health`). | `dynamodb:PutItem` + `dynamodb:Query` on the events table and indexes via private DynamoDB Gateway Endpoint.<br/>**Zero internet access:** Cannot communicate with the outside internet, preventing data exfiltration. |

**Why this satisfies business requirements:**
1. **Separation of Concerns:** Authentication and identity management is a distinct public-facing capability with different scaling, lifecycle, and security needs than internal campus operations.
2. **True Network Isolation:** The function that connects to the public internet (to reach Cognito's public API) has no permission to access campus data. The function that manages campus data is sealed inside a private network with no internet gateway or NAT gateway, reaching DynamoDB exclusively through an internal gateway endpoint.
3. **Operational Performance:** Co-locating related campus operations within a warm container context eliminates redundant cold starts between telemetry ingestion and operational queries while sharing common validation and configuration logic (`campus_config.py`).
4. **Least-Privilege Defense in Depth:** While the consolidated `api` function combines read and write permissions, this risk is tightly bounded by three independent controls: (a) physical network isolation in private subnets, (b) the VPC endpoint policy which whitelists our table only, and (c) strict per-route Cognito group authorization checks (`common/auth.py`).

---

## AD-12: Backups in two independent layers (October 2026)

**Context.** Project review: "backup missing". PITR existed, but it is a feature *of the table*; it is not a backup system and it does not survive the table being deleted beyond a short window.

**Chosen:** keep PITR (any second, 35 days, RPO ≈ 5 min) **and** add AWS Backup: a vault, a daily rule (03:00 UTC, kept 7 days) and a weekly rule (Sunday 04:00 UTC, kept 35 days) selecting the events table; S3 versioning on the site bucket (old versions kept 30 days). `scripts/backup-now.sh` takes an on-demand backup; `scripts/restore-drill.sh` restores the latest recovery point into a new table, times it (the measured RTO) and deletes the copy.

**Why AWS Backup rather than DynamoDB on-demand backups by script.** A schedule, retention and a separate vault are configuration, not a cron job someone must remember; it is also the service an operations team would use for more than one resource.

**What it costs us.** Backup storage is billed per GB-month (≈$0.10). Our table is under 10 MB: fractions of a cent. `force_destroy` on the vault lets `terraform destroy` clean up — which also means a destroy deletes the backups; that is right for a course project and wrong for production.

---

## AD-13: Team alerts by email through CloudWatch alarms and SNS (October 2026)

**Context.** Project review: "alerts should be redirected to the team with school mail".

**Options**
| Option | Verdict |
|---|---|
| The `api` function publishes to SNS for each critical event | **Rejected** — needs internet or an SNS interface endpoint (~$8/AZ/month) from inside the VPC, and would email once per event |
| DynamoDB Streams → a third Lambda → SNS | **Rejected** — reintroduces a function the review asked us to remove |
| **EMF metric → CloudWatch alarm → SNS topic → email to each team address** | **Chosen** |

**How.** The ingest route emits `AlertsRaised{Severity=critical}` and `UrgentRequests` in its log line (EMF). Two new alarms (`critical-alert`, `urgent-request`, 1-minute period, threshold 1) and all five existing alarms notify the topic `campuspulse-dev-alerts`, which has one email subscription per entry of `alert_emails` — the team's `@epita.fr` addresses (and optionally a Teams channel's email address).

**What it costs us.** An email per alarm *state change*, not per event, and it names the alarm rather than the room; the admin page has the detail. The topic is not KMS-encrypted, because CloudWatch alarms cannot publish to a topic using the AWS-managed SNS key; a customer-managed key would cost $1/month.

---

## AD-14: Two role-specific pages — administrator and student (October 2026)

**Context.** Project review: "required two pages, one for admin, one for student". The original dashboard served two staff roles (`ops`, `staff`) on one page.

**Chosen:** Cognito groups renamed `admin` and `student`; three static pages — `index.html` (sign-in, redirects by role), `admin.html`, `student.html` — sharing `app.js`. A new route `GET /requests` answers per role: an administrator gets every request of a day with who raised it; a student gets only their own, read from a new sparse index (GSI3) keyed on their verified Cognito `sub`.

| | Administrator | Student |
|---|---|---|
| Sensor events, alerts | yes | **no (403)** |
| Statistics (occupancy, temperature, energy) | yes | yes — shown as "free rooms" and "building comfort" |
| Raise a service request | yes | yes |
| See service requests | all, with requester | own only, no requester field |

**Why the page guard is not the security.** A student who edits the JavaScript to stay on `admin.html` gets 403 from every admin route. The page decides what is shown; the API decides what is returned.

---

## Summary of the stack

| Layer | Service | Why it is here in one line |
|---|---|---|
| Data source | Python simulator (laptop) | Stands in for campus IoT devices |
| Edge / API | API Gateway **HTTP API** | Public HTTPS entry point, validates JWTs before our code runs |
| Identity | Cognito user pool (Essentials) | Users, passwords, tokens, and the `admin`/`student` groups |
| Compute | 2 × Lambda (Python): `api` in the VPC, `auth` outside | Runs our logic per request, nothing when idle |
| Network | VPC, 2 private subnets, security group, DynamoDB gateway endpoint, flow logs | The data function can reach our table and nothing else |
| Storage | DynamoDB, one table + 3 GSIs | Events, queryable by day, by building, alerts-only, and requests by student |
| Pages | Static site on S3: sign-in, admin, student | One page per role |
| Observability | CloudWatch Logs, metrics, 7 alarms, dashboard; SNS email to the team | Proof the system works, the way we debug it, and alerts in the team's school inbox |
| Security | IAM roles per function, Cognito groups, HTTPS API, private network | Least privilege, enforced roles, network isolation |
| Backup / DR | DynamoDB PITR + AWS Backup (daily, weekly) + S3 versioning | Any second for 35 days, plus snapshots that survive the table |
