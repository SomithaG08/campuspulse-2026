# Handlers

One file per Lambda function. Each exports `handler(event, context)`.

| File | Route | IAM permission | Phase |
|---|---|---|---|
| `health.py` | `GET /health` | logs only | 5 ✅ |
| `auth.py` | `POST /login` | `cognito-idp:InitiateAuth` | 5 ✅ |
| `ingest.py` | `POST /events`, `POST /requests` | `dynamodb:PutItem` — **write only** | 5 ✅ |
| `query.py` | `GET /events`, `GET /alerts` | `dynamodb:Query` — **read only** | 6 ✅ |
| `stats.py` | `GET /stats` | `dynamodb:Query` — **read only** | 6 ✅ |

All seven endpoints in the API contract are now implemented.

Handlers stay thin: authorize, validate, call a `common/` module, respond. The logic lives in `common/` precisely so it can be tested without AWS.
