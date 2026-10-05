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
| Free tier | 1M calls/month, 12 months | 1M calls/month, 12 months |
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

## AD-5: Four small Lambdas, not one big one

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

## AD-7: No VPC

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

## Summary of the stack

| Layer | Service | Why it is here in one line |
|---|---|---|
| Data source | Python simulator (laptop) | Stands in for campus IoT devices |
| Edge / API | API Gateway **HTTP API** | Public HTTPS entry point, validates JWTs before our code runs |
| Identity | Cognito user pool (Essentials) | Users, passwords, tokens, and the `ops`/`staff` groups |
| Compute | 4 × Lambda (Python) | Runs our logic per request, nothing when idle |
| Storage | DynamoDB, one table + 2 GSIs | Events, queryable by day, by building, and alerts-only |
| Dashboard | Static site on S3 | What the operations team looks at |
| Observability | CloudWatch Logs, metrics, alarms, dashboard | Proof the system works and the way we debug it |
| Security | IAM roles per function, Cognito groups, HTTPS | Least privilege and enforced roles |
| Backup / DR | DynamoDB point-in-time recovery | Restore to any second in the retention window |
