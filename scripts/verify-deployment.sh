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
check "both secondary indexes exist" "2" \
  "$(aws dynamodb describe-table --table-name "$TABLE" --region "$REGION" --query 'length(Table.GlobalSecondaryIndexes)' --output text 2>/dev/null)"
check "TTL is enabled (storage stays small)" "ENABLED" \
  "$(aws dynamodb describe-time-to-live --table-name "$TABLE" --region "$REGION" --query 'TimeToLiveDescription.TimeToLiveStatus' --output text 2>/dev/null)"
check "point-in-time recovery is on (our entire DR story)" "ENABLED" \
  "$(aws dynamodb describe-continuous-backups --table-name "$TABLE" --region "$REGION" --query 'ContinuousBackupsDescription.PointInTimeRecoveryDescription.PointInTimeRecoveryStatus' --output text 2>/dev/null)"

echo
echo "Identity"
check "both roles exist as Cognito groups" "ops staff" \
  "$(aws cognito-idp list-groups --user-pool-id "$POOL" --region "$REGION" --query 'sort_by(Groups,&GroupName)[].GroupName' --output text 2>/dev/null | tr '\t' ' ')"
MFA=$(aws cognito-idp describe-user-pool --user-pool-id "$POOL" --region "$REGION" --query 'UserPool.Policies.PasswordPolicy.MinimumLength' --output text 2>/dev/null)
check "password minimum length is 12" "12" "$MFA"

echo
echo "Compute"
for fn in health auth ingest query stats; do
  NAME=$(aws lambda get-function-configuration --function-name "campuspulse-dev-$fn" --region "$REGION" --query 'FunctionName' --output text 2>/dev/null)
  check "function $fn is deployed" "campuspulse-dev-$fn" "${NAME:-missing}"
done

echo
echo "Observability and cost"
BAD_RETENTION=$(aws logs describe-log-groups --log-group-name-prefix /aws/lambda/campuspulse --region "$REGION" \
  --query 'length(logGroups[?retentionInDays==`null`])' --output text 2>/dev/null)
check "no log group is set to never expire" "0" "${BAD_RETENTION:-?}"
check "four alarms exist" "4" \
  "$(aws cloudwatch describe-alarms --alarm-name-prefix campuspulse --region "$REGION" --query 'length(MetricAlarms)' --output text 2>/dev/null)"
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
