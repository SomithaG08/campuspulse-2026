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

  # Password reset goes to the user's verified email address only.
  # (Account-enumeration protection is a CLIENT setting:
  # prevent_user_existence_errors on aws_cognito_user_pool_client below.)
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

  # Do not reveal whether an email exists. Without this, a wrong-password
  # response differs from an unknown-user response and the login form becomes
  # a way to enumerate valid accounts.
  prevent_user_existence_errors = "ENABLED"
}

# ---------------------------------------------------------------------------
# The two roles - renamed after the professor's review (October 2026), which
# asked for one page for administrators and one for students:
#
#   admin    -> admin.html   full operations view; also the simulator's account
#   student  -> student.html room availability, raise and follow own requests
#
# The group name travels inside the JWT as cognito:groups and is what
# common/auth.py checks on every protected route.
#
# MIGRATING A LIVE DEPLOYMENT (it had groups "ops" and "staff", created with
# the AWS CLI and never imported into this state):
#   1. terraform apply           -> creates "admin" and "student"
#   2. add the demo users to the new groups (docs/deployment/05-runbook.md):
#        aws cognito-idp admin-add-user-to-group --user-pool-id <id> \
#            --username admin@northbridge.edu   --group-name admin
#        aws cognito-idp admin-add-user-to-group --user-pool-id <id> \
#            --username student@northbridge.edu --group-name student
#   3. delete the old CLI-created groups so no token carries them:
#        aws cognito-idp delete-group --user-pool-id <id> --group-name ops
#        aws cognito-idp delete-group --user-pool-id <id> --group-name staff
# (The resource type is aws_cognito_user_group and its argument is `name`.)
# ---------------------------------------------------------------------------
resource "aws_cognito_user_group" "admin" {
  name         = "admin"
  user_pool_id = aws_cognito_user_pool.main.id
  description  = "Campus administrators: full access - events, alerts, stats, all student requests"
  precedence   = 1
}

resource "aws_cognito_user_group" "student" {
  name         = "student"
  user_pool_id = aws_cognito_user_pool.main.id
  description  = "Students: room availability, raise service requests, see their own requests"
  precedence   = 2
}
