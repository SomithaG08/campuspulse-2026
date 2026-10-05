# Deploying the Backend (Phase 5)

Adds three Lambda functions and the HTTP API to the foundation from Phase 4.
Cost impact: **none while idle.** Lambda and API Gateway bill per request, and both are inside their free allowances at our volume.

## 1. Test before you deploy

```bash
cd backend
python -m pytest tests -q
```

74 tests, no AWS needed, about a quarter of a second. **If these fail, do not deploy** — you would be shipping a bug you already know about.

## 2. Apply

```bash
cd infrastructure/terraform
terraform plan -out=tfplan     # ~19 more if the foundation is applied; ~61 from an empty account
terraform apply tfplan
```

Terraform zips `backend/src` itself (the `archive_file` data source), so there is no build step. Change a `.py` file, run `apply` again, and the hash change redeploys every function.

## 3. Smoke test

```bash
terraform output -raw api_endpoint          # note this down
curl -s $(terraform output -raw api_endpoint)/health
```

Expect `{"status":"ok","version":"0.1.0","stage":"dev"}`.

If this fails, nothing else will work — stop here and check the route, the Lambda permission, and the function's CloudWatch log in that order.

## 4. Log in

```bash
API=$(terraform output -raw api_endpoint)

curl -s -X POST $API/login -H 'Content-Type: application/json' \
  -d '{"username":"ops@northbridge.edu","password":"<password>"}'
```

Expect an `id_token`, `expires_in`, and `"role": "ops"`. If you get `Additional step required: NEW_PASSWORD_REQUIRED`, the user is still on a temporary password — set a permanent one with `admin-set-user-password ... --permanent`.

## 5. Store an event

```bash
TOKEN=<the id_token from step 4>

curl -s -X POST $API/events \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"event_id":"evt-test-001","building":"Library-A","room":"A203",
       "event_type":"occupancy","value":58,"unit":"people",
       "severity":"normal","timestamp":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}'
```

Expect:

```json
{"event_id":"evt-test-001","severity":"critical",
 "reason":"occupancy 58 exceeds 120% of capacity 45","alert":true,"stored_at":"..."}
```

**Note the response says `critical` although you sent `normal`.** That is the server overruling the device, and it is worth showing at the demo.

Then confirm it really landed:

```bash
aws dynamodb get-item --table-name campuspulse-dev-events \
  --key '{"pk":{"S":"DAY#'$(date -u +%Y-%m-%d)'"},"sk":{"S":"<timestamp>#evt-test-001"}}'
```

The item should have `gsi2pk` set, because it is an alert.

## 6. Prove the refusals

These three matter more than the success — they are the security demonstration.

```bash
# 401 - no token at all
curl -s -o /dev/null -w '%{http_code}\n' -X POST $API/events -d '{}'

# 403 - valid token, wrong role (log in as staff@ first)
curl -s -X POST $API/events -H "Authorization: Bearer $STAFF_TOKEN" \
  -H 'Content-Type: application/json' -d '{"event_id":"x","building":"Library-A",
  "room":"A203","event_type":"occupancy","value":10,"unit":"people",
  "severity":"normal","timestamp":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}'

# 400 - valid token, right role, bad payload
curl -s -X POST $API/events -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{"event_id":"x"}'
```

Expect `401`, then a 403 with `"This action requires one of: ops"`, then a 400 naming the missing field. **Screenshot all three into `docs/evidence/`.**

## 7. Read the logs

```bash
aws logs tail /aws/lambda/campuspulse-dev-ingest --follow --format short
```

Each stored event produces one JSON line with `request_id`, `severity`, `reason` and `latency_ms`, plus an EMF line that becomes the `EventsIngested` metric. Take one `request_id` from a response and find its line — that is the debugging habit for the rest of the project.

## Troubleshooting

| Symptom | Likely cause | Where to look |
|---|---|---|
| 500 on every route | Lambda permission missing, or a handler import error | The function's log group; an `Unable to import module` line means the handler path is wrong |
| 401 with a token you just got | Token expired (1 hour), or the authorizer's audience/issuer do not match the pool | `terraform output cognito_issuer_url`, and the API access log's `authError` |
| 500 only on `POST /events` | IAM denies `PutItem`, or `TABLE_NAME` is unset | The ingest log — `AccessDenied` or a `KeyError` at cold start |
| `NotAuthorizedException` on a correct password | The user is not confirmed, or `USER_PASSWORD_AUTH` is not enabled on the client | `admin-set-user-password --permanent`; check `explicit_auth_flows` |
| CORS error in the browser | Only matters from Phase 9; `curl` is unaffected | The API's `cors_configuration` |

---

# Read path (Phase 6)

Two more functions and three more routes. Same `terraform apply`; cost impact still nil while idle.

## Verify each endpoint

```bash
API=$(terraform output -raw api_endpoint)
AUTH="Authorization: Bearer $TOKEN"

curl -s -H "$AUTH" "$API/events?limit=5"                   # newest five
curl -s -H "$AUTH" "$API/events?building=Library-A"        # uses GSI1
curl -s -H "$AUTH" "$API/alerts"                           # uses the sparse GSI2
curl -s -H "$AUTH" "$API/alerts?severity=critical"
curl -s -H "$AUTH" "$API/stats"                            # the aggregated picture
```

`GET /stats` is the one to screenshot for the report: a single response that answers every operational question in the brief — overloaded rooms, energy per building, alert counts, urgent requests.

## Prove the design claims

```bash
# A staff token must be refused on /alerts (ops-only) but allowed on /events
curl -s -o /dev/null -w 'alerts as staff: %{http_code}\n' \
  -H "Authorization: Bearer $STAFF_TOKEN" "$API/alerts"
curl -s -o /dev/null -w 'events as staff: %{http_code}\n' \
  -H "Authorization: Bearer $STAFF_TOKEN" "$API/events"
```

Expect **403** then **200**. That one pair of commands demonstrates two roles with genuinely different permissions — the clearest evidence for the spec's two-role requirement.

```bash
# Bad parameters are rejected, not ignored
curl -s -H "$AUTH" "$API/events?limit=9999"      # 400
curl -s -H "$AUTH" "$API/events?date=04-10-2026" # 400
```

## Confirm no Scan is happening

```bash
aws logs tail /aws/lambda/campuspulse-dev-query --format short | grep '"message":"query served"'
```

Each line reports `count` and `scanned`. For a query without a filter they are equal — that is the proof you read only what you returned. A large `scanned` with a small `count` would mean something is filtering instead of querying.
