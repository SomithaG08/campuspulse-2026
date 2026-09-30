# AWS Account Verification — RESOLVED 2026-09-22

> **Outcome:** the team confirmed a standard AWS account created with a school email address, carrying 100 credits, with all services working normally — not a restricted Learner Lab. Cognito, IAM role creation, the Billing console and the AWS CLI are all expected to be available, so the architecture in `docs/architecture/` assumes them. The first real confirmation comes in Phase 4 when resources are actually created; if anything below turns out to be restricted, the fallbacks at the bottom of this file still apply.
>
> **Two checks remain open and matter a great deal — see risk C5:**
> - **Which plan is the account on (Free or Paid), and what date was it created?** On the Free plan the account closes 6 months after sign-up or when the credits are depleted, whichever comes first.
> - **Never join an AWS Organization or set up Control Tower** with this account: either action expires the credits immediately.
>
> The original checklist is kept below as a reference for anyone who needs to re-verify, and because the fallback designs are still the documented plan B.

---

## How to run the checks

Open the lab, start the session, and open the AWS Management Console. Note the **region** shown in the top right — sandboxes are usually locked to `us-east-1`. Then work down the table. For each one, you only need to get far enough to see whether the console lets you proceed or shows an access-denied error; **do not actually create anything expensive**.

| # | Check | How to check | Why it matters | Result |
|---|---|---|---|---|
| V1 | Which region(s) are allowed | Try switching region in the console top-right | Everything we build must live in one allowed region | |
| V2 | Does the session/credits persist between logins? Do resources survive? | Read the lab's own instructions; note whether it says resources are deleted | Decides whether we must be able to redeploy from scripts quickly | |
| V3 | **Lambda** — can you open the console and see "Create function"? | Lambda → Create function (stop before creating) | Our entire compute layer | |
| V4 | **API Gateway** — can you open it and start creating an HTTP API? | API Gateway → Create API (stop before creating) | Our entire API layer | |
| V5 | **DynamoDB** — can you open "Create table"? | DynamoDB → Tables → Create table (stop) | Our storage layer | |
| V6 | **Cognito** — does the service open, or is it access-denied / absent from the service list? | Search "Cognito" in the console | **Decides OD-1**: Cognito user pool vs. custom JWT auth in Lambda | |
| V7 | **IAM role creation** — can you create a new role, or only use a provided one (usually `LabRole`)? | IAM → Roles → Create role (stop before creating) | **Decides OD-2**: whether Terraform can manage IAM, and whether per-function least-privilege is possible or we must document a forced exception | |
| V8 | Is there a pre-provided role (e.g. `LabRole`) and what does it allow? | IAM → Roles → look for `LabRole` / `LabInstanceProfile` → Permissions tab | If we must attach one shared role to every Lambda, our security section must say so honestly instead of claiming least privilege | |
| V9 | **CloudWatch** — logs, metrics, alarms accessible? | CloudWatch → Alarms → Create alarm (stop) | Observability requirement (F6, A5) | |
| V10 | **S3** — can you create a bucket and enable static website hosting / public-read policy? | S3 → Create bucket (stop); check whether bucket policies are blocked | Dashboard hosting. If public policies are blocked we host the dashboard differently — say, running it locally against the API for the demo | |
| V11 | **AWS Budgets / Billing** — is the Billing console visible? | Account menu → Billing and Cost Management | **Requirement C2 is mandatory.** Sandboxes often hide Billing and show only a credit gauge — if so, our "billing alert evidence" becomes a screenshot of the credit gauge plus a CloudWatch alarm on usage, and the report must explain why | |
| V12 | **SNS** — available? (only needed if we add email alerting later) | SNS → Topics | Optional feature O2 | |
| V13 | Can you use the **AWS CLI** with the lab's temporary credentials? | Lab page usually shows "AWS Details" / CLI credentials → run `aws sts get-caller-identity` | Decides whether scripted deployment (and Terraform) is possible at all | |
| V14 | How long is a lab session, and what happens to running resources at the end? | Lab instructions | Demo-day risk M2 | |

## What each outcome changes

**If Cognito is unavailable (V6 = no)**
→ We implement authentication ourselves: a `users` table in DynamoDB, passwords hashed with a vetted library, login issuing a signed JWT, and a Lambda authorizer validating it. This is *more* work but is fully explainable and arguably demonstrates the concepts better. The report will state plainly that Cognito was unavailable in the academic account and this was the substitute.

**If IAM role creation is blocked (V7 = no)**
→ Every Lambda uses the provided lab role. We cannot claim per-function least privilege. Instead the report documents: the constraint, what our policies *would* be (the JSON is written and included in the repo as the intended design), and how we compensate (validation, throttling, token checks). Honest constraint reporting is worth more than a false claim.

**If the AWS CLI is unavailable (V13 = no)**
→ Terraform and scripted deployment are impossible. The "reproducible deployment" requirement (I4) is then satisfied by a very detailed console-click deployment guide with screenshots, which the PDF explicitly allows ("*or detailed deployment guide*", §7).

**If Billing is hidden (V11 = no)**
→ Cost evidence becomes: credit-balance screenshots over time, a CloudWatch alarm on Lambda invocations as a proxy spend guard, and the cost estimate table. The report explains the limitation instead of faking a Budgets screenshot.

**If the region is locked**
→ Fine. We were building single-region anyway. It goes in the architecture doc.

---

## Report back with

Just the Result column filled in — or a screenshot of the lab's service list. With those answers I can finalise Phase 2 (architecture) with no guesswork and no rework later.
