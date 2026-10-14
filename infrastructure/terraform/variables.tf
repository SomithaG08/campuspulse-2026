variable "project" {
  description = "Name prefix for every resource, so everything is identifiable and deletable."
  type        = string
  default     = "campuspulse"
}

variable "region" {
  description = "AWS region. Everything lives in one region (see AD-1)."
  type        = string
  default     = "eu-west-3" # Paris
}

variable "environment" {
  description = "Environment suffix. 'dev' is the only one we build."
  type        = string
  default     = "dev"
}

variable "notification_email" {
  description = "Email that receives budget alerts. Required - no default, so it cannot be forgotten."
  type        = string

  validation {
    condition     = can(regex("^[^@]+@[^@]+\\.[^@]+$", var.notification_email))
    error_message = "notification_email must be a valid email address."
  }
}

variable "budget_limit_usd" {
  description = "Monthly spend that triggers alerts, in USD. Low on purpose: this is a tripwire, not a ceiling."
  type        = number
  default     = 10

  validation {
    condition     = var.budget_limit_usd > 0 && var.budget_limit_usd <= 100
    error_message = "budget_limit_usd must be between 1 and 100 - the whole account only has 100 credits."
  }
}

variable "log_retention_days" {
  description = "CloudWatch log retention. Never leave this unset: the default is 'never expire', which quietly accrues storage cost."
  type        = number
  default     = 7
}

variable "ttl_days" {
  description = "Days an event lives before DynamoDB deletes it. Passed to cp-ingest as TTL_DAYS and read by common/campus_config.py (default 30)."
  type        = number
  default     = 30
}

locals {
  name = "${var.project}-${var.environment}"

  common_tags = {
    Project     = "CampusPulse2026"
    Environment = var.environment
    Course      = "BigData-CloudComputing-EPITA"
    ManagedBy   = "Terraform"
  }
}

variable "app_version" {
  description = "Reported by GET /health. Bump it when you deploy, so you can tell which code is live."
  type        = string
  default     = "0.1.0"
}

variable "metric_namespace" {
  description = "CloudWatch namespace for our custom metrics."
  type        = string
  default     = "CampusPulse"
}

variable "throttle_rate_limit" {
  description = "Steady-state requests per second allowed by the API. Low on purpose: it is a budget guard as much as a security control."
  type        = number
  default     = 20
}

variable "throttle_burst_limit" {
  description = "Short burst allowance above the steady rate."
  type        = number
  default     = 40
}

variable "alert_emails" {
  description = "Team school addresses (@epita.fr) that receive every alarm and campus alert by email. A Microsoft Teams channel email address can be added too. Each address must click the AWS confirmation email once."
  type        = list(string)

  validation {
    condition     = length(var.alert_emails) > 0 && alltrue([for e in var.alert_emails : can(regex("^[^@]+@[^@]+\\.[^@]+$", e))])
    error_message = "alert_emails must contain at least one valid email address - alerts must reach the team."
  }
}

variable "alarm_error_threshold" {
  description = "Lambda errors in a 5-minute window before the alarm fires. 1 is deliberate: at our volume any error is worth looking at."
  type        = number
  default     = 1
}

variable "alarm_alert_burst" {
  description = "Alerts in 5 minutes that suggest something campus-wide rather than one bad room. INITIAL GUESS - tune after observing a real run."
  type        = number
  default     = 20
}

variable "alarm_invocation_ceiling" {
  description = "Invocations in 5 minutes that indicate a runaway client. A cost guard, not a performance one. INITIAL GUESS - tune after observing a real run."
  type        = number
  default     = 2000
}

# --- network (vpc.tf) --------------------------------------------------------
variable "vpc_cidr" {
  description = "Address range of the CampusPulse VPC. Two /24 private subnets are carved from it."
  type        = string
  default     = "10.20.0.0/16"
}

variable "enable_flow_logs" {
  description = "Record VPC network traffic to CloudWatch Logs (7-day retention). A few MB a month at our volume."
  type        = bool
  default     = true
}

# --- backups (backup.tf) -----------------------------------------------------
variable "backup_retention_days" {
  description = "How long each DAILY AWS Backup snapshot of the events table is kept."
  type        = number
  default     = 7
}

variable "backup_weekly_retention_days" {
  description = "How long each WEEKLY AWS Backup snapshot is kept."
  type        = number
  default     = 35
}
