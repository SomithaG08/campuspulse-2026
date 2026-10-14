"""
The one place that opens the DynamoDB table.

Before the Lambda consolidation (Oct 2026) each of five functions created its
own table handle at import time. With a single API function and a router,
that would mean three handles in one process. Here there is exactly one,
created lazily on first use - which also means importing a handler in a unit
test does not need AWS credentials or a TABLE_NAME.

Inside the VPC this client reaches DynamoDB through the gateway endpoint
(infrastructure/terraform/vpc.tf). Nothing in this code knows or cares: the
route table sends DynamoDB traffic to the endpoint, so the SDK call is
identical inside and outside a VPC.
"""

import os

_table = None


def table():
    global _table
    if _table is None:
        import boto3

        _table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
    return _table


def set_table(fake) -> None:
    """Test hook: swap in a stub table."""
    global _table
    _table = fake
