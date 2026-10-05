# Authentication with Amazon Cognito — explained

**Owner:** Meha · **Read after:** `05-api-explained.md` · **Code:** `backend/src/handlers/auth.py`, `common/auth.py`, `infrastructure/terraform/cognito.tf`

---

## 1. Two words people mix up, and the exam will not

| | Authentication | Authorization |
|---|---|---|
| Question | **Who are you?** | **What may you do?** |
| Analogy | Showing ID at the door | Which rooms your badge opens |
| Our mechanism | Cognito issues a token | The group inside that token |
| Failure code | **401** | **403** |
| Does logging in again help? | Maybe | **No** |

Say this out loud a few times. "401 means I don't know who you are; 403 means I know exactly who you are and the answer is still no."

## 2. What Cognito is

**Level 1 — simple.** The security guard at the entrance. You show your password *to the guard only*, once, and the guard gives you a badge. Everywhere else you show the badge. Nobody else ever sees your password.

**Level 2 — technical.** A managed identity provider. A **user pool** stores users, hashes and verifies passwords, enforces the password policy, manages group membership, and issues signed JSON Web Tokens on successful authentication.

**Why we use it instead of writing our own:** the most dangerous code in a typical web application — password storage, hashing, token signing, expiry — is simply absent from ours. You cannot leak a password table you do not have. That is the strongest security claim in this project, and it comes from a decision not to write code.

## 3. What a JWT actually is

Three base64 pieces joined by dots:

```text
eyJraWQiOiJhYmMi...  .  eyJzdWIiOiIxMjMi...  .  SflKxwRJSMeKKF2QT4...
      header                   claims                 signature
   which key signed it    who you are, what      proof it was us
                          groups, when it expires
```

**A JWT is signed, not encrypted.** Anyone can read the claims — paste one into jwt.io and look. What nobody can do is *change* a claim, because any edit invalidates the signature.

Two consequences worth remembering:
- **Never put a secret in a token.** It is public to whoever holds it.
- **Never trust a token you have not verified.** Reading the claims is trivial; proving they are authentic requires checking the signature.

Our claims look like this:

```json
{
  "sub": "a1b2c3...",
  "cognito:username": "ops@northbridge.edu",
  "cognito:groups": ["ops"],      ← the role, and the whole authorization decision
  "exp": 1760000000,              ← expiry, one hour out
  "iss": "https://cognito-idp.eu-west-3.amazonaws.com/eu-west-3_XXXX",
  "aud": "<our client id>"
}
```

## 4. The login flow, step by step

```text
 1. POST /login {username, password}
          ↓
 2. cp-auth calls Cognito initiate_auth    ← our code passes the password
          ↓                                   through; it never stores,
 3. Cognito verifies against its hash        hashes or compares it
          ↓
 4. Cognito signs and returns id/access/refresh tokens
          ↓
 5. cp-auth reads cognito:groups to tell the client its role
          ↓
 6. Client stores the token and sends it on every later call
```

**Step 5 has a subtlety worth understanding.** `cp-auth` decodes the token *without verifying the signature* — and that is safe **only** because we received it from Cognito ourselves, over TLS, moments earlier. Decoding without verifying a token that arrived from a client would be how you accept a forged role. Incoming tokens are verified by API Gateway, never by us.

## 5. The three checks on every protected call

```text
Request with Authorization: Bearer <jwt>
   │
   ├─ 1. API Gateway JWT authorizer
   │      signature? issuer our pool? audience our client? not expired?
   │      NO → 401, and our code never runs (so a token flood costs us nothing)
   │
   ├─ 2. Lambda: auth.check_group(event, allowed)
   │      is "ops" (or "staff") in cognito:groups?
   │      NO → 403
   │
   └─ 3. IAM, on every AWS call the function makes
          may this role do this action on this resource?
          NO → AccessDenied
```

Three independent layers. Defeating one leaves the other two standing — that is what "defence in depth" means in concrete terms, and it is a much better answer than the phrase itself.

## 6. Our two roles

| Group | `POST /events` | `GET /events` | `GET /stats` | `GET /alerts` | `POST /requests` |
|---|---|---|---|---|---|
| `ops` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `staff` | **403** | ✅ | ✅ | **403** | ✅ |

The two 403 cells are the demonstration. `staff` cannot inject sensor readings into campus telemetry, and does not get the operational failure view — but can raise a service request, so the role can *do* something rather than only read.

## 7. A detail that will bite you

`cognito:groups` arrives as a **real list** sometimes and as a **string** like `"[ops staff]"` or `"ops,staff"` other times, depending on the path the token took. Code that handles one shape and then meets the other is a genuinely unpleasant afternoon of debugging.

`common/auth.py` normalises all three forms, and there are tests for each. Look at `get_groups()` — it is six lines and it is there for a reason.

## 8. How the pool is configured, and why

| Setting | Value | Why |
|---|---|---|
| Tier | **Essentials** | Free tier is 10,000 MAU on Lite/Essentials. **Plus has no free tier at all** |
| Password policy | 12+ chars, upper, lower, number, symbol | Longer beats clever |
| Token lifetime | 60 minutes | A stolen token is briefly useful |
| `generate_secret` | `false` | The dashboard is browser JavaScript; a secret shipped to a browser is not a secret |
| `allow_admin_create_user_only` | `true` | No public sign-up — this is a staff tool |
| `prevent_user_existence_errors` | `ENABLED` | Otherwise the login form tells an attacker which emails have accounts |
| Auth flow | `USER_PASSWORD_AUTH` only | The one flow we use; everything else stays off |

**A cost trap we avoided:** machine-to-machine (client-credentials) tokens have **no free tier** and are billed per token request. So the simulator signs in as an ordinary user, `device@campuspulse.local`, and reuses its token — free, and it exercises the same auth path a human does.

## 9. Verify it yourself

```bash
# Get a token and look inside it
TOKEN=$(curl -s -X POST $API/login -H 'Content-Type: application/json' \
  -d '{"username":"ops@northbridge.edu","password":"<pw>"}' | jq -r .id_token)

# Decode the claims (base64, not decryption)
echo $TOKEN | cut -d. -f2 | base64 -d 2>/dev/null | jq

# 401: no token
curl -s -o /dev/null -w '%{http_code}\n' $API/alerts

# 403: valid token, wrong role
curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $STAFF_TOKEN" $API/alerts

# 200: valid token, right role
curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $TOKEN" $API/alerts
```

**Run all four.** Watching 401, 403 and 200 come back from rules you configured is worth more than three readings of this page — and those three status codes are the evidence for the spec's two-role requirement.

---

## Can you explain this?

1. What is the difference between authentication and authorization, and which status code goes with each?
2. Is a JWT encrypted? What follows from the answer?
3. Why does our backend never see a stored password?
4. Name the three checks a protected request passes through, in order.
5. Why is there no client secret in the dashboard?

### Answers

1. Authentication is "who are you" and fails with 401; authorization is "what may you do" and fails with 403. Logging in again can fix a 401 and never fixes a 403.
2. No — it is signed, not encrypted. Anyone holding it can read the claims, so never put a secret inside one; but nobody can alter a claim without breaking the signature.
3. Because Cognito stores and verifies passwords. Our `cp-auth` passes the credentials to Cognito's `initiate_auth` and handles only the resulting token, so there is no password table to leak.
4. API Gateway's JWT authorizer (signature, issuer, audience, expiry → 401); the Lambda's group check against `cognito:groups` (→ 403); and IAM on every AWS call the function makes (→ `AccessDenied`).
5. Because the dashboard is JavaScript running in the user's browser — anyone can open developer tools and read it. A secret that ships to the client is not a secret.
