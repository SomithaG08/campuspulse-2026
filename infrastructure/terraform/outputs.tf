# These values are needed by the deployment script, the simulator config and
# the dashboard config. Print them with `terraform output`.

output "region" {
  value = var.region
}

output "dynamodb_table_name" {
  description = "Set as an environment variable on every Lambda."
  value       = aws_dynamodb_table.events.name
}

output "dynamodb_table_arn" {
  value = aws_dynamodb_table.events.arn
}

output "cognito_user_pool_id" {
  description = "Needed by cp-auth and by the API Gateway JWT authorizer."
  value       = aws_cognito_user_pool.main.id
}

output "cognito_client_id" {
  description = "Needed by cp-auth, the simulator and the dashboard."
  value       = aws_cognito_user_pool_client.api.id
}

output "cognito_issuer_url" {
  description = "The JWT authorizer's issuer. Phase 5 uses this."
  value       = "https://cognito-idp.${var.region}.amazonaws.com/${aws_cognito_user_pool.main.id}"
}

output "lambda_role_arns" {
  description = "One role per function - attach in Phase 5."
  value = {
    auth   = aws_iam_role.auth.arn
    ingest = aws_iam_role.ingest.arn
    query  = aws_iam_role.query.arn
    stats  = aws_iam_role.stats.arn
  }
}

output "site_bucket_name" {
  value = aws_s3_bucket.site.id
}

output "site_url" {
  description = "Where the dashboard will live once Phase 9 uploads it."
  value       = "http://${aws_s3_bucket_website_configuration.site.website_endpoint}"
}

output "budget_name" {
  value = aws_budgets_budget.monthly.name
}

output "api_endpoint" {
  description = "Base URL of the API. The simulator and the dashboard both need this."
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "smoke_test" {
  description = "Paste this to confirm the API is alive."
  value       = "curl -s ${aws_apigatewayv2_stage.default.invoke_url}/health"
}

output "cloudwatch_dashboard_url" {
  description = "The operations dashboard - screenshot this for the report."
  value       = "https://${var.region}.console.aws.amazon.com/cloudwatch/home?region=${var.region}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
}

output "alarm_names" {
  value = [
    aws_cloudwatch_metric_alarm.ingest_errors.alarm_name,
    aws_cloudwatch_metric_alarm.api_5xx.alarm_name,
    aws_cloudwatch_metric_alarm.alert_burst.alarm_name,
    aws_cloudwatch_metric_alarm.invocation_ceiling.alarm_name,
  ]
}
