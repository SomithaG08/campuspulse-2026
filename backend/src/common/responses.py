"""
Every HTTP response the API returns is built here.

WHY: if each handler builds its own response dict, they drift - one returns
{"error": ...}, another {"message": ...}, a third forgets the Content-Type -
and the dashboard has to handle three shapes. One module, one shape.

The response format is fixed by docs/architecture/05-api-contract.md.
"""

import json
from typing import Any, Optional

_HEADERS = {
    "Content-Type": "application/json",
    # Do not let a browser guess at the content type of our responses.
    "X-Content-Type-Options": "nosniff",
    # CORS headers are added by API Gateway (see apigateway.tf). Setting them
    # here as well produces duplicate headers, which browsers reject.
}


def _response(status: int, payload: dict) -> dict:
    return {
        "statusCode": status,
        "headers": _HEADERS,
        "body": json.dumps(payload, default=str),  # default=str so Decimal/datetime never crash us
    }


def ok(payload: dict) -> dict:
    return _response(200, payload)


def created(payload: dict) -> dict:
    return _response(201, payload)


def error(status: int, code: str, message: str, request_id: Optional[str] = None) -> dict:
    """
    One error shape for the whole API:
        {"error": "...", "message": "...", "request_id": "..."}

    request_id is the Lambda request ID. It is also in the CloudWatch log line,
    which is what turns "it returned 500" into a one-minute investigation.
    """
    body: dict[str, Any] = {"error": code, "message": message}
    if request_id:
        body["request_id"] = request_id
    return _response(status, body)


# Named shortcuts, so handlers read as prose and status codes are never guessed.
def bad_request(message: str, request_id: Optional[str] = None) -> dict:
    return error(400, "ValidationError", message, request_id)


def unauthorized(message: str = "Missing or invalid token", request_id: Optional[str] = None) -> dict:
    return error(401, "Unauthorized", message, request_id)


def forbidden(message: str = "Your role does not permit this action", request_id: Optional[str] = None) -> dict:
    return error(403, "Forbidden", message, request_id)


def server_error(request_id: Optional[str] = None) -> dict:
    # Deliberately vague. An exception message can leak table names, ARNs or
    # library internals to whoever is probing us. The detail goes to the log.
    return error(500, "InternalError", "Something went wrong on our side", request_id)
