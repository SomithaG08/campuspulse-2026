# Team and Ownership — CampusPulse 2026

**Team members:** Somitha Gudivada · Meha · Madhavan · MD

This is a **proposal**, not a decision. Swap components around to match who actually wants to learn what — but keep the two rules at the bottom.

## Proposed ownership

| Member | Owns | Builds | Writes the learning doc for | Speaks at the oral about |
|---|---|---|---|---|
| **Somitha** | Architecture + ingestion | `cp-ingest`, `cp-stats`, the severity rules, the shared config | `06-lambda-explained.md`, `13-big-data-and-analytics.md` | Architecture overview, data flow, processing logic |
| **Meha** | Identity and security | Cognito user pool, groups, `cp-auth`, the IAM policies, the threat model | `08-cognito-authentication.md`, `10-iam-security.md` | Authentication, authorization, security design |
| **Madhavan** | Data generation and testing | `simulator.py`, the test suite, the demo script and backup video | `14-simulator-explained.md`, `17-testing-explained.md` | The simulator, testing and evaluation, the live demo |
| **MD** | Interface and observability | The dashboard, `cp-query`, the CloudWatch dashboard and alarms, evidence collection | `15-frontend-explained.md`, `09-cloudwatch-monitoring.md` | The dashboard, monitoring, troubleshooting |

**Shared by everyone:** the deployment guide (each person deploys from it at least once), the report, and the glossary.

**One person holds the deploy.** Whoever owns the Terraform state runs the official deployment; everyone else experiments with their own name prefix. Two people applying infrastructure to one account at the same time is how a working stack becomes a broken one.

## Why ownership is split this way

The spec grades participation directly: *"All team members must participate and be able to explain both the architecture and the implementation"* (§11), and each report needs a per-member contribution table (§16). The four areas above are deliberately **explainable independently** — you can understand and present the simulator without understanding IAM, and vice versa — while still touching every graded dimension.

Each area also has a beginner on-ramp: the simulator is plain Python with no AWS knowledge required to start; the dashboard is HTML, CSS and `fetch`; the security work is mostly console configuration plus careful reading; the ingestion path is the most AWS-heavy and suits whoever is furthest along.

## The two rules

1. **You write the learning document for what you own.** Not because documentation is a chore to distribute, but because writing the explanation is how you find out whether you actually understand it — three weeks before an examiner finds out for you.
2. **Nobody presents a component they did not build.** If that feels risky for someone's section, that is the signal to pair up on it now rather than the night before.

## Cross-review pairs

So that no component has exactly one person who understands it:

- Somitha ↔ Meha — ingestion and auth meet at the token check
- Madhavan ↔ MD — the simulator writes what the dashboard reads

Each pair reads the other's code and learning doc once before Phase 13.

## Contribution table (for the report — fill in as you go, do not reconstruct at the end)

| Member | Components | Documentation | Other | Approx. share |
|---|---|---|---|---|
| Somitha Gudivada | | | | |
| Meha | | | | |
| Madhavan | | | | |
| MD | | | | |
