#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# verify-prices.sh
#
# Resolves the prices that docs/cost/01-cost-model.md marks [unverified].
#
# Why this script exists: the AWS pricing web pages render their regional
# tables in JavaScript, so the figures in our cost model for eu-west-3 came
# from N. Virginia examples and were flagged rather than trusted. The AWS
# Price List API returns the real numbers. Sourced facts beat plausible ones,
# especially in a graded report.
#
# The pricing API lives only in us-east-1. That is not a mistake.
#
# Usage:  bash scripts/verify-prices.sh [region]
# ---------------------------------------------------------------------------
set -euo pipefail

REGION="${1:-eu-west-3}"
PRICING_REGION="us-east-1"

command -v aws >/dev/null || { echo "aws CLI not found - see docs/deployment/01-prerequisites.md"; exit 1; }
command -v jq  >/dev/null || { echo "jq not found - install jq, or read the raw JSON yourself"; exit 1; }

# The pricing API identifies regions by their long name, not their code.
case "$REGION" in
  eu-west-3)   LOCATION="EU (Paris)" ;;
  eu-west-1)   LOCATION="EU (Ireland)" ;;
  us-east-1)   LOCATION="US East (N. Virginia)" ;;
  *) echo "Add a LOCATION mapping for $REGION in this script."; exit 1 ;;
esac

echo "=================================================================="
echo " CampusPulse price verification"
echo " Region : $REGION  ($LOCATION)"
echo " Date   : $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "=================================================================="
echo

price () {  # service, then filters
  local svc="$1"; shift
  aws pricing get-products \
    --region "$PRICING_REGION" \
    --service-code "$svc" \
    --filters "$@" \
    --max-results 20 \
    --query 'PriceList' --output text 2>/dev/null \
  | jq -rs '.[]? | fromjson? // empty
            | . as $p
            | ($p.terms.OnDemand // {}) | to_entries[]?.value.priceDimensions | to_entries[]?.value
            | select(.pricePerUnit.USD != null)
            | "  \(.description // "-")\n      USD \(.pricePerUnit.USD) per \(.unit)"' \
  | sort -u | head -20
}

echo "--- DynamoDB on-demand -------------------------------------------"
echo "(cost model currently assumes ~\$0.625/M writes, ~\$0.125/M reads - N. Virginia, unverified)"
price AmazonDynamoDB \
  "Type=TERM_MATCH,Field=location,Value=$LOCATION" \
  "Type=TERM_MATCH,Field=group,Value=DDB-WriteUnits" || echo "  (no result)"
price AmazonDynamoDB \
  "Type=TERM_MATCH,Field=location,Value=$LOCATION" \
  "Type=TERM_MATCH,Field=group,Value=DDB-ReadUnits" || echo "  (no result)"
echo

echo "--- DynamoDB storage and PITR ------------------------------------"
price AmazonDynamoDB \
  "Type=TERM_MATCH,Field=location,Value=$LOCATION" \
  "Type=TERM_MATCH,Field=productFamily,Value=Database Storage" || echo "  (no result)"
echo

echo "--- Lambda -------------------------------------------------------"
echo "(free tier: 1M requests + 400,000 GB-seconds per month - verified on the pricing page)"
price AWSLambda "Type=TERM_MATCH,Field=location,Value=$LOCATION" || echo "  (no result)"
echo

echo "--- API Gateway --------------------------------------------------"
echo "(free tier: 1M calls/month for 12 months; HTTP API \$1.00/M - verified on the pricing page)"
price AmazonApiGateway "Type=TERM_MATCH,Field=location,Value=$LOCATION" || echo "  (no result)"
echo

echo "--- S3 Standard --------------------------------------------------"
echo "(free-tier figures could NOT be read from the S3 pricing page - this is the gap to close)"
price AmazonS3 \
  "Type=TERM_MATCH,Field=location,Value=$LOCATION" \
  "Type=TERM_MATCH,Field=storageClass,Value=General Purpose" || echo "  (no result)"
echo

echo "--- CloudWatch ---------------------------------------------------"
echo "(free tier: 5GB logs, 10 custom metrics, 10 alarms, 3 dashboards - verified on the pricing page)"
price AmazonCloudWatch "Type=TERM_MATCH,Field=location,Value=$LOCATION" || echo "  (no result)"
echo

echo "=================================================================="
echo " Paste this output into docs/cost/01-cost-model.md, replace the"
echo " [unverified] tags with [verified <today's date>], and cite the"
echo " AWS Price List API as the source."
echo "=================================================================="
