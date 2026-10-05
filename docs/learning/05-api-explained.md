# APIs, HTTP and JSON — explained

**Read after:** `00-start-here.md` · **Code:** `docs/architecture/05-api-contract.md`

---

## 1. What an API is

**Simple:** a menu. A restaurant kitchen can do many things, but you order from the menu, in the words the menu uses, and food comes back. You never walk into the kitchen.

**Technical:** an agreed set of requests a program will accept and the responses it will return. Our API accepts seven requests. Anything else gets a 404.

The point of the agreement is that the two sides can change independently. Our dashboard does not know DynamoDB exists. If we replaced the database tomorrow, the dashboard would not notice — as long as `GET /stats` still returns the same shape.

## 2. HTTP: the four parts of a request

```http
POST /events HTTP/1.1                        ← method and path
Host: abc123.execute-api.eu-west-3.amazonaws.com
Content-Type: application/json               ← headers
Authorization: Bearer eyJraWQiOi...

{"event_id": "evt-1", "value": 58}           ← body
```

| Part | What it is | Ours |
|---|---|---|
| **Method** | The verb | `GET` to read, `POST` to create |
| **Path** | Which resource | `/events`, `/stats`, `/alerts` |
| **Headers** | Metadata about the request | `Content-Type`, `Authorization` |
| **Body** | The data itself | The JSON event. GET requests have no body |

**GET versus POST is not arbitrary.** A GET must be safe to repeat — it changes nothing, so a browser can retry it freely. A POST creates something, so repeating it creates a second something. That is why `GET /stats` is a GET and `POST /events` is a POST.

## 3. The response

```http
HTTP/1.1 201 Created
Content-Type: application/json

{"event_id": "evt-1", "severity": "critical", "alert": true}
```

The status code is the summary; the body is the detail.

| Code | Family | Means | In our API |
|---|---|---|---|
| 200 | success | Here it is | `GET /stats` worked |
| 201 | success | I created it | `POST /events` stored an event |
| **400** | your fault | Malformed request | Missing field, wrong unit, bad timestamp |
| **401** | your fault | **I don't know who you are** | No token, expired token, bad signature |
| **403** | your fault | **I know who you are, and no** | `staff` token on an ops-only route |
| 429 | your fault | Too many requests | You hit the throttle |
| **500** | our fault | We broke | A bug, or DynamoDB refused us |

**401 versus 403 is the single most likely question at the oral.** 401 = authentication failed, so logging in again might help. 403 = authentication succeeded and authorization failed, so logging in again will not help at all. Different problem, different fix.

## 4. JSON

JavaScript Object Notation — text that represents structured data.

```json
{
  "building": "Library-A",      // string
  "value": 58,                  // number, no quotes
  "alert": true,                // boolean
  "message": null,              // nothing
  "tags": ["urgent", "room"],   // list
  "location": { "floor": 2 }    // nested object
}
```

Rules that bite beginners: double quotes only, no trailing comma after the last item, and keys are always strings.

Why everyone uses it: a human can read it, every language can parse it, and it needs no schema file to travel.

## 5. Our API, end to end

```text
                 public              requires a token
                 ───────             ────────────────
  POST /login  ──────────► token ──► POST /events    (ops only)
  GET  /health                       POST /requests  (ops + staff)
                                     GET  /events    (ops + staff)   ← Phase 6
                                     GET  /stats     (ops + staff)   ← Phase 6
                                     GET  /alerts    (ops only)      ← Phase 6
```

1. Call `POST /login` with a username and password.
2. Get back an `id_token`, valid for one hour.
3. Send that token in the `Authorization: Bearer ...` header on every other call.
4. API Gateway verifies it before our code runs; the function then checks your group.

## 6. Try it yourself

```bash
API=https://<api-id>.execute-api.eu-west-3.amazonaws.com

# Public — no token needed
curl -s $API/health

# Get a token
TOKEN=$(curl -s -X POST $API/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"ops@northbridge.edu","password":"<password>"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['id_token'])")

# Submit an event
curl -s -X POST $API/events \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"event_id":"evt-test-1","building":"Library-A","room":"A203",
       "event_type":"occupancy","value":58,"unit":"people",
       "severity":"normal","timestamp":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}'

# And the three refusals, which are as important as the success:
curl -s -X POST $API/events -d '{}'                                  # 401 — no token
curl -s -X POST $API/events -H "Authorization: Bearer $STAFF_TOKEN" \
     -H 'Content-Type: application/json' -d '{...}'                  # 403 — wrong role
curl -s -X POST $API/events -H "Authorization: Bearer $TOKEN" \
     -H 'Content-Type: application/json' -d '{"event_id":"x"}'       # 400 — invalid
```

**Run all five.** Seeing a 403 arrive because of a rule you wrote is worth more than reading about it three times.

---

## Can you explain this?

1. What are the four parts of an HTTP request?
2. Why is `POST /events` a POST and `GET /stats` a GET?
3. A caller gets a 403. What went wrong, and will logging in again fix it?
4. What does the `Authorization: Bearer ...` header carry, and who checks it first?
5. Why does the dashboard not talk to DynamoDB directly?

### Answers

1. Method, path, headers, body.
2. POST creates something, so repeating it creates another. GET only reads, so it is safe to repeat and to retry.
3. Authentication succeeded — we know exactly who they are — but their role does not permit that route. Logging in again will not help; they need a different role.
4. A JWT from Cognito proving who the caller is. API Gateway's JWT authorizer verifies its signature, issuer, audience and expiry before any of our code runs.
5. Because then every client would need database credentials, could read everything, and could bypass all our validation and severity rules. The API is the only door, and it is the place the rules live.
