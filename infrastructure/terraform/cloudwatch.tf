# ---------------------------------------------------------------------------
# Log groups are created HERE, before the functions exist, for one reason:
# if Lambda creates its own log group on first invocation, that group has
# retention set to "Never expire". Logs then accumulate forever and quietly
# consume the 5 GB free allowance and then real money.
#
# Creating them ourselves with an explicit retention is a one-line fix to a
# cost leak that most student projects never notice.
# ---------------------------------------------------------------------------

locals {
  # Two functions since the October 2026 consolidation (was five).
  functions = ["api", "auth"]
}

resource "aws_cloudwatch_log_group" "lambda" {
  for_each = toset(local.functions)

  name              = "/aws/lambda/${local.name}-${each.key}"
  retention_in_days = var.log_retention_days

  tags = {
    Name = "${local.name}-${each.key}-logs"
  }
}

# Alarms on the Lambda functions come in Phase 10, once the functions exist
# and we know what normal looks like. An alarm threshold invented before the
# system has ever run is a guess, and a guessed threshold either never fires
# or never stops firing.
