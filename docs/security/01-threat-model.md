# Threat Model — CampusPulse 2026

Covers the seven threats the project brief names. Every row carries a status word with a fixed meaning, and nothing is claimed beyond it:

| Status | Means |
|---|---|
| **Implemented** | Code exists that does this, and it is tested |
| **Configured** | Infrastructure declares it; it takes effect on deployment |
| **Planned** | Designed and written down. **Not built.** |
| **Not verified** | Exists in code or config but nobody has observed it working |

Everything below is **Not verified against a live deployment** — nothing has been deployed yet. That is stated once here rather than repeated in every row.

---

## T1 · Unauthorized access to campus data

**What an attacker tries:** call `/events`, `/stats` or `/alerts` with no token, an expired token, or a token from a different Cognito pool.

| Control | Status | Where |
|---|---|---|
| Every data route requires a JWT; API Gateway's authorizer validates signature, issuer, audience and expiry **before our code runs** | Configured | `apigateway.tf` — `aws_apigatewayv2_authorizer.cognito` |
| The authorizer accepts only tokens from our pool, for our client | Configured | `jwt_configuration.issuer`, `.audience` |
| Tokens expire after 60 minutes | Configured | `cognito.tf` — `id_token_validity` |
| HTTPS only; there is no HTTP listener to downgrade to | Configured | API Gateway has no plaintext endpoint |

**Residual risk:** a stolen, unexpired token works until it expires. Mitigation would be shorter lifetimes or revocation on sign-out — **Planned**, not built. Worth saying plainly: an hour is a deliberate trade-off against usability, not an oversight.

## T2 · Credential compromise

**What an attacker tries:** find AWS keys in the repository, or brute-force a user password.

| Control | Status | Where |
|---|---|---|
| **No AWS credentials exist in the code at all.** Functions assume an IAM role and receive temporary, auto-rotating credentials | Implemented | every handler; verified by scan |
| Passwords are never stored, hashed, compared or logged by our code — Cognito does all of it | Implemented | `handlers/auth.py` |
| Password policy: 12+ characters, upper, lower, number, symbol | Configured | `cognito.tf` — `password_policy` |
| `prevent_user_existence_errors` on, and the same message for wrong-password and unknown-user, so the login form cannot be used to discover which emails have accounts | Configured + Implemented | `cognito.tf`; `auth.py` returns one message for both |
| No client secret in the browser app — a secret shipped to a client is not a secret | Configured | `generate_secret = false` |
| `.gitignore` excludes `.env`, `credentials`, `.aws/`, `*.tfvars`, `*.tfstate` **before the first commit** | Implemented | `.gitignore` |

**Verified this phase:** a scan for `AKIA[0-9A-Z]{16}`, `aws_secret_access_key`, `aws_access_key_id =`, private-key headers and hardcoded password or token literals across every `.py`, `.tf`, `.md`, `.sh`, `.html` and `.js` file found **nothing**. The only mentions of access keys anywhere are instructions in the deployment guide telling you never to commit them.

## T3 · Malicious or malformed event submission

**What an attacker tries:** oversized payloads, injection strings, absurd values, or events backdated to hide in partitions nobody queries.

| Control | Status | Where |
|---|---|---|
| Every field validated: type, enum membership, string length, unit match, finite numeric value | Implemented | `common/validation.py`, 30 tests |
| Body capped at 4 KB | Implemented | `MAX_BODY_BYTES` |
| Values must be **plausible**, not merely numeric — 4000 °C is rejected | Implemented | `plausible` ranges per type |
| Timestamps must be ISO-8601 UTC, no more than 24 h old and no more than 5 minutes ahead | Implemented | `_check_window` |
| Building and room must exist on the real campus | Implemented | `campus_config` lookups |
| **The client's `severity` is discarded and recomputed server-side** | Implemented | `validation.py` strips it, `rules.py` decides |
| Injection is structurally unavailable: no SQL, and DynamoDB calls use parameterised expression values, never string concatenation | Implemented | `common/queries.py` |

**The `severity` control is the one to highlight.** Without it, anyone able to write an event could mark a critical overcrowding as normal and make it vanish from the alerts list — a data-integrity attack that needs no credentials beyond ordinary write access.

## T4 · Excessive permissions

**What an attacker gains:** whatever the compromised component was allowed to do.

Audited this phase by listing every AWS call in the code and comparing it with every action each policy grants:

| Function | Calls it makes | Policy grants | Verdict |
|---|---|---|---|
| `cp-health` | none | logs only | exact |
| `cp-auth` | `initiate_auth` | `cognito-idp:InitiateAuth` on our pool | exact |
| `cp-ingest` | `put_item` | `dynamodb:PutItem` on one table | exact — **cannot read** |
| `cp-query` | `query` | `dynamodb:Query` on the table + indexes | exact — **cannot write** |
| `cp-stats` | `query` | `dynamodb:Query` on the table + indexes | exact — **cannot write** |

| Control | Status |
|---|---|
| No `Action: "*"` and no `Resource: "*"` anywhere | Configured — verified by scan |
| Every statement scoped to a named ARN | Configured |
| `dynamodb:Scan` granted to nobody; a future `Scan` would fail with `AccessDenied` rather than work slowly | Configured |
| `logs:CreateLogGroup` deliberately **not** granted — Terraform creates the groups with 7-day retention, so a function cannot create one with "never expire" | Configured |

**Trade-off we chose knowingly:** because `logs:CreateLogGroup` is withheld, a function whose log group is missing writes no logs instead of creating one. All five groups are created by Terraform, so this is a controlled condition, and the alternative (letting functions create groups) reintroduces the retention cost leak.

**Honest note on the deployment identity:** the human running `terraform apply` uses a broad IAM user. That is a convenience for a course project and is written as such in the deployment guide. It is a different thing from the runtime least privilege above, and the report should not blur the two.

## T5 · Data exposure

| Control | Status | Where |
|---|---|---|
| Encryption in transit everywhere (HTTPS, and AWS-internal service calls) | Configured |
| Encryption at rest by default on DynamoDB and S3 | Configured | AWS-managed keys |
| The API returns an explicit field list, so `pk`, `sk`, `gsi1pk` and `expires_at` never leave the system | Implemented | `query.py` — `PUBLIC_FIELDS` |
| 500 responses are deliberately vague; exception text never reaches the caller | Implemented | `responses.server_error` |
| No credential material in any log line | Implemented — verified by scan of all 12 log calls |
| Events self-delete after 30 days | Configured | DynamoDB TTL |

**The public S3 bucket is a deliberate, bounded exposure.** It serves only `index.html`, CSS and JavaScript — the page shell. It contains no campus data, and the bucket policy allows `s3:GetObject` only: nobody can list, write or delete. Every piece of data the page displays is fetched from the API, which refuses without a token. The alternative, CloudFront with a signed origin, buys nothing for one browser in one room.

## T6 · API abuse and cost attacks

**What an attacker tries:** flood the API to run up the bill — on a fixed 100-credit budget, a denial-of-wallet attack is more dangerous than denial of service.

| Control | Status | Where |
|---|---|---|
| Stage throttling: 20 requests/second steady, 40 burst | Configured | `apigateway.tf` |
| Invalid tokens are rejected at the edge, so a token flood invokes no Lambda and costs nothing | Configured | JWT authorizer |
| `limit` capped at 200; `/stats` capped at 10 pages | Implemented | `queries.py`, 24 tests |
| Budget alert at 50 %, 80 % and forecast 100 %, with credits excluded so it tracks real usage | Configured | `budget.tf` |
| Nothing in the architecture bills by the hour | — | the architecture itself |

**Residual risk:** a sustained flood of *valid* requests from a compromised account would consume credits up to the throttle ceiling. The budget alert is the detection; manual response is the remedy. Automatic shutdown on a budget breach is **Planned**, not built.

## T7 · Misconfiguration

**The likeliest way a student project actually gets breached** — not a clever attack, but a wrong setting nobody noticed.

| Control | Status | Where |
|---|---|---|
| All infrastructure is Terraform: reviewable, diffable, reproducible, and `terraform plan` shows drift | Configured |
| S3 public-ACL blocks stay on; only the bucket policy is unblocked | Configured | `s3.tf` |
| `BucketOwnerEnforced` — ACLs disabled entirely | Configured |
| Log retention set explicitly, never left at "never expire" | Configured |
| Cognito **Essentials** tier pinned (Plus has no free tier) | Configured |
| No public sign-up: `allow_admin_create_user_only` | Configured | `cognito.tf` |
| Structural validation of all Terraform on every change | Implemented | run each phase |
| `terraform validate` | **Not executed** — Terraform not installed where these files were written |

---

## The security model in three sentences

Data crosses a trust boundary in exactly three places, and each has its own control: **API Gateway's JWT authorizer** decides whether we know who you are (401), **the Lambda's group check** decides whether your role permits this route (403), and **IAM** decides whether that function may touch that resource at all (`AccessDenied`). The three are independent — defeating one leaves the other two standing. Every member of the team should be able to name all three in order.

## What we are not claiming

- No penetration testing has been done.
- No WAF, no DDoS protection beyond API Gateway's throttling.
- No multi-region anything.
- No token revocation before expiry.
- No automated secret rotation (there are no secrets to rotate).
- `terraform validate` has not been run; nothing has been deployed.

Listing these is deliberate. A threat model that claims complete coverage is the least credible document a team can submit.
