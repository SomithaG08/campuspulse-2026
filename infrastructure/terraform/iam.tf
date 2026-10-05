# ---------------------------------------------------------------------------
# One role per Lambda. This file is where "least privilege" stops being a word
# in a report and becomes something an examiner can read.
#
# The function exposed to the internet (cp-ingest) can WRITE and cannot READ.
# The functions that read cannot write. If an attacker found a bug in ingest,
# they could add junk events - they could not read a single student request.
#
# The roles are created now even though the functions arrive in Phase 5: a
# role is an identity, it does not need the function to exist.
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

# Every function may write its own logs, and nothing else.
data "aws_iam_policy_document" "logs" {
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${local.name}-*:*"]
  }
}

resource "aws_iam_policy" "logs" {
  name   = "${local.name}-logs"
  policy = data.aws_iam_policy_document.logs.json
}

# --- cp-ingest: write only -------------------------------------------------
resource "aws_iam_role" "ingest" {
  name               = "${local.name}-ingest-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "ingest" {
  statement {
    effect    = "Allow"
    actions   = ["dynamodb:PutItem"]
    resources = [aws_dynamodb_table.events.arn]
  }
}

resource "aws_iam_role_policy" "ingest" {
  name   = "${local.name}-ingest-policy"
  role   = aws_iam_role.ingest.id
  policy = data.aws_iam_policy_document.ingest.json
}

resource "aws_iam_role_policy_attachment" "ingest_logs" {
  role       = aws_iam_role.ingest.name
  policy_arn = aws_iam_policy.logs.arn
}

# --- cp-query and cp-stats: read only --------------------------------------
# Both need exactly the same permission, so they share a policy document but
# keep separate roles - separate roles mean we can tighten one later without
# touching the other.
data "aws_iam_policy_document" "read_events" {
  statement {
    effect  = "Allow"
    actions = ["dynamodb:Query"] # deliberately NOT dynamodb:Scan
    resources = [
      aws_dynamodb_table.events.arn,
      "${aws_dynamodb_table.events.arn}/index/*",
    ]
  }
}

resource "aws_iam_role" "query" {
  name               = "${local.name}-query-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy" "query" {
  name   = "${local.name}-query-policy"
  role   = aws_iam_role.query.id
  policy = data.aws_iam_policy_document.read_events.json
}

resource "aws_iam_role_policy_attachment" "query_logs" {
  role       = aws_iam_role.query.name
  policy_arn = aws_iam_policy.logs.arn
}

resource "aws_iam_role" "stats" {
  name               = "${local.name}-stats-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy" "stats" {
  name   = "${local.name}-stats-policy"
  role   = aws_iam_role.stats.id
  policy = data.aws_iam_policy_document.read_events.json
}

resource "aws_iam_role_policy_attachment" "stats_logs" {
  role       = aws_iam_role.stats.name
  policy_arn = aws_iam_policy.logs.arn
}

# --- cp-auth: talk to Cognito, touch no data -------------------------------
resource "aws_iam_role" "auth" {
  name               = "${local.name}-auth-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "auth" {
  statement {
    effect    = "Allow"
    actions   = ["cognito-idp:InitiateAuth"]
    resources = [aws_cognito_user_pool.main.arn]
  }
}

resource "aws_iam_role_policy" "auth" {
  name   = "${local.name}-auth-policy"
  role   = aws_iam_role.auth.id
  policy = data.aws_iam_policy_document.auth.json
}

resource "aws_iam_role_policy_attachment" "auth_logs" {
  role       = aws_iam_role.auth.name
  policy_arn = aws_iam_policy.logs.arn
}

# --- cp-health: logs only --------------------------------------------------
# The health check touches nothing, so its role grants nothing beyond writing
# its own logs. A function that needs no permissions should HAVE no
# permissions - it is the cheapest least-privilege win in the project.
resource "aws_iam_role" "health" {
  name               = "${local.name}-health-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy_attachment" "health_logs" {
  role       = aws_iam_role.health.name
  policy_arn = aws_iam_policy.logs.arn
}
