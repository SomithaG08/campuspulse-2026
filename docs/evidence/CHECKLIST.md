# Evidence Checklist

Every artefact the report and the presentation need, mapped to the requirement it satisfies.

**Collect as you go.** Evidence gathered in week three is easy; evidence reconstructed in week eleven is painful and sometimes impossible.

**Nothing here is ever fabricated.** Until an item exists, its row stays unticked and the report says *not verified yet*.

---

## How to save it

```text
docs/evidence/
├── cost/           budget alert, credit balance over time
├── deploy/         terraform output, verification script, console screenshots
├── security/       401, 403, IAM simulation, encryption settings
├── demo/           dashboard, alerts, the log line, the DynamoDB item
├── monitoring/     alarm in ALARM, CloudWatch dashboard
├── dr/             restore in progress, restored table, timing
└── api-test-results.json
```

Name files `YYYY-MM-DD-what-it-shows.png`. A folder of `Screenshot 2026-11-14 at 15.32.08.png` is useless three weeks later.

**Redact before saving:** the 12-digit account ID, any token, any password. Endpoint URLs and Cognito client IDs are public identifiers and need no redaction.

---

## Cost — spec §8

| # | Artefact | Requirement | Done |
|---|---|---|---|
| C1 | Budget alert in the Budgets console | **C2, mandatory** | ☐ |
| C2 | The alert email, or the alarm configuration if Billing is restricted | C2 | ☐ |
| C3 | Credit balance, early in the project, dated | C5 monitoring | ☐ |
| C4 | Credit balance at the end, dated | cost analysis | ☐ |
| C5 | `verify-deployment.sh` output showing **no EC2, no RDS, no NAT Gateway** | C4 | ☐ |

C5 is unusual and worth including: evidence of what is *not* running is what makes a low-cost claim credible.

## Deployment — spec §7

| # | Artefact | Requirement | Done |
|---|---|---|---|
| D1 | `terraform apply` completing, resource count visible | I4 | ☐ |
| D2 | `terraform output` (account ID redacted) | I4 | ☐ |
| D3 | Full `verify-deployment.sh` output | I4 | ☐ |
| D4 | DynamoDB console: both indexes, TTL, PITR | A6, F3 | ☐ |
| D5 | Cognito console: both groups, three users | F5 | ☐ |
| D6 | Lambda console: five functions | I1 | ☐ |
| D7 | **A teammate's note from deploying off the guide alone** — what worked, what was unclear | **I4** | ☐ |

D7 is the real test of "reproducible", and the only one that can fail honestly.

## Security — spec §6, §17

| # | Artefact | Requirement | Done |
|---|---|---|---|
| S1 | `curl` with no token → **401** | A3, I6 | ☐ |
| S2 | `curl` with a staff token on `/alerts` → **403** | **F5 — two roles** | ☐ |
| S3 | Same staff token on `/events` → **200** | F5 | ☐ |
| S4 | A decoded JWT showing `cognito:groups` (token redacted) | F5 | ☐ |
| S5 | `aws iam simulate-principal-policy` for `cp-ingest`: `PutItem` allowed, `Query` and `Scan` implicitDeny | **A3 least privilege** | ☐ |
| S6 | DynamoDB and S3 encryption-at-rest settings | A3 | ☐ |
| S7 | A log line proving no password or token is recorded | A3 | ☐ |

**S2 + S3 together are the two-role requirement.** S5 is machine-generated proof of least privilege — far stronger than a paragraph claiming it.

## The working system — spec §4, §7

| # | Artefact | Requirement | Done |
|---|---|---|---|
| W1 | Simulator terminal, events flowing | I7, F1 | ☐ |
| W2 | Dashboard with live data | F7, I2 | ☐ |
| W3 | A red critical alert on the dashboard | F4 | ☐ |
| W4 | The same event as a DynamoDB item, `gsi2pk` present | F3 | ☐ |
| W5 | The CloudWatch log line for that `request_id` | F6 | ☐ |
| W6 | `GET /stats` response | F4, F7 | ☐ |
| W7 | **The same page as `staff`, alerts panel absent** | F5 | ☐ |
| W8 | `api-test-results.json` from a real run — 45 passed | testing | ☐ |
| W9 | Backup demo video, recorded and stored offline | **M1 — demo risk** | ☐ |

**W4 → W5 is the traceability story**: one event, visible in the response, in the database, and in the log, tied by one id. Show those three side by side.

**W9 is not optional.** Venue Wi-Fi fails. The spec accepts a video as evidence.

## Monitoring — spec §6

| # | Artefact | Requirement | Done |
|---|---|---|---|
| M1 | CloudWatch dashboard with real curves | A5 | ☐ |
| M2 | **An alarm in ALARM, triggered deliberately** | A5 | ☐ |
| M3 | The same alarm back in OK | A5 | ☐ |
| M4 | A Logs Insights query and its results | A5 | ☐ |
| M5 | Log retention showing 7 days, not never | cost | ☐ |

M2 is the one that counts. An alarm that has never fired is an untested alarm.

## Disaster recovery — spec §6

| # | Artefact | Requirement | Done |
|---|---|---|---|
| R1 | PITR enabled | A6 | ☐ |
| R2 | A restore **actually performed** | **A6** | ☐ |
| R3 | The restored table containing the data | A6 | ☐ |
| R4 | **Elapsed restore time — the measured RTO** | A6 | ☐ |

R4 turns "our RTO is about 20 minutes" into "we measured it: 18 minutes". One of those is a claim, the other is a finding.

## Scalability — spec §6

| # | Artefact | Requirement | Done |
|---|---|---|---|
| P1 | Cold-start vs warm latency from the API test output | A1 | ☐ |
| P2 | Lambda `Duration` p95 from the dashboard | A1 | ☐ |
| P3 | A higher-rate simulator run and its effect on latency | A1 | ☐ |

Three measurements beat three paragraphs of theory. The scalability section should contain numbers somebody observed.

## Submission — spec §13

| # | Item | Done |
|---|---|---|
| F1 | Architecture diagram exported as PDF or image | ☐ |
| F2 | Report as PDF, all eleven sections | ☐ |
| F3 | Repository link, accessible | ☐ |
| F4 | Deployment guide / scripts included | ☐ |
| F5 | Demo evidence (this folder) | ☐ |
| F6 | Presentation slides | ☐ |
| F7 | Contribution table, filled from what actually happened | ☐ |
| F8 | References complete, none fabricated | ☐ |

---

## The four that would hurt most to be missing

1. **S2 + S3** — the two roles behaving differently. 15% of the grade leans on it.
2. **M2** — an alarm you actually triggered.
3. **R2 + R4** — a restore you actually performed, and timed.
4. **W9** — the backup video, for the day the Wi-Fi fails.
