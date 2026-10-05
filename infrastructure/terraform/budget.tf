# ---------------------------------------------------------------------------
# THE BUDGET ALERT IS CREATED FIRST, BEFORE ANYTHING ELSE.
#
# Requirement C2 of the project spec makes a billing alert mandatory, and the
# reason is not bureaucratic: a budget created after the resources is a smoke
# detector installed after the fire.
#
# include_credit = false is the important line. By default a cost budget counts
# the bill AFTER credits are applied, which on a credit-funded account reads
# $0.00 right up until the credits are gone. Excluding credits means this
# budget tracks what we are ACTUALLY consuming, which is the number we need to
# watch.
# ---------------------------------------------------------------------------

resource "aws_budgets_budget" "monthly" {
  name         = "${local.name}-monthly"
  budget_type  = "COST"
  limit_amount = tostring(var.budget_limit_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  cost_types {
    include_credit = false # track real usage, not the post-credit bill
    include_refund = false
    include_tax    = true
  }

  # Warn early, warn again, then warn on forecast.
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 50
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.notification_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.notification_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.notification_email]
  }
}
