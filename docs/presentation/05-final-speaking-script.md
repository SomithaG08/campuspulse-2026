# Final Presentation — Speaking Script (10 minutes)

Deck: `CampusPulse_2026_Final_Presentation.pptx` · 15 slides (slide 14 = what we learned, slide 15 = thank you / questions) · four speakers, equal time.
The same words are in each slide's speaker notes. Read aloud at a natural pace this is about 9.5 minutes, leaving room for the demo.

| Speaker | Slides | Time |
|---|---|---|
| Somitha Gudivada | 1 – 4 | 0:00 – 2:20 |
| Meha | 5 – 7 | 2:20 – 4:40 |
| Madhavan | 8 – 10 (incl. live demo) | 4:40 – 7:00 |
| MD | 11 – 13 | 7:00 – 9:20 |
| Everyone | 14 | 9:20 – 10:00 |

---

## SOMITHA — slides 1 to 4

**Slide 1 · Title (15 s)**
Good morning. We are Team 4, and this is CampusPulse 2026, a platform that monitors a university campus in real time. It is deployed on AWS in Paris, and every number today comes from the running system. Each of us built one part and will present it: I cover architecture and ingestion, Meha security, Madhavan the simulator, tests and demo, and MD the dashboard, monitoring and cost.

**Slide 2 · The problem and what we delivered (30 s)**
A campus produces thousands of readings a day. Individually they mean nothing; the operations team only needs answers to the four questions on the left. CampusPulse answers them automatically. Following review feedback, we delivered an upgraded, corrected system: eight API routes, two Lambda functions grouped strictly by business requirement, a dedicated VPC with private subnets across two Availability Zones, automated backups, and one hundred and sixty-one automated tests, on a simulated campus of five buildings and eleven rooms.

**Slide 3 · Solution architecture (45 s)**
This is our deployed architecture. Users load two role-specific pages from S3 (1) — one for administrators, one for students. All API calls, from the browser (2) or simulator (3), enter through API Gateway, whose JWT authorizer validates tokens before code runs (4). We grouped our functions by business requirement: `auth` handles public identity outside the VPC to reach Cognito without costly NAT gateways (5). All campus operational routes go to the `api` Lambda inside our private VPC across two Availability Zones (6). It reaches DynamoDB through a free Gateway Endpoint (7). CloudWatch monitors the system and sends email alerts to our team inboxes via SNS (8).

**Slide 4 · One event, end to end (45 s)**
Here is one real event. The simulator reports fifty-eight people in room A203 and labels it normal. The `api` function validates every field, then discards the client's severity and recomputes it: the room holds forty-five, fifty-eight is a hundred and twenty-nine per cent, above the hundred-and-twenty threshold, so it is stored as critical. A sensor must never be able to declare itself normal. On the right, the data model: one table keyed by day and time, a building index, a sparse index of alerts, and a student request index. There is no Scan anywhere. Meha will explain who is allowed to send that event.

---

## MEHA — slides 5 to 7

**Slide 5 · Authentication with Amazon Cognito (40 s)**
Thank you. Identity is handled by Amazon Cognito. A user, or the simulator, sends an email and password to POST /login. My function, `auth`, passes them to Cognito, which checks the password, so our code never stores one. Cognito returns a JWT valid for sixty minutes that carries the user's role: admin or student. Deliberate choices: users are created by an admin only; a wrong password and an unknown user get the same error, so nobody can probe which emails exist; and we chose the Essentials tier because it provides ten thousand free monthly active users.

**Slide 6 · Three independent security layers (50 s)**
Every request passes three independent layers. First, the JWT authorizer: a missing or forged token gets a 401 before any Lambda runs, so fake tokens cost us nothing. Second, the function checks the group in the token: the wrong role gets a 403. 401 means we do not know you; 403 means we know you and the answer is still no. Third, IAM limits what each function can touch. The table shows the two roles really differ: students cannot submit sensor events or read alerts. On the right is real output from our deployed API: 401 without a token, 403 for student on alerts, 200 on stats.

**Slide 7 · Least privilege and VPC network isolation (40 s)**
Least privilege in practice: our compute is grouped into two business domains. `auth` only calls Cognito and has zero database access — it cannot touch campus data. The `api` function runs inside our custom VPC in private subnets with no internet gateway and no NAT Gateway. It communicates with DynamoDB exclusively through a private Gateway Endpoint with a policy restricted to our table. Even if credentials were leaked, an attacker has no path to exfiltrate data to the internet. Madhavan will now show where the events come from.

---

## MADHAVAN — slides 8 to 10

**Slide 8 · The campus simulator (40 s)**
Thank you. With no real sensors, I built a simulator that plays the campus devices. It logs in through Cognito like a user, keeps its token fresh, and sends readings for all five buildings and eleven rooms, with a controllable share of anomalies. It uses only the Python standard library, so nothing can fail to install on demo day, and it refuses to send faster than every half second, to protect our budget. One real bug: force-alert used a range that straddled the critical threshold, so a forced alert sometimes arrived as a warning. We fixed the range and verified it over three hundred events.

**Slide 9 · Testing: 161 checks, 0 failures (45 s)**
We test in two layers. A hundred and forty-three backend unit tests and eighteen simulator tests run in about a second with no AWS account, because the business logic contains no cloud code. Two are design guarantees: no query we build can become a table scan, and a thousand simulated events pass through the real validator. Then fifty API checks run against the live system for what unit tests cannot see: routing, permissions and tokens. The key ones: student gets 403 on alerts, and an over-capacity event comes back critical even when the client says normal.

**Slide 10 · Live demo (55 s, mostly the demo)**
[1] The admin dashboard is open, signed in as admin: active alerts, building occupancy and energy tiles update live. [2] I start the simulator; readings stream in and the tiles update within ten seconds. [3] Now I force one alert: the simulator sends one reading pushed past the critical threshold; a red critical row appears with the reason in plain words, and our team receives an email alert. [4] On the student page, signed in as student, we see room availability and comfort; if I submit an urgent maintenance request, the team gets an urgent-request alarm within a minute, while GET /alerts returns 403. MD, over to you.

---

## MD — slides 11 to 13

**Slide 11 · Two role-specific pages and backups (40 s)**
Thank you. In response to the professor's review, we split the interface into two dedicated pages: `admin.html` for campus operations and `student.html` for room comfort and maintenance reporting. The pages contain no data, so they are securely hosted on S3 with versioning enabled. For disaster recovery, we combine DynamoDB Point-in-Time Recovery with an automated AWS Backup vault running daily and weekly snapshots. Our rehearsed restore drill measured an RTO of under three minutes.

**Slide 12 · Observability with Amazon CloudWatch and SNS alerts (40 s)**
To watch the system itself we use CloudWatch. Every function writes structured JSON logs with a request id that ties directly to the API access log. Our metrics come straight out of those log lines with Embedded Metric Format, with no extra API calls. Under simulator load, p95 latency was 133 milliseconds. Seven alarms monitor errors, alert bursts, and urgent student requests. When an anomaly occurs, CloudWatch triggers an SNS topic that emails the team's school inboxes immediately.

**Slide 13 · Cost: measured, not guessed (45 s)**
Cost, with real numbers from the billing console. This month our budget shows under two dollars billed against a ten-dollar limit. The credits page shows about fourteen dollars of estimated usage out of a hundred and sixty across the whole account. The biggest architectural achievement: our custom VPC uses a free DynamoDB Gateway Endpoint instead of a NAT Gateway, avoiding thirty-two dollars a month while achieving full private network isolation. Nothing in this design bills by the hour. To close, one lesson from each of us.

---

## EVERYONE — slide 14 · What we learned (40 s), then slide 15 · Thank you

- **Somitha:** A careful data model shapes every query after it; our partition key and TTL decided our speed and our cost.
- **Meha:** Authentication working is not authorization being correct; we audited every route.
- **Madhavan:** Testing against the live API found three validation gaps unit tests missed.
- **MD:** Business-driven grouping and network boundaries let us meet strict security requirements at zero additional cost.
- **Somitha (close):** Our limits are stated: one region, a write ceiling with a designed fix, threshold rules rather than machine learning. Thank you, we are happy to take questions.
