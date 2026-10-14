# ---------------------------------------------------------------------------
# One table holds every campus event.
#
# Key design and the reasoning behind it: docs/architecture/04-data-model.md.
# In short: pk = DAY#<date> groups a day together, sk = <timestamp>#<id> keeps
# it ordered so "newest first" is free, GSI1 answers "this building today",
# and GSI2 is SPARSE - an item only enters it if cp-ingest wrote gsi2pk, which
# it does only for abnormal events. The alerts index therefore contains alerts
# and nothing else.
#
# Only the attributes used in a key are declared here. DynamoDB is schemaless
# for everything else: building, room, value, severity and the rest simply
# exist on the item.
# ---------------------------------------------------------------------------

resource "aws_dynamodb_table" "events" {
  name = "${local.name}-events"

  # On-demand. Costs nothing while idle, absorbs a demo-day burst without
  # throttling, and needs no capacity planning. See AD-4 for the trade-off
  # against the provisioned free tier.
  billing_mode = "PAY_PER_REQUEST"

  hash_key  = "pk"
  range_key = "sk"

  attribute {
    name = "pk"
    type = "S"
  }
  attribute {
    name = "sk"
    type = "S"
  }
  attribute {
    name = "gsi1pk"
    type = "S"
  }
  attribute {
    name = "gsi1sk"
    type = "S"
  }
  attribute {
    name = "gsi2pk"
    type = "S"
  }
  attribute {
    name = "gsi2sk"
    type = "S"
  }
  attribute {
    name = "gsi3pk"
    type = "S"
  }
  attribute {
    name = "gsi3sk"
    type = "S"
  }

  # "Recent events for one building on one day"
  global_secondary_index {
    name            = "gsi1-by-building"
    hash_key        = "gsi1pk"
    range_key       = "gsi1sk"
    projection_type = "ALL"
  }

  # "Today's alerts" - sparse, see the header comment
  global_secondary_index {
    name            = "gsi2-alerts"
    hash_key        = "gsi2pk"
    range_key       = "gsi2sk"
    projection_type = "ALL"
  }

  # "My service requests" - sparse, added Oct 2026 for the student page.
  # Only service requests carry gsi3pk = USER#<cognito sub>, so a student's
  # GET /requests is one Query on their own partition and nothing else.
  # Adding a GSI to a live table is an online operation: no downtime, the
  # index backfills in the background (older requests have no gsi3pk and
  # simply do not appear in it).
  global_secondary_index {
    name            = "gsi3-by-requester"
    hash_key        = "gsi3pk"
    range_key       = "gsi3sk"
    projection_type = "ALL"
  }

  # Events delete themselves after ttl_days. Deletion by TTL is not billed.
  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  # Layer 1 of the backup strategy: restores the table to any second in the
  # last 35 days. Layer 2 is AWS Backup (backup.tf), which keeps snapshots in
  # a separate vault that survives even if this table is deleted.
  point_in_time_recovery {
    enabled = true
  }

  # prevent_destroy is deliberately FALSE so `terraform destroy` can clean up
  # at the end of the course. It therefore does NOT guard the data against a
  # stray destroy - the AWS Backup vault (backup.tf) and the cleanup
  # checklist are the safeguards.
  # Set it to true if the table ever holds data worth protecting.
  lifecycle {
    prevent_destroy = false
  }

  tags = {
    Name = "${local.name}-events"
  }
}
