# ---------------------------------------------------------------------------
# State moves for the October 2026 restructuring.
#
# The routes were rewritten as one for_each block. Without these `moved`
# blocks Terraform would DELETE each old route and CREATE a new one with the
# same route key - and if the create ran first, API Gateway would reject it
# as a duplicate. `moved` tells Terraform it is the same object under a new
# address, so each route is updated in place (only its target changes).
# Safe to keep forever; harmless on a fresh deployment.
# ---------------------------------------------------------------------------

moved {
  from = aws_apigatewayv2_route.post_events
  to   = aws_apigatewayv2_route.protected["post_events"]
}

moved {
  from = aws_apigatewayv2_route.post_requests
  to   = aws_apigatewayv2_route.protected["post_requests"]
}

moved {
  from = aws_apigatewayv2_route.get_events
  to   = aws_apigatewayv2_route.protected["get_events"]
}

moved {
  from = aws_apigatewayv2_route.get_alerts
  to   = aws_apigatewayv2_route.protected["get_alerts"]
}

moved {
  from = aws_apigatewayv2_route.get_stats
  to   = aws_apigatewayv2_route.protected["get_stats"]
}

# The ingest integration becomes the api integration (its target changes in
# place). The health, query and stats integrations are removed.
moved {
  from = aws_apigatewayv2_integration.ingest
  to   = aws_apigatewayv2_integration.api
}

moved {
  from = aws_cloudwatch_metric_alarm.ingest_errors
  to   = aws_cloudwatch_metric_alarm.api_errors
}
