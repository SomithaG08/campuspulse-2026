# ---------------------------------------------------------------------------
# Users, passwords and roles. Our code never sees a stored password.
#
# Tier: Essentials. The free tier is 10,000 monthly active users on Lite or
# Essentials; the PLUS tier has no free tier at all, so do not switch it.
# ---------------------------------------------------------------------------

resource "aws_cognito_user_pool" "main" {
  name = "${local.name}-users"

  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  password_policy {
    minimum_length                   = 12
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = true
    temporary_password_validity_days = 7
  }

  # Do not reveal whether an email exists. Without this, a wrong-password
  # response differs from an unknown-user response and the login form becomes
  # a way to enumerate valid accounts.
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  admin_create_user_config {
    allow_admin_create_user_only = true # no public sign-up; we create the demo users
  }

  tags = {
    Name = "${local.name}-users"
  }
}

resource "aws_cognito_user_pool_client" "api" {
  name         = "${local.name}-client"
  user_pool_id = aws_cognito_user_pool.main.id

  # No client secret: the dashboard is browser JavaScript, where a secret
  # would be visible to anyone who opens developer tools. A "secret" that
  # ships to the client is not a secret.
  generate_secret = false

  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH", # what cp-auth uses on POST /login
    "ALLOW_REFRESH_TOKEN_AUTH",
  ]

  id_token_validity      = 60 # minutes - a stolen token is briefly useful
  access_token_validity  = 60
  refresh_token_validity = 1 # day

  token_validity_units {
    id_token      = "minutes"
    access_token  = "minutes"
    refresh_token = "days"
  }

  prevent_user_existence_errors = "ENABLED"
}

# NOTE: Cognito groups (ops, staff) are created via AWS CLI after deployment.
# See docs/deployment/03-deploy-backend.md for the commands.