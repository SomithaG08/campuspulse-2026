# Cost Model — CampusPulse 2026

> **Rule for this file: every number carries its source and its confidence.** Nothing is called free because it feels free. Figures marked **[verified]** were read from the AWS page cited on 2026-09-22; figures marked **[unverified]** could not be read because those pages render their price tables in JavaScript, and are re-checked in Phase 4 using `aws pricing get-products`.

---

## 1. The most important thing on this page: how the account actually works

The AWS Free Tier changed on 15 July 2025, and the new model is **not** the 12-month free tier most tutorials describe. For an account created in 2026:

| Fact | Detail | Source |
|---|---|---|
| Signup credits | **$100 on sign-up**, plus up to **$100 more** earned by using certain services | [What's New, 16 Jul 2025](https://aws.amazon.com/about-aws/whats-new/2025/07/aws-free-tier-credits-month-free-plan/) |
| Credit expiry | **Credits expire 12 months from account creation** | [Free Tier FAQs](https://aws.amazon.com/free/free-tier-faqs/) |
| Free plan duration | Ends at **6 months after sign-up, or when the credits are depleted — whichever comes first** | [Free Tier FAQs](https://aws.amazon.com/free/free-tier-faqs/) |
| **What happens at expiry** | On the Free plan, **AWS closes the account**. Access to resources and data is lost. AWS retains the data for **90 days**, during which upgrading to the Paid plan reopens it; after that it is permanently erased | [Free Tier FAQs](https://aws.amazon.com/free/free-tier-faqs/), Free Plan Q5/Q6 |
| Always-free services | 30+ services keep a monthly free allowance on both plans; credits are applied automatically beyond it | [aws.amazon.com/free](https://aws.amazon.com/free/) |
| Instant-credit-expiry traps | Joining an AWS Organization or setting up Control Tower **expires the credits immediately** and force-upgrades the account | [Free Tier FAQs](https://aws.amazon.com/free/free-tier-faqs/) |

### What this means for the team, in plain words

1. **Find out today which plan the account is on and when it was created.** If it is on the Free plan and the six-month mark falls before the presentation, the account can close *with the project inside it*. That is a project-ending event, and it is scheduled, not random.
2. **Do not join an AWS Organization** and do not set up Control Tower. Either one instantly expires the credits.
3. The credits are the real budget. Everything below is about protecting them.

---

## 2. Per-service free allowances and prices

| Service | Free allowance | Confidence | Price beyond it | Our expected usage |
|---|---|---|---|---|
| **Lambda** | 1,000,000 requests + 400,000 GB-seconds **per month**, not time-limited. Does **not** apply to Provisioned Concurrency | **[verified]** [pricing](https://aws.amazon.com/lambda/pricing/) | $0.20 per 1M requests; ~$0.0000166667 per GB-s (x86, N. Virginia) | « 100k requests total |
| **API Gateway HTTP API** | 1,000,000 calls/month **for 12 months** (new customers) | **[verified]** [pricing](https://aws.amazon.com/api-gateway/pricing/) | **$1.00 per 1M** (HTTP API) — REST would be $3.50 | « 100k calls total |
| **DynamoDB** | 25 GB storage, 25 WCU, 25 RCU, 2.5M stream reads — per region per month, **stated for provisioned capacity + Standard class** | **[verified]** [pricing](https://aws.amazon.com/dynamodb/pricing/) | on-demand ≈ $0.625/1M writes, $0.125/1M reads (N. Virginia) | **[unverified]** — 100k writes ≈ **$0.06**; storage « 1 GB |
| **Cognito** | **10,000 MAU/month** for **Lite or Essentials** pools; not limited to 12 months. **No free tier on Plus.** No free tier for M2M token requests | **[verified]** [pricing](https://aws.amazon.com/cognito/pricing/) | $0.015/MAU (Essentials) | ~6 users |
| **CloudWatch** | 5 GB logs (ingest + storage + Insights scanning combined), 10 custom metrics, 10 alarm metrics, 3 dashboards, 1M API requests | **[verified]** [pricing](https://aws.amazon.com/cloudwatch/pricing/) | metrics ~$0.30/metric/month at the top tier **[unverified]**; logs ~$0.50/GB **[unverified]** | 2 metrics, 3 alarms, 1 dashboard, « 1 GB logs |
| **S3** | The familiar 5 GB / 20,000 GET / 2,000 PUT figures **could not be read from the pricing page** and are therefore not asserted here | **[unverified]** | not read | < 1 MB of static files |
| **IAM** | Free | **[verified]** — no charge for IAM | — | 4 roles |
| **DynamoDB PITR** | Priced per GB of table size; rate not read | **[unverified]** | — | table « 1 GB, so cents |
| **Data transfer out** | The DynamoDB page notes 100 GB/month free data transfer out to the internet, aggregated across services | **[verified]** [pricing](https://aws.amazon.com/dynamodb/pricing/) | — | a few MB |

### Expected total

**Well under $5 of the 100 credits for the entire project**, dominated by DynamoDB on-demand requests and PITR — both of which are cents at our scale. **This is an estimate, not a measurement.** The real figure goes in the report from the Billing console in Phase 12, and if it differs from this table, the table is corrected rather than the reality.

---

## 3. What could actually destroy the budget

Ranked by how much damage per hour of inattention:

| Hazard | Rough cost if left running | Our defence |
|---|---|---|
| **NAT Gateway** | ~$0.045/hour + per-GB ≈ **$32+/month** | We have no VPC. Architecturally impossible for us to create one by accident |
| **RDS instance** | Hourly, 24/7 | Not used; on the forbidden list |
| **EC2 instance left on** | Hourly, 24/7 | Not used; on the forbidden list |
| **Load balancer** | Hourly, 24/7 | Not used; API Gateway replaces it |
| **A runaway simulator loop** | Per request; grows fast | Default interval in seconds; hard `--number-of-events` cap; CloudWatch alarm on invocation count |
| **Log retention left at "never expire"** | Slow, quiet growth | Retention set to **7 days** at creation |
| **Cognito Plus tier selected by mistake** | $0.020/MAU **from the first user** | Use **Essentials**. Written into the deployment guide |
| **Provisioned Concurrency on Lambda** | Bills per GB-s continuously and **voids the Lambda free tier** | Never enable it |

**The end-of-session habit:** before closing the laptop, check the Billing console's credit balance. A number that moves while nobody is working is the early warning for all of the above.

---

## 4. Required cost-control actions (spec §8)

| Action | How | Status |
|---|---|---|
| Budget / billing alert with evidence | AWS Budgets: alert at a low threshold of the credit balance, email to the team | **Not done — Phase 4, before any other resource** |
| Cost estimate table in the report | This file, corrected with measured figures in Phase 12 | Draft, unverified figures flagged |
| Stop/delete unused resources | `docs/deployment/cleanup.md` + teardown script | **Not written yet** |
| Justify any non-free resource | DynamoDB on-demand requests and PITR are the only two; justified in AD-4 and the DR section | Written |
| Monitor consumption | Credit balance checked at the end of each work session, recorded in `docs/evidence/cost/` | **Not started** |

## 5. Cleanup, when the project is over

In dependency order: empty and delete the S3 bucket → delete the API → delete the four Lambdas and their log groups → delete the DynamoDB table (**export first if the data is needed as evidence**) → delete the Cognito user pool → delete the IAM roles → delete the alarms, dashboard and budget. Then confirm the credit balance stops moving for 24 hours.

A `terraform destroy` does most of this in one command, which is one more argument for Infrastructure as Code.

---

**Sources:** [AWS Free Tier](https://aws.amazon.com/free/) · [Free Tier FAQs](https://aws.amazon.com/free/free-tier-faqs/) · [Free Tier credits announcement](https://aws.amazon.com/about-aws/whats-new/2025/07/aws-free-tier-credits-month-free-plan/) · [Account Management doc](https://docs.aws.amazon.com/accounts/latest/reference/bcm-lite-free-tier.html) · [Lambda pricing](https://aws.amazon.com/lambda/pricing/) · [API Gateway pricing](https://aws.amazon.com/api-gateway/pricing/) · [DynamoDB pricing](https://aws.amazon.com/dynamodb/pricing/) · [Cognito pricing](https://aws.amazon.com/cognito/pricing/) · [CloudWatch pricing](https://aws.amazon.com/cloudwatch/pricing/) · [S3 pricing](https://aws.amazon.com/s3/pricing/) — all read 2026-09-22.
