terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }

  # State is kept in a local file, deliberately.
  #
  # The "proper" answer is a remote S3 backend with locking, and for a team
  # working in parallel it would be the right call. We are four people making
  # infrequent, coordinated changes, and a remote backend means another bucket,
  # another table and another way for a deployment to fail the week before
  # submission. ONE person owns this state file. See docs/deployment/.
}
