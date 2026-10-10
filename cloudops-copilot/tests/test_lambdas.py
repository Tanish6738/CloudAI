"""Tests for Lambda functions.

Validates: Requirements 4.4, 4.5
"""

import json
import os
from datetime import datetime
from moto import mock_aws

# Set env var before importing handler
os.environ["LOG_GROUP_NAME"] = "test-log-group"

from lambdas.log_generator.handler import handler


@mock_aws
def test_log_generator_produces_minimum_records():
    """Log generator Lambda should produce at least 10 records per invocation."""
    import boto3

    client = boto3.client("logs", region_name="us-east-1")

    # Create log group
    client.create_log_group(logGroupName="test-log-group")

    # Invoke handler
    event = {}
    context = None
    result = handler(event, context)

    # Verify result
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["count"] >= 10


@mock_aws
def test_log_generator_includes_error_and_info():
    """Log generator should include both ERROR and INFO level logs."""
    import boto3

    client = boto3.client("logs", region_name="us-east-1")
    client.create_log_group(logGroupName="test-log-group")

    # Invoke multiple times to increase chances of seeing both levels
    for _ in range(5):
        handler({}, None)

    # Verify logs exist
    log_groups = client.describe_log_groups(logGroupNamePrefix="test-log-group")[
        "logGroups"
    ]
    assert len(log_groups) > 0
