# ---------------------------------------------------------------------------
# The functions - TWO, down from five (professor's review, October 2026).
#
#   api   every route except POST /login. Runs INSIDE the VPC, in the private
#         subnets, and reaches DynamoDB only through the gateway endpoint.
#         handlers/api.py routes on the API Gateway routeKey.
#   auth  POST /login only. Runs OUTSIDE the VPC because it must call
#         Cognito's public endpoint, and holds no database permission.
#
# Why not one? Putting login inside the VPC would need a path to Cognito: a
# NAT Gateway (~$35/month) or a Cognito interface endpoint (~$8/month per AZ).
# Both break the cost rule. Two functions keep the cost at zero AND keep the
# important split: the function that can reach the internet cannot touch
# data; the function that touches data cannot reach the internet.
#
# PACKAGING: one zip of backend/src, shared by both functions. No dependencies
# are vendored: boto3 ships with the Lambda Python runtime.
# ---------------------------------------------------------------------------

data "archive_file" "backend" {
  type        = "zip"
  source_dir  = "${path.module}/../../backend/src"
  output_path = "${path.module}/build/backend.zip"
  excludes    = ["**/__pycache__/**"]
}

locals {
  # Changing this value alone redeploys both functions.
  source_hash = data.archive_file.backend.output_base64sha256
}

resource "aws_lambda_function" "api" {
  function_name    = "${local.name}-api"
  description      = "CampusPulse API router: events, requests, alerts, stats, health"
  role             = aws_iam_role.api.arn
  handler          = "handlers.api.handler"
  filename         = data.archive_file.backend.output_path
  source_code_hash = local.source_hash
  runtime          = "python3.12"
  # /stats holds a day of items in memory, and it is now in the same function
  # as everything else, so the function takes the old stats sizing. More
  # memory also means more CPU, so every route gets slightly faster.
  memory_size = 512
  timeout     = 15

  # Private subnets in two Availability Zones: if one AZ fails, Lambda keeps
  # running in the other. No public IP, no internet route - see vpc.tf.
  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      STAGE            = var.environment
      APP_VERSION      = var.app_version
      TABLE_NAME       = aws_dynamodb_table.events.name
      TTL_DAYS         = tostring(var.ttl_days)
      METRIC_NAMESPACE = var.metric_namespace
    }
  }

  # Log group first (explicit retention), and the VPC permissions must exist
  # before Lambda tries to create its network interfaces in the subnets.
  depends_on = [
    aws_cloudwatch_log_group.lambda,
    aws_iam_role_policy.api_vpc,
  ]
}

resource "aws_lambda_function" "auth" {
  function_name    = "${local.name}-auth"
  description      = "CampusPulse POST /login - Cognito only, no data access"
  role             = aws_iam_role.auth.arn
  handler          = "handlers.auth.handler"
  filename         = data.archive_file.backend.output_path
  source_code_hash = local.source_hash
  runtime          = "python3.12"
  memory_size      = 256
  timeout          = 10

  environment {
    variables = {
      STAGE             = var.environment
      APP_VERSION       = var.app_version
      COGNITO_CLIENT_ID = aws_cognito_user_pool_client.api.id
      METRIC_NAMESPACE  = var.metric_namespace
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda]
}
