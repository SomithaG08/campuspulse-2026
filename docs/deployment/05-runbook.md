# Deployment Runbook — empty account to working demo

One ordered sequence. Roughly **90 minutes** the first time, 10 the second.

Do it **in this order**. Each step has a checkpoint; if a checkpoint fails, stop and fix it — later steps assume it passed.

> **Read `00-COST-WARNING.md` first.** Nothing in this runbook bills by the hour, which is why you can walk away afterwards — but that is only true while the never-create list is respected.

---

## Before you start (15 min)

| Step | Checkpoint |
|---|---|
| Install AWS CLI v2, Terraform ≥1.5, Python ≥3.11 | `aws --version && terraform version && python --version` |
| Create the `campuspulse-deploy` IAM user, configure credentials | `aws sts get-caller-identity` shows your account |
| **Record the account's plan and creation date** in `docs/evidence/cost/` | You know whether the six-month free-plan clock threatens your presentation date |
| Decide who owns the Terraform state. **One person.** | Everyone else knows not to run `apply` |
| `cp terraform.tfvars.example terraform.tfvars`, set `notification_email` | The file exists and is gitignored |

**Stop condition:** if `aws sts get-caller-identity` fails, nothing else will work.

---

## Stage 1 — Foundation (20 min)

```bash
cd infrastructure/terraform
terraform fmt -check && terraform init && terraform validate   # ← first time anyone has run this
terraform plan -out=tfplan
```

**Read the plan.** Three things: about 61 resources to add; no `nat_gateway`, `instance`, `db_instance` or `load_balancer` anywhere; every ARN says `eu-west-3`.

```bash
terraform apply tfplan
```

**Checkpoint — the budget, before anything else:**

```bash
aws budgets describe-budgets --account-id $(aws sts get-caller-identity --query Account --output text) --region us-east-1
```

📸 **Screenshot the Budgets console now.** Requirement C2 is mandatory and this is far easier today than in week eleven.

```bash
terraform output        # save all of it - every later stage needs it
```

**Stop condition:** no budget, no further deploying. If the Billing console is restricted on this account plan, record that fact and use the fallback in the cost model instead — but record it deliberately, do not just skip it.

---

## Stage 2 — Users (10 min)

Three users, created by CLI because a password in a `.tf` file is a password in Git.

```bash
POOL=$(terraform output -raw cognito_user_pool_id)

for u in "ops@northbridge.edu:ops" "staff@northbridge.edu:staff" "device@campuspulse.local:ops"; do
  USER="${u%%:*}"; GROUP="${u##*:}"
  aws cognito-idp admin-create-user --user-pool-id $POOL --username "$USER" \
    --message-action SUPPRESS \
    --user-attributes Name=email,Value="$USER" Name=email_verified,Value=true
  aws cognito-idp admin-set-user-password --user-pool-id $POOL --username "$USER" \
    --password '<a strong password>' --permanent
  aws cognito-idp admin-add-user-to-group --user-pool-id $POOL --username "$USER" --group-name "$GROUP"
done
```

**Checkpoint:** `aws cognito-idp list-users --user-pool-id $POOL --query 'Users[].[Username,UserStatus]' --output table` — three users, all `CONFIRMED`.

Passwords need 12+ characters with upper, lower, number and symbol. Put them wherever the team keeps shared secrets — **never in the repo, a slide, or a screenshot.**

---

## Stage 3 — Verify the foundation (5 min)

```bash
bash scripts/verify-deployment.sh
```

Twenty-odd checks: table active and on-demand, both indexes, TTL on, **PITR on**, both groups, all five functions, no log group set to never expire, four alarms, a budget, and — importantly — **no EC2, no RDS, no NAT Gateway running**.

📸 **Screenshot this output.** It is the cheapest and most convincing evidence in the project: every line corresponds to a claim the report makes.

**Stop condition:** any FAIL. Fix before continuing.

---

## Stage 4 — Dashboard (10 min)

```bash
bash scripts/deploy-dashboard.sh
```

**Checkpoint:** open the URL it prints. You should see the sign-in form, not an error about `config.js`.

---

## Stage 5 — Prove it works (20 min)

```bash
export CAMPUSPULSE_API=$(terraform -chdir=infrastructure/terraform output -raw api_endpoint)
export OPS_USER=ops@northbridge.edu     OPS_PASSWORD='...'
export STAFF_USER=staff@northbridge.edu STAFF_PASSWORD='...'

python tests/api/run_api_tests.py
```

**Checkpoint: 45 passed, 0 failed**, and `docs/evidence/api-test-results.json` is overwritten with a real run. **Commit that file.**

Then the human-visible path:

```bash
export CAMPUSPULSE_USER=device@campuspulse.local
export CAMPUSPULSE_PASSWORD='...'

python simulator/simulator.py -n 60 --interval 2      # watch the dashboard fill
python simulator/simulator.py --force-alert -n 3      # watch a red alert appear
```

📸 Dashboard with data · 📸 a red alert · 📸 the DynamoDB item · 📸 the CloudWatch log line for that `request_id`.

---

## Stage 6 — Operational evidence (20 min)

The parts people forget until the night before.

**Drive an alarm into ALARM on purpose:**

```bash
python simulator/simulator.py --force-alert --interval 0.5 -n 30
sleep 300
aws cloudwatch describe-alarms --alarm-names campuspulse-dev-alert-burst \
  --query 'MetricAlarms[].{State:StateValue,Reason:StateReason}'
```

📸 the alarm in ALARM · 📸 the CloudWatch dashboard with real curves.

**Rehearse the restore — this is the DR requirement, and it must actually happen:**

```bash
aws dynamodb restore-table-to-point-in-time \
  --source-table-name campuspulse-dev-events \
  --target-table-name campuspulse-dev-events-restoretest \
  --use-latest-restorable-time
```

Time it. Note the number — **that is your measured RTO**, not a guess. Then delete the restored table so it does not sit there consuming storage.

📸 the restore in progress · 📸 the restored table · note the elapsed minutes.

**Record the cost:** 📸 the credit balance, with the date.

---

## Stage 7 — The test that matters most (next day)

**A teammate who did not write the deployment guide deploys from it, into a clean state, using only these documents.**

That is the real test of requirement I4 — "a reproducible deployment process" — and the only way to discover what the guide leaves out. Whatever they get stuck on is a gap in the documentation, not a failing of theirs: fix the doc, note it in the report's Implementation Process section.

---

## Afterwards

Everything idles at zero. Leave it running until after the presentation, then follow `cleanup.md`.

**Habit until then:** check the credit balance at the end of each session. A balance that moves while nobody is working is the early warning for every cost hazard in this project.
