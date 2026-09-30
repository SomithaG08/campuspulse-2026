# Phase 2 — Architecture Design (complete, pending your review)

## What we built

The design. No infrastructure exists and no code has been written. Everything below is a decision recorded with its alternatives, so it can be defended or changed on purpose rather than drifted away from.

## Files created

| File | What it is |
|---|---|
| `docs/architecture/01-architecture-decisions.md` | Nine decisions (AD-0…AD-9), each with options considered, the choice, the reasoning, and what the choice costs us |
| `docs/architecture/02-diagram.md` | ASCII diagram + Mermaid diagram + a table explaining all 10 numbered connections + the trust-zone model |
| `docs/architecture/03-services-explained.md` | The eleven required questions answered for API Gateway, Lambda, DynamoDB, Cognito, S3, CloudWatch and IAM — plus the services we deliberately refuse and why |
| `docs/architecture/04-data-model.md` | **Frozen contract.** Event schema, validation rules, severity thresholds, DynamoDB keys and both GSIs, the five access patterns, TTL, and a worked example |
| `docs/architecture/05-api-contract.md` | Every endpoint: method, auth, request, response, error cases, plus the permission matrix and the three enforcement layers |
| `docs/architecture/06-data-flow.md` | One occupancy reading traced through 14 stages, input → processing → output at each, failures at each, and the 45-second spoken version |
| `docs/cost/01-cost-model.md` | Free-tier allowances and prices, each tagged verified or unverified with its source |
| `docs/requirements/06-team-assignment.md` | Component ownership for the four of you, with the contribution table to fill in as you go |

## Files changed

`01-requirements-matrix.md` (open decisions resolved, team recorded) · `03-risks.md` (T1 closed, C5 and C6 added, top-five reordered) · `05-aws-account-verification.md` (marked resolved, two open items kept).

## The architecture in one paragraph

A Python simulator signs in to **Cognito** and sends campus events over HTTPS to an **API Gateway HTTP API**, which validates the JWT before any of our code runs and routes to one of four small **Lambda** functions — each with its own least-privilege IAM role. `cp-ingest` validates the payload, applies threshold rules to set the severity itself rather than trusting the device, and writes to a single **DynamoDB** table with two indexes, one of them a sparse index containing only alerts. `cp-query` and `cp-stats` read from those indexes for a static **S3**-hosted dashboard. Every function logs to **CloudWatch**, which also holds our metrics, alarms and dashboard. There is no VPC, no EC2 and no NAT Gateway — which is both the security model and the cost model.

## Beginner explanation

We decided who does what in the system. The simulator pretends to be sensors. The reception desk (API Gateway) checks everyone's badge. Four small workers (Lambda) each do one job and can only open the one door they need. The filing system (DynamoDB) stores events in a way that makes "what happened today" and "what's wrong right now" fast to look up. The control room (CloudWatch) records everything. Nothing runs when nobody is using it, which is why this costs close to nothing.

## AWS explanation

Seven services: API Gateway (entry point + token validation), Lambda (our code), DynamoDB (storage), Cognito (users, passwords, roles), S3 (dashboard files), CloudWatch (logs, metrics, alarms), IAM (who may do what). Region **eu-west-3, Paris**. All serverless: no instance, no cluster, no load balancer, no NAT Gateway.

## How the pieces connect

Simulator/browser → API Gateway → JWT authorizer → Lambda → DynamoDB → dashboard, with CloudWatch beside every step and IAM under all of them. `06-data-flow.md` walks one event through all 14 stages.

## Testing

Nothing executable exists yet. Verification done: every endpoint in the spec's Appendix B appears in the API contract; every field of the spec's Appendix A event appears in the data model; the five access patterns cover every query the API contract can issue, with no `Scan`; the architecture was checked against each mandatory row of the requirements matrix.

## Documentation updated

Eight new files, three updated. Learning documentation (`docs/learning/`) still does not exist — it starts in Phase 3.

## Problems / open items

| ID | Item | Who |
|---|---|---|
| **C5** | **Which plan is the AWS account on, and what date was it created?** On the Free plan it closes at 6 months or credit depletion — the account can shut with the project inside it | You, today |
| C6 | Never join an AWS Organization / Control Tower with this account — instant credit expiry | Everyone |
| — | eu-west-3 unit prices, DynamoDB on-demand rates, S3 free-tier figures unverified (pricing pages render in JS) | Phase 4, via the pricing API |
| — | Confirm the proposed ownership split works for the four of you | Team |

## Next phase

**Phase 3 — Repository and project structure**: the full folder tree, the shared campus config the simulator and backend both import, the `docs/learning/` skeleton with `00-start-here.md`, the glossary, the learning path, and the README. After that, Phase 4 creates the budget alert first and infrastructure second.
