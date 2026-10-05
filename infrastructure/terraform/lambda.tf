# ---------------------------------------------------------------------------
# The functions.
#
# PACKAGING: one zip of backend/src, shared by every function. Each function
# points at a different handler inside it. This means one artifact to build
# and no chance of two functions running different versions of the validation
# code - which is the sort of drift that produces a bug nobody can reproduce.
#
# No dependencies are vendored: boto3 is already in the Lambda Python runtime,
# and our own code imports nothing else. The zip is a few kilobytes, which
# keeps cold starts short.
#
# Phase 5 deploys the WRITE path: health, auth, ingest. The read path (query,
# stats) and its routes arrive in Phase 6.
# ---------------------------------------------------------------------------

data "archive_file" "backend" {
  type        = "zip"
  source_dir  = "${path.module}/../../backend/src"
  output_path = "${path.module}/build/backend.zip"
}

locals {
  # Changing this value alone redeploys every function, which is what you want
  # when only the code changed.
  source_hash = data.archive_file.backend.output_base64sha256

  lambda_defaults = {
    runtime     = "python3.12"
    memory_size = 256 # more memory also means more CPU; 256MB is a good
    timeout     = 10  # price/latency point for work this small
  }
}

resource "aws_lambda_function" "health" {
  function_name    = "${local.name}-health"
  role             = aws_iam_role.health.arn
  handler          = "handlers.health.handler"
  filename         = data.archive_file.backend.output_path
  source_code_hash = local.source_hash
  runtime          = local.lambda_defaults.runtime
  memory_size      = 128 # it returns a constant; it needs nothing
  timeout          = 3

  environment {
    variables = {
      STAGE       = var.environment
      APP_VERSION = var.app_version
    }
  }

  # Without this, Lambda creates its own log group on first invocation with
  # retention set to "never expire".
  depends_on = [aws_cloudwatch_log_group.lambda]
}

resource "aws_lambda_function" "auth" {
  function_name    = "${local.name}-auth"
  role             = aws_iam_role.auth.arn
  handler          = "handlers.auth.handler"
  filename         = data.archive_file.backend.output_path
  source_code_hash = local.source_hash
  runtime          = local.lambda_defaults.runtime
  memory_size      = local.lambda_defaults.memory_size
  timeout          = local.lambda_defaults.timeout

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

resource "aws_lambda_function" "ingest" {
  function_name    = "${local.name}-ingest"
  role             = aws_iam_role.ingest.arn
  handler          = "handlers.ingest.handler"
  filename         = data.archive_file.backend.output_path
  source_code_hash = local.source_hash
  runtime          = local.lambda_defaults.runtime
  memory_size      = local.lambda_defaults.memory_size
  timeout          = local.lambda_defaults.timeout

  environment {
    variables = {
      STAGE            = var.environment
      APP_VERSION      = var.app_version
      TABLE_NAME       = aws_dynamodb_table.events.name
      TTL_DAYS         = tostring(var.ttl_days)
      METRIC_NAMESPACE = var.metric_namespace
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda]
}

# --- read path (Phase 6) ---------------------------------------------------
# Same zip, different handlers, read-only roles.

resource "aws_lambda_function" "query" {
  function_name    = "${local.name}-query"
  role             = aws_iam_role.query.arn
  handler          = "handlers.query.handler"
  filename         = data.archive_file.backend.output_path
  source_code_hash = local.source_hash
  runtime          = local.lambda_defaults.runtime
  memory_size      = local.lambda_defaults.memory_size
  timeout          = local.lambda_defaults.timeout

  environment {
    variables = {
      STAGE            = var.environment
      APP_VERSION      = var.app_version
      TABLE_NAME       = aws_dynamodb_table.events.name
      METRIC_NAMESPACE = var.metric_namespace
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda]
}

resource "aws_lambda_function" "stats" {
  function_name    = "${local.name}-stats"
  role             = aws_iam_role.stats.arn
  handler          = "handlers.stats.handler"
  filename         = data.archive_file.backend.output_path
  source_code_hash = local.source_hash
  runtime          = local.lambda_defaults.runtime
  # Aggregation holds a day of items in memory, so it gets a little more room.
  # More memory also means more CPU, which makes the summarise pass faster.
  memory_size = 512
  timeout     = 15

  environment {
    variables = {
      STAGE            = var.environment
      APP_VERSION      = var.app_version
      TABLE_NAME       = aws_dynamodb_table.events.name
      METRIC_NAMESPACE = var.metric_namespace
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda]
}
