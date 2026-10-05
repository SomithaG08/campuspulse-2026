# Deploying the Foundation (Phase 4)

What this creates: the budget alert, the DynamoDB table, the Cognito user pool and its two groups, four IAM roles, the S3 site bucket, and four CloudWatch log groups.

What it does **not** create: Lambda functions and the API. Those arrive in Phase 5, when the code they run exists.

**Read `00-COST-WARNING.md` first.** Prerequisites: `01-prerequisites.md`.

---

## Step 0 — Validate before you create anything

```bash
cd infrastructure/terraform
terraform fmt -check
terraform init
terraform validate
```

`init` downloads the AWS and random providers into `.terraform/` (gitignored). `validate` checks syntax and references without touching AWS.

> **Note:** these files passed a structural check (every variable, local and resource reference resolves; braces balanced; providers declared) but **`terraform validate` has not been run by anyone yet** — Terraform was not installed where they were written. You are the first. If `validate` reports an error, fix it and note it here; that is ordinary, not a failure.

## Step 1 — Look at the plan. Actually look at it.

```bash
terraform plan -out=tfplan
```

Read the output. You are checking for three things:

1. **The count.** From an empty account the full stack is about **61 resources** to add, 0 to change, 0 to destroy. (The foundation described on this page is about 26 of them.)
2. **Nothing hourly.** Search the plan for `nat_gateway`, `instance`, `db_instance`, `load_balancer`. Finding any of them means something is wrong.
3. **The region.** Every ARN should say `eu-west-3`.

`terraform plan` makes no changes. Run it as often as you like.

## Step 2 — Apply

```bash
terraform apply tfplan
```

Takes roughly a minute. If it fails halfway, that is normal and recoverable: fix the cause and run `plan` and `apply` again. Terraform reconciles to the desired state; it does not need a clean slate.

## Step 3 — Confirm the budget exists FIRST

Before touching anything else:

```bash
aws budgets describe-budgets \
  --account-id $(aws sts get-caller-identity --query Account --output text) \
  --region us-east-1
```

You should see `campuspulse-dev-monthly` with a $10 limit.

**Screenshot the Budgets console page now** and save it to `docs/evidence/cost/`. This is mandatory evidence for requirement C2, and it is far easier to capture today than to reconstruct in week eleven.

> Budgets are a global service, so the CLI call uses `us-east-1` even though everything else is in `eu-west-3`. This surprises people; it is not a mistake.

## Step 4 — Capture the outputs

```bash
terraform output
```

Save these — Phase 5 needs all of them:

```text
region                = "eu-west-3"
dynamodb_table_name   = "campuspulse-dev-events"
cognito_user_pool_id  = "eu-west-3_XXXXXXXXX"
cognito_client_id     = "XXXXXXXXXXXXXXXXXXXXXXXXXX"
cognito_issuer_url    = "https://cognito-idp.eu-west-3.amazonaws.com/eu-west-3_XXXXXXXXX"
site_bucket_name      = "campuspulse-dev-site-XXXXXXXX"
site_url              = "http://campuspulse-dev-site-XXXXXXXX.s3-website.eu-west-3.amazonaws.com"
```

None of these are secrets — they are identifiers, not credentials — but do redact the account ID from screenshots out of habit.

## Step 5 — Verify each piece yourself

Do not trust "apply complete". Check.

```bash
# Table exists, on-demand, PITR on
aws dynamodb describe-table --table-name campuspulse-dev-events \
  --query 'Table.{Status:TableStatus,Billing:BillingModeSummary.BillingMode,Indexes:GlobalSecondaryIndexes[].IndexName}'
aws dynamodb describe-continuous-backups --table-name campuspulse-dev-events \
  --query 'ContinuousBackupsDescription.PointInTimeRecoveryDescription.PointInTimeRecoveryStatus'

# Both groups exist
aws cognito-idp list-groups --user-pool-id <pool-id> --query 'Groups[].GroupName'

# Log retention is 7 days, not "never"
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/campuspulse \
  --query 'logGroups[].{Name:logGroupName,Days:retentionInDays}'
```

Expected: `ACTIVE`, `PAY_PER_REQUEST`, both indexes, `ENABLED`, both groups, and `7` for every log group.

## Step 6 — Create the demo users

Terraform does not create users, on purpose: a password in a `.tf` file is a password in Git.

```bash
POOL=<cognito_user_pool_id>

# Operations user
aws cognito-idp admin-create-user --user-pool-id $POOL \
  --username ops@northbridge.edu --message-action SUPPRESS \
  --user-attributes Name=email,Value=ops@northbridge.edu Name=email_verified,Value=true
aws cognito-idp admin-set-user-password --user-pool-id $POOL \
  --username ops@northbridge.edu --password '<choose-a-strong-one>' --permanent
aws cognito-idp admin-add-user-to-group --user-pool-id $POOL \
  --username ops@northbridge.edu --group-name ops

# Staff user  -> group staff
# Device user -> group ops   (this is who the simulator signs in as)
```

Repeat for `staff@northbridge.edu` (group `staff`) and `device@campuspulse.local` (group `ops`).

**Passwords must satisfy the policy: 12+ characters, upper, lower, number, symbol.** Keep them in whatever the team uses for shared secrets — never in the repository, never in a slide, never in a screenshot.

## Step 7 — Verify the prices you were told

```bash
bash scripts/verify-prices.sh
```

This resolves the eu-west-3 figures that `docs/cost/01-cost-model.md` currently marks **unverified**. Paste the output into that file and change those tags to verified, with today's date.

## Step 8 — Record what you did

In `docs/evidence/`:

- Screenshot: the Budgets console showing the alert
- Screenshot: the DynamoDB table showing both indexes
- Screenshot: the Cognito pool showing both groups
- Text file: the `terraform output`, with the account ID redacted
- A note of anything that went wrong and how you fixed it — this becomes the report's "Implementation Process" section, and reconstructing it later is how vague reports get written

---

## When it goes wrong

| Error | What it means | Fix |
|---|---|---|
| `InvalidClientTokenId` | Credentials not configured or expired | `aws configure`, then `aws sts get-caller-identity` |
| `AccessDenied` on budgets | The IAM user lacks budget permissions, or the Billing console is restricted for this account plan | Check the account plan; budget permissions are separate from most service permissions |
| `BucketAlreadyExists` | S3 names are globally unique across all AWS customers | Re-run — `random_id` generates a new suffix |
| `ResourceInUseException` on the table | A table of that name already exists | `terraform import`, or choose a different `environment` value |
| Terraform hangs on `init` | Network or proxy blocking the provider registry | Try another network; the registry must be reachable |
| `Error acquiring the state lock` | Another apply is running, or one crashed | Make sure nobody else is applying, then `terraform force-unlock <id>` |

**When in doubt, `terraform plan` tells you the truth about what exists versus what should exist, and changes nothing.**
