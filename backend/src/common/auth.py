"""
Authorization: what a caller is allowed to do, once API Gateway has already
established who they are.

THE DIVISION OF LABOUR MATTERS
------------------------------
API Gateway's JWT authorizer has already verified the token's signature,
issuer, audience and expiry before this code ever runs. If the token were
forged or expired, we would not be here - the caller got a 401 from the edge.

So this module never validates a token. It reads the claims the authorizer
extracted and answers one question: does this caller's group allow this route?
That is the 403 decision, and it is a different question from the 401 one.
"""

from typing import Optional

GROUPS_CLAIM = "cognito:groups"

OPS = "ops"
STAFF = "staff"


def get_claims(event: dict) -> dict:
    """Claims placed by the HTTP API JWT authorizer. Empty dict on an unauthenticated route."""
    return (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("jwt", {})
        .get("claims", {})
    ) or {}


def get_groups(claims: dict) -> list:
    """
    Cognito groups, normalised.

    A wrinkle worth knowing: depending on the path a token takes, this claim
    arrives either as a real list, or as a string like "[ops staff]" or
    "ops,staff". Handling one shape and meeting another in production is a
    genuinely unpleasant afternoon, so we handle all three.
    """
    raw = claims.get(GROUPS_CLAIM)
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(g).strip() for g in raw if str(g).strip()]
    text = str(raw).strip().strip("[]")
    parts = text.replace(",", " ").split()
    return [p.strip() for p in parts if p.strip()]


def get_username(claims: dict) -> str:
    return claims.get("cognito:username") or claims.get("email") or claims.get("sub", "unknown")


def check_group(event: dict, allowed: tuple) -> Optional[str]:
    """
    Returns None when the caller may proceed, or a message explaining the refusal.

    Deny by default: no claims and no group both mean refusal. A permission
    check that fails open is not a permission check.
    """
    claims = get_claims(event)
    if not claims:
        return "No identity on this request"
    groups = get_groups(claims)
    if not groups:
        return "This user belongs to no group"
    if not any(g in allowed for g in groups):
        return f"This action requires one of: {', '.join(allowed)}"
    return None
