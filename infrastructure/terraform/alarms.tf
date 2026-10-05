# ---------------------------------------------------------------------------
# Alarms and the operations dashboard.
#
# FREE-TIER BUDGET (verified on the CloudWatch pricing page):
#   10 alarm metrics free  -> we use 4
#   3 custom dashboards    -> we use 1
#   10 custom metrics      -> we use 3 (EventsIngested, AlertsRaised, StatsRequested)
#
# ON THE THRESHOLDS, HONESTLY
# ---------------------------
# Two of the four are initial guesses. A threshold invented before a system has
# ever run is exactly that, and pretending otherwise would be the kind of
# unfounded claim this project avoids elsewhere. They are variables so they can
# be corrected from a real run, and the report records both the guess and the
# tuned value - which is a better story than a number that was always "right".
#
# The error alarm is NOT a guess: at our volume any Lambda error is worth a look.
# ---------------------------------------------------------------------------

# --- optional email ---------------------------------------------------------
# Alarms work without this: they change state and show red in the console,
# which is enough to demonstrate. Set alarm_email to also get an email, which
# is the optional feature O2 from the scope document.
resource "aws_sns_topic" "alarms" {
  count = var.alarm_email == "" ? 0 : 1
  name  = "${local.name}-alarms"
}

resource "aws_sns_topic_subscription" "alarms_email" {
  count     = var.alarm_email == "" ? 0 : 1
  topic_arn = aws_sns_topic.alarms[0].arn
  protocol  = "email"
  endpoint  = var.alarm_email
  # AWS sends a confirmation email. Until someone clicks it, nothing arrives -
  # a step that is easy to forget and then blame on the alarm.
}

locals {
  alarm_actions = var.alarm_email == "" ? [] : [aws_sns_topic.alarms[0].arn]
}

# --- 1. the system is broken -----------------------------------------------
resource "aws_cloudwatch_metric_alarm" "ingest_errors" {
  alarm_name        = "${local.name}-ingest-errors"
  alarm_description = "cp-ingest raised at least one error in 5 minutes. Check its log group, filter level=ERROR."

  namespace   = "AWS/Lambda"
  metric_name = "Errors"
  dimensions  = { FunctionName = aws_lambda_function.ingest.function_name }

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
  metric_name = "AlertsRaised"

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
  dimensions  = { FunctionName = aws_lambda_function.ingest.function_name }

  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = var.alarm_invocation_ceiling
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions
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
            ["AWS/Lambda", "Invocations", "FunctionName", aws_lambda_function.ingest.function_name, { label = "ingest" }],
            [".", ".", ".", aws_lambda_function.query.function_name, { label = "query" }],
            [".", ".", ".", aws_lambda_function.stats.function_name, { label = "stats" }],
            [".", "Errors", ".", aws_lambda_function.ingest.function_name, { label = "ingest errors" }],
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
            ["AWS/Lambda", "Duration", "FunctionName", aws_lambda_function.ingest.function_name, { label = "ingest" }],
            [".", ".", ".", aws_lambda_function.stats.function_name, { label = "stats" }],
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
            [var.metric_namespace, "AlertsRaised", { label = "alerts" }],
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
          query  = "SOURCE '/aws/lambda/${local.name}-ingest' | fields @timestamp, level, message, reason, request_id | filter level in [\"ERROR\", \"WARN\"] | sort @timestamp desc | limit 20"
        }
      },
    ]
  })
}
