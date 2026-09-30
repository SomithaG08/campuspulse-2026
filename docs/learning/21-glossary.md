# Glossary

Every term the report, the slides and the code use. Format: plain meaning → what it is in *our* project → an example you can point at.

Terms are grouped, not alphabetical, because they make more sense in families. Use Ctrl+F.

---

## The web and APIs

**API** — a way for one program to ask another program to do something, with an agreed set of requests and answers. *Ours:* the six endpoints in `docs/architecture/05-api-contract.md`. *Example:* the simulator calls `POST /events` to submit a reading.

**Endpoint** — one specific address on an API, a method plus a path. *Ours:* `GET /alerts`. *Example:* `https://abc123.execute-api.eu-west-3.amazonaws.com/alerts`.

**REST** — a style of API where you act on named resources using standard HTTP methods. *Ours:* events are the resource; `POST` creates one, `GET` lists them.

**HTTP** — the protocol browsers and APIs speak. A request has a method, a path, headers and an optional body; a response has a status code, headers and a body.

**HTTPS** — HTTP inside an encrypted TLS tunnel. *Ours:* every single call. Nobody on the café Wi-Fi can read or alter a campus event in transit.

**GET / POST** — GET asks for data and changes nothing; POST sends data and creates something. *Ours:* `GET /stats` reads, `POST /events` writes.

**Status code** — a three-digit outcome. *Ours:* 200 fine · 201 created · 400 your request was malformed · 401 who are you · 403 I know who you are and no · 429 slow down · 500 our bug.

**JSON** — a text format for structured data: objects in `{}`, lists in `[]`, keys and values. *Ours:* every request and response body. *Example:* `{"building": "Library-A", "value": 58}`.

**Request / Response** — what you send, and what comes back.

**CORS** — a browser rule that blocks a page on one domain from calling an API on another unless the API explicitly allows it. *Ours:* the dashboard (S3) calls the API (API Gateway) — different domains, so CORS must be enabled or the dashboard shows nothing while `curl` works perfectly. The classic two-hour bug.

**Latency** — how long one request takes end to end. *Ours:* measured in the Lambda `REPORT` log line.

**Throughput** — how many requests per second the system handles.

---

## Cloud fundamentals

**Cloud** — renting computing over the internet, on demand, paying for use.

**AWS** — Amazon Web Services, the provider we use.

**Region** — a geographic cluster of AWS data centres. *Ours:* `eu-west-3`, Paris.

**Availability Zone** — one or more physically separate data centres inside a region. Managed services replicate across several, which is where our availability comes from.

**Serverless** — you write code, the provider runs it on demand; there is no machine you manage. Servers still exist — they are just not *yours*. *Ours:* Lambda.

**Managed service** — a service AWS operates for you (patching, scaling, replication). *Ours:* all seven.

**Free Tier** — allowances that cost nothing. Under the rules current since July 2025 a new account also gets credits and, on the free plan, **closes after six months or when the credits run out**. See `docs/cost/01-cost-model.md` §1 — this one matters.

**Credits** — prepaid balance applied to the bill. *Ours:* 100, non-renewable.

---

## The services we use

**Lambda** — runs a function when something invokes it; bills per request and per GB-second; nothing while idle. *Ours:* four functions — auth, ingest, query, stats.

**Function** — a unit of code with a handler AWS calls: `handler(event, context)`.

**Cold start** — the extra delay when Lambda has to create a fresh container for your function. *Ours:* 1-3 s on the first request after idle; we warm the API before the demo.

**API Gateway** — the managed HTTPS front door: routing, token validation, throttling, CORS.

**DynamoDB** — a managed NoSQL key-value database. Fast and cheap when you query by key; unsuited to arbitrary ad-hoc queries.

**NoSQL** — a non-relational database. No joins, no `SELECT * WHERE anything`; you design around the questions you will ask.

**Partition key** — the attribute that decides which physical partition an item lives in; every query must supply it. *Ours:* `DAY#2026-09-22`.

**Sort key** — orders items inside a partition and allows range queries. *Ours:* `<timestamp>#<event_id>`, which makes "newest first" free.

**Item / Attribute** — DynamoDB's row and column. *Ours:* one item = one campus event.

**GSI (Global Secondary Index)** — a second view of a table with different keys, for a different question. *Ours:* GSI1 by building, GSI2 alerts only.

**Sparse index** — a GSI that only contains items which *have* its key attributes. *Ours:* GSI2 — we write its key only for abnormal events, so the alerts index physically contains only alerts. Cheaper and faster than filtering.

**Query vs Scan** — a Query jumps straight to a partition; a Scan reads the whole table and gets slower and dearer as the table grows. *Ours:* there is no Scan anywhere, deliberately.

**TTL (Time To Live)** — an attribute holding an expiry time; DynamoDB deletes the item automatically, free. *Ours:* 30 days.

**PITR (Point-In-Time Recovery)** — continuous backup letting you restore a table to any second in the retention window. *Ours:* our backup mechanism.

**Cognito** — managed users, passwords and tokens. *Ours:* one user pool with the groups `ops` and `staff`.

**User pool** — the directory of users inside Cognito.

**S3** — object storage: files, addressed by key, over HTTPS. *Ours:* the dashboard's HTML, CSS and JS — and no campus data.

**Bucket** — a named container for S3 objects.

**CloudWatch** — logs, metrics, alarms and dashboards.

**IAM** — who may do what to which resource.

---

## Security

**Authentication** — proving who you are. *Ours:* `POST /login` with a password, in exchange for a token.

**Authorization** — deciding what you may do once you are known. *Ours:* is `ops` in your token's groups?

**They are not the same thing.** 401 is failed authentication; 403 is failed authorization. Knowing the difference is a near-certain exam question.

**User / Role / Group** — a person who signs in; the set of permissions attached to them; Cognito's mechanism for attaching it. *Ours:* two groups, `ops` and `staff`.

**Token / JWT** — a signed, time-limited string proving who you are. A JSON Web Token has three dot-separated parts: header, claims, signature. It is **signed, not encrypted** — anyone can read the claims, nobody can alter them without invalidating the signature. Never put a secret inside one.

**Claim** — one fact inside a token. *Ours:* `cognito:groups` carries the role.

**Signature** — the cryptographic proof the token came from our Cognito pool and has not been edited.

**Expiry** — tokens die, ours after an hour, so a stolen one is only briefly useful.

**IAM role** — an identity a service assumes, receiving temporary credentials. *Ours:* four, one per Lambda.

**IAM policy** — the JSON document listing allowed actions on specific resources.

**Least privilege** — grant exactly what is needed and nothing more. *Ours:* `cp-ingest` may `PutItem` and cannot read; `cp-query` may `Query` and cannot write. If one is compromised, the damage is bounded.

**Encryption at rest / in transit** — scrambled on disk / scrambled on the wire. *Ours:* DynamoDB and S3 encrypt at rest by default; HTTPS covers transit.

**Secrets management** — keeping passwords, keys and tokens out of code. *Ours:* no credentials in the repo at all; configuration arrives via environment variables.

**Input validation** — checking untrusted data before using it. *Ours:* every field of every event, at ingestion.

**Threat model** — writing down what an attacker might try and what stops them. *Ours:* `docs/security/`, Phase 7.

**Blast radius** — how much an attacker reaches after compromising one component. Least privilege is how you shrink it.

---

## Operations

**Log** — a line of text recording that something happened. *Ours:* structured JSON with the `request_id`.

**Metric** — a number over time. *Ours:* `EventsIngested`, `AlertsRaised`.

**Alarm** — a rule that watches a metric and changes state when it crosses a threshold. *Ours:* three.

**Dashboard** — a screen of graphs. We have two different ones: the CloudWatch dashboard (for us, about the system) and the CampusPulse dashboard (for the operations team, about the campus). Do not mix them up on a slide.

**Monitoring / Observability** — watching known signals / being able to answer new questions about the system from what it emits.

**Scalability** — coping with more load. **Horizontal** = more instances; **vertical** = a bigger machine. *Ours:* horizontal, automatically.

**Availability** — the share of time the system is usable. Ours rests on AWS-managed services replicated across Availability Zones, in **one region**. We do not claim more than that.

**Stateless** — keeps nothing between requests, so any instance can serve any request. *Ours:* every Lambda.

**Throttling** — deliberately rejecting excess requests (429) to protect the system and the budget.

**RPO (Recovery Point Objective)** — how much data you can afford to lose, measured in time. *"We can lose at most N minutes of events."*

**RTO (Recovery Time Objective)** — how long you can afford to be down. *"We can be back within N minutes."*

**Disaster recovery** — the plan for getting back after data loss or an outage.

---

## Building and deploying

**Infrastructure as Code (IaC)** — your cloud resources defined in files, version-controlled, applied by a tool. The opposite of clicking around a console and forgetting what you clicked.

**Terraform** — the IaC tool we plan to use: `terraform init`, `plan`, `apply`, `destroy`.

**CloudFormation / SAM** — AWS's own IaC alternatives.

**Container** — an application packaged with its dependencies, running the same everywhere. *Ours:* none — we chose serverless instead, and should be able to say why.

**Docker** — the usual tool for building containers.

**CI/CD** — automatically testing and deploying on every change. *Ours:* out of scope, deliberately.

**Environment variable** — configuration passed to a program at start-up rather than written in its code. *Ours:* the table name, the region, the user pool ID.

**Deployment package** — the zip of code AWS runs as a Lambda.

**Idempotent** — running it twice leaves the same result as running it once. A good property for a deploy script.

---

## Data

**Event** — one thing that happened, at a time, with a value. *Ours:* the JSON object in `docs/architecture/04-data-model.md`.

**Ingestion** — getting data into the system.

**Aggregation** — combining many records into a summary. *Ours:* `/stats` — counts, averages, per-building totals.

**Filtering** — keeping only what matches. *Ours:* `/alerts`.

**Anomaly** — a value outside the expected range. *Ours:* decided by fixed thresholds, not by a model — and we can explain every threshold, which a model would not let us do.

**Volume / Velocity / Variety** — the three Vs: how much, how fast, how many shapes.

**Schema** — the agreed shape of the data. *Ours:* frozen in the data model, which is why the four components fit together.

**Validation** — checking data matches the schema before trusting it.
