# Slide Deck — CampusPulse 2026

**17 slides · 15 minutes · four speakers.** The spoken words are in `02-speaking-script.md`; this file is what goes **on** the slides.

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

**This is the slide that frames everything after it — the five questions come straight from the brief.**

---

## 4 — Architecture

```text
Simulator ──HTTPS+JWT──► API Gateway ──► Lambda ×5 ──► DynamoDB
                              │            │              │
                          JWT check    CloudWatch      PITR backup
Browser ──► S3 (dashboard) ───┘         Cognito · IAM
```

- Fully serverless — no EC2, no VPC, no NAT Gateway
- Region: eu-west-3 (Paris)
- Nothing bills by the hour

*Visual:* the full architecture diagram.

---

## 5 — Why serverless

| | Server | Serverless |
|---|---|---|
| Idle cost | **full hourly rate** | **zero** |
| Scaling | you configure it | automatic |
| You manage | OS, patches, scaling | your function |

- Bursty workload, idle most of the time
- 100 credits, non-renewable
- NAT Gateway alone would be ~$32/month

*Visual:* the table.

---

## 6 — One event, end to end

```text
Simulator → API Gateway → JWT check → Lambda
   → validate → classify → DynamoDB → dashboard
```

- Client sends `severity: normal`
- Server computes `critical` — **and overrules it**
- 58 people in a room that holds 45

*Visual:* the flow, with the overrule highlighted.

**The strongest single idea in the project: a device cannot declare itself normal.**

---

## 7 — Security: three independent layers

| Layer | Decides | Fails with |
|---|---|---|
| JWT authorizer | do we know you? | **401** |
| Lambda group check | may you do this? | **403** |
| IAM | may this function touch this? | `AccessDenied` |

- Each is independently sufficient
- The first runs **before our code**

*Visual:* three concentric gates.

---

## 8 — Two roles, really different

| | `ops` | `staff` |
|---|---|---|
| Submit events | ✅ | **403** |
| Read alerts | ✅ | **403** |
| Read events, stats | ✅ | ✅ |
| Raise a request | ✅ | ✅ |

*Visual:* the matrix, with the two 403 cells highlighted.

**Demonstrated live on slide 15, not just claimed.**

---

## 9 — Least privilege, concretely

| Function | Can | Cannot |
|---|---|---|
| `cp-ingest` | write one table | **read anything** |
| `cp-query` | read | **write anything** |
| `cp-auth` | call Cognito | touch the database |

- No AWS credentials anywhere in the code
- `dynamodb:Scan` granted to nobody

*Visual:* the table.

**The internet-facing function cannot read a single student request.**

---

## 10 — The dashboard

*Visual:* a full-width screenshot of the dashboard with a red alert visible.

- Five KPI tiles · alerts · occupancy · energy · recent events
- Polls every 10 seconds
- Pauses when hidden — a cost control

---

## 11 — Observability

- Structured JSON logs, one `request_id` throughout
- Metrics via EMF — no extra API calls
- **Four alarms**: errors, 5xx, alert burst, invocation ceiling
- One dashboard, 7-day log retention

*Visual:* the CloudWatch dashboard, plus the alarm in ALARM.

---

## 12 — Cost control

- **Nothing bills by the hour**
- No NAT Gateway (~$32/month avoided)
- Budget alert, credits excluded so it tracks real usage
- Estimated spend: **under $5** of 100 credits
- Actual: `[INSERT]`

*Visual:* the budget console screenshot.

---

## 13 — Scalability, and our limit

- Lambda and DynamoDB scale horizontally, automatically
- **Our ceiling: ~1,000 writes/second** — one partition per day
- **The fix:** shard the partition key across ten
- We designed it; we did not build it

*Visual:* one partition vs ten sharded partitions.

**Knowing where your design breaks is worth more than pretending it doesn't.**

---

## 14 — Testing

- **131 unit tests**, ~1 second, no AWS needed
- **45 API checks** against the deployed system
- 1000 generated events through the real validator
- A test that proves **no query can become a `Scan`**

*Visual:* the test run output.

---

## 15 — Live demo

*No bullets. Switch to the terminal and the browser.*

1. Dashboard, signed in as `ops`
2. Start the simulator — events appear
3. `--force-alert` — a red alert appears
4. The same event in DynamoDB, then in the log
5. Sign in as `staff` — the alerts panel is gone

*Backup: the recorded video, if anything fails.*

---

## 16 — What we learned

- Deploy earlier — some bugs only exist in AWS
- Some bugs only exist **visually**
- Verify numbers; do not quote plausible ones
- Explainable thresholds beat an unexplainable model

*Visual:* none. Just the four lines.

---

## 17 — Conclusion

- A working cloud-native platform, end to end
- Secure by design, not by addition
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
