# Applying the October 2026 corrections to the live deployment

The step-by-step upgrade from the 5 October deployment (5 Lambdas, no VPC, `ops`/`staff`) to the corrected one (2 Lambdas grouped by business domain with VPC isolation, backups, team email alerts, `admin`/`student` pages).

Run these commands from the project root by **the person who has AWS credentials and Terraform state access**.

Time: about 30 minutes, plus a few minutes for the team to click their email confirmation links.

---

## 0. Before you start

### On macOS / Linux (Terminal / Zsh / Bash):
```bash
cd ~/Downloads/campuspulse-2026
aws sts get-caller-identity          # must show the project account
terraform -version                   # any 1.5+ (state was written by 1.15.8)
```

### On Windows (PowerShell):
```powershell
cd "C:\Users\EPW INDIA\Desktop\EPITA\Courses\Big Data Infrastructure and Cloud Computing\Project\campuspulse-2026"
aws sts get-caller-identity          # must show the project account
terraform -version                   # any 1.5+ (state was written by 1.15.8)
```

Take an on-demand backup of the table **before** changing anything (PITR already protects it, this is belt and braces):

```bash
aws dynamodb create-backup --table-name campuspulse-dev-events --backup-name before-corrections --region eu-west-3
```

---

## 1. Add the team's school addresses

Open `infrastructure/terraform/terraform.tfvars` and ensure `alert_emails` is set (keep `notification_email` as it is):

```hcl
alert_emails = [
  "somitha.gudivada@epita.fr",
  "meha@epita.fr",
  "madhavan@epita.fr",
  "md@epita.fr",
]
```

Optional: add the email address of your Microsoft Teams channel (channel `…` menu → *Get email address*) to get every alert posted in the channel as well.

---

## 2. Plan — and read it

### On macOS / Linux:
```bash
cd infrastructure/terraform
terraform init -upgrade
terraform validate
terraform plan -out=tfplan
```

### On Windows PowerShell:
```powershell
cd infrastructure\terraform
terraform init -upgrade
terraform validate
terraform plan -out=tfplan
```

### What you should expect to see:

| Expect to **create** | Expect to **update in place** | Expect to **destroy** |
|---|---|---|
| VPC `10.20.0.0/16`, 2 private subnets, route table + 2 associations, security group + egress rule, default SG takeover, DynamoDB gateway endpoint, flow log + its group and role | 7 routes (now `aws_apigatewayv2_route.protected[...]` — the `moved` blocks make these updates, not replacements) | Lambda functions `health`, `ingest`, `query`, `stats` and their roles, policies, permissions and log groups |
| Lambda `api`, its role and policies, its permission, its log group | the API integration (`ingest` → `api`) | integrations `health`, `query`, `stats` |
| Backup vault, plan, selection, backup role | the DynamoDB table (**adds GSI3 — online, no downtime**) | |
| SNS topic, policy, one subscription per address; alarms `critical-alert`, `urgent-request`, `auth-errors` | the CloudWatch dashboard, `alert-burst`, `api-5xx`, `invocation-ceiling` | |
| Cognito groups `admin` and `student` | the `auth` Lambda (new description), the site bucket (`force_destroy`) | |
| S3 versioning and lifecycle | | |

**Stop if the plan wants to destroy** the DynamoDB table, the Cognito user pool, the API itself (`aws_apigatewayv2_api.main`) or the S3 bucket. None of those should be replaced. Also check there is still **no** `aws_nat_gateway`, `aws_instance`, `aws_db_instance` or `aws_lb`.

```bash
terraform apply tfplan
```

Adding GSI3 to the live table can take a few minutes; Terraform waits for it.

---

## 3. Everyone confirms their email

Each address in `alert_emails` receives **"AWS Notification - Subscription Confirmation"** from `no-reply@sns.amazonaws.com`. Click **Confirm subscription**. School mail often quarantines this first message — check spam/quarantine.

### Verify subscriptions:
```bash
aws sns list-subscriptions-by-topic --topic-arn $(terraform output -raw alerts_topic_arn) --region eu-west-3 \
  --query "Subscriptions[].[Endpoint,SubscriptionArn]" --output table
```
*(On PowerShell, use `(terraform output -raw alerts_topic_arn)` with backtick line continuation)*

`PendingConfirmation` means that person has not clicked yet.

---

## 4. Users and the new groups

Set the pool ID and update groups:

### On macOS / Linux:
```bash
POOL=$(terraform output -raw cognito_user_pool_id)

# Administrators
aws cognito-idp admin-add-user-to-group --user-pool-id "$POOL" --username admin@northbridge.edu --group-name admin --region eu-west-3
aws cognito-idp admin-add-user-to-group --user-pool-id "$POOL" --username ops@northbridge.edu   --group-name admin --region eu-west-3

# A student account for the student page and the API tests
aws cognito-idp admin-create-user --user-pool-id "$POOL" --username student@northbridge.edu \
  --message-action SUPPRESS --user-attributes Name=email,Value=student@northbridge.edu Name=email_verified,Value=true --region eu-west-3
aws cognito-idp admin-set-user-password --user-pool-id "$POOL" --username student@northbridge.edu \
  --password "Campus2026!!" --permanent --region eu-west-3
aws cognito-idp admin-add-user-to-group --user-pool-id "$POOL" --username student@northbridge.edu --group-name student --region eu-west-3

# Retire the old groups
aws cognito-idp delete-group --user-pool-id "$POOL" --group-name ops   --region eu-west-3
aws cognito-idp delete-group --user-pool-id "$POOL" --group-name staff --region eu-west-3
```

### On Windows PowerShell:
```powershell
$POOL = terraform output -raw cognito_user_pool_id

# Administrators
aws cognito-idp admin-add-user-to-group --user-pool-id $POOL --username admin@northbridge.edu --group-name admin --region eu-west-3
aws cognito-idp admin-add-user-to-group --user-pool-id $POOL --username ops@northbridge.edu   --group-name admin --region eu-west-3

# A student account for the student page and the API tests
aws cognito-idp admin-create-user --user-pool-id $POOL --username student@northbridge.edu `
  --message-action SUPPRESS --user-attributes Name=email,Value=student@northbridge.edu Name=email_verified,Value=true --region eu-west-3
aws cognito-idp admin-set-user-password --user-pool-id $POOL --username student@northbridge.edu `
  --password "Campus2026!!" --permanent --region eu-west-3
aws cognito-idp admin-add-user-to-group --user-pool-id $POOL --username student@northbridge.edu --group-name student --region eu-west-3

# Retire the old groups
aws cognito-idp delete-group --user-pool-id $POOL --group-name ops   --region eu-west-3
aws cognito-idp delete-group --user-pool-id $POOL --group-name staff --region eu-west-3
```

Group membership is read at sign-in: **sign out and sign in again** after this step.

---

## 5. Publish the three pages

### On macOS / Linux (from the project root):
```bash
cd ../..
bash scripts/deploy-dashboard.sh
```

### On Windows PowerShell:
```powershell
cd ..\..
$API    = terraform -chdir=infrastructure/terraform output -raw api_endpoint
$BUCKET = terraform -chdir=infrastructure/terraform output -raw site_bucket_name

Remove-Item -Recurse -Force frontend\.build -ErrorAction SilentlyContinue
New-Item -ItemType Directory frontend\.build | Out-Null
Copy-Item frontend\index.html, frontend\admin.html, frontend\student.html, frontend\style.css, `
          frontend\app.js, frontend\admin.js, frontend\student.js frontend\.build\
(Get-Content frontend\config.js) -replace 'API_URL: "[^"]*"', "API_URL: `"$API`"" | Set-Content frontend\.build\config.js

aws s3 sync frontend\.build\ "s3://$BUCKET/" --delete --cache-control "public, max-age=60"
terraform -chdir=infrastructure/terraform output admin_page_url
terraform -chdir=infrastructure/terraform output student_page_url
```

---

## 6. Prove it

### On macOS / Linux:
```bash
API=$(terraform -chdir=infrastructure/terraform output -raw api_endpoint)
export CAMPUSPULSE_API="$API"
export ADMIN_USER="admin@northbridge.edu"
export ADMIN_PASSWORD="<password>"
export STUDENT_USER="student@northbridge.edu"
export STUDENT_PASSWORD="<password>"

python3 tests/api/run_api_tests.py          # expect 50 passed, 0 failed
```

### Trigger alert emails to verify SNS:
```bash
cd simulator
export CAMPUSPULSE_USER="admin@northbridge.edu"
export CAMPUSPULSE_PASSWORD="<password>"
python3 simulator.py --api-url "$API" -n 30
python3 simulator.py --api-url "$API" -n 3 --force-alert     # within ~1-2 min: "ALARM: campuspulse-dev-critical-alert" in inbox
```

Run verification and disaster recovery drill:
```bash
cd ..
bash scripts/verify-deployment.sh
bash scripts/backup-now.sh
bash scripts/restore-drill.sh              # measures and prints RTO
```

---

## 7. Evidence to capture

Follow the checklist in [`docs/requirements/21-professor-corrections.md`](../requirements/21-professor-corrections.md) §3:
- Output from `verify-deployment.sh`
- Output from `run_api_tests.py` (50 passed)
- Screenshots of AWS Lambda console (showing `api` in VPC and `auth` outside VPC)
- Screenshot of VPC Resource Map (showing 2 subnets, route table, and gateway endpoint with no IGW/NAT)
- Received alert email in team inbox
- Admin dashboard and student page running live
