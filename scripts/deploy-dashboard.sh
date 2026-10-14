#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Publishes the dashboard to S3.
#
# It builds into frontend/.build/ rather than editing frontend/config.js in
# place, so the repository never ends up holding one person's deployed
# endpoint and `git status` stays clean after a deploy.
#
# Usage:  bash scripts/deploy-dashboard.sh
# ---------------------------------------------------------------------------
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF="$ROOT/infrastructure/terraform"
BUILD="$ROOT/frontend/.build"

command -v aws >/dev/null || { echo "aws CLI not found - see docs/deployment/01-prerequisites.md"; exit 1; }
command -v terraform >/dev/null || { echo "terraform not found"; exit 1; }

API=$(terraform -chdir="$TF" output -raw api_endpoint)
BUCKET=$(terraform -chdir="$TF" output -raw site_bucket_name)
SITE=$(terraform -chdir="$TF" output -raw site_url)

echo "API    : $API"
echo "bucket : $BUCKET"

rm -rf "$BUILD"
mkdir -p "$BUILD"
# Three pages since October 2026: sign-in, administrator, student.
cp "$ROOT/frontend/index.html" "$ROOT/frontend/admin.html" "$ROOT/frontend/student.html" \
   "$ROOT/frontend/style.css" "$ROOT/frontend/app.js" "$ROOT/frontend/admin.js" \
   "$ROOT/frontend/student.js" "$BUILD/"

# config.js is the only file that differs between deployments.
# The API_URL line is rewritten whatever it currently holds (a placeholder or
# a previous deployment's endpoint), so a stale endpoint can never be shipped.
sed -E "s|API_URL: \"[^\"]*\"|API_URL: \"$API\"|" "$ROOT/frontend/config.js" > "$BUILD/config.js"

grep -q "REPLACE_WITH" "$BUILD/config.js" && { echo "config.js substitution failed"; exit 1; }

# --delete keeps the bucket exactly matching the build: no stale file from a
# previous version can linger and be served.
aws s3 sync "$BUILD/" "s3://$BUCKET/" --delete \
  --cache-control "public, max-age=60"

echo
echo "Sign in : $SITE/index.html"
echo "Admin   : $SITE/admin.html"
echo "Student : $SITE/student.html"
echo "Smoke test: curl -s $API/health"
