# ⚠️ COST WARNING — read before running `terraform apply`

Phase 4 is the first phase that creates real AWS resources. Real resources can spend real credits, and your 100 credits do not refill. Read this page before you type `apply`.

## What Terraform creates, and what each one can cost

| Resource | Bills by the hour? | Cost while idle | Realistic cost for us |
|---|---|---|---|
| AWS Budget (1) | No | $0 | AWS provides a small number of budgets at no charge; we create exactly one. **Verify on the Billing pricing page** — this is the one charge that could apply to a monitoring tool |
| DynamoDB table, on-demand | **No** | **$0** | Per request: ~$0.625/M writes, ~$0.125/M reads (N. Virginia figures, **unverified** — see the verification script) plus storage. Our expected total: **cents** |
| DynamoDB point-in-time recovery | No | Priced per GB of table size | Table « 1 GB → cents |
| Cognito user pool | No | $0 | Free tier 10,000 MAU on Essentials. We will have ~6 users → **$0** |
| S3 bucket | No | Per GB stored + per request | A few hundred KB of static files → effectively $0 |
| IAM roles and policies (4 + 1) | No | **$0** | IAM is free |
| CloudWatch log groups (4) | No | Per GB ingested and stored | Retention set to 7 days; free tier is 5 GB → **$0** |

**Nothing in this phase bills by the hour.** That is the whole point of the architecture, and it is why you can apply this and then walk away for a week without checking.

## What must NEVER be created

If you find yourself about to create one of these, stop and ask the team first:

| Resource | Why not |
|---|---|
| **NAT Gateway** | ~$0.045/hour + data charges ≈ **$32+/month for nothing**. The single most common way a student AWS budget disappears |
| **EC2 instance** | Hourly, 24/7, even when idle |
| **RDS instance** | Hourly, 24/7, even when idle |
| **Load balancer (ALB/NLB)** | Hourly, 24/7 |
| **Lambda Provisioned Concurrency** | Bills continuously **and voids the Lambda free tier entirely** |
| **Cognito Plus tier** | No free tier at all — billed from the first user |
| **Kinesis, OpenSearch, EKS, MSK** | No meaningful free tier; all far beyond what this project needs |

## Two account-level rules

1. **Do not join an AWS Organization, and do not set up Control Tower.** Either action expires the Free Tier credits immediately and force-upgrades the account.
2. **Know your account's plan and creation date.** On the free plan, an account closes at six months from sign-up or when the credits run out — whichever comes first — and the resources become inaccessible. See `docs/cost/01-cost-model.md` §1.

## The habit that prevents every cost incident

At the end of every working session, before closing the laptop:

```bash
# What did we actually spend?
aws ce get-cost-and-usage \
  --time-period Start=$(date -d '7 days ago' +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity DAILY --metrics UnblendedCost \
  --region us-east-1
```

Or simply open **Billing and Cost Management → Credits** and look at the balance.

**A credit balance that moves while nobody is working is the early warning for every hazard on this page.**

## If something does start costing money

1. Find it: Billing → Cost Explorer → group by service.
2. Stop it: delete the resource, or `terraform destroy` if Terraform made it.
3. Write it down in `docs/evidence/cost/` with the date and what happened. A real incident, honestly reported in the Lessons Learned section, is worth more marks than a project that pretends nothing went wrong.
