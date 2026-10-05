# ---------------------------------------------------------------------------
# The bucket that serves the dashboard.
#
# It is publicly readable, and that is a decision rather than an oversight:
# it contains ONLY the page shell - HTML, CSS, JavaScript. No campus data is
# ever stored here. Every piece of data the page displays is fetched from the
# API, which refuses to answer without a valid Cognito token.
#
# This goes in the threat model as a bounded, deliberate exposure.
# ---------------------------------------------------------------------------

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "site" {
  # Bucket names are globally unique across all of AWS, so a suffix is needed.
  bucket = "${local.name}-site-${random_id.bucket_suffix.hex}"

  tags = {
    Name    = "${local.name}-site"
    Content = "static-assets-only-no-data"
  }
}

resource "aws_s3_bucket_ownership_controls" "site" {
  bucket = aws_s3_bucket.site.id
  rule {
    object_ownership = "BucketOwnerEnforced" # ACLs off; the policy is the only access control
  }
}

# Public access is blocked by default on new buckets. We unblock exactly one
# thing - the bucket policy - and leave the ACL blocks in place.
resource "aws_s3_bucket_public_access_block" "site" {
  bucket = aws_s3_bucket.site.id

  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = false # required for the read-only policy below
  restrict_public_buckets = false
}

resource "aws_s3_bucket_website_configuration" "site" {
  bucket = aws_s3_bucket.site.id

  index_document {
    suffix = "index.html"
  }
  error_document {
    key = "index.html"
  }
}

data "aws_iam_policy_document" "site_public_read" {
  statement {
    sid    = "PublicReadStaticAssetsOnly"
    effect = "Allow"
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    actions   = ["s3:GetObject"] # read only: nobody can write, list or delete
    resources = ["${aws_s3_bucket.site.arn}/*"]
  }
}

resource "aws_s3_bucket_policy" "site" {
  bucket = aws_s3_bucket.site.id
  policy = data.aws_iam_policy_document.site_public_read.json

  depends_on = [aws_s3_bucket_public_access_block.site]
}
