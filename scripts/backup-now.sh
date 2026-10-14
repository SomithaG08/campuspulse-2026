#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Takes an on-demand AWS Backup of the events table, right now, and waits for
# it to finish. Use it to produce backup evidence without waiting for the
# 03:00 UTC scheduled run, and before any risky change.
#
# Usage:  bash scripts/backup-now.sh
# Evidence: screenshot the output, or AWS Backup console -> Backup vaults ->
#           campuspulse-dev-vault -> Recovery points.
# ---------------------------------------------------------------------------
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF="$ROOT/infrastructure/terraform"

VAULT=$(terraform -chdir="$TF" output -raw backup_vault_name)
ROLE=$(terraform -chdir="$TF" output -raw backup_role_arn)
TABLE_ARN=$(terraform -chdir="$TF" output -raw dynamodb_table_arn)
REGION=$(terraform -chdir="$TF" output -raw region)

echo "vault : $VAULT"
echo "table : $TABLE_ARN"

JOB=$(aws backup start-backup-job --region "$REGION" \
  --backup-vault-name "$VAULT" \
  --resource-arn "$TABLE_ARN" \
  --iam-role-arn "$ROLE" \
  --lifecycle DeleteAfterDays=7 \
  --query BackupJobId --output text)
echo "backup job: $JOB"

START=$(date +%s)
while true; do
  STATE=$(aws backup describe-backup-job --region "$REGION" --backup-job-id "$JOB" \
    --query State --output text)
  echo "  $(date -u +%H:%M:%S)  $STATE"
  case "$STATE" in
    COMPLETED) break ;;
    FAILED|ABORTED|EXPIRED) echo "backup did not complete: $STATE"; exit 1 ;;
  esac
  sleep 10
done

echo
echo "Backup completed in $(( $(date +%s) - START )) s."
aws backup list-recovery-points-by-backup-vault --region "$REGION" \
  --backup-vault-name "$VAULT" \
  --query 'RecoveryPoints[].{created:CreationDate,status:Status,arn:RecoveryPointArn}' \
  --output table
