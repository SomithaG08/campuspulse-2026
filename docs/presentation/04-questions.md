# Anticipated Questions

Rehearse these **cold** — a teammate asks, you answer without notes. The weakest answer in the room sets the grade for participation.

**If you do not know: say so.** *"We did not test that"* or *"we considered it and chose not to"* is a far better answer than a confident invention. An examiner can tell, and will follow up on the invention.

---

## Architecture

**Why serverless rather than containers or EC2?**
Our workload is bursty and idle most of the time. A VM bills every hour regardless; Lambda bills per request and costs nothing idle. We have a hundred non-renewable credits. It also removed OS patching, web-server configuration and NAT Gateway cost entirely. The trade-off is cold starts of one to three seconds and a design that would not lift to another cloud unchanged.

**Why no VPC?**
Because nothing of ours listens on a network. Lambda, API Gateway, DynamoDB and Cognito are managed services — there is no server in a subnet, so there is no subnet to configure. Our boundary is IAM plus the token check. A private-subnet design would need a NAT Gateway at about thirty-two dollars a month, a third of our budget, for something that does nothing for us. If we later ran a database speaking a network protocol, a VPC would become the right answer.

**What happens if a Lambda fails?**
The caller gets a 500 with a request identifier, and the detail goes to CloudWatch. Lambda retries asynchronous invocations automatically, but ours are synchronous through API Gateway, so the client decides whether to retry. An error alarm fires. Nothing is lost that was already written — DynamoDB writes are atomic.

**Why four Lambdas rather than one?**
So each gets its own permissions. The internet-facing function can write to one table and cannot read anything. The read functions cannot write. One function with one broad role would turn any bug into a full data breach.

**Why DynamoDB and not a relational database?**
Our access patterns are known and fixed — recent events, events by building, today's alerts. DynamoDB answers those in one query each and costs nothing while idle. RDS bills hourly and needs a VPC. If the campus wanted arbitrary analytical queries, a relational store or an S3 data lake with Athena would be the right answer, and we would say so.

---

## Security

**How is the API protected?**
Three layers. API Gateway validates the token's signature, issuer, audience and expiry before our code runs — that is the 401. The function checks the caller's group — that is the 403. IAM limits what the function can touch at all. Plus HTTPS throughout, input validation on every field, and throttling.

**What stops someone sending fake events?**
They need a valid token from our Cognito pool, in the `ops` group. And even then, every field is validated and the severity they claim is discarded — we compute it ourselves. The most an authorised attacker could do is insert plausible but false readings, which is an authentication problem rather than an API one.

**Where are your AWS credentials?**
Nowhere. Each function assumes an IAM role at invocation and receives temporary, automatically rotated credentials. There is no key in the code or the repository to leak.

**Is least privilege real here, or just claimed?**
Real, and audited. We listed every AWS call the code makes and compared it with every permission granted — exact match. You can verify it with `iam simulate-principal-policy`: for the ingest function, `PutItem` is allowed, `Query` and `Scan` are implicitly denied.
*Then add, unprompted:* the human deployment identity is broad, near-administrator, for convenience. That is a different thing and our report says so.

**Why is the S3 bucket public?**
It contains the page — HTML, CSS, JavaScript — and no campus data. Every value shown comes from the API, which refuses without a token. The policy allows reading objects only: nobody can list, write or delete.

---

## Data and scale

**How does the system scale?**
Lambda creates a new execution environment per concurrent request, automatically. DynamoDB on-demand splits partitions as load grows. Nothing is configured by us. The dashboard is static files, which scale trivially.

**Where does it break?**
At about a thousand writes per second. All of one day's events share a partition key, and a DynamoDB partition sustains roughly that. The fix is a shard suffix on the key — ten partitions, read in parallel — which touches two files. We designed it and did not build it, because we are nowhere near that volume.

**Why no `Scan` anywhere?**
A scan reads the whole table and gets slower and more expensive as it grows. Every one of our access patterns supplies a partition key. It is enforced three ways: by the key design, by a unit test, and by IAM — no role is granted the scan permission, so a future scan would fail loudly rather than quietly degrade.

**Is this really Big Data?**
Not by volume — we handle thousands of events, not billions, and we would not claim otherwise. But it is built on big-data principles: streaming ingestion, classification at write time, storage designed around access patterns, horizontal scaling, and validation at the boundary. And we can name exactly what we would change for a thousand times the volume.

**Why thresholds rather than machine learning?**
Explainability, data and defensibility. Our alert gives a reason an engineer can act on; a model gives a score. We have no labelled history to train on. And every one of us can defend a threshold under questioning. With real history we would add a rolling mean and standard deviation per room — that is in our future work.

---

## Operations and cost

**What does it cost?**
Estimated under five dollars of our hundred credits, actual figure on the slide. Nothing bills by the hour — no EC2, no RDS, no load balancer, no NAT Gateway. Log retention is seven days rather than the default of never, data expires after thirty days, and our budget alert excludes credits so it tracks real consumption rather than reading zero until the credits run out.

**How would you know if something went wrong?**
Four alarms: Lambda errors, API server errors, a burst of alerts suggesting something campus-wide, and an invocation ceiling that catches a runaway client before it appears on a bill. Plus structured logs where one request identifier ties the response, the function log and the gateway log together.

**What is your RPO and RTO?**
RPO is effectively zero: point-in-time recovery restores the table to any second in the last thirty-five days. RTO we measured by actually performing a restore — [the measured number]. We did not estimate it.

**What happens if the region goes down?**
We go down. We are single-region with no failover, and we are not going to claim otherwise. Multi-region would be the first thing a real campus deployment required, and it is first on our future-work list.

---

## Process

**What was the hardest part?**
[Answer honestly, in your own words, about your own component.]

**What would you do differently?**
Deploy earlier. We built and tested a lot before anything existed in AWS. The logic was genuinely testable locally, but deployment-shaped problems — permissions, cross-origin rules, token wiring — only appear when you deploy.

**How did you split the work?**
Each of us owns one area end to end: architecture and ingestion, security and identity, simulation and testing, interface and monitoring. Each of us wrote the documentation for our own area, because writing the explanation is how you find out whether you understand it. And none of us is presenting a component we did not build.

**Did you use AI assistance?**
Yes, for planning and drafting, and our report says so in the references. Every generated draft was reviewed and verified by whoever owns that component, and we checked the AWS pricing claims against AWS's own pages rather than accepting them — several we could not verify are marked unverified in the report.

---

## The three hardest, and the honest answers

**"You did not really implement X, did you?"**
If true: *"That is right — it is designed and documented, and we did not build it."* Our documentation already marks everything as Implemented, Configured or Planned for exactly this reason.

**"Your prototype is tiny."**
*"Deliberately. The brief asks for something coherent, functional and aligned with the architecture rather than something large. We chose a scale we could build, deploy, test, and all four of us explain."*

**"How do you know this works?"**
*"A hundred and thirty-one unit tests, forty-five API tests against the deployed system, a restore we actually performed and timed, and an alarm we deliberately triggered. Where we have no evidence, our report says 'not verified' rather than claiming it."*
