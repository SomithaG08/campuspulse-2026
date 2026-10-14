# ---------------------------------------------------------------------------
# One role per Lambda - two roles since the October 2026 consolidation.
#
#   api role   dynamodb:PutItem + dynamodb:Query on ONE table and its indexes,
#              plus the EC2 network-interface actions Lambda needs to run in
#              the VPC. No Scan, no Delete, no Update, no other table.
#   auth role  cognito-idp:InitiateAuth on ONE user pool. No data at all.
#
# WHAT WE GAVE UP, STATED PLAINLY
# The old design had a write-only ingest role and read-only query/stats roles.
# Merging them means the API role can both write and read. We accept that
# because three other controls now bound the same risk:
#   1. the function runs in private subnets with no internet route, so data
#      it can read has nowhere to go except back through API Gateway;
#   2. the DynamoDB gateway endpoint policy (vpc.tf) only allows our table;
#   3. every route still checks the caller's Cognito group before acting.
# Recorded as AD-11 in docs/architecture/01-architecture-decisions.md.
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

# --- api: the data function ------------------------------------------------
resource "aws_iam_role" "api" {
  name               = "${local.name}-api-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "api_data" {
  statement {
    sid       = "WriteEvents"
    effect    = "Allow"
    actions   = ["dynamodb:PutItem"]
    resources = [aws_dynamodb_table.events.arn]
  }
  statement {
    sid     = "ReadEventsByKeyOnly"
    effect  = "Allow"
    actions = ["dynamodb:Query"] # deliberately NOT dynamodb:Scan
    resources = [
      aws_dynamodb_table.events.arn,
      "${aws_dynamodb_table.events.arn}/index/*",
    ]
  }
}

resource "aws_iam_role_policy" "api_data" {
  name   = "${local.name}-api-data"
  role   = aws_iam_role.api.id
  policy = data.aws_iam_policy_document.api_data.json
}

# Running in a VPC means Lambda creates elastic network interfaces (ENIs) in
# our private subnets. These are exactly the EC2 actions of the AWS managed
# policy AWSLambdaVPCAccessExecutionRole, written out so the role grants
# nothing we have not read. EC2 does not support resource-level restriction
# for these calls, so the resource is "*" - the same scope AWS itself uses.
# They allow managing network interfaces, not reading any data.
data "aws_iam_policy_document" "api_vpc" {
  statement {
    sid    = "LambdaVpcNetworkInterfaces"
    effect = "Allow"
    actions = [
      "ec2:CreateNetworkInterface",
      "ec2:DescribeNetworkInterfaces",
      "ec2:DescribeSubnets",
      "ec2:DeleteNetworkInterface",
      "ec2:AssignPrivateIpAddresses",
      "ec2:UnassignPrivateIpAddresses",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "api_vpc" {
  name   = "${local.name}-api-vpc"
  role   = aws_iam_role.api.id
  policy = data.aws_iam_policy_document.api_vpc.json
}

resource "aws_iam_role_policy_attachment" "api_logs" {
  role       = aws_iam_role.api.name
  policy_arn = aws_iam_policy.logs.arn
}

# --- auth: talk to Cognito, touch no data -----------------------------------
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
