# Disaster recovery — explained

**Read after:** `07-dynamodb-explained.md` · **Code:** `infrastructure/terraform/dynamodb.tf`

---

## 1. The two numbers everything turns on

**RPO — Recovery Point Objective.** How much data you can afford to lose, measured in time. "RPO 5 minutes" means after a disaster you may be missing the last five minutes.

**RTO — Recovery Time Objective.** How long you can afford to be down. "RTO 30 minutes" means you are back within half an hour.

```text
        disaster
            │
  ──────────┼──────────────────────►  time
      ◄─────┤                  ├────►
       RPO  │                  │  RTO
   data you │                  │ how long until
   may lose │                  │ you are back
```

They are **business decisions, not technical ones**. A bank's RPO is zero and it pays enormously for that. A campus dashboard can lose five minutes of temperature readings without anyone noticing.

Every student project gets asked these two. Know yours and know *why*.

## 2. What could actually go wrong

Ranked by how likely it is, which is not how dramatic it is:

| Scenario | Likelihood | Our answer |
|---|---|---|
| Someone deletes or corrupts data by mistake | **Most likely** | PITR restore to just before the mistake |
| A bad deploy breaks the system | Likely | `terraform apply` the previous commit |
| The table is deleted | Possible | PITR, within the retention window |
| **The AWS account closes** (free plan, 6 months) | **Real and scheduled** | See §6 — this is our biggest one |
| An Availability Zone fails | Rare | Automatic: managed services replicate across AZs |
| A whole region fails | Very rare | **We do not survive this, and we say so** |

Notice the shape: the likeliest disaster is a person, not infrastructure. Backups mostly protect you from yourself.

## 3. Our backup mechanism

**DynamoDB point-in-time recovery (PITR)**, enabled in `dynamodb.tf`.

It continuously records changes and lets you restore the table to **any second within the retention window** (35 days). Not a nightly snapshot — any second.

```hcl
point_in_time_recovery { enabled = true }
```

One line, because the hard part is done by the service. The restore creates a **new table**; it never overwrites the existing one, which means a restore is a safe thing to rehearse.

**Also protecting us, though not usually called backup:**

| Thing | Protects against |
|---|---|
| Terraform in Git | Infrastructure loss — the whole stack is rebuildable from code |
| Lambda code in Git | Code loss |
| Cognito users | **Not backed up** — three demo users, recreated by two CLI commands |
| The dashboard | Rebuilt by `deploy-dashboard.sh` |
| TTL, 30 days | Keeps the table small, so restores stay fast |

## 4. Our RPO and RTO, with reasons

| | Target | Why |
|---|---|---|
| **RPO** | **≈ 0, bounded by PITR's granularity** | PITR restores to any second, so almost nothing is lost. This is a property of the service, not an achievement of ours |
| **RTO** | **Target: under 60 minutes.** Measured: ___ | Restore time depends on table size; ours is tiny. **The blank is deliberate — it gets filled from a real rehearsal** |

**Do not write an RTO you have not measured.** Phase 12's runbook has the rehearsal: restore the table, time it, record the number. "We measured 18 minutes" is a finding; "our RTO is about 20 minutes" is a guess wearing a number's clothes.

## 5. The restore procedure

```bash
# 1. Restore to a NEW table - the original is untouched
aws dynamodb restore-table-to-point-in-time \
  --source-table-name campuspulse-dev-events \
  --target-table-name campuspulse-dev-events-restored \
  --use-latest-restorable-time        # or --restore-date-time 2026-10-05T14:00:00Z

# 2. Wait, and time it
aws dynamodb describe-table --table-name campuspulse-dev-events-restored \
  --query 'Table.TableStatus'

# 3. Verify the data is really there
aws dynamodb scan --table-name campuspulse-dev-events-restored --max-items 5

# 4. Point the functions at it, if this is a real recovery
#    (change TABLE_NAME in terraform.tfvars and apply)

# 5. Clean up the test table so it does not sit there consuming storage
```

**Step 5 matters.** A forgotten restored table is exactly the kind of quiet storage cost the cost model warns about.

## 6. The disaster we are actually most likely to have

Not an AZ failure. **The account closing.**

Under the AWS Free Tier rules current since July 2025, a free-plan account ends **six months after sign-up or when the credits run out, whichever comes first** — and AWS then closes it, making the resources inaccessible (retained 90 days, recoverable only by upgrading to the paid plan).

That is a disaster with a **date on it**, which is unusual and makes it manageable:

1. Know the date. (Still open — risk C5.)
2. Everything is reproducible from Git, so rebuilding in another account is a `terraform apply`, not a rewrite.
3. **Export the evidence out of AWS as it is collected.** Screenshots, logs and test results live in the repository, not only in the console.

Point 3 is the real mitigation, and it costs nothing to do early.

## 7. What we do NOT claim

- **No multi-region anything.** A region failure takes us down. We are single-region and we say so.
- **No automated failover.** Recovery is a human running documented commands.
- **No Cognito user backup.** Three demo users; recreating them is two commands.
- **No tested recovery of the whole stack** — only of the data. Rebuilding the stack is `terraform apply`, which we will have done several times, but a full disaster rehearsal is not in scope.

Listing these is the point. Claiming multi-region DR that does not exist is the single most common way a student report loses credibility, because it takes one question to expose.

---

## Can you explain this?

1. What are RPO and RTO, in one sentence each?
2. What is our backup mechanism, and what makes it better than a nightly snapshot?
3. What is the most likely disaster for this project?
4. Why is our RTO written with a blank in it?
5. What disaster do we explicitly not survive?

### Answers

1. RPO is how much data you can afford to lose, measured in time. RTO is how long you can afford to be down.
2. DynamoDB point-in-time recovery. It continuously records changes, so you can restore to *any second* in the last 35 days — a nightly snapshot can only return you to the last midnight, losing up to a day.
3. Not infrastructure failure — a person deleting something, or the AWS account closing at the six-month free-plan boundary. The second is a disaster with a date on it, which is why knowing that date matters.
4. Because it has not been measured yet. A restore rehearsal fills it with a real number; until then writing one would be inventing evidence.
5. A full region failure. We are single-region, there is no failover, and we state that plainly rather than claiming multi-region DR we have not built.
