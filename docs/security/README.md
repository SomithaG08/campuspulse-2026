# Security

| File | What it is |
|---|---|
| `01-threat-model.md` | The seven threats from the brief, each control marked Implemented / Configured / Planned / Not verified, plus what we explicitly do not claim |

Learning documents: `docs/learning/08-cognito-authentication.md` (authentication, JWTs, the three checks) and `docs/learning/10-iam-security.md` (least privilege, blast radius, the honest caveat about the deployment identity).

**The security model in one line:** API Gateway's JWT authorizer decides whether we know who you are (401), the Lambda's group check decides whether your role permits this route (403), and IAM decides whether that function may touch that resource at all (`AccessDenied`) — three independent layers.
