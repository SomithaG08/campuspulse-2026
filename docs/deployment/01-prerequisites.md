# Deployment Prerequisites

Everything below is done once per person. Expect 30-45 minutes the first time.

## 1. Tools

| Tool | Version | Check | Where |
|---|---|---|---|
| AWS CLI | v2 | `aws --version` | https://aws.amazon.com/cli/ |
| Terraform | ≥ 1.5 | `terraform version` | https://developer.hashicorp.com/terraform/install |
| Python | ≥ 3.11 | `python --version` | https://www.python.org/downloads/ |
| Git | any | `git --version` | https://git-scm.com/ |

On Windows, PowerShell is fine for all of them. Where this guide shows a bash-only command, it says so.

## 2. AWS credentials — the part to get right

You need an **IAM user with programmatic access**, not your root login.

**In the AWS console:**

1. IAM → Users → Create user, name it `campuspulse-deploy`.
2. Attach a policy. For a course project `AdministratorAccess` is the pragmatic choice, and it is the honest thing to write in the report: *we used a broad deployment identity for convenience, while every runtime component uses a least-privilege role.* Those are different things, and the second is what the security criterion is actually about.
3. Create the user, then Security credentials → Create access key → Command Line Interface.
4. Copy the access key ID and secret. **The secret is shown once.**

**On your machine:**

```bash
aws configure
# AWS Access Key ID:     AKIA...
# AWS Secret Access Key: ...
# Default region name:   eu-west-3
# Default output format: json
```

Verify:

```bash
aws sts get-caller-identity
```

You should see your account ID and the user ARN.

### Rules about credentials, which are not negotiable

- **Never** paste an access key into a file in this repository, a document, a slide, a screenshot or a chat message.
- `aws configure` stores them in `~/.aws/credentials`, which is outside the repo. That is the only place they belong.
- If a key is ever exposed, deactivate it in IAM immediately — not later, immediately.
- Before any commit: `git status` and check nothing under `.aws/` or any `.tfvars` is staged. `.gitignore` covers both, but look anyway.

## 3. Confirm the account's plan and dates

Open **Billing and Cost Management** and record, in `docs/evidence/cost/`:

- The account creation date
- Which plan the account is on (Free or Paid)
- The current credit balance

**Why this matters:** on the Free plan the account closes at six months from sign-up, or when the credits run out. If that date lands near your presentation, you need to know now, not then.

## 4. Pick who owns the deployment

Terraform keeps its state in a local file, `terraform.tfstate`, which records what exists. **One person owns that file and runs `terraform apply`.** Two people applying from two laptops produces two conflicting views of reality and a broken stack.

Everyone else can — and should — read the `.tf` files and run `terraform plan` after copying the state file from the owner, to see what *would* change without changing anything.

## 5. Set your variables

```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` and set `notification_email` to an address someone actually reads. This file is gitignored.
