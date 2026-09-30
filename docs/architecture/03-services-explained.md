# Every AWS Service We Use — the eleven questions

For each service: what it is, why it's here, what problem it solves, what goes in, what happens inside, what comes out, what it talks to, why not the alternative, what it costs, what breaks without it, and how we prove it works.

Cost figures are summarised here and sourced in full in `07-cost-model.md`.

---

## Amazon API Gateway (HTTP API)

**1. What is it?**
*Simple:* the university's reception desk. Everything from outside arrives here first, gets its ID checked, and is directed to the right office. Nobody walks straight into the back rooms.
*Technical:* a managed HTTPS front door that terminates TLS, matches the method and path against routes, runs an authorizer, applies throttling, and invokes the configured Lambda with the request as a JSON event.

**2. Why are we using it?** We need one public, secure, scaling entry point that we do not have to run, patch or keep alive.

**3. What problem does it solve?** Without it we would need a public server, a TLS certificate and its renewal, a web server config, rate limiting, and our own token validation — days of work and a large attack surface.

**4. What enters?** HTTPS requests: method, path, query string, headers (including `Authorization`), and a JSON body.

**5. What happens inside?** Route match → JWT authorizer validates the token's signature against Cognito's public keys, plus issuer, audience and expiry → CORS headers applied → throttle check → invoke the mapped Lambda with the claims attached.

**6. What comes out?** The Lambda's response as HTTP, or a 401 from the authorizer, a 429 from throttling, or a 5xx if the function failed.

**7. What does it communicate with?** Inbound: simulator, browser. Outbound: the four Lambdas. Sideways: Cognito for public keys, CloudWatch for logs.

**8. Why not the alternative?** REST API v1 costs $3.50 per million against HTTP API's $1.00, needs more configuration for CORS and Cognito, and its extra features (API keys, WAF, caching) are ones we do not use. An Nginx/Node API on EC2 would bill by the hour and make us responsible for TLS and patching.

**9. Cost.** Free tier 1M calls/month for 12 months; then $1.00 per million. Our whole project is far below 1M calls. *(Confirmed on the pricing page.)*

**10. If we removed it?** Lambda has no public URL in our design, so the system would have no way in at all.

**11. How do we verify it?** `curl` the `/health` route; check the access log; deliberately send a bad token and confirm the 401 comes from API Gateway, not from our code.

---

## AWS Lambda

**1. What is it?**
*Simple:* a worker who is hired for the exact seconds they are working. No request, no worker, no wages.
*Technical:* a function-as-a-service runtime. AWS starts a container with our Python code, calls our `handler(event, context)`, and freezes or destroys it afterwards. Concurrent requests get concurrent containers.

**2. Why are we using it?** Our workload is bursty and mostly idle — the worst possible fit for an always-on server and the best possible fit for per-request billing.

**3. What problem does it solve?** Running, patching, scaling and paying for a server that does nothing most of the time.

**4. What enters?** An event object from API Gateway: path, method, query, body, and the verified token claims.

**5. What happens inside?** Cold start (download code, start runtime, run module-level code) *or* reuse of a warm container → our handler runs: parse, validate, apply rules, call DynamoDB or Cognito, build the response.

**6. What comes out?** An HTTP-shaped JSON response, plus log lines and metrics to CloudWatch.

**7. What does it communicate with?** Invoked by API Gateway; calls DynamoDB and Cognito; writes to CloudWatch. It holds no credentials — it assumes an IAM role at invocation and receives temporary keys.

**8. Why not the alternative?** EC2 or a container means hourly billing, capacity planning and OS maintenance. Our peak is a few requests per second in a demo; provisioning a machine for that is renting a lorry to carry one box.

**9. Cost.** Free tier **1 million requests and 400,000 GB-seconds per month** — this allowance is not limited to a 12-month window. Then $0.20 per million requests plus ~$0.0000166667 per GB-second (x86, N. Virginia). Our usage sits inside the free allowance. *(Confirmed on the pricing page. Note: the free tier does not apply to functions with Provisioned Concurrency — we will not enable it.)*

**10. If we removed it?** Nothing would process or validate anything. API Gateway can proxy straight to DynamoDB, but then there is no validation, no severity logic and no aggregation — the actual product would be gone.

**11. How do we verify it?** Invoke from the console with a test event; check the log for the structured line; confirm `Duration`, `Billed Duration` and `Init Duration` in the `REPORT` line, which is also our cold-start evidence.

---

## Amazon DynamoDB

**1. What is it?**
*Simple:* a very fast filing system. You must decide in advance how files are labelled, because you retrieve them by label, not by searching every drawer.
*Technical:* a managed key-value/document database. Items live in partitions chosen by the partition key and are ordered inside a partition by the sort key. Queries must supply a partition key.

**2. Why are we using it?** Our access patterns are known and simple — "recent events", "today's events for building X", "today's alerts" — and it has no server to run and nothing to pay while idle.

**3. What problem does it solve?** Persistent storage with predictable single-digit-millisecond reads and no capacity planning, unlike an RDS instance that bills hourly forever.

**4. What enters?** `PutItem` with the classified event; `Query` with a key condition.

**5. What happens inside?** The partition key is hashed to choose a partition; the item is written to storage replicated across three Availability Zones; index entries are written for GSI1 and, only for alerts, GSI2.

**6. What comes out?** Success/failure for writes; ordered item lists plus a pagination token for queries.

**7. What does it communicate with?** Called by `cp-ingest`, `cp-query`, `cp-stats`. Sends metrics to CloudWatch. Feeds point-in-time recovery.

**8. Why not the alternative?** RDS/PostgreSQL gives SQL and ad-hoc queries, which we do not need, in exchange for an instance billing every hour and a VPC to put it in. S3 alone gives no indexed queries. For fixed, known access patterns DynamoDB is both cheaper and simpler — but we should say plainly that if the campus later wanted arbitrary analytical queries, a relational store or an S3 data lake with Athena would be the right answer.

**9. Cost.** Free tier: 25 GB storage, 25 WCU, 25 RCU, per region per month — **stated for provisioned capacity and the Standard table class**. We chose on-demand (see AD-4), so our request charges come out of credits: roughly $0.625 per million writes and $0.125 per million reads in N. Virginia — *these two figures are not yet verified* and are re-checked in Phase 4. Our storage stays far under 25 GB thanks to the 30-day TTL.

**10. If we removed it?** Every event would vanish the moment its Lambda finished. No history, no statistics, no dashboard.

**11. How do we verify it?** Write one event through the API, then find that exact item in the console; run each of the five access-pattern queries and confirm none of them requires a Scan.

---

## Amazon Cognito (user pool)

**1. What is it?**
*Simple:* the security guard who issues a badge. Show your badge everywhere else; the guard is the only one who ever sees your password.
*Technical:* a managed identity provider. It stores users, hashes and verifies passwords, enforces the password policy, manages groups, and issues signed JWTs (ID, access, refresh) on successful authentication.

**2. Why are we using it?** The spec requires authentication and at least two roles, and the safest way for a student team to handle passwords is to never handle them.

**3. What problem does it solve?** Password storage, hashing, token signing, expiry and revocation — each of which is easy to get subtly and dangerously wrong.

**4. What enters?** `InitiateAuth` with a username and password, from `cp-auth`.

**5. What happens inside?** Verifies the credentials against the stored hash, checks the user's status, assembles the claims including `cognito:groups`, signs the tokens with its private key.

**6. What comes out?** An ID token, an access token, a refresh token, and an expiry — or an authentication error.

**7. What does it communicate with?** Called by `cp-auth`; its public JWKS endpoint is read by the API Gateway authorizer.

**8. Why not the alternative?** Rolling our own means a users table, a password-hashing library, a JWT library, key management and token expiry logic — more code, more to explain, and one mistake away from a plaintext-password incident. We keep the design for that fallback documented, because we planned for it before confirming Cognito was available.

**9. Cost.** Free tier **10,000 monthly active users** for Lite or Essentials pools, and it does not expire with the 12-month window. We use **Essentials** ($0.015/MAU beyond the free 10,000). **The Plus tier has no free tier — do not select it.** Machine-to-machine token requests also have no free tier, which is why the simulator signs in as an ordinary user. *(Confirmed on the pricing page.)*

**10. If we removed it?** No login, no tokens, no roles — the entire security requirement collapses.

**11. How do we verify it?** Log in as each user, decode the returned token at jwt.io and show `cognito:groups`; then show that a `staff` token gets a 403 on `/alerts`.

---

## Amazon S3

**1. What is it?**
*Simple:* an infinite, cheap hard drive on the internet, addressed by file name.
*Technical:* object storage. Objects live in a bucket, are retrieved by key over HTTPS, and are replicated across Availability Zones.

**2. Why are we using it?** To serve the dashboard's HTML, CSS and JavaScript without running a web server.

**3. What problem does it solve?** Hosting static files with high durability and no infrastructure.

**4. What enters?** Our three or four static files, uploaded at deploy time.

**5. What happens inside?** Objects are stored, versioned if enabled, and served over HTTPS by static website hosting.

**6. What comes out?** The page, to a browser.

**7. What does it communicate with?** Browsers only. It never touches campus data. *(If we add DynamoDB backup exports later, they land in a separate, private bucket.)*

**8. Why not the alternative?** Serving the page from EC2 means an hourly bill for a task S3 does for pennies. CloudFront in front would add a CDN we do not need for a single-room demo.

**9. Cost.** The classic 5 GB / 20,000 GET / 2,000 PUT free-tier figures **could not be confirmed** from the S3 pricing page (its tables render in JavaScript) and are therefore **not asserted**. Our site is a few hundred kilobytes; whatever the exact rate, the cost is a rounding error. Verified in Phase 4 with the pricing API.

**10. If we removed it?** No dashboard UI. The API would still work from `curl`, so this is the least critical component — worth saying, because it shows we can rank our own components by importance.

**11. How do we verify it?** Open the website endpoint in a browser; confirm with `aws s3 ls` that the bucket contains only static assets and no data.

---

## Amazon CloudWatch

**1. What is it?**
*Simple:* the building's control room — the camera feeds (logs), the gauges (metrics), and the fire alarm (alarms).
*Technical:* logs, metrics, alarms and dashboards. Lambda writes to a log group automatically; alarms watch a metric against a threshold over a period and change state.

**2. Why are we using it?** §4 and §6 require monitoring, logging and observability, and honestly: without logs, a failed Lambda is a silent 500 with nothing to look at.

**3. What problem does it solve?** Knowing whether the system works, and finding out why when it does not.

**4. What enters?** Every `print`/logger line from our functions; built-in metrics (invocations, errors, duration, throttles); our custom counters `EventsIngested` and `AlertsRaised`.

**5. What happens inside?** Log events are stored in a log group with **7-day retention** (set deliberately — the default "never expire" quietly accrues storage cost); metrics are aggregated into time series; alarms evaluate and change state.

**6. What comes out?** Searchable logs, metric graphs, alarm states, and our dashboard.

**7. What does it communicate with?** Receives from every Lambda and from API Gateway and DynamoDB. Alarms could notify SNS — deferred, see the optional list.

**8. Why not the alternative?** A third-party tool would need an agent, an account and probably money. CloudWatch is already integrated and included.

**9. Cost.** Free tier confirmed on the pricing page: **5 GB of logs** (ingestion, archive storage and Logs Insights scanning share that 5 GB), **10 custom metrics**, **10 alarm metrics**, **3 custom dashboards**, 1M API requests. We stay inside every one of those: 2 custom metrics, 3 alarms, 1 dashboard, and 7-day log retention.

**10. If we removed it?** We would be operating blind, and we would have no evidence for the report — losing marks in two graded criteria at once.

**11. How do we verify it?** Force an error, find its log line by `request_id`; drive an alarm into ALARM state deliberately and screenshot it.

---

## AWS IAM

**1. What is it?**
*Simple:* the master key cabinet. Each worker gets a key that opens exactly one door, and only while they're on shift.
*Technical:* identity and access management. Our Lambdas assume execution **roles**; each role has a **policy** naming allowed actions on specific resource ARNs. Credentials are temporary and rotated automatically.

**2. Why are we using it?** Nothing in AWS can call anything else without it, and it is how least privilege stops being a slogan.

**3. What problem does it solve?** Blast radius. It decides what an attacker gets if they compromise one component.

**4. What enters?** A role-assumption request when a function is invoked.

**5. What happens inside?** IAM issues temporary credentials; every subsequent API call is evaluated against the role's policy and denied by default unless explicitly allowed.

**6. What comes out?** Allow or `AccessDenied`.

**7. What does it communicate with?** Every service, invisibly.

**8. Why not the alternative?** The alternative is hard-coded access keys in code — the single most common cause of student cloud breaches, and a straight fail on the security criterion.

**9. Cost.** IAM itself is free.

**10. If we removed it?** Not possible. The meaningful question is what happens if we do it *badly*: one over-broad policy turns a small bug into full account compromise.

**11. How do we verify it?** Temporarily point `cp-query` at a resource outside its policy and show the `AccessDenied`. Proving the wall exists is better evidence than asserting it.

---

## Services we deliberately do NOT use

| Service | Why not |
|---|---|
| **EC2** | Hourly billing for something that idles; OS patching; a VPC to manage |
| **RDS** | Hourly billing 24/7; needs a VPC; SQL we do not need |
| **NAT Gateway** | ~$30-35/month to give private subnets internet access we do not need. The most common way a student AWS budget disappears |
| **ELB / ALB** | Hourly billing; API Gateway already load-balances |
| **Kinesis / MSK** | Built for high-throughput streaming; our volume does not justify it; no free tier |
| **ECS / EKS** | Orchestration for containers we are not running |
| **CloudFront** | A CDN for one browser in one room |
| **SNS** | Only if we add email alerting later (optional feature O2) |

Being able to say *why not* is worth as much at the oral as saying why.
