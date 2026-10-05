"""
POST /login - exchange a username and password for a token.

WHAT THIS FUNCTION DOES NOT DO, AND WHY THAT IS THE POINT
---------------------------------------------------------
It does not store passwords. It does not hash passwords. It does not compare
passwords. It does not issue tokens, sign them, or decide when they expire.
Cognito does all of that.

This function's entire job is to pass the credentials to Cognito and shape the
answer to match our API contract. The most dangerous code in a typical web
application is simply absent from ours, which is the strongest security claim
in this project.

IAM: this function's role allows cognito-idp:InitiateAuth on our user pool and
nothing else. It cannot read the database. It cannot list users.
"""

import base64
import json
import os

import boto3
from botocore.exceptions import ClientError

from common import log, responses

# Created once per container, not once per request. On a warm invocation this
# line has already run, which saves roughly 100-200ms of client setup.
_cognito = boto3.client("cognito-idp")

CLIENT_ID = os.environ["COGNITO_CLIENT_ID"]


def _role_from_id_token(id_token: str) -> str:
    """
    Read cognito:groups out of the ID token so the dashboard knows which
    controls to show.

    We decode without verifying the signature, and that is safe HERE and only
    here: we received this token from Cognito ourselves, over TLS, moments ago.
    Never decode-without-verify a token that arrived from a client - that is
    how you accept a forged role. Incoming tokens are verified by API Gateway's
    JWT authorizer before our code runs.
    """
    try:
        payload_b64 = id_token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)  # base64url needs padding
        claims = json.loads(base64.urlsafe_b64decode(payload_b64))
        groups = claims.get("cognito:groups") or []
        if isinstance(groups, str):
            groups = groups.strip("[]").replace(",", " ").split()
        return groups[0] if groups else "none"
    except Exception:  # noqa: BLE001 - a malformed token must not break login
        return "unknown"


def handler(event, context):
    request_id = getattr(context, "aws_request_id", None)

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return responses.bad_request("request body is not valid JSON", request_id)

    username = (body.get("username") or "").strip()
    password = body.get("password") or ""

    if not username or not password:
        return responses.bad_request("username and password are required", request_id)

    try:
        result = _cognito.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": username, "PASSWORD": password},
        )
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        # Note what is logged: the username and the error code, never the
        # password and never the raw exception body.
        log.warn("login failed", request_id, username=username, reason=code)

        if code in ("NotAuthorizedException", "UserNotFoundException"):
            # The same message for both, deliberately. Different messages would
            # let anyone discover which email addresses have accounts.
            return responses.unauthorized("Incorrect username or password", request_id)
        if code == "PasswordResetRequiredException":
            return responses.unauthorized("Password reset required - contact an administrator", request_id)
        log.error("cognito error during login", request_id, reason=code)
        return responses.server_error(request_id)

    if "ChallengeName" in result:
        # e.g. a user still on their temporary password.
        return responses.unauthorized(
            f"Additional step required: {result['ChallengeName']}. Set a permanent password first.",
            request_id,
        )

    auth = result["AuthenticationResult"]
    id_token = auth["IdToken"]
    role = _role_from_id_token(id_token)

    log.info("login succeeded", request_id, username=username, role=role)

    return responses.ok({
        "id_token": id_token,
        "expires_in": auth.get("ExpiresIn", 3600),
        "role": role,
        "username": username,
    })
