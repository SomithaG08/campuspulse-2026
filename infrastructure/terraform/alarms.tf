# ---------------------------------------------------------------------------
# Alarms, email alerts to the team, and the operations dashboard.
#
# PROFESSOR'S REVIEW (October 2026): "alerts should be redirected to the team
# with school mail". Every alarm below now notifies one SNS topic, and that
# topic emails every address in var.alert_emails - the team's @epita.fr
# addresses (set in terraform.tfvars, which is gitignored). A Microsoft Teams
# channel can be added to the same list: every Teams channel has an email
# address (channel menu -> "Get email address"), and mail sent to it is posted
# in the channel.
#
# The two alarms that matter most to the campus are new:
#   critical-alert   any CRITICAL campus event (room >120% full, temperature
#                    outside the safe range, equipment failed, ...)
#   urgent-request   any URGENT student service request (priority 3)
# Both fire within about a minute and email the team immediately.
#
# HOW THE MAIL FLOWS, AND WHY IT COSTS NOTHING
#   api Lambda prints an EMF log line -> CloudWatch metric -> alarm -> SNS ->
#   email. The Lambda never calls SNS itself: it sits in private subnets with
#   no internet route, and an SNS interface endpoint would cost ~$8/month per
#   AZ. Alarms are free up to 10, SNS email is free up to 1,000 a month.
#
# An alarm emails on a STATE CHANGE (OK -> ALARM), not once per event. A room
# that stays overloaded produces one email, not one every ten seconds, and an
# "OK" email when it clears. That is what an on-call inbox needs.
#
# FREE-TIER BUDGET (CloudWatch pricing page):
#   10 alarm metrics free  -> we use 7
#   3 custom dashboards    -> we use 1
#   10 custom metrics      -> we use 9 (EventsIngested x3 severities + total,
#                             AlertsRaised x2 severities + total,
#                             UrgentRequests, StatsRequested)
#
# ON THE THRESHOLDS, HONESTLY: alert-burst and invocation-ceiling are initial
# guesses, kept as variables so they can be tuned from a real run. The error,
# critical-alert and urgent-request thresholds are not guesses: at our volume,
# one of any of them is worth a human looking.
# ---------------------------------------------------------------------------

# --- the team's alert inbox ---------------------------------------------------
resource "aws_sns_topic" "alerts" {
  name = "${local.name}-alerts"
  # Deliberately NOT encrypted with the AWS-managed key alias/aws/sns:
  # CloudWatch alarms cannot publish to a topic using that key (its key
  # policy cannot be edited to admit CloudWatch), so the alarm would fire and
  # the email would silently never arrive. Encryption would need a
  # customer-managed KMS key at $1/month; the messages hold an alarm name and
  # a room number, not personal data, so we accept that. Noted in the threat
  # model.
}

# Only CloudWatch alarms of THIS project may publish to the topic.
data "aws_iam_policy_document" "alerts_topic" {
  statement {
    sid     = "AllowCloudWatchAlarms"
    effect  = "Allow"
    actions = ["sns:Publish"]
    principals {
      type        = "Service"
      identifiers = ["cloudwatch.amazonaws.com"]
    }
    resources = [aws_sns_topic.alerts.arn]
    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:aws:cloudwatch:${var.region}:${data.aws_caller_identity.current.account_id}:alarm:${local.name}-*"]
    }
  }
}

resource "aws_sns_topic_policy" "alerts" {
  arn    = aws_sns_topic.alerts.arn
  policy = data.aws_iam_policy_document.alerts_topic.json
}

resource "aws_sns_topic_subscription" "team_email" {
  for_each  = toset(var.alert_emails)
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = each.value
  # AWS sends each address a confirmation email ("AWS Notification -
  # Subscription Confirmation"). Until it is clicked, nothing arrives. With
  # school mail, check the spam/quarantine folder - university filters often
  # hold the first message from no-reply@sns.amazonaws.com.
}

locals {
  alarm_actions = [aws_sns_topic.alerts.arn]
}

# --- 1. the system is broken -----------------------------------------------
resource "aws_cloudwatch_metric_alarm" "api_errors" {
  alarm_name        = "${local.name}-api-errors"
  alarm_description = "The api Lambda raised at least one error in 5 minutes. Check /aws/lambda/${local.name}-api, filter level=ERROR."

  namespace   = "AWS/Lambda"
  metric_name = "Errors"
  dimensions  = { FunctionName = aws_lambda_function.api.function_name }

  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = var.alarm_error_threshold
  comparison_operator = "GreaterThanOrEqualToThreshold"

  # Without this, a period with no invocations at all counts as INSUFFICIENT_DATA
  # and the alarm sits grey instead of green. Treating "no data" as OK is right
  # here: no traffic is not a failure.
  treat_missing_data = "notBreaching"
  alarm_actions      = local.alarm_actions
  ok_actions         = local.alarm_actions
}

# --- 2. the front door is failing ------------------------------------------
resource "aws_cloudwatch_metric_alarm" "api_5xx" {
  alarm_name        = "${local.name}-api-5xx"
  alarm_description = "The API returned server errors. Check the API access log for integrationErrorMessage, then the function's own log."

  namespace   = "AWS/ApiGateway"
  metric_name = "5xx"
  dimensions  = { ApiId = aws_apigatewayv2_api.main.id }

  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions
}

# --- 3. the campus is having a bad day -------------------------------------
# The only alarm about the DOMAIN rather than the infrastructure. One room over
# capacity is normal campus life; twenty alerts in five minutes suggests
# something systemic - or a simulator left running with --force-alert.
resource "aws_cloudwatch_metric_alarm" "alert_burst" {
  alarm_name        = "${local.name}-alert-burst"
  alarm_description = "Unusually many alerts campus-wide in 5 minutes. Either something systemic, or a simulator left on --force-alert."

  namespace   = var.metric_namespace
  metric_name = "AlertsRaised" # the dimensionless campus-wide total (log.metric aggregate=True)

  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = var.alarm_alert_burst
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions
}

# --- 4. the budget is under attack -----------------------------------------
# A cost guard, not a performance one. A runaway loop or a hostile script shows
# up here long before it shows up on the monthly bill.
resource "aws_cloudwatch_metric_alarm" "invocation_ceiling" {
  alarm_name        = "${local.name}-invocation-ceiling"
  alarm_description = "Far more invocations than a demo produces. Suspect a runaway simulator or an open loop. Check the API access log for the source IP."

  namespace   = "AWS/Lambda"
  metric_name = "Invocations"
  dimensions  = { FunctionName = aws_lambda_function.api.function_name }

  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = var.alarm_invocation_ceiling
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions
}

# --- 5. a critical campus event: email the team now -------------------------
resource "aws_cloudwatch_metric_alarm" "critical_alert" {
  alarm_name        = "${local.name}-critical-alert"
  alarm_description = "CRITICAL campus event in the last minute (overloaded room, unsafe temperature/humidity, failed equipment, or urgent request). Open the admin page -> Active alerts for the room and the reason."

  namespace   = var.metric_namespace
  metric_name = "AlertsRaised"
  dimensions  = { Severity = "critical" }

  statistic           = "Sum"
  period              = 60
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions
}

# --- 6. an urgent student request: email the team now -----------------------
resource "aws_cloudwatch_metric_alarm" "urgent_request" {
  alarm_name        = "${local.name}-urgent-request"
  alarm_description = "A student raised an URGENT service request. Open the admin page -> Student requests to see who, where and what."

  namespace   = var.metric_namespace
  metric_name = "UrgentRequests"

  statistic           = "Sum"
  period              = 60
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions
}

# --- 7. login is failing ------------------------------------------------------
resource "aws_cloudwatch_metric_alarm" "auth_errors" {
  alarm_name        = "${local.name}-auth-errors"
  alarm_description = "The auth Lambda raised an error: nobody can sign in. Check /aws/lambda/${local.name}-auth."

  namespace   = "AWS/Lambda"
  metric_name = "Errors"
  dimensions  = { FunctionName = aws_lambda_function.auth.function_name }

  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = var.alarm_error_threshold
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions
}

# --- the dashboard ----------------------------------------------------------
# Six widgets, arranged so the top row answers "is it working?" and the bottom
# row answers "what is it doing?".
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${local.name}-operations"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric", x = 0, y = 0, width = 12, height = 6,
        properties = {
          title  = "Requests and errors",
          region = var.region,
          view   = "timeSeries",
          stat   = "Sum",
          period = 60,
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", aws_lambda_function.api.function_name, { label = "api" }],
            [".", ".", ".", aws_lambda_function.auth.function_name, { label = "auth (logins)" }],
            [".", "Errors", ".", aws_lambda_function.api.function_name, { label = "api errors" }],
            [".", "Errors", ".", aws_lambda_function.auth.function_name, { label = "auth errors" }],
          ]
        }
      },
      {
        type = "metric", x = 12, y = 0, width = 12, height = 6,
        properties = {
          title  = "Latency (p95 ms)",
          region = var.region,
          view   = "timeSeries",
          stat   = "p95",
          period = 60,
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", aws_lambda_function.api.function_name, { label = "api" }],
            [".", ".", ".", aws_lambda_function.auth.function_name, { label = "auth" }],
          ]
        }
      },
      {
        type = "metric", x = 0, y = 6, width = 12, height = 6,
        properties = {
          title  = "Campus events and alerts",
          region = var.region,
          view   = "timeSeries",
          stat   = "Sum",
          period = 300,
          metrics = [
            [var.metric_namespace, "EventsIngested", { label = "events" }],
            [var.metric_namespace, "AlertsRaised", { label = "alerts (all)" }],
            [var.metric_namespace, "AlertsRaised", "Severity", "critical", { label = "critical" }],
            [var.metric_namespace, "UrgentRequests", { label = "urgent student requests" }],
          ]
        }
      },
      {
        type = "metric", x = 12, y = 6, width = 12, height = 6,
        properties = {
          title  = "API responses by class",
          region = var.region,
          view   = "timeSeries",
          stat   = "Sum",
          period = 60,
          metrics = [
            ["AWS/ApiGateway", "Count", "ApiId", aws_apigatewayv2_api.main.id, { label = "total" }],
            [".", "4xx", ".", ".", { label = "4xx (client)" }],
            [".", "5xx", ".", ".", { label = "5xx (server)" }],
          ]
        }
      },
      {
        type = "metric", x = 0, y = 12, width = 12, height = 6,
        properties = {
          title  = "DynamoDB capacity consumed",
          region = var.region,
          view   = "timeSeries",
          stat   = "Sum",
          period = 300,
          metrics = [
            ["AWS/DynamoDB", "ConsumedWriteCapacityUnits", "TableName", aws_dynamodb_table.events.name, { label = "writes" }],
            [".", "ConsumedReadCapacityUnits", ".", ".", { label = "reads" }],
          ]
        }
      },
      {
        type = "log", x = 12, y = 12, width = 12, height = 6,
        properties = {
          title  = "Recent errors and warnings",
          region = var.region,
          query  = "SOURCE '/aws/lambda/${local.name}-api' | fields @timestamp, level, message, reason, request_id | filter level in [\"ERROR\", \"WARN\"] | sort @timestamp desc | limit 20"
        }
      },
    ]
  })
}
