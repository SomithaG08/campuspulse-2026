provider "aws" {
  region = var.region

  # Every resource gets these tags automatically. Tags are how you find out
  # later what a charge belongs to, and how you prove at cleanup time that
  # nothing of ours is left running.
  default_tags {
    tags = local.common_tags
  }
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
