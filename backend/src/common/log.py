"""
Structured logging and metrics.

TWO IDEAS WORTH UNDERSTANDING
-----------------------------
1. Structured logs. `print("stored event")` is unsearchable. A JSON line with
   named fields can be queried in CloudWatch Logs Insights:
       fields @timestamp, severity | filter severity = "critical"
   Same effort to write, vastly more useful to read.

2. EMF (Embedded Metric Format). CloudWatch can extract METRICS from a
   specially shaped log line. So instead of calling PutMetricData - an extra
   API call, extra latency, and billed per request - we print one line and get
   a metric for free. The log we were writing anyway becomes the metric.
"""

import json
import os
import sys
import time
from typing import Any, Optional

NAMESPACE = os.environ.get("METRIC_NAMESPACE", "CampusPulse")
STAGE = os.environ.get("STAGE", "dev")


def log(level: str, message: str, request_id: Optional[str] = None, **fields: Any) -> None:
    """One JSON object per line. Never log a password, a token or a full auth header."""
    entry = {
        "level": level,
        "message": message,
        "stage": STAGE,
        **({"request_id": request_id} if request_id else {}),
        **fields,
    }
    print(json.dumps(entry, default=str), file=sys.stdout, flush=True)


def info(message: str, request_id: Optional[str] = None, **fields: Any) -> None:
    log("INFO", message, request_id, **fields)


def warn(message: str, request_id: Optional[str] = None, **fields: Any) -> None:
    log("WARN", message, request_id, **fields)


def error(message: str, request_id: Optional[str] = None, **fields: Any) -> None:
    log("ERROR", message, request_id, **fields)


def metric(name: str, value: float = 1, unit: str = "Count",
           aggregate: bool = False, **dimensions: str) -> None:
    """
    Publish a CloudWatch metric by printing an EMF line.

    Keep the dimension count small: every distinct combination of dimension
    values is a separate custom metric, and the free tier allows ten. Splitting
    by building would give us five metrics per counter; splitting by room would
    give us eleven. We split by severity only.

    aggregate=True also publishes the same value with NO dimensions, i.e. the
    campus-wide total. CloudWatch does not sum across dimension values for you:
    a metric published only as AlertsRaised{Severity=...} has no plain
    AlertsRaised series, so an alarm on the plain name would never fire. That
    was a real bug in the alert-burst alarm, found during the Oct 2026 review.
    """
    dims = {k: str(v) for k, v in dimensions.items()}
    dimension_sets = [list(dims.keys())] if dims else [[]]
    if aggregate and dims:
        dimension_sets.append([])
    payload = {
        "_aws": {
            "Timestamp": int(time.time() * 1000),
            "CloudWatchMetrics": [
                {
                    "Namespace": NAMESPACE,
                    "Dimensions": dimension_sets,
                    "Metrics": [{"Name": name, "Unit": unit}],
                }
            ],
        },
        name: value,
        **dims,
    }
    print(json.dumps(payload), file=sys.stdout, flush=True)
