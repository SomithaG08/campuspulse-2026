# Phase 1 — Requirements Analysis (complete, pending your review)

## What we built

No code. A planning layer that turns the official PDF into a checklist we can be graded against.

## Files created

| File | What it is |
|---|---|
| `docs/requirements/01-requirements-matrix.md` | Every requirement extracted from the PDF (§4, §6, §7, §8, §9, §10, §11, §13, §15, §16) with how we plan to satisfy it, which component will do it, and what evidence we must produce. 10 groups, ~60 rows. Nothing marked done. |
| `docs/requirements/02-scope.md` | The use case we chose, what we build, what we explicitly refuse to build and why, the rule for optional features, and why the scope is realistic against the grading weights |
| `docs/requirements/03-risks.md` | 7 risk categories, ~30 risks with likelihood, severity, mitigation and early-warning signs; top five called out |
| `docs/requirements/04-definition-of-done.md` | 10 checklists mapped to the 5 grading criteria — the bar for calling this project finished |
| `docs/requirements/05-aws-account-verification.md` | **Blocking.** 14 checks to run in your school account before the architecture is fixed |
| `.gitignore` | Written now, not later: the single worst outcome in this project is AWS credentials pushed to a public repo (risk S1) |

## Why we created them

The PDF grades 75% of this project on design, explanation and evidence rather than code volume (§12). Building first and reading the requirements later is how teams lose those marks. The matrix makes every requirement traceable to a component and a piece of evidence, so nothing is discovered missing the week before submission.

## Beginner explanation

Before writing software, engineers write down exactly what the software must do, what it must *not* do, what could go wrong, and how they will know when it is finished. That is all Phase 1 is. The four documents answer four questions: **What is required? What are we building? What could go wrong? When are we done?**

## AWS explanation

None yet — no AWS service has been chosen or created. Phase 2 does that. One AWS-related decision is already made and worth knowing now: we plan a **serverless** design, meaning we never run or pay for a server that sits idle. That choice is what keeps this project inside your 100 credits.

## How the pieces connect

`01-requirements-matrix.md` is the master list. `02-scope.md` narrows it to what we will actually do. `03-risks.md` says what could stop us. `04-definition-of-done.md` is the finish line. `05-aws-account-verification.md` is the gate: its answers decide the architecture in Phase 2.

## Testing

Nothing to test yet. Verification performed: the extracted PDF text was re-read section by section against the matrix to confirm every mandatory requirement appears.

## Documentation updated

All files listed above are new. No learning documentation exists yet — that starts in Phase 3.

## Problems / open items

| ID | Open item | Needed from |
|---|---|---|
| OD-1 | Cognito or custom JWT authentication? | Account check V6 |
| OD-2 | Terraform or CLI/console deployment? | Account checks V7, V13 |
| OD-3 | Which region? | Account check V1 |
| OD-4 | Is any EC2/VPC needed at all? | V1-V13 combined |
| TEAM-1 | Team member names and who owns which component | You |

## Next phase

**Phase 2 — Architecture design**: service-by-service selection with justification, the frozen event schema and DynamoDB key design, the text + Mermaid architecture diagram, the full data-flow walkthrough of one event, the cost model, and the answers to the 11 required questions per service.

**Phase 2 should not start until the account verification answers are in** — otherwise we risk designing around a service the account does not allow.
