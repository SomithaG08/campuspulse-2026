# Phase 3 — Repository and Project Structure (complete, pending your review)

## What we built

The skeleton the rest of the project hangs on, plus the first real code: the shared campus configuration that stops the simulator and the backend from ever disagreeing.

## Files created

| File | What it is |
|---|---|
| `README.md` | Project overview, stack, structure, API summary, security, cost, and the **scale guardrails** |
| `REFERENCES.md` | Citation list, started now so it is accurate later — including an honest note on AI assistance |
| `backend/src/common/campus_config.py` | **Real code.** Five buildings, eleven rooms, capacities, energy baselines, the six event types with their units and thresholds, validation limits, and lookup helpers |
| `docs/learning/00-start-here.md` | Zero-knowledge introduction: what we're building, cloud computing, AWS, big data, the analogy and where it breaks, plus self-check questions |
| `docs/learning/21-glossary.md` | ~90 terms in families, each with a plain meaning, its role in *our* project, and an example |
| `docs/learning/learning-path.md` | Ten steps from nothing to presenting, with what to read, what to run, and what you must be able to answer |
| Folder notes | One line in each empty folder saying what goes there and in which phase |

## Files changed

None — Phase 1 and 2 documents are unchanged.

## Why we created them

A structure agreed before the code exists is what keeps four people from inventing four incompatible layouts. `campus_config.py` exists now, before any handler, because it is the concrete form of the frozen data model: capacities and thresholds live in exactly one file that both sides import, which is the mitigation for risk N1 (components that don't fit together).

The three learning documents are the ones that are useful *before* there is code to explain. The remaining learning documents are deliberately **not** written yet: the rule is that documentation describes the actual implementation, and a document written now about a Lambda that does not exist would be fiction that needs rewriting anyway.

## Beginner explanation

We decided where every file goes and wrote down the campus itself — which buildings exist, how many people each room holds, and what counts as too hot, too crowded or too much electricity. Everything built later reads those numbers from this one file, so the simulator and the server can never disagree about what "overloaded" means.

## AWS explanation

None. Nothing in this phase touches AWS or costs anything. `campus_config.py` is pure Python with no cloud dependencies, which is exactly why it can be tested on a laptop in a second.

## How the pieces connect

`campus_config.py` is imported by the simulator (to generate plausible readings) and by `cp-ingest` (to classify them). The docs it implements are `docs/architecture/04-data-model.md` §2. The folder tree matches the repository structure section of the README.

## Testing

**Executed.** A verification script cross-checked `campus_config.py` against the frozen data model: all six event types present with matching units; the temperature and humidity normal and critical bands identical to the document; TTL 30 days; the severity set correct; every room resolvable to an integer capacity; and the document's worked example (58 people in A203, capacity 45) classifying as `critical` in code exactly as the document states. **Result: no mismatches.**

`python backend/src/common/campus_config.py` prints the campus: 5 buildings, 11 rooms, total capacity 666.

## Documentation updated

Three new learning documents, the README and REFERENCES. The learning documents for Lambda, DynamoDB, Cognito, CloudWatch, the simulator, the frontend, IaC, testing, costs, DR and troubleshooting arrive with the components they describe.

## Problems / open items

| Item | Who |
|---|---|
| **Still open from Phase 2:** which plan is the AWS account on, and what date was it created? (risk C5 — a free-plan account closes at six months or credit depletion) | You |
| Confirm the ownership split in `06-team-assignment.md` works for the four of you | Team |
| `git init` and first push — `.gitignore` is already in place, so this is safe to do now | You |

## Next phase

**Phase 4 — Infrastructure.** In this order, deliberately:

1. **The budget alert first**, before any other resource exists.
2. Verify the unverified prices from the cost model using the AWS pricing API.
3. Then the DynamoDB table, Cognito user pool with both groups, IAM roles, S3 bucket, and the API — as Terraform.
4. The deployment guide and the cleanup procedure, written as we go rather than reconstructed afterwards.

Phase 4 is the first phase that creates real resources and can therefore spend real credits. It will begin with an explicit cost warning listing exactly what is being created and what each thing can cost.
