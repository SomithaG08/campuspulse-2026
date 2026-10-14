# ---------------------------------------------------------------------------
# The network (added after the professor's review, October 2026).
#
#            VPC 10.20.0.0/16  (eu-west-3, no Internet Gateway, no NAT)
#   ┌─────────────────────────────────────────────────────────────────┐
#   │  private subnet A  10.20.1.0/24 (eu-west-3a)                    │
#   │     └─ api Lambda ENI ──┐                                       │
#   │  private subnet B  10.20.2.0/24 (eu-west-3b)                    │
#   │     └─ api Lambda ENI ──┤  security group: no inbound,          │
#   │                         │  outbound 443 to DynamoDB only        │
#   │  private route table ───┴──> DynamoDB GATEWAY endpoint ──> table │
#   │  VPC Flow Logs ──> CloudWatch Logs (7 days)                     │
#   └─────────────────────────────────────────────────────────────────┘
#
# DESIGN DECISIONS
# * PRIVATE SUBNETS ONLY. There is no Internet Gateway and no NAT Gateway, so
#   nothing in this VPC can reach the internet and nothing on the internet can
#   reach into it. API Gateway still invokes the function: invocation goes
#   through the Lambda service, not through the VPC network.
# * TWO AVAILABILITY ZONES. Lambda places a network interface in each subnet;
#   if one AZ is lost the function keeps running in the other.
# * DYNAMODB GATEWAY ENDPOINT. A gateway endpoint is a route-table entry, not
#   a machine: it is FREE (no hourly charge, no data charge), unlike a NAT
#   Gateway (~$35/month) or interface endpoints (~$8/month per AZ). It is why
#   a VPC costs this project nothing.
# * ENDPOINT POLICY. Even with valid credentials, traffic through the endpoint
#   can only touch OUR table. A compromised function cannot copy data to a
#   DynamoDB table in someone else's account.
# * WHY auth IS NOT IN HERE: it must reach Cognito's public API. See lambda.tf.
#
# COST: VPC, subnets, route tables, security groups and gateway endpoints are
# free. Flow logs are billed as CloudWatch Logs ingestion: at our traffic a
# few MB a month, inside the 5 GB free allowance.
# ---------------------------------------------------------------------------

data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true # required for the endpoint's DNS resolution
  enable_dns_hostnames = true

  tags = {
    Name = "${local.name}-vpc"
  }
}

# --- subnets: private, two AZs ---------------------------------------------
resource "aws_subnet" "private" {
  count = 2

  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index + 1) # 10.20.1.0/24, 10.20.2.0/24
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = false

  tags = {
    Name = "${local.name}-private-${substr(data.aws_availability_zones.available.names[count.index], -1, 1)}"
    Tier = "private"
  }
}

# One route table for both private subnets. Its only routes are the implicit
# "local" route (inside the VPC) and the DynamoDB prefix list added by the
# gateway endpoint below. There is no 0.0.0.0/0 route: no internet.
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${local.name}-private-rt"
  }
}

resource "aws_route_table_association" "private" {
  count = 2

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

# --- DynamoDB gateway endpoint ---------------------------------------------
data "aws_iam_policy_document" "dynamodb_endpoint" {
  statement {
    sid    = "OnlyOurTable"
    effect = "Allow"
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    actions = [
      "dynamodb:PutItem",
      "dynamodb:Query",
    ]
    resources = [
      aws_dynamodb_table.events.arn,
      "${aws_dynamodb_table.events.arn}/index/*",
    ]
  }
}

resource "aws_vpc_endpoint" "dynamodb" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.region}.dynamodb"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private.id]
  policy            = data.aws_iam_policy_document.dynamodb_endpoint.json

  tags = {
    Name = "${local.name}-dynamodb-endpoint"
  }
}

# --- security group for the api Lambda -------------------------------------
# No ingress rules at all: nothing initiates a connection TO a Lambda ENI.
# Egress only on HTTPS, only to DynamoDB's address ranges (the endpoint's
# managed prefix list). The default "allow all outbound" rule is replaced.
resource "aws_security_group" "lambda" {
  name        = "${local.name}-lambda-sg"
  description = "api Lambda: no inbound; outbound HTTPS to DynamoDB only"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name = "${local.name}-lambda-sg"
  }
}

resource "aws_vpc_security_group_egress_rule" "lambda_to_dynamodb" {
  security_group_id = aws_security_group.lambda.id
  description       = "HTTPS to DynamoDB via the gateway endpoint"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  prefix_list_id    = aws_vpc_endpoint.dynamodb.prefix_list_id
}

# The VPC's default security group allows all traffic between its members.
# Nothing uses it, and leaving it permissive is a classic audit finding, so
# Terraform takes it over and empties it.
resource "aws_default_security_group" "default" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${local.name}-default-sg-locked"
  }
}

# --- VPC Flow Logs -----------------------------------------------------------
# Records every accepted and rejected connection attempt at the network
# interfaces. This is the network half of observability: "did the Lambda even
# try to reach DynamoDB, and was it allowed?" is answered here.
resource "aws_cloudwatch_log_group" "flow_logs" {
  count             = var.enable_flow_logs ? 1 : 0
  name              = "/aws/vpc/${local.name}-flow-logs"
  retention_in_days = var.log_retention_days
}

data "aws_iam_policy_document" "flow_logs_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["vpc-flow-logs.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "flow_logs" {
  count              = var.enable_flow_logs ? 1 : 0
  name               = "${local.name}-flow-logs-role"
  assume_role_policy = data.aws_iam_policy_document.flow_logs_assume.json
}

data "aws_iam_policy_document" "flow_logs_write" {
  count = var.enable_flow_logs ? 1 : 0
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:DescribeLogStreams",
    ]
    resources = ["${aws_cloudwatch_log_group.flow_logs[0].arn}:*"]
  }
}

resource "aws_iam_role_policy" "flow_logs" {
  count  = var.enable_flow_logs ? 1 : 0
  name   = "${local.name}-flow-logs-write"
  role   = aws_iam_role.flow_logs[0].id
  policy = data.aws_iam_policy_document.flow_logs_write[0].json
}

resource "aws_flow_log" "vpc" {
  count                    = var.enable_flow_logs ? 1 : 0
  vpc_id                   = aws_vpc.main.id
  traffic_type             = "ALL"
  log_destination_type     = "cloud-watch-logs"
  log_destination          = aws_cloudwatch_log_group.flow_logs[0].arn
  iam_role_arn             = aws_iam_role.flow_logs[0].arn
  max_aggregation_interval = 600 # 10 minutes: fewer, larger log batches

  tags = {
    Name = "${local.name}-flow-log"
  }
}
