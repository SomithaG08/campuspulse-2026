# How Data Flows — one event, end to end

One occupancy reading, from the moment it is invented to the moment it turns red on a screen. Every arrow is a numbered stage with **Input → Processing → Output**.

```text
Simulator → JSON → HTTPS POST → API Gateway → JWT check → Lambda → validate
   → classify → DynamoDB → (GSI2 if alert) → CloudWatch → Dashboard poll → red row
```

---

### Stage 1 — The simulator invents a reading

**Input:** the campus config — `Library-A / A203`, capacity 45 — and a random draw that, this time, lands high.
**Processing:** builds the event object, generates `event_id`, stamps `timestamp` in UTC.
**Output:**
```json
{ "event_id": "evt-2026-0042", "building": "Library-A", "room": "A203",
  "event_type": "occupancy", "value": 58, "unit": "people",
  "severity": "normal", "timestamp": "2026-09-22T14:05:00Z" }
```
*Note it claims `normal`. It is wrong, and it will be overruled — deliberately. Never trust a client's own assessment of itself.*

### Stage 2 — HTTPS POST

**Input:** that JSON object and the token the simulator got at startup.
**Processing:** DNS resolves the API Gateway host; TLS handshake; the request is sent:
```http
POST /events HTTP/1.1
Host: <api-id>.execute-api.eu-west-3.amazonaws.com
Content-Type: application/json
Authorization: Bearer eyJraWQiOi...
```
**Output:** an encrypted request in flight. *Beginner point: TLS is what makes it impossible for someone on the café Wi-Fi to read or alter this.*

### Stage 3 — API Gateway matches the route

**Input:** the HTTPS request.
**Processing:** method + path → route `POST /events` → mapped to `cp-ingest` → authorizer attached to this route.
**Output:** handed to the authorizer. *If the path were unknown: 404, and no Lambda is invoked or billed.*

### Stage 4 — The JWT authorizer decides

**Input:** the `Authorization` header.
**Processing:** decode the token; fetch and cache Cognito's public keys; verify the **signature**, the **issuer**, the **audience** and the **expiry**.
**Output:** either the verified claims (including `cognito:groups: ["ops"]`) passed to Lambda, or **401** returned straight to the caller.
**The important part: this happens before our code exists.** An attacker spraying bad tokens never reaches our logic and costs us nothing.

### Stage 5 — Lambda starts

**Input:** an event object containing the body, headers, query string and claims.
**Processing:** if no warm container exists, a **cold start** — download the package, start Python, run module-level imports (our DynamoDB client is created here, once, so warm invocations skip it). Then `handler(event, context)` is called.
**Output:** our code is running, with `context.aws_request_id` — the ID that will tie every log line together.

### Stage 6 — Authorization

**Input:** the claims.
**Processing:** is `ops` in `cognito:groups`? `POST /events` requires it.
**Output:** continue, or **403** with `{"error": "Forbidden"}`. *401 means "I don't know who you are"; 403 means "I know exactly who you are and the answer is still no."*

### Stage 7 — Validation

**Input:** the raw body.
**Processing:** parse JSON (malformed → 400); check required fields; `event_type` in the enum; `unit` matches the type; `value` finite and numeric; `timestamp` parses as ISO-8601 UTC and falls inside the allowed window; body under 4 KB; strings within length limits.
**Output:** a clean event object, or **400** naming the offending field.
**Why it matters:** this is the boundary between the untrusted internet and our data. Every injection-style attack starts with input nobody checked.

### Stage 8 — Classification (the business logic)

**Input:** the validated event.
**Processing:** look up `A203` → capacity 45. `58 / 45 = 129 %`. Rule: >120 % → `critical`. Build `reason`: *"occupancy 58 exceeds 120% of capacity 45"*. **The client's `severity` is discarded.**
**Output:** the event with `severity: "critical"`, a human-readable `reason`, `received_at`, and `expires_at` = now + 30 days.

### Stage 9 — Key construction

**Input:** the classified event.
**Processing:**
- `pk` = `DAY#2026-09-22`
- `sk` = `2026-09-22T14:05:00Z#evt-2026-0042`
- `gsi1pk` = `BLD#Library-A#2026-09-22`
- `gsi2pk` = `ALERT#2026-09-22` ← **only because severity is not normal**

**Output:** the full item, ready to write. *A `normal` event simply never gets `gsi2pk`, and so never exists in the alerts index. That is the sparse index doing its job.*

### Stage 10 — The write

**Input:** the item.
**Processing:** `PutItem` over the AWS network (encrypted in transit) using the temporary credentials from `cp-ingest`'s IAM role. DynamoDB hashes `pk`, writes to the partition, replicates across three Availability Zones, and updates both index entries — **atomically**: the item cannot be in the table but missing from the alerts index.
**Output:** success. *If IAM denied it: `AccessDenied` → we log it and return 500. If throttled: retry with backoff, which the AWS SDK does for us.*

### Stage 11 — Telemetry

**Input:** what just happened.
**Processing:** one structured log line and two metric increments.
```json
{"level":"INFO","request_id":"abc-123","event_id":"evt-2026-0042",
 "building":"Library-A","room":"A203","severity":"critical",
 "reason":"occupancy 58 exceeds 120% of capacity 45","latency_ms":41}
```
**Output:** into CloudWatch Logs; `EventsIngested` +1 and `AlertsRaised` +1 as metrics, which is what the alarms watch.

### Stage 12 — The response

**Input:** the outcome.
**Processing:** build the JSON response; API Gateway adds the CORS headers.
**Output:**
```json
{ "event_id": "evt-2026-0042", "severity": "critical", "alert": true,
  "stored_at": "2026-09-22T14:05:01Z" }
```
The simulator prints this line in red. **Elapsed so far: well under a second** (to be measured, not assumed).

### Stage 13 — The dashboard notices

**Input:** the dashboard's polling timer (every 10 s) and the operator's stored token.
**Processing:** `GET /stats` and `GET /alerts` with the token → stages 3-6 again → `cp-query` runs `Query` on GSI2 for `ALERT#2026-09-22`, newest first.
**Output:** JSON to the browser; JavaScript renders the alerts panel.

### Stage 14 — What the human sees

**Input:** the JSON.
**Processing:** the alert count tile increments; a red row appears at the top of the alerts panel.
**Output:**
> **CRITICAL · Library-A / A203 · occupancy 58 · 14:05:00Z**
> *occupancy 58 exceeds 120% of capacity 45*

Somebody can now go and open a second study room. **That is the entire product.**

---

## Failure at every stage

| Stage | If it fails | Caller sees | Where you look |
|---|---|---|---|
| 2 | No network / wrong URL | connection error in the simulator | the URL in the simulator config |
| 4 | Expired or bad token | 401 | log in again; check the token's `exp` |
| 6 | `staff` token on an `ops` route | 403 | the permission matrix — this is correct behaviour |
| 7 | Bad payload | 400 + the field name | the simulator's event builder |
| 10 | IAM denies, or throttling | 500 | CloudWatch log, `AccessDenied` or `ProvisionedThroughputExceeded` |
| 10 | Lambda times out | 502/504 | the `REPORT` line's `Duration` vs the configured timeout |
| 13 | CORS misconfigured | dashboard empty, API fine in curl | browser console, then API Gateway CORS settings |

**The debugging rule for the whole team: start from the `request_id`.** It is in the error response, in the Lambda log, and in the API Gateway access log. One ID ties the three together.

## The short version, for the oral

> "Our simulator represents IoT devices around the university. It signs in to Cognito once and then sends events over HTTPS to API Gateway. API Gateway validates the JWT before any of our code runs, then invokes a Lambda function. That function validates the payload, applies our threshold rules to decide the severity — overriding whatever the device claimed — and writes the event to DynamoDB, adding it to a sparse alerts index only if it is abnormal. It logs a structured line and publishes a metric to CloudWatch. Our dashboard polls the stats and alerts endpoints with the operator's token, and the abnormal reading appears as a red alert within about ten seconds."

That is roughly 45 seconds spoken. Every team member should be able to say it.
