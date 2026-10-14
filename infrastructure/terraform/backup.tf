# ---------------------------------------------------------------------------
# Backups (added after the professor's review, October 2026).
#
# Two independent layers, because a backup that lives in the same place as
# the thing it protects is only half a backup:
#
#   layer                  what it covers                  RPO        kept
#   ---------------------  ------------------------------  ---------  -------
#   DynamoDB PITR          any second in the last 35 days  ~5 min     35 days
#                          (dynamodb.tf)
#   AWS Backup, daily      full snapshot into a SEPARATE   24 h       backup_retention_days
#                          vault, own lifecycle
#   AWS Backup, weekly     longer-lived snapshot           7 days     backup_weekly_retention_days
#   S3 versioning          every version of the dashboard  0          noncurrent: 30 days
#                          files (s3.tf)
#
# Why AWS Backup on top of PITR? PITR is a feature OF the table: delete the
# table and its continuous backups go with it after a short window. An AWS
# Backup recovery point is a separate object in a separate vault, with its
# own retention and its own access policy, that survives the table.
#
# What is NOT backed up, stated plainly: Cognito users (re-created from the
# runbook in minutes - four demo accounts), and the Terraform state file
# (kept by its owner; see docs/deployment/).
#
# COST: AWS Backup for DynamoDB is billed per GB-month of backup storage
# (~$0.10-0.11/GB-month, eu-west-3 - verify with scripts/verify-prices.sh).
# Our table is well under 10 MB, so 7 daily + 4 weekly copies cost well under
# one cent a month. Restores are billed per GB restored - also cents.
# ---------------------------------------------------------------------------

resource "aws_backup_vault" "main" {
  name = "${local.name}-vault"
  # Encrypted with the AWS-managed key for AWS Backup (aws/backup) by default.

  # Lets `terraform destroy` remove the vault even though it holds recovery
  # points. Without it, destroy fails and the course cleanup is blocked.
  # Set to false if the data ever needs protecting from a stray destroy.
  force_destroy = true

  tags = {
    Name = "${local.name}-vault"
  }
}

resource "aws_backup_plan" "main" {
  name = "${local.name}-backup-plan"

  rule {
    rule_name         = "daily"
    target_vault_name = aws_backup_vault.main.name
    schedule          = "cron(0 3 * * ? *)" # 03:00 UTC, the quietest hour on campus
    start_window      = 60                  # minutes
    completion_window = 180

    lifecycle {
      delete_after = var.backup_retention_days
    }
  }

  rule {
    rule_name         = "weekly"
    target_vault_name = aws_backup_vault.main.name
    schedule          = "cron(0 4 ? * SUN *)" # Sundays 04:00 UTC
    start_window      = 60
    completion_window = 180

    lifecycle {
      delete_after = var.backup_weekly_retention_days
    }
  }

  tags = {
    Name = "${local.name}-backup-plan"
  }
}

# --- the role AWS Backup uses to read the table and write the snapshot -------
data "aws_iam_policy_document" "backup_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["backup.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "backup" {
  name               = "${local.name}-backup-role"
  assume_role_policy = data.aws_iam_policy_document.backup_assume.json
}

resource "aws_iam_role_policy_attachment" "backup" {
  role       = aws_iam_role.backup.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup"
}

resource "aws_iam_role_policy_attachment" "restore" {
  role       = aws_iam_role.backup.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForRestores"
}

# --- what the plan protects ---------------------------------------------------
resource "aws_backup_selection" "dynamodb" {
  name         = "${local.name}-events-table"
  plan_id      = aws_backup_plan.main.id
  iam_role_arn = aws_iam_role.backup.arn

  resources = [aws_dynamodb_table.events.arn]
}
