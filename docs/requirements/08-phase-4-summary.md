# Phase 4 — Infrastructure (complete, pending your review)

> **Nothing has been deployed.** No AWS resource exists, no credit has been spent. This phase produced the code and the procedure; running it is yours, and the cost warning comes first.

## What we built

The foundation infrastructure as Terraform, the deployment and cleanup procedures, and a script that closes the pricing gaps left open in Phase 2.

## Files created

| File | What it is |
|---|---|
| `infrastructure/terraform/*.tf` | 10 files, **26 resources**: budget alert, DynamoDB table with both GSIs + TTL + PITR, Cognito pool with `ops` and `staff` groups, 4 IAM roles, S3 site bucket with a read-only policy, 4 log groups with 7-day retention |
| `infrastructure/terraform/terraform.tfvars.example` | The one value you must set (`notification_email`); the real file is gitignored |
| `docs/deployment/00-COST-WARNING.md` | Every resource and what it can cost; the never-create list; the end-of-session habit |
| `docs/deployment/01-prerequisites.md` | Tools, IAM user setup, credential rules, who owns the state file |
| `docs/deployment/02-deploy-foundation.md` | Step-by-step with exact commands, verification for each resource, and a troubleshooting table |
| `docs/deployment/cleanup.md` | Teardown in dependency order, with what to export before deleting |
| `scripts/verify-prices.sh` | Queries the AWS Price List API for the eu-west-3 figures our cost model flags unverified |
| `docs/learning/16-infrastructure-as-code.md` | Terraform from zero, tied to our actual files, with self-check questions |

## Files changed

None.

## Why we built it this way

**The budget comes first.** `budget.tf` is applied in the same run as everything else, but it is written first and verified first, because a billing alert created after the resources is a smoke detector installed after the fire. It uses `include_credit = false` — the detail that matters on a credit-funded account, where a normal cost budget reads $0.00 right up until the credits are gone.

**No Lambda, no API in this phase.** Their code does not exist yet. Their IAM roles and log groups do, which is the useful half.

**Log groups are created by us, not by Lambda.** A log group Lambda creates for itself has retention set to *never expire*. Creating them with an explicit 7 days is a one-line fix to a cost leak most projects never notice.

**Users are not in Terraform.** A password in a `.tf` file is a password in Git.

## Beginner explanation

Instead of clicking through the AWS website to create a database, a user directory and some permissions, we wrote down what we want in files. A tool called Terraform reads those files and builds exactly that. If something gets deleted, running one command rebuilds it identically — and anyone can read the files to see what exists, which is much better than trying to remember what somebody clicked.

## AWS explanation

Created by this phase: **AWS Budgets** (spend alerting), **DynamoDB** (the events table, on-demand, two indexes, 30-day TTL, point-in-time recovery), **Cognito** (user pool, app client, two groups), **IAM** (four execution roles, each scoped to one action set on one resource), **S3** (static site bucket, public *read* only, no data in it), **CloudWatch Logs** (four groups, 7-day retention).

Everything is in **eu-west-3 (Paris)** except the budget, which is global and queried through `us-east-1`.

## How the pieces connect

The table ARN flows into the IAM policies, which is how Terraform knows to create the table first. The Cognito pool ARN flows into the auth role's policy. Everything a later phase needs — table name, pool ID, client ID, issuer URL, role ARNs, bucket name — comes out of `terraform output`, which is the handover to Phase 5.

## Testing

| Check | Status |
|---|---|
| Structural validation of all 10 `.tf` files: every `var.`, `local.` and resource reference resolves; braces balanced; both providers declared | **Executed — passed.** 26 resources, 8 data sources, 7 variables. One intentional finding: `ttl_days` is declared but unused until Phase 5 passes it to the Lambdas |
| `terraform fmt -check`, `terraform init`, `terraform validate` | **Not executed.** Terraform is not installed where these files were written, and the container's network blocks the download. **You will be the first to run these** — step 0 of the deployment guide |
| `scripts/verify-prices.sh` | **Not executed** — needs AWS credentials. Syntax checked with `bash -n`: passed |
| Anything in AWS | **Not deployed.** Nothing to test yet |

## Documentation updated

Four new deployment documents, one new learning document, one script. `docs/cost/01-cost-model.md` still carries its `[unverified]` tags — those are cleared by running the verification script, not by assertion.

## Problems / open items

| Item | Who |
|---|---|
| `terraform validate` has never been run. Expect to fix something on the first pass; that is normal | Whoever deploys |
| **Still open since Phase 2:** the AWS account's plan and creation date (risk C5 — a free-plan account closes at six months or credit depletion) | You |
| The Billing console may be restricted depending on the account plan; if `aws budgets describe-budgets` fails with AccessDenied, the cost evidence has to take a different form and the report must say so | Whoever deploys |
| Confirm the ownership split in `06-team-assignment.md` | Team |

## Next phase

**Phase 5 — Backend and API.** The four Lambda handlers (`auth`, `ingest`, `query`, `stats`), the shared validation and response helpers, the HTTP API with its JWT authorizer wired to the Cognito pool from this phase, and the Terraform to deploy them. Phase 5 is where `terraform output` from Phase 4 gets consumed — so deploy this phase, or at least run `plan`, before we start.
