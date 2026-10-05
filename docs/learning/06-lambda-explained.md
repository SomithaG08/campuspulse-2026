# AWS Lambda — explained

**Owner:** Somitha · **Read after:** `05-api-explained.md` · **Code:** `backend/src/handlers/`

---

## 1. The idea

**Level 1 — simple.** Normally you rent a computer, it runs day and night, and you pay for every hour whether anyone uses it or not. Lambda is the opposite: you hand AWS a function, and AWS runs it when a request arrives. No request, no charge.

**Level 2 — technical.** Lambda is a function-as-a-service runtime. On an invocation AWS finds or creates an execution environment — a micro-VM with your runtime and your code — and calls your handler with an event and a context. Concurrent requests get concurrent environments, so scaling is the default rather than a feature you configure.

**Why it suits this project:** campus events arrive in bursts during a demo and never in between. An EC2 instance would bill every idle hour; Lambda bills nothing. On a fixed 100-credit budget that is the difference between finishing the project and running out.

## 2. The handler

Every function is one entry point:

```python
def handler(event, context):
    return {"statusCode": 200, "body": "..."}
```

- **`event`** — what happened, as a dict. From API Gateway it holds the path, method, query string, headers, body and the verified token claims.
- **`context`** — information about this invocation. We use `context.aws_request_id`, the ID that ties the response, the log line and the access log together.
- **The return value** — for an HTTP API with payload format 2.0, a dict with `statusCode`, `headers` and a string `body`.

## 3. Our four functions

| Function | Route | IAM permission | Why separate |
|---|---|---|---|
| `cp-health` | `GET /health` | logs only | Needs nothing, so it gets nothing |
| `cp-auth` | `POST /login` | `cognito-idp:InitiateAuth` | Talks to Cognito, never to the database |
| `cp-ingest` | `POST /events`, `POST /requests` | `dynamodb:PutItem` | **Write only. Cannot read.** |
| `cp-query`, `cp-stats` | the GET routes (Phase 6) | `dynamodb:Query` | **Read only. Cannot write.** |

**This table is the security argument.** `cp-ingest` is the function exposed to the internet. If an attacker found a flaw in it, the worst available to them is writing junk events — they cannot read a single student service request, because its role does not allow reading. One function with one broad role would turn the same bug into a full data breach.

## 4. Cold starts

The first invocation after idleness has to create an environment: download the zip, start Python, run module-level code. That is a **cold start**, 1-3 seconds for us. Afterwards the environment is reused and invocations take milliseconds — until it is reclaimed after a period of inactivity.

**This is why our boto3 clients are created at module level:**

```python
_table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])   # once per container

def handler(event, context):
    _table.put_item(...)                                              # every request
```

Module-level code runs once per environment; handler code runs once per request. Moving client setup outside the handler saves roughly 100-200 ms on every warm invocation.

**What we do about it:** warm the API with a `GET /health` before the demo. What we do *not* do is enable Provisioned Concurrency — it bills continuously and voids the Lambda free tier entirely.

Expect to be asked about cold starts. The honest answer — "1-3 seconds on the first call, milliseconds afterwards, and here is how we measured it" — is much stronger than pretending the problem does not exist.

## 5. Reading `cp-ingest`

Six steps, in an order that cannot be rearranged:

```python
1. authorize      # is this caller's group allowed here?     → 403
2. validate       # is this payload well-formed, plausible?  → 400
3. classify       # what severity do OUR rules give it?
4. build item     # keys, including the sparse alert key
5. put_item       # one write
6. log + metric   # one structured line, one or two metrics
```

Authorization is first because an unauthorized caller should not get free validation of their payload. Classification comes after validation because you cannot apply a rule to a value you have not checked is a number.

**Step 3 is the one to remember.** The client sends a `severity`, and we throw it away and compute our own. A sensor must not be able to declare itself normal — otherwise anyone who can write an event can make an alert disappear.

## 6. Configuration and secrets

Nothing is hard-coded. The table name, the Cognito client ID, the stage and the namespace all arrive as **environment variables**, set by Terraform:

```python
_table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
```

`os.environ[...]` rather than `os.environ.get(...)` is deliberate: if the variable is missing, the function should fail loudly at cold start, not mysteriously at the first request.

**There are no AWS credentials anywhere in our code.** The function assumes its IAM role at invocation and receives temporary keys automatically. If you ever find yourself typing `aws_access_key_id=` into a handler, stop — something has gone wrong.

## 7. Errors

| Situation | Response | Why |
|---|---|---|
| Bad JSON, missing field, wrong unit | 400 with the offending field | The caller can fix it |
| Not in the right group | 403 | Correct behaviour, not a bug |
| DynamoDB refuses (`AccessDenied`) | 500, generic | Our IAM is wrong; the caller cannot help |
| Unexpected exception | 500, generic | See below |

**500 responses are deliberately vague.** An exception message can leak table names, ARNs and library internals to whoever is probing you. The detail goes to CloudWatch with the `request_id`; the caller gets "Something went wrong on our side" and that ID.

## 8. Testing without AWS

The interesting logic — validation, the severity rules, key building — imports no boto3 and touches no network. It is plain Python, so it can be tested on a laptop in a quarter of a second:

```bash
cd backend && python -m pytest tests -q
```

That is not an accident; it is why those modules are separate from the handlers. Code that can only be tested by deploying it does not get tested.

---

## Can you explain this?

1. What is a cold start, and why are our boto3 clients created outside the handler?
2. Why four functions instead of one, in terms of what an attacker gets?
3. The client sends `"severity": "normal"` with an event that is clearly abnormal. What happens, and why?
4. Where do the table name and the Cognito client ID come from?
5. Why do our 500 responses not include the exception message?

### Answers

1. The delay when Lambda must build a fresh execution environment — download the code, start the runtime, run module-level code — about 1-3 seconds for us. Clients created at module level are built once per environment instead of once per request, saving 100-200 ms on every warm call.
2. Because each function's IAM role grants only what that function needs. `cp-ingest` is internet-facing and can only write; a bug in it cannot read data. With one shared role, the same bug would expose everything.
3. It is discarded during validation, and `rules.classify()` computes the real severity from the value and the room's capacity. A device must not be able to declare itself normal and silence an alert.
4. Environment variables set by Terraform. Nothing is hard-coded, and there are no AWS credentials in the code — the function assumes its IAM role and gets temporary ones.
5. Because exception text can reveal table names, ARNs and internals to an attacker. The detail goes to CloudWatch with the request ID; the caller gets that ID and nothing else.
