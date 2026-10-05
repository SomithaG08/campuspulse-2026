# Phase 7 — Authentication and Security (complete, pending your review)

> **Still nothing deployed.** This phase was an audit of what Phases 4-6 actually built, plus the documentation of it. Almost no new code, by design: the security mechanisms were built into the architecture rather than added at the end.

## What we built

An audit with findings, a threat model that distinguishes what exists from what does not, and the two security learning documents.

## Files created

| File | What it is |
|---|---|
| `docs/security/01-threat-model.md` | All seven threats from the brief. Every control carries one of four status words — **Implemented / Configured / Planned / Not verified** — with the file that proves it, and a closing list of what we do *not* claim |
| `docs/learning/08-cognito-authentication.md` | Authentication vs authorization, what a JWT really is, the login flow, the three checks, our pool configuration and why each setting is set |
| `docs/learning/10-iam-security.md` | Least privilege, blast radius, how to read a policy, what we verified, and the honest caveat about the deployment identity |
| `docs/security/README.md` | Index |

## The audit: method and findings

**IAM reviewed against the code, not against intentions.** I listed every AWS API call each handler makes and compared it with every action its policy grants:

| Function | Calls | Granted | Verdict |
|---|---|---|---|
| `cp-health` | none | logs only | exact |
| `cp-auth` | `initiate_auth` | `cognito-idp:InitiateAuth` on our pool | exact |
| `cp-ingest` | `put_item` | `dynamodb:PutItem`, one table | exact — cannot read |
| `cp-query` | `query` | `dynamodb:Query`, table + indexes | exact — cannot write |
| `cp-stats` | `query` | `dynamodb:Query`, table + indexes | exact — cannot write |

No function is granted anything it does not call, and none calls anything it is not granted.

**Scans confirmed:**

- **No `Action: "*"`, no `Resource: "*"`** anywhere in `iam.tf`; every statement names a specific ARN.
- **`dynamodb:Scan` granted to nobody.** The only occurrence of the word is a comment. So the "no Scan" rule is enforced by permissions as well as by a test.
- **No credentials in the repository.** A scan for `AKIA[0-9A-Z]{16}`, `aws_secret_access_key`, `aws_access_key_id =`, private-key headers, and hardcoded password or token literals across every `.py`, `.tf`, `.md`, `.sh`, `.html` and `.js` file found nothing. The only mentions of access keys are instructions telling you never to commit them.
- **No credential material is logged.** All 12 log calls were read individually: `auth.py` logs the username and Cognito's error code on a failed login, never the password, never the token, never the raw exception.
- `.gitignore` covers `.env`, `credentials`, `.aws/`, `*.tfvars` and `*.tfstate` — and was written in Phase 3, before the first commit.

**One deliberate trade-off surfaced and documented:** `logs:CreateLogGroup` is withheld from every role. Terraform creates all five log groups with 7-day retention, so a function cannot create one with "never expire" — but a function whose group went missing would write no logs rather than create one. Controlled condition, chosen knowingly, and now written down instead of discovered at the oral.

## The honest caveat, written into the docs

The human running `terraform apply` uses a broad, near-administrator IAM user. That is a convenience for a course project, and the report says so in those words. It is a **different claim** from runtime least privilege, and the documents are careful not to let one imply the other. The defensible sentence is: *the deployment identity is broad for convenience; every runtime component is scoped to one action set on one resource.*

## Testing

| Check | Status |
|---|---|
| IAM policies vs actual code calls, per function | **Executed — exact match, no excess, no gaps** |
| Wildcard actions/resources scan | **Executed — none found** |
| `dynamodb:Scan` grant scan | **Executed — granted nowhere** |
| Credential scan across the whole repo | **Executed — nothing found** |
| Log-leak review of all 12 log calls | **Executed — no credential material logged** |
| 113 unit tests still passing | **Executed — 113 passed** |
| Any control observed working against live AWS | **Not verified — nothing deployed** |

## Problems / open items

| Item | Who |
|---|---|
| Every control is **Configured** or **Implemented**, none is **Verified** — that needs a deployment and the 401/403/200 evidence | Whoever deploys |
| `aws iam simulate-principal-policy` output is the best least-privilege evidence available; the command is in the IAM doc, ready to run and screenshot | Meha |
| **Still open:** the AWS account's plan and creation date (risk C5) | You |
| Residual risks accepted and documented: a stolen token works until it expires (1 h); a flood of *valid* requests consumes credits up to the throttle ceiling | — |

## Next phase

**Phase 8 — Simulator.** `simulator.py` with `--interval` and `--number-of-events`, Cognito login as the device user, realistic readings per building and room, a `--force-alert` mode so the demo alert fires on cue, and the simulator learning document. It is the last piece before the dashboard, and it is the piece that makes the demo legible.
