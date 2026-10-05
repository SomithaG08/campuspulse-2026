# ---------------------------------------------------------------------------
# The public front door.
#
# HTTP API (v2), not REST API (v1): 3.5x cheaper, CORS is a setting rather
# than a per-method chore, and the JWT authorizer is built in. See AD-2.
#
# The authorizer is the security line that matters most: it verifies the
# token's signature, issuer, audience and expiry BEFORE any of our code runs.
# A flood of forged tokens costs us nothing because no Lambda is invoked.
# ---------------------------------------------------------------------------

resource "aws_apigatewayv2_api" "main" {
  name          = "${local.name}-api"
  protocol_type = "HTTP"
  description   = "CampusPulse 2026 - campus operations API"

  cors_configuration {
    # The dashboard is served from S3, a different origin from the API, so
    # without this the browser blocks every call while curl works perfectly.
    # "*" is acceptable here because the API carries no cookies and no
    # ambient authority: every protected call must present a bearer token.
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["content-type", "authorization"]
    max_age       = 300
  }
}

resource "aws_apigatewayv2_authorizer" "cognito" {
  api_id           = aws_apigatewayv2_api.main.id
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]
  name             = "${local.name}-jwt"

  jwt_configuration {
    # Only tokens issued by OUR pool, for OUR client, are accepted.
    audience = [aws_cognito_user_pool_client.api.id]
    issuer   = "https://cognito-idp.${var.region}.amazonaws.com/${aws_cognito_user_pool.main.id}"
  }
}

# --- integrations ----------------------------------------------------------
# AWS_PROXY with payload format 2.0: API Gateway hands the whole request to
# Lambda as a JSON event and returns whatever Lambda gives back.

resource "aws_apigatewayv2_integration" "health" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.health.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "auth" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.auth.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "ingest" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.ingest.invoke_arn
  payload_format_version = "2.0"
}

# --- routes ----------------------------------------------------------------
# Two public routes and two protected ones. A route with no authorizer is
# reachable by anyone on the internet, so each one below is a deliberate
# decision, not a default.

resource "aws_apigatewayv2_route" "health" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /health"
  target    = "integrations/${aws_apigatewayv2_integration.health.id}"
  # Public: it returns a constant and touches nothing.
}

resource "aws_apigatewayv2_route" "login" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /login"
  target    = "integrations/${aws_apigatewayv2_integration.auth.id}"
  # Public by necessity: this is where you go to GET a token.
}

resource "aws_apigatewayv2_route" "post_events" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /events"
  target             = "integrations/${aws_apigatewayv2_integration.ingest.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
  # The ops-only check happens inside the function; the authorizer only
  # establishes WHO is calling.
}

resource "aws_apigatewayv2_route" "post_requests" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /requests"
  target             = "integrations/${aws_apigatewayv2_integration.ingest.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# --- read path routes (Phase 6) -------------------------------------------
# All three require a token. The role check inside each function decides
# whether this particular caller may see this particular view.

resource "aws_apigatewayv2_integration" "query" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.query.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "stats" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.stats.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "get_events" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /events"
  target             = "integrations/${aws_apigatewayv2_integration.query.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "get_alerts" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /alerts"
  target             = "integrations/${aws_apigatewayv2_integration.query.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
  # ops-only, enforced in the function
}

resource "aws_apigatewayv2_route" "get_stats" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /stats"
  target             = "integrations/${aws_apigatewayv2_integration.stats.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_lambda_permission" "query" {
  statement_id  = "AllowAPIGatewayInvokeQuery"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.query.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "stats" {
  statement_id  = "AllowAPIGatewayInvokeStats"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.stats.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# --- stage -----------------------------------------------------------------

resource "aws_cloudwatch_log_group" "api_access" {
  name              = "/aws/apigateway/${local.name}"
  retention_in_days = var.log_retention_days
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true

  # Throttling is a budget control as much as a security one: it caps how much
  # a runaway simulator loop or a hostile script can cost us.
  default_route_settings {
    throttling_rate_limit  = var.throttle_rate_limit
    throttling_burst_limit = var.throttle_burst_limit
  }

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_access.arn
    # One JSON line per request. This is what tells you whether a failure
    # happened at the edge (401 from the authorizer, never reaching Lambda) or
    # inside the function - the first question in any API investigation.
    format = jsonencode({
      requestId      = "$context.requestId"
      httpMethod     = "$context.httpMethod"
      path           = "$context.path"
      status         = "$context.status"
      responseLength = "$context.responseLength"
      latency        = "$context.responseLatency"
      integrationErr = "$context.integrationErrorMessage"
      authError      = "$context.authorizer.error"
      sourceIp       = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
    })
  }
}

# --- permissions -----------------------------------------------------------
# A Lambda does not accept invocations from a service unless that service is
# explicitly permitted. Without these, every route returns 500.

resource "aws_lambda_permission" "health" {
  statement_id  = "AllowAPIGatewayInvokeHealth"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.health.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "auth" {
  statement_id  = "AllowAPIGatewayInvokeAuth"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.auth.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "ingest" {
  statement_id  = "AllowAPIGatewayInvokeIngest"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingest.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}
