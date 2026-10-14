# Serverless — explained

**Read after:** `06-lambda-explained.md`

---

## 1. The name is a lie, and that is fine

There are servers. You do not manage them.

**Level 1 — simple.** Taking a taxi instead of owning a car. The car exists, someone maintains it, insures it and parks it — you pay for the trip. No trip, no cost.

**Level 2 — technical.** A model where the provider manages provisioning, scaling and availability, and bills by actual consumption rather than reserved capacity. Three properties define it: **no capacity to provision**, **automatic scaling to and from zero**, and **pay-per-use**.

## 2. The comparison that decides it for us

| | EC2 (a server) | Lambda (serverless) |
|---|---|---|
| You manage | OS, patches, the runtime, scaling | your function |
| Cost while idle | **full hourly rate** | **zero** |
| Scaling | you configure it | automatic |
| Start-up | minutes | milliseconds, or 1-3 s cold |
| Max run time | unlimited | 15 minutes |
| State between requests | yes | **no** |
| Right for | steady load, long jobs, full control | **bursty, event-driven work** |

**Our workload is the textbook case for the right-hand column.** Campus events arrive in bursts during a demo and never in between. An EC2 instance would bill every idle hour; Lambda bills nothing. With 100 non-renewable credits, "costs nothing while idle" is the single most valuable property available to us.

## 3. Stateless, and why it matters

A Lambda keeps nothing between requests. Two consecutive calls may run in different containers; anything written to local disk may vanish.

This sounds like a limitation and is actually the mechanism that makes scaling free: **if no instance holds state, any instance can serve any request**, so AWS can create a thousand of them without coordination. Horizontal scaling and statelessness are the same property viewed from two sides.

It also means all state must live somewhere designed for it — DynamoDB for events, Cognito for sessions. Our functions hold nothing.

## 4. What serverless costs us

Being able to name these is what separates understanding from enthusiasm.

| Cost | Detail | What we do |
|---|---|---|
| **Cold starts** | 1-3 s on the first call after idle | Warm the API before the demo; never use Provisioned Concurrency (it bills continuously *and* voids the Lambda free tier) |
| **Vendor lock-in** | This design does not lift to another cloud unchanged | Accepted, and stated in Lessons Learned. The *logic* in `common/` is plain Python and would port; the glue would not |
| **Harder local testing** | You cannot run API Gateway on a laptop | We kept the logic free of AWS imports, so 131 tests run locally in a second |
| **Debugging moves to logs** | No server to SSH into | Structured logs plus a `request_id` that ties response, function log and access log together |
| **Limits** | 15-minute run time, 6 MB response, 10 GB memory | None binds us; worth knowing before someone proposes a long batch job |

## 5. "Serverless" is more than Lambda

Our whole stack is serverless, which is why there is no server anywhere in it:

| Service | Serverless because |
|---|---|
| **Lambda** | compute, per request |
| **API Gateway** | the HTTPS endpoint, per request |
| **DynamoDB on-demand** | storage, per request, nothing while idle |
| **Cognito** | identity, per monthly active user |
| **S3** | storage, per GB and per request |
| **CloudWatch** | logs and metrics, per GB and per metric |

**Nothing in this architecture bills by the hour.** That one sentence is the cost model, the availability story and the reason the project survives on 100 credits.

## 6. When serverless is the wrong answer

Worth being able to say, because an examiner may well ask:

- **Steady, predictable, high load.** Past a certain constant throughput a reserved instance is cheaper than per-request billing.
- **Long-running jobs.** Fifteen minutes is a hard ceiling.
- **Very latency-sensitive paths.** Cold starts are unacceptable for some systems.
- **Heavy state in memory**, such as a large model held between requests.
- **Specific OS or hardware needs** — a GPU, a kernel module, a licensed binary.

A real campus platform running continuously at scale might well justify containers. Our prototype does not, and saying both halves is a stronger answer than defending serverless everywhere.

---

## Can you explain this?

1. If it is called serverless, where does the code run?
2. Why does statelessness make scaling easy?
3. Name two real costs of going serverless, and what we do about them.
4. Why does "nothing bills by the hour" matter so much for this project?
5. When would you *not* choose serverless?

### Answers

1. On servers AWS owns and manages. The name means we do not provision or maintain them, not that they do not exist.
2. Because no instance holds anything another instance would need. Any request can go to any instance, so AWS can add instances without coordinating between them.
3. Cold starts — 1-3 s on the first call, which we handle by warming the API before the demo and never enabling Provisioned Concurrency. And vendor lock-in — the design does not move to another cloud unchanged, though the pure logic in `common/` would.
4. Because we have 100 credits that do not refill. Hourly billing spends while nobody is working; our stack costs nothing between demos.
5. Steady high load, jobs longer than 15 minutes, latency-critical paths, large in-memory state, or specific hardware. A continuously-running production campus platform might justify containers instead.
