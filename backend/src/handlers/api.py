"""
The single API function - every route except POST /login.

WHY ONE FUNCTION INSTEAD OF FIVE (professor's review, October 2026)
-------------------------------------------------------------------
The first version had one Lambda per concern: health, auth, ingest, query,
stats. That gave each function a minimal IAM role, but it meant five things
to deploy, five log groups to watch, five cold starts and five places for a
configuration to drift. For a system this size the cost outweighed the
benefit. We now run TWO functions:

  campuspulse-dev-api   this router. Inside the VPC (private subnets, no
                        internet route), reaches DynamoDB only through the
                        gateway endpoint. Role: PutItem + Query on one table.
  campuspulse-dev-auth  POST /login. Outside the VPC because it must reach
                        Cognito's public endpoint. Role: InitiateAuth only,
                        no database access at all.

The split that remains is the one that matters: the function that can reach
the internet cannot touch data, and the function that touches data cannot
reach the internet.

HOW ROUTING WORKS
-----------------
API Gateway (HTTP API, payload 2.0) puts the matched route in `routeKey`,
e.g. "GET /stats". We look it up in ROUTES and call the handler. The handler
modules are unchanged in shape - each still does its own authorisation check -
so the security logic did not move, only the packaging did.
"""

from common import log, responses
from handlers import health, ingest, query, requests, stats

ROUTES = {
    "GET /health": health.handler,
    "POST /events": ingest.handler,
    "POST /requests": ingest.handler,
    "GET /requests": requests.handler,
    "GET /events": query.handler,
    "GET /alerts": query.handler,
    "GET /stats": stats.handler,
}


def handler(event, context):
    route = event.get("routeKey", "")
    target = ROUTES.get(route)
    if target is None:
        # API Gateway only forwards routes it knows, so reaching this means the
        # Terraform routes and this table disagree - worth a loud log line.
        log.error("no handler for route", getattr(context, "aws_request_id", None), route=route)
        return responses.error(404, "NotFound", f"No such route: {route}")
    return target(event, context)
