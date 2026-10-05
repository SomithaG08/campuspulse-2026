# Learning documentation

Written for teammates starting from zero cloud knowledge. Every document defines its terms simply, then technically, shows how *our* project uses the idea, and ends with self-check questions and answers.

**Start at `00-start-here.md`, then follow `learning-path.md`.**

| # | Document | Owner | Covers |
|---|---|---|---|
| 00 | `00-start-here.md` | everyone | What we are building, cloud computing, AWS, Big Data, the analogy and where it breaks |
| 05 | `05-api-explained.md` | everyone | HTTP, JSON, status codes, 401 vs 403, our seven endpoints |
| 06 | `06-lambda-explained.md` | Somitha | Handlers, cold starts, the four functions, configuration, errors |
| 07 | `07-dynamodb-explained.md` | Somitha, MD | Key design, Query vs Scan, the sparse index, TTL, our ceiling |
| 08 | `08-cognito-authentication.md` | Meha | Authentication vs authorization, JWTs, the three checks, pool settings |
| 09 | `09-cloudwatch-monitoring.md` | MD | Logs vs metrics vs alarms, EMF, p95, the free-tier budget |
| 10 | `10-iam-security.md` | Meha | Least privilege, blast radius, reading a policy, the honest caveat |
| 11 | `11-networking-explained.md` | everyone | VPC, subnets, security groups — and why we have none |
| 12 | `12-serverless-explained.md` | everyone | What serverless means, what it costs us, when it is wrong |
| 13 | `13-big-data-and-analytics.md` | Somitha | The three Vs, where each idea lives in our code, what changes at 1000× |
| 14 | `14-simulator-explained.md` | Madhavan | Generation, the time-of-day curve, guard rails, zero dependencies |
| 15 | `15-frontend-explained.md` | MD | Frontend vs backend trust, the colour method, the token trade-off |
| 16 | `16-infrastructure-as-code.md` | state owner | Terraform, the state file, our files, what it deliberately does not do |
| 17 | `17-testing-explained.md` | Madhavan | Two layers, boundary values, why most tests assert failure |
| 19 | `19-disaster-recovery.md` | everyone | RPO, RTO, PITR, the restore procedure, what we do not claim |
| 20 | `20-troubleshooting.md` | everyone | Every failure mode: cause, where to look, fix, verify |
| 21 | `21-glossary.md` | everyone | ~95 terms, grouped by family |
| — | `learning-path.md` | everyone | Ten steps from nothing to presenting |

## Topics the brief lists that live elsewhere

Rather than duplicate content into near-empty files, these are covered where they belong:

| Topic | Where it is |
|---|---|
| Cloud computing basics | `00-start-here.md` §3, `12-serverless-explained.md` |
| AWS basics | `00-start-here.md` §4, `docs/architecture/03-services-explained.md` (the eleven questions, per service) |
| Project architecture | `docs/architecture/01-architecture-decisions.md` and `02-diagram.md` |
| How data flows | `docs/architecture/06-data-flow.md` — one event through 14 stages |
| Costs and free tier | `docs/cost/01-cost-model.md` — every figure with its source and confidence |

**One idea, one place.** A fact in two files is a fact that will disagree with itself by submission week.
