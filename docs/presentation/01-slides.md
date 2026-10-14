# Slide Deck — CampusPulse 2026

**17 slides · 15 minutes · four speakers.** The spoken words are in `05-final-speaking-script.md`; this file is what goes **on** the slides.

**Rule for every slide: at most six bullets, at most eight words each.** The slide is the illustration, the speaker is the explanation. A slide you read aloud is a slide the audience is reading instead of listening to you.

| Speaker | Slides | Time |
|---|---|---|
| Somitha | 1-6 | ~4:30 |
| Meha | 7-9 | ~3:00 |
| MD | 10-12 | ~2:30 |
| Madhavan | 13-15 (incl. demo) | ~4:00 |
| Somitha | 16-17 | ~1:00 |

---

## 1 — Title

**CampusPulse 2026**
A Cloud-Native Smart Campus Operations Platform

NorthBridge University · Big Data & Cloud Computing · EPITA 2025-2026
Somitha Gudivada · Meha · Madhavan · MD

*Visual:* the architecture diagram, faded, as the background.

---

## 2 — The problem

- A campus produces thousands of readings a day
- Individually, none of them matter
- Nobody can watch them all
- The handful that matter need action **now**

*Visual:* a wall of grey numbers with three highlighted in red.

---

## 3 — What the operations team needs to know

- Which rooms are overloaded
- Which buildings burn the most energy
- What is abnormal right now
- Which student requests are urgent

*Visual:* the four questions, large, nothing else.

**This is the slide that frames everything after it — the questions come straight from the brief.**

---

## 4 — Architecture

```text
Simulator ──HTTPS+JWT──► API Gateway ──► auth Lambda ──► Cognito
Browser ──► S3 (pages)        │           (Public Auth Gateway)
                              │
                              └──► api Lambda (VPC 2 AZs) ──► DynamoDB Endpoint ──► DynamoDB
                                   (Private Operations)
```

- VPC with 2 private subnets across 2 AZs
- 2 Lambdas grouped by business domain
- DynamoDB Gateway Endpoint — zero NAT cost
- Region: eu-west-3 (Paris)

*Visual:* the full architecture diagram with VPC boundary and Gateway Endpoint.

---

## 5 — Why serverless & zero-cost networking

| | Traditional Server | CampusPulse Architecture |
|---|---|---|
| Compute idle cost | **full hourly rate** | **zero** ($0/request when idle) |
| Scaling | manual configuration | automatic per concurrent request |
| Networking cost | NAT Gateway (~$32/mo) | **$0** (DynamoDB Gateway Endpoint) |

- Bursty workload, idle most of the time
- 100 credits, non-renewable
- Full private-network isolation at $0/month

*Visual:* the comparison table.

---

## 6 — One event, end to end

```text
Simulator → API Gateway → JWT check → api Lambda (VPC)
   → validate → classify → DynamoDB → admin dashboard
```

- Client sends `severity: normal`
- Server computes `critical` — **and overrules it**
- 58 people in a room that holds 45
- Emits EMF metrics; alerts team via SNS

*Visual:* the flow, with the server overrule highlighted.

**The strongest single idea in the project: a device cannot declare itself normal.**

---

## 7 — Security: three independent layers

| Layer | Decides | Fails with |
|---|---|---|
| JWT authorizer | do we know you? | **401** |
| Lambda group check | may you do this? | **403** |
| IAM + VPC boundary | can code reach this resource? | `AccessDenied` / No Route |

- Each layer is independently sufficient
- Edge authorizer validates **before our code runs**

*Visual:* three concentric security gates.

---

## 8 — Two roles, strictly enforced

| Action | `admin` | `student` |
|---|---|---|
| Ingest sensor events | ✅ | **403** |
| Read alerts & raw events | ✅ | **403** |
| View room stats & comfort | ✅ | ✅ |
| Submit service request | ✅ | ✅ |
| View service requests | All requests | **Own requests only (GSI3)** |

*Visual:* the matrix, with student 403 cells highlighted.

**Demonstrated live on slide 15, not just claimed.**

---

## 9 — Least privilege & network isolation

| Business Domain | Network Boundary | Permissions | Cannot Do |
|---|---|---|---|
| `auth` (Identity) | Outside VPC | `cognito-idp:InitiateAuth` | **Touch database** |
| `api` (Operations) | Inside private VPC | `dynamodb:PutItem`, `Query` | **Reach internet** |

- Zero AWS credentials stored in code
- `dynamodb:Scan` granted to nobody
- Data function cannot exfiltrate packets to internet

*Visual:* the business-domain isolation diagram.

---

## 10 — Two dedicated pages

*Visual:* side-by-side screenshots of `admin.html` and `student.html`.

- **Admin page**: 5 KPI tiles, active alerts, energy, all requests
- **Student page**: free rooms, room comfort, report an issue
- Hosted on S3 with versioning enabled
- Polling pauses when tab hidden (cost control)

---

## 11 — Observability & automated alerting

- Structured JSON logs with `request_id`
- Metrics via EMF — zero extra API calls
- **7 CloudWatch alarms** + SNS email alerts to team inboxes
- Immediate notifications on critical events & urgent requests
- AWS Backup: daily (7d) & weekly (35d) snapshots

*Visual:* CloudWatch dashboard and received alert email in Epita inbox.

---

## 12 — Cost control

- **Nothing bills by the hour**
- Private VPC with Gateway Endpoint ($32/mo NAT avoided)
- Budget alert configured before any resource created
- Estimated spend: **under $5** of 100 credits
- Actual spend: ~$2

*Visual:* the AWS Budgets console screenshot.

---

## 13 — Scalability, and our limit

- Lambda and DynamoDB scale horizontally, automatically
- **Our ceiling: ~1,000 writes/second** — one partition per day
- **The fix:** shard the partition key across ten partitions
- We designed it; we did not build it (scope discipline)

*Visual:* one partition vs ten sharded partitions.

**Knowing where your design breaks is worth more than pretending it doesn't.**

---

## 14 — Testing: 161 checks, 0 failures

- **143 backend unit tests**, ~1 second, no AWS needed
- **18 simulator generator tests**
- **50 API checks** against the live deployed stack
- Proven: no query can become a `Scan`

*Visual:* test run output showing 100% green checks.

---

## 15 — Live demo

*No bullets. Switch to the terminal and the browser.*

1. Admin dashboard open, signed in as `admin`
2. Start simulator — events stream in live
3. Trigger `--force-alert` — red critical alert appears & team email fires
4. Open student page as `student` — see room comfort & submit urgent request
5. Show 403 on protected admin endpoints for student token

*Backup: the recorded video, if anything fails.*

---

## 16 — What we learned

- Grouping functions by business domain simplifies security
- VPC Gateway Endpoints give network isolation for $0
- Deploy earlier — some bugs only exist in AWS
- Verify numbers; do not quote plausible ones

*Visual:* none. Just the four key lessons.

---

## 17 — Conclusion

- A cloud-native platform with full private VPC isolation
- Grouped by business domain, secure by design
- Under $5 of 100 credits
- Honest about its limits

**Questions?**

*Visual:* the architecture diagram again, full screen.

---

## Slides we deliberately did not make

| Not included | Why |
|---|---|
| A code walkthrough | Nobody reads code on a projector; the demo shows behaviour instead |
| A full AWS service catalogue | We use seven; the other 190 are not our project |
| An agile-process slide | The brief asks for architecture and implementation |
| A "future with AI" slide | We would be claiming something we did not build |
