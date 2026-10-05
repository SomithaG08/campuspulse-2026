# Infrastructure as Code, explained

**Owner:** whoever runs the deployment · **Read after:** `00-start-here.md`

---

## 1. The problem it solves

You can build all of this by clicking in the AWS console. Many student projects do. Then one of these happens:

- Someone asks *"how exactly did you configure the table?"* and nobody remembers.
- A resource gets deleted and rebuilding it by hand produces something subtly different.
- A teammate wants their own copy to experiment with, and has to repeat forty clicks.
- At cleanup time, nobody is sure what still exists.

**Level 1 — simple.** Instead of clicking buttons to create things, you write down what you want in a file, and a tool creates it. The file becomes the truth. If the file says the table has two indexes, the table has two indexes — and anyone can read the file to find out.

**Level 2 — technical.** Infrastructure as Code means your cloud resources are declared in version-controlled files and reconciled by a tool that compares *desired state* (your files) with *actual state* (what exists in AWS) and makes the minimum set of API calls to close the gap. It is **declarative**: you describe the destination, not the route.

## 2. Terraform in four commands

| Command | What it does | Safe to run? |
|---|---|---|
| `terraform init` | Downloads the provider plugins into `.terraform/` | Yes — touches nothing in AWS |
| `terraform plan` | Compares your files against reality and prints what it *would* change | **Yes — changes nothing.** Run it constantly |
| `terraform apply` | Actually makes the changes | This is the one that creates and bills |
| `terraform destroy` | Deletes everything it created | Permanent. No recycle bin |

The rhythm is always: **edit → plan → read the plan → apply**. Skipping the middle step is how people accidentally delete a database.

## 3. The state file

`terraform.tfstate` is Terraform's memory: a JSON record mapping each resource in your files to the real thing in AWS.

It matters more than it looks:

- **Delete it** and Terraform forgets everything exists, then tries to create it all again — and fails, because it is already there.
- **Two people applying from two machines** produce two states, each unaware of the other's changes.
- **It can contain sensitive values**, which is why `*.tfstate` is in `.gitignore`.

Our rule: **one person owns the state file and runs `apply`.** Everyone else reads the `.tf` files, which are the human-readable version of the same truth.

*A real team would use a remote S3 backend with DynamoDB locking, so state is shared and concurrent applies are impossible. We chose not to, because it means two more resources and one more failure mode for a four-person course project. That is a trade-off, and it belongs in the report as one.*

## 4. Our files, and why each one exists

```text
infrastructure/terraform/
├── versions.tf     which Terraform and which providers
├── variables.tf    the knobs (project, region, budget, retention) + local values
├── main.tf         the AWS provider, region, and default tags on everything
├── budget.tf       the spend alarm — first, deliberately
├── dynamodb.tf     the events table, both GSIs, TTL, PITR
├── cognito.tf      the user pool, the app client, the ops and staff groups
├── iam.tf          four roles, one per Lambda, each scoped to one job
├── s3.tf           the dashboard bucket and its read-only public policy
├── cloudwatch.tf   four log groups with explicit 7-day retention
└── outputs.tf      the identifiers Phase 5 needs
```

One concern per file. You could put all of this in one `main.tf` — Terraform would not care — but then nobody could find anything.

## 5. Reading a resource block

```hcl
resource "aws_dynamodb_table" "events" {
  name         = "${local.name}-events"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"
}
```

- `resource` — "I want this to exist"
- `"aws_dynamodb_table"` — the type, from the AWS provider
- `"events"` — **Terraform's** name for it, used to reference it elsewhere as `aws_dynamodb_table.events.arn`. It is not the name AWS sees
- `name = ...` — the name AWS *does* see
- `${local.name}` — string interpolation, here producing `campuspulse-dev-events`

## 6. Three things in our configuration worth understanding

**Dependencies are inferred, not declared.** `iam.tf` references `aws_dynamodb_table.events.arn`, so Terraform knows the table must exist before the policy. You almost never write dependencies by hand — the references are the graph.

**`for_each` avoids repetition.** In `cloudwatch.tf`:
```hcl
for_each = toset(["auth", "ingest", "query", "stats"])
name     = "/aws/lambda/${local.name}-${each.key}"
```
One block, four log groups. Add a fifth function and you add one word.

**Default tags.** `main.tf` sets tags on every resource automatically. Tags are how you later answer "what is this charge for?" and how you prove at cleanup that nothing of yours survives.

## 7. What Terraform deliberately does *not* do for us

**It does not create the Cognito users.** A password in a `.tf` file is a password in Git. Users are created with CLI commands in the deployment guide instead.

**It does not create the CloudWatch alarms yet.** A threshold invented before the system has ever run is a guess, and a guessed threshold either never fires or never stops. Phase 10 sets them from observed behaviour.

**It does not create the Lambda functions in Phase 4.** There is no code to deploy yet. Their roles and log groups exist, waiting.

Knowing what a tool should *not* do is as much a part of using it well as knowing what it can.

## 8. How to verify it worked

Never trust "Apply complete!". Check the thing itself:

```bash
terraform output
aws dynamodb describe-table --table-name campuspulse-dev-events
aws cognito-idp list-groups --user-pool-id <pool-id>
```

Then `terraform plan` once more. **A clean plan — "No changes" — is the real proof** that what you declared and what exists are the same thing.

---

## Can you explain this?

1. What is the difference between `terraform plan` and `terraform apply`?
2. What is in the state file, and why is only one person allowed to run `apply`?
3. Why is the budget defined in Terraform rather than clicked in the console?
4. Why are the Cognito *users* not in Terraform, when the user *pool* is?
5. How does Terraform know the DynamoDB table must be created before the IAM policy?

### Answers

1. `plan` compares your files against what actually exists and prints the difference, changing nothing. `apply` performs those changes. Always read a plan before applying.
2. The state file maps each resource in your configuration to the real AWS resource. Two people applying from two machines keep two divergent states, each blind to the other's changes — so one person owns it.
3. Because it is then version-controlled, reviewable, reproducible, and impossible to forget. A billing alert someone clicked once and nobody can find again is not a control.
4. Because creating a user requires a password, and anything in a `.tf` file ends up in Git. The pool is configuration; the users are credentials.
5. The IAM policy references `aws_dynamodb_table.events.arn`. Terraform builds a dependency graph from references like that one and orders the work itself.
