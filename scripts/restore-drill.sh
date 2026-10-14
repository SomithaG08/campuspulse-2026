#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Disaster-recovery drill: restores the LATEST AWS Backup recovery point into
# a NEW table, measures how long it took (this is our measured RTO), counts
# the items, then deletes the restored copy.
#
# It never touches the live table. Restoring "in place" is not possible with
# DynamoDB anyway: a restore always creates a new table, and switching the
# application to it is a one-line change of TABLE_NAME (see
# docs/learning/19-disaster-recovery.md).
#
# Usage:  bash scripts/restore-drill.sh            # restore, measure, clean up
#         KEEP=1 bash scripts/restore-drill.sh     # keep the restored table
# Cost: restore is billed per GB restored - our table is a few MB, so cents.
# ---------------------------------------------------------------------------
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF="$ROOT/infrastructure/terraform"

VAULT=$(terraform -chdir="$TF" output -raw backup_vault_name)
ROLE=$(terraform -chdir="$TF" output -raw backup_role_arn)
TABLE=$(terraform -chdir="$TF" output -raw dynamodb_table_name)
REGION=$(terraform -chdir="$TF" output -raw region)
TARGET="${TABLE}-restore-$(date -u +%Y%m%d%H%M)"

RP=$(aws backup list-recovery-points-by-backup-vault --region "$REGION" \
  --backup-vault-name "$VAULT" \
  --query 'sort_by(RecoveryPoints[?Status==`COMPLETED`], &CreationDate)[-1].RecoveryPointArn' \
  --output text)
[ "$RP" = "None" ] || [ -z "$RP" ] && { echo "No completed recovery point yet - run scripts/backup-now.sh first."; exit 1; }

echo "recovery point : $RP"
echo "restoring into : $TARGET"

START=$(date +%s)
JOB=$(aws backup start-restore-job --region "$REGION" \
  --recovery-point-arn "$RP" \
  --iam-role-arn "$ROLE" \
  --metadata "TargetTableName=$TARGET" \
  --query RestoreJobId --output text)
echo "restore job    : $JOB"

while true; do
  STATE=$(aws backup describe-restore-job --region "$REGION" --restore-job-id "$JOB" \
    --query Status --output text)
  echo "  $(date -u +%H:%M:%S)  $STATE"
  case "$STATE" in
    COMPLETED) break ;;
    FAILED|ABORTED) echo "restore did not complete: $STATE"; exit 1 ;;
  esac
  sleep 15
done
aws dynamodb wait table-exists --region "$REGION" --table-name "$TARGET"
ELAPSED=$(( $(date +%s) - START ))

LIVE=$(aws dynamodb scan --region "$REGION" --table-name "$TABLE"  --select COUNT --query Count --output text)
COPY=$(aws dynamodb scan --region "$REGION" --table-name "$TARGET" --select COUNT --query Count --output text)

echo
echo "=================  RESTORE DRILL RESULT  ================="
echo " restored table : $TARGET"
echo " measured RTO   : ${ELAPSED} s (backup -> usable table)"
echo " items live     : $LIVE"
echo " items restored : $COPY   (fewer is expected: events written since the backup)"
echo "=========================================================="

if [ "${KEEP:-0}" != "1" ]; then
  aws dynamodb delete-table --region "$REGION" --table-name "$TARGET" >/dev/null
  echo "restored copy deleted (set KEEP=1 to keep it)."
fi
