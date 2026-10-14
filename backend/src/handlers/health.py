"""
GET /health - the only endpoint with no authentication.

Purpose: answer "is the API reachable and is the function warm?" in one call.
Used by the demo-day smoke test, which runs it a few minutes before the
presentation so the first request the professor sees is not a cold start.

It touches nothing. No database, no Cognito. If /health works and /events does
not, the problem is downstream of the API - which is already half the
diagnosis.
"""

import os

from common import responses

VERSION = os.environ.get("APP_VERSION", "0.1.0")
STAGE = os.environ.get("STAGE", "dev")


def handler(event, context):
    return responses.ok({"status": "ok", "version": VERSION, "stage": STAGE})
