# Corrections from the project review — 12 October 2026

The professor reviewed CampusPulse 2026 and asked for five changes. This page maps each one to what changed, where, and the evidence still to capture. How to deploy the changes: `docs/deployment/06-apply-corrections.md`.

## 1. The five corrections

| # | Review comment | Before | After | Files |
|---|---|---|---|---|
| 1 | **VPC missing** | No VPC (AD-7: "IAM is our boundary") | VPC `10.20.0.0/16`; 2 private subnets in eu-west-3a/3b; no internet gateway, no NAT; security group (no inbound, outbound 443 to DynamoDB only); DynamoDB **gateway endpoint** (free) with a table-only policy; default SG emptied; VPC Flow Logs. The `api` Lambda runs inside | `infrastructure/terraform/vpc.tf` (new), `lambda.tf`, `iam.tf`, `variables.tf` |
| 2 | **Backup missing** | PITR only | PITR (35 d) **+ AWS Backup**: vault, daily (kept 7 d) and weekly (kept 35 d) snapshots of the table; S3 versioning on the pages (old versions 30 d); `backup-now.sh` and `restore-drill.sh` (measures RTO) | `backup.tf` (new), `s3.tf`, `dynamodb.tf`, `scripts/backup-now.sh`, `scripts/restore-drill.sh` |
| 3 | **Alerts should go to the team's school mail** | Optional single `alarm_email`, off by default | SNS topic `campuspulse-dev-alerts` always on; one email subscription per address in `alert_emails` (team `@epita.fr`, optionally a Teams channel address); **all 7 alarms** notify it; new alarms `critical-alert` (any critical campus event, 1 min) and `urgent-request` (any urgent student request, 1 min) | `alarms.tf`, `variables.tf`, `terraform.tfvars.example`, `backend/src/common/log.py`, `handlers/ingest.py` |
| 4 | **Two pages: one for admin, one for student** | One dashboard; roles `ops`/`staff` | Roles `admin`/`student`. `index.html` signs in and redirects by role. **`admin.html`**: KPIs, active alerts, all student requests (with who raised them), occupancy, energy, recent events. **`student.html`**: free rooms, building comfort, *report a problem*, *my requests*. New route `GET /requests` (student: own only, via new sparse GSI3; admin: the day's requests) | `frontend/*`, `cognito.tf`, `dynamodb.tf`, `common/auth.py`, `common/keys.py`, `common/queries.py`, `handlers/requests.py` (new), `apigateway.tf` |
| 5 | **Group Lambda functions to business requirements** | 5 nano-functions split by technical CRUD action (`health`, `auth`, `ingest`, `query`, `stats`) | Grouped into **two core business domains**: **Identity & Access Gateway** (`auth`, `POST /login`, outside VPC to communicate with Cognito; zero data access) and **Campus Operations & Telemetry Platform** (`api`, inside private VPC subnets with DynamoDB gateway endpoint, handling telemetry ingestion, student requests, analytics, and health) | `handlers/api.py` (router), `lambda.tf`, `iam.tf`, `apigateway.tf`, `cloudwatch.tf`, `moved.tf` |

Design reasoning for each: AD-10 to AD-14 in `docs/architecture/01-architecture-decisions.md`.

### Found while making the changes

- **The `alert-burst` alarm could never fire.** It watched `AlertsRaised` with no dimension; the code only ever published `AlertsRaised{Severity=…}`. CloudWatch treats these as different metrics. Fixed: `log.metric(..., aggregate=True)` also publishes the dimensionless total.
- **Encrypting the SNS topic with `alias/aws/sns` would have silently stopped every email** (CloudWatch alarms cannot use that key). The topic is left unencrypted; reason recorded in `alarms.tf` and the report.
- **Restructuring the routes would have recreated them.** `moved.tf` makes Terraform update the existing routes in place.

## 2. What it costs

| Added | Cost |
|---|---|
| VPC, subnets, route table, security groups, DynamoDB gateway endpoint | $0 |
| VPC Flow Logs (7 days) | CloudWatch Logs ingestion — a few MB/month, inside the 5 GB free allowance |
| AWS Backup — table < 10 MB, 7 daily + 5 weekly copies | well under $0.01/month |
| S3 versioning — a few tens of KB | ≈ $0 |
| SNS email | first 1,000/month free |
| 3 extra alarms (7 in total) | free up to 10 |
| **Avoided:** NAT Gateway (~$32/month), Cognito + SNS interface endpoints (~$32/month for two AZs) | — |

## 3. Evidence to capture after deploying

Replace the 5 October screenshots in `docs/evidence/` and drop "(5 Oct deployment)" from the report captions as each one is refreshed.

- [ ] `verify-deployment.sh` output — all checks OK (network, backup and email lines included)
- [ ] `tests/api/run_api_tests.py` — **50 passed**, `api-test-results.json` committed
- [ ] Lambda console: **two functions**; `api` → Configuration → VPC showing the VPC, two subnets, the security group
- [ ] VPC console → *Resource map* (subnets, route table, endpoint — no IGW, no NAT)
- [ ] AWS Backup → vault → a recovery point; `restore-drill.sh` output with the **measured RTO** → put the number in report §9.2
- [ ] A received alert email in a team `@epita.fr` inbox (`ALARM: campuspulse-dev-critical-alert` or `…-urgent-request`)
- [ ] `admin.html` with data, `student.html` with a sent request
- [ ] 403 for a student on `GET /alerts` and `GET /events`; 200 on `GET /stats`
- [ ] Architecture image `docs/architecture/campuspulse-architecture.png` in the slides

## 4. Unit tests

161 passing (143 backend + 18 simulator), up from 131. New: `backend/tests/test_api_router.py` — every route reaches a handler, the admin/student permission matrix for every route, students only ever query their own requests, admins page past the filter, urgent requests emit the metric the email alarm watches.

## 5. Not changed in this round

- The learning documents in `docs/learning/` and the step-by-step deployment pages `02`–`04` still describe the five-function, `ops`/`staff` version in places. The report, the architecture decisions, the diagram, the API contract, the runbook and the audit are up to date.
- The slides (`CampusPulse_2026_Final_Presentation.pptx`) and the speaking script need the new architecture slide, the two pages and the backup/alert story.
- Energy totals (audit note E1) — unrelated to the review, still open.
