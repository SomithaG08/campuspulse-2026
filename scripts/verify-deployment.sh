#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# verify-deployment.sh
#
# Checks that what is DEPLOYED matches what was DESIGNED. "terraform apply
# complete" means Terraform is satisfied; it does not mean PITR is on, that log
# retention is 7 days rather than forever, or that both Cognito groups exist.
#
# Every line below corresponds to a claim the report makes. Run it after
# deploying, screenshot the output, and keep it: it is the cheapest evidence
# in the project.
#
# Usage:  bash scripts/verify-deployment.sh
# ---------------------------------------------------------------------------
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF="$ROOT/infrastructure/terraform"
PASS=0; FAIL=0

ok()   { echo "  [ OK ] $1"; PASS=$((PASS+1)); }
bad()  { echo "  [FAIL] $1"; echo "         expected: $2"; echo "         actual:   $3"; FAIL=$((FAIL+1)); }
check(){ [ "$2" = "$3" ] && ok "$1" || bad "$1" "$2" "$3"; }

command -v aws >/dev/null || { echo "aws CLI not found"; exit 1; }
command -v terraform >/dev/null || { echo "terraform not found"; exit 1; }

REGION=$(terraform -chdir="$TF" output -raw region)
TABLE=$(terraform -chdir="$TF" output -raw dynamodb_table_name)
POOL=$(terraform -chdir="$TF" output -raw cognito_user_pool_id)
API=$(terraform -chdir="$TF" output -raw api_endpoint)
BUCKET=$(terraform -chdir="$TF" output -raw site_bucket_name)

echo
echo "CampusPulse deployment verification"
echo "  region : $REGION"
echo "  date   : $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo

echo "Storage"
check "table is ACTIVE" "ACTIVE" \
  "$(aws dynamodb describe-table --table-name "$TABLE" --region "$REGION" --query 'Table.TableStatus' --output text 2>/dev/null)"
check "billing is on-demand (nothing billed while idle)" "PAY_PER_REQUEST" \
  "$(aws dynamodb describe-table --table-name "$TABLE" --region "$REGION" --query 'Table.BillingModeSummary.BillingMode' --output text 2>/dev/null)"
check "all three secondary indexes exist" "3" \
  "$(aws dynamodb describe-table --table-name "$TABLE" --region "$REGION" --query 'length(Table.GlobalSecondaryIndexes)' --output text 2>/dev/null)"
check "TTL is enabled (storage stays small)" "ENABLED" \
  "$(aws dynamodb describe-time-to-live --table-name "$TABLE" --region "$REGION" --query 'TimeToLiveDescription.TimeToLiveStatus' --output text 2>/dev/null)"
check "point-in-time recovery is on (backup layer 1)" "ENABLED" \
  "$(aws dynamodb describe-continuous-backups --table-name "$TABLE" --region "$REGION" --query 'ContinuousBackupsDescription.PointInTimeRecoveryDescription.PointInTimeRecoveryStatus' --output text 2>/dev/null)"

VAULT=$(terraform -chdir="$TF" output -raw backup_vault_name)
check "AWS Backup vault exists (backup layer 2)" "$VAULT" \
  "$(aws backup describe-backup-vault --backup-vault-name "$VAULT" --region "$REGION" --query BackupVaultName --output text 2>/dev/null)"
PLANS=$(aws backup list-backup-plans --region "$REGION" --query "length(BackupPlansList[?starts_with(BackupPlanName, 'campuspulse')])" --output text 2>/dev/null)
check "a backup plan protects the table" "1" "${PLANS:-0}"
check "dashboard bucket keeps old versions (S3 versioning)" "Enabled" \
  "$(aws s3api get-bucket-versioning --bucket "$BUCKET" --query Status --output text 2>/dev/null)"

echo
echo "Network"
VPC=$(terraform -chdir="$TF" output -raw vpc_id)
check "api function runs inside the CampusPulse VPC" "$VPC" \
  "$(aws lambda get-function-configuration --function-name campuspulse-dev-api --region "$REGION" --query 'VpcConfig.VpcId' --output text 2>/dev/null)"
check "api function uses two subnets (two AZs)" "2" \
  "$(aws lambda get-function-configuration --function-name campuspulse-dev-api --region "$REGION" --query 'length(VpcConfig.SubnetIds)' --output text 2>/dev/null)"
check "VPC has no internet gateway" "0" \
  "$(aws ec2 describe-internet-gateways --region "$REGION" --filters Name=attachment.vpc-id,Values="$VPC" --query 'length(InternetGateways)' --output text 2>/dev/null)"
check "DynamoDB gateway endpoint is available" "available" \
  "$(aws ec2 describe-vpc-endpoints --region "$REGION" --filters Name=vpc-id,Values="$VPC" Name=service-name,Values="com.amazonaws.$REGION.dynamodb" --query 'VpcEndpoints[0].State' --output text 2>/dev/null | tr 'A-Z' 'a-z')"
check "VPC flow logs are active" "ACTIVE" \
  "$(aws ec2 describe-flow-logs --region "$REGION" --filter Name=resource-id,Values="$VPC" --query 'FlowLogs[0].FlowLogStatus' --output text 2>/dev/null)"

echo
echo "Identity"
COGNITO_GROUPS=$(aws cognito-idp list-groups --user-pool-id "$POOL" --region "$REGION" --query 'Groups[].GroupName' --output text 2>/dev/null)
if [[ "$COGNITO_GROUPS" == *"admin"* && "$COGNITO_GROUPS" == *"student"* ]]; then
  ok "both roles exist as Cognito groups (admin, student)"
else
  bad "both roles exist as Cognito groups" "admin student" "$COGNITO_GROUPS"
fi
MFA=$(aws cognito-idp describe-user-pool --user-pool-id "$POOL" --region "$REGION" --query 'UserPool.Policies.PasswordPolicy.MinimumLength' --output text 2>/dev/null)
check "password minimum length is 12" "12" "$MFA"

echo
echo "Compute"
for fn in api auth; do
  NAME=$(aws lambda get-function-configuration --function-name "campuspulse-dev-$fn" --region "$REGION" --query 'FunctionName' --output text 2>/dev/null)
  check "function $fn is deployed" "campuspulse-dev-$fn" "${NAME:-missing}"
done

echo
echo "Observability and cost"
BAD_RETENTION=$(aws logs describe-log-groups --log-group-name-prefix /aws/lambda/campuspulse --region "$REGION" \
  --query 'length(logGroups[?retentionInDays==`null`])' --output text 2>/dev/null)
check "no log group is set to never expire" "0" "${BAD_RETENTION:-?}"
check "seven alarms exist" "7" \
  "$(aws cloudwatch describe-alarms --alarm-name-prefix campuspulse --region "$REGION" --query 'length(MetricAlarms)' --output text 2>/dev/null)"
TOPIC=$(terraform -chdir="$TF" output -raw alerts_topic_arn)
CONFIRMED=$(aws sns list-subscriptions-by-topic --topic-arn "$TOPIC" --region "$REGION" \
  --query "length(Subscriptions[?SubscriptionArn!='PendingConfirmation'])" --output text 2>/dev/null)
if [ "${CONFIRMED:-0}" -ge 1 ] 2>/dev/null; then ok "team alert emails confirmed: $CONFIRMED address(es)"
else bad "at least one team alert email is confirmed" ">=1" "${CONFIRMED:-0} - click the AWS confirmation email (check spam)"; fi
BUDGETS=$(aws budgets describe-budgets --account-id "$(aws sts get-caller-identity --query Account --output text)" \
  --region us-east-1 --query 'length(Budgets)' --output text 2>/dev/null)
if [ "${BUDGETS:-0}" -ge 1 ] 2>/dev/null; then ok "a budget alert exists (mandatory, spec section 8)"
else bad "a budget alert exists (mandatory, spec section 8)" ">=1" "${BUDGETS:-none - the Billing console may be restricted}"; fi

echo
echo "Nothing expensive is running"
for svc in "ec2 describe-instances --query length(Reservations[].Instances[?State.Name=='running'][])" \
           "rds describe-db-instances --query length(DBInstances)" \
           "ec2 describe-nat-gateways --query length(NatGateways[?State=='available'])"; do
  NAME=$(echo "$svc" | awk '{print $1" "$2}')
  COUNT=$(eval aws $svc --region "$REGION" --output text 2>/dev/null)
  check "no $NAME resources" "0" "${COUNT:-0}"
done

echo
echo "The API answers"
HEALTH=$(curl -s -o /dev/null -w '%{http_code}' "$API/health" 2>/dev/null)
check "GET /health returns 200" "200" "${HEALTH:-no response}"
UNAUTH=$(curl -s -o /dev/null -w '%{http_code}' "$API/stats" 2>/dev/null)
check "GET /stats without a token returns 401" "401" "${UNAUTH:-no response}"

echo
echo "  $PASS passed, $FAIL failed"
echo
[ "$FAIL" -eq 0 ] || echo "  See docs/learning/20-troubleshooting.md"
exit $([ "$FAIL" -eq 0 ] && echo 0 || echo 1)
