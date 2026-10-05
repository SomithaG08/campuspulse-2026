# IAM and least privilege — explained

**Owner:** Meha · **Read after:** `08-cognito-authentication.md` · **Code:** `infrastructure/terraform/iam.tf`

---

## 1. What IAM is

**Level 1 — simple.** The master key cabinet. Every worker gets a key cut for exactly one door, and only while they are on shift. Nobody carries the key to everything.

**Level 2 — technical.** Identity and Access Management controls which identities may perform which actions on which resources. Our Lambdas assume **execution roles**; each role carries a **policy** listing allowed actions against specific resource ARNs. Credentials are temporary and rotated automatically. **Everything is denied unless explicitly allowed.**

**Cognito and IAM are not the same thing, and the report must not blur them:** Cognito decides which *humans* may use the API. IAM decides which *AWS resources* our components may touch. A caller could hold a perfectly valid `ops` token and still get `AccessDenied` if the function tried something its role forbids.

## 2. The one idea: blast radius

The useful question is not "is it secure?" — it is **"if this component is compromised, what exactly does the attacker get?"**

That answer is written entirely by the component's IAM policy. Which means least privilege is not a virtue you add; it is the number you are choosing when you write the policy.

```text
ONE function, ONE broad role              FIVE functions, FIVE narrow roles
───────────────────────────               ─────────────────────────────────
  a bug in the public endpoint              a bug in the public endpoint
            ↓                                          ↓
  read + write + delete EVERYTHING          write one table. Cannot read.
  every student service request              Cannot delete. Cannot list users.
```

Same bug. Two completely different incidents. The difference is a file.

## 3. Our five roles

Audited in Phase 7 by listing every AWS call in the code and comparing it with every action granted:

| Function | AWS calls it makes | Policy grants | Cannot |
|---|---|---|---|
| `cp-health` | none | logs only | touch anything |
| `cp-auth` | `initiate_auth` | `cognito-idp:InitiateAuth` on our pool | read the database, list users |
| `cp-ingest` | `put_item` | `dynamodb:PutItem` on one table | **read a single stored event** |
| `cp-query` | `query` | `dynamodb:Query` on table + indexes | **write or delete anything** |
| `cp-stats` | `query` | `dynamodb:Query` on table + indexes | **write or delete anything** |

**The `cp-ingest` row is the sentence to say at the oral.** It is the function exposed to the internet. An attacker who found a flaw in it could add junk events — and could not read one student's service request, because its role has no read permission at all.

## 4. Reading a policy

```hcl
data "aws_iam_policy_document" "ingest" {
  statement {
    effect    = "Allow"
    actions   = ["dynamodb:PutItem"]            # exactly one verb
    resources = [aws_dynamodb_table.events.arn] # exactly one thing
  }
}
```

Four parts: **effect** (Allow or Deny), **action** (the API call), **resource** (the ARN), and optional **conditions**.

The anti-pattern, which appears in a great many tutorials:

```hcl
actions   = ["dynamodb:*"]   # every DynamoDB operation that exists
resources = ["*"]            # on every table in the account
```

That is the policy people write to "make it work", intend to tighten later, and never do. If you see it in our repo, it is a bug.

## 5. What we verified, and what we found

A scan of `iam.tf` this phase confirmed:

- **No `Action: "*"` and no `Resource: "*"`** anywhere.
- Every statement scoped to a **named ARN** — the one table, the one pool, our own log groups.
- **`dynamodb:Scan` granted to nobody.** If someone added a `Scan` to the code later it would fail with `AccessDenied` rather than quietly working and getting slower every week. The design rule is enforced by permissions, not only by a comment.
- **`logs:CreateLogGroup` deliberately withheld.** Terraform creates all five log groups with 7-day retention; a function that could create its own would create it with retention "never expire", which is a slow cost leak.

The last one is a **trade-off we chose knowingly**: if a log group were missing, that function would write no logs rather than create one. All five are created by Terraform, so the condition is controlled — and being able to explain a deliberate trade-off is better than having no trade-offs to explain.

## 6. No credentials, anywhere

Our code contains no AWS keys. Not in a config file, not in an environment variable, not in the repository.

```python
_table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
```

That line has no credentials because it needs none. At invocation the function assumes its role and receives temporary credentials that AWS rotates automatically. If you ever find yourself typing `aws_access_key_id=` into a handler, stop — something has gone wrong.

**What this prevents:** the single most common way student cloud projects get compromised is a long-lived access key committed to a public repository, found by an automated scanner within minutes, and used to mine cryptocurrency on someone's card. Roles remove the key that could be committed.

## 7. The honest caveat

The human who runs `terraform apply` uses a broad IAM user, close to administrator. That is a pragmatic choice for a course project, and the report says so in exactly those words.

**It is a different thing from runtime least privilege**, and the report must not use one to claim the other. The defensible version of the sentence is: *"the deployment identity is broad for convenience; every runtime component is scoped to a single action set on a single resource."* Both halves are true, and the second is the one the security criterion is about.

## 8. Verify it yourself

```bash
# What can cp-ingest actually do?
aws iam list-role-policies --role-name campuspulse-dev-ingest-role
aws iam get-role-policy --role-name campuspulse-dev-ingest-role \
  --policy-name campuspulse-dev-ingest-policy

# Prove the wall exists: ask whether ingest's role could read the table
aws iam simulate-principal-policy \
  --policy-source-arn $(aws iam get-role --role-name campuspulse-dev-ingest-role \
                        --query Role.Arn --output text) \
  --action-names dynamodb:Query dynamodb:PutItem dynamodb:Scan \
  --resource-arns $(aws dynamodb describe-table --table-name campuspulse-dev-events \
                    --query Table.TableArn --output text) \
  --query 'EvaluationResults[].{Action:EvalActionName,Decision:EvalDecision}'
```

Expect `PutItem: allowed`, `Query: implicitDeny`, `Scan: implicitDeny`. **Screenshot that output** — it is direct, machine-generated evidence of least privilege, which is far stronger than a paragraph asserting it.

---

## Can you explain this?

1. What is the difference between what Cognito controls and what IAM controls?
2. What does "blast radius" mean, and what sets it for `cp-ingest`?
3. Why does `cp-ingest` have no read permission, when reading would be convenient?
4. Where are our AWS credentials stored?
5. Is our deployment identity least privilege? Answer honestly.

### Answers

1. Cognito decides which humans may call the API. IAM decides which AWS resources our components may touch. A valid `ops` token still gets `AccessDenied` if the function attempts something its role forbids.
2. What an attacker obtains after compromising one component. For `cp-ingest` it is exactly `dynamodb:PutItem` on one table — write junk events, read nothing.
3. Because it is the internet-facing function, so it is the one most likely to be attacked. Convenience for us is also capability for an attacker; it does not need to read, so it cannot.
4. Nowhere. Each function assumes its IAM role at invocation and receives temporary, auto-rotated credentials. There is no key in the code to leak or commit.
5. No. The human deployment identity is broad, close to administrator, for convenience on a course project — and the report says so. Runtime least privilege is a separate claim, and that one is true and verifiable.
