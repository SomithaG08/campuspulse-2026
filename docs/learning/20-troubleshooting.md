# Troubleshooting

**Read this before you ask the group chat.** Nine times out of ten the answer is in a log line you have not looked at yet.

---

## The method: start from the request_id

Every error response carries one:

```json
{ "error": "ValidationError", "message": "unit for occupancy must be 'people'",
  "request_id": "a1b2c3d4-..." }
```

That same id appears in the Lambda log line **and** in the API Gateway access log. One id ties the three together.

```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/campuspulse-dev-ingest \
  --filter-pattern '"a1b2c3d4"' --max-items 10
```

**The first question is always: did the request reach our code at all?** A 401 from the authorizer never invokes a Lambda, so looking in the function's log for it is a wasted ten minutes. The API access log knows; the function log does not.

```bash
aws logs tail /aws/apigateway/campuspulse-dev --format short --since 10m
```

---

## HTTP errors

### 400 — Validation error

**Means:** the request was malformed. Your fault, and the message says which field.

| Cause | Fix |
|---|---|
| Missing required field | The message names it |
| Wrong `unit` for the `event_type` | `celsius` not `fahrenheit`, `people` not `count` — see the data model |
| `value` not a number | `"42"` is a string; send `42` |
| Timestamp older than 24 h or more than 5 min ahead | Use UTC with a `Z`. A laptop clock that is wrong by hours does this |
| Unknown building or room | It must exist in `campus_config.py` |
| Body over 4 KB | Something is wrong with what you are sending |

**Verify the fix:** resend the corrected event, expect 201.

### 401 — Unauthorized

**Means:** we do not know who you are. The request never reached our code.

| Cause | Fix |
|---|---|
| No `Authorization` header | Add `Authorization: Bearer <token>` |
| Token older than one hour | Log in again — they expire |
| Token from a different pool, or a typo when pasting | Get a fresh one from `POST /login` |
| Token pasted with a line break | Common with copy-paste from a terminal |

**Where to look:** the API access log's `authError` field, not the function log.

```bash
echo $TOKEN | cut -d. -f2 | base64 -d 2>/dev/null | python -m json.tool   # check exp
```

### 403 — Forbidden

**Means:** we know exactly who you are, and the answer is still no. **Usually this is correct behaviour, not a bug.**

| Situation | Correct? |
|---|---|
| `staff` token on `POST /events` | **Yes** — staff do not submit sensor readings |
| `staff` token on `GET /alerts` | **Yes** — alerts are an operations view |
| `ops` token getting 403 anywhere | **No** — check the user is actually in the `ops` group |

```bash
aws cognito-idp admin-list-groups-for-user \
  --user-pool-id <pool-id> --username ops@northbridge.edu
```

If the group is right but the token is old, it predates the group change — log in again.

### 429 — Too many requests

You hit the stage throttle (20/s steady, 40 burst). Almost always a simulator with too small an `--interval`. The throttle is doing its job: protecting the credit budget.

### 500 — Internal error

**Means:** our bug. The response is deliberately vague; the detail is in the log.

```bash
aws logs tail /aws/lambda/campuspulse-dev-ingest --since 15m --format short | grep ERROR
```

| Log line says | Cause | Fix |
|---|---|---|
| `AccessDenied` on `dynamodb:PutItem` | IAM policy wrong, or pointing at another table | Check `iam.tf`, re-apply |
| `KeyError: 'TABLE_NAME'` | Environment variable missing | Check the function's config in `lambda.tf` |
| `Unable to import module 'handlers.ingest'` | Handler path or packaging wrong | Handler must be `handlers.ingest.handler`; the zip's root is `backend/src` |
| `ProvisionedThroughputExceeded` | Throttled | Should not happen on-demand; check the table is `PAY_PER_REQUEST` |
| `Task timed out after 10.00 seconds` | Something is hanging | Check the timeout in `lambda.tf`; `/stats` gets 15 s |

---

## Component failures

### Lambda does not run at all

```bash
aws lambda get-function --function-name campuspulse-dev-ingest --query Configuration.LastUpdateStatus
aws lambda invoke --function-name campuspulse-dev-ingest \
  --payload '{"routeKey":"GET /health"}' /tmp/out.json && cat /tmp/out.json
```

If a direct invoke works but the API returns 500, the problem is between API Gateway and Lambda — almost always the missing `aws_lambda_permission`.

### DynamoDB has no data

Work backwards along the path:

1. **Did the API accept the event?** A 201 with an `event_id` means it was stored.
2. **Is anything in the table at all?**
   ```bash
   aws dynamodb scan --table-name campuspulse-dev-events --max-items 3
   ```
   *(The one acceptable `Scan`: debugging by hand, never in the application.)*
3. **Are you querying the right day?** `pk` is `DAY#<UTC date>`. After 01:00 in Paris the UTC date is still yesterday — this catches people out regularly.
4. **Have the items expired?** TTL deletes after 30 days.

### The dashboard is empty

| Check | How |
|---|---|
| Is the API reachable? | `curl $API/health` |
| Is there data today? | `curl -H "Authorization: Bearer $TOKEN" "$API/events?limit=5"` |
| CORS? | Browser devtools → Console. "blocked by CORS policy" is browser-only; `curl` works fine |
| Right endpoint? | View source on `config.js` — the deployed one, not the repo's |
| Signed in as staff? | Then the alerts panel is *supposed* to be missing |

**If `curl` works and the browser does not, it is CORS or config.js. Those are the only two options.**

### Login fails

| Message | Cause | Fix |
|---|---|---|
| "Incorrect username or password" | Wrong credentials — **or the user does not exist.** The same message on purpose, so the form cannot be used to discover accounts | Check the username; list users |
| "Additional step required: NEW_PASSWORD_REQUIRED" | Still on a temporary password | `admin-set-user-password ... --permanent` |
| "Could not reach the API" | Wrong URL, API not deployed, or no network | `curl $API/health` |
| 500 on `/login` | `COGNITO_CLIENT_ID` missing, or `USER_PASSWORD_AUTH` not enabled | Check `cognito.tf` and the function's environment |

### The simulator cannot connect

```bash
python simulator.py --dry-run -n 3     # does generation work at all?
curl -s $CAMPUSPULSE_API/health        # is the API alive?
echo $CAMPUSPULSE_API                  # is the variable even set?
```

| Symptom | Cause |
|---|---|
| `ConnectionError: Name or service not known` | `CAMPUSPULSE_API` is empty or malformed |
| `Login failed (401)` | Wrong password, or the device user is not in `ops` |
| Every event returns 403 | The device user is not in the `ops` group |
| Every event returns 400 | Backend and simulator disagree — are you running the same commit? |

### Deployment fails

| Error | Fix |
|---|---|
| `InvalidClientTokenId` | `aws configure`, then `aws sts get-caller-identity` |
| `BucketAlreadyExists` | S3 names are globally unique — re-run, `random_id` makes a new suffix |
| `ResourceInUseException` | A table of that name exists — import it or change `environment` |
| `Error acquiring the state lock` | Another apply is running or crashed — `terraform force-unlock <id>` |
| `Error: Invalid function argument` on `archive_file` | `backend/src` path wrong, or the file is open in an editor on Windows |
| Everything plans as "to add" when it already exists | Wrong state file, or you are in the wrong directory |

**`terraform plan` always tells you the truth about what exists versus what should exist, and changes nothing.** Run it first, every time.

---

## When nothing makes sense

In order:

1. **`curl $API/health`.** If this fails, nothing downstream is worth checking.
2. **Check the API access log** — did the request arrive, and what status went back?
3. **Check the function log** for that `request_id`.
4. **Check the CloudWatch dashboard** — is this one request or everything?
5. **`terraform plan`** — has the deployed infrastructure drifted from the code?
6. **Ask, with evidence.** "500 on POST /events, request_id a1b2c3, log says AccessDenied on PutItem" gets an answer in a minute. "It's broken" does not.

## Things that look broken but are not

| Looks wrong | Actually |
|---|---|
| First request takes 2 seconds | Cold start. Normal |
| `staff` gets 403 on `/alerts` | Correct, and it is the demo |
| Alarm shows INSUFFICIENT_DATA | No traffic yet. `treat_missing_data` handles the ones that matter |
| Dashboard stops updating after 15 minutes | Idle pause, saving cost. Press Refresh |
| Events vanish after a month | TTL. By design |
| `/stats` says `truncated: true` | More events than the ten-page window — honest, not broken |
