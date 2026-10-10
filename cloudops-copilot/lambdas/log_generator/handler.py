"""Lambda handler for generating synthetic CloudWatch logs."""

import json
import os
import random
from datetime import datetime
from typing import Any

import boto3

cloudwatch = boto3.client("logs")

LOG_GROUP_NAME = os.environ.get("LOG_GROUP_NAME", "cloudops-copilot-logs")

SERVICES = ["checkout-lambda", "payment-processor", "inventory-service"]
MESSAGES = {
    "ERROR": [
        "Database connection timed out",
        "Permission denied accessing S3 bucket",
        "Cold start latency spike detected",
        "DynamoDB throttle limit exceeded",
        "Bedrock API rate limit exceeded",
    ],
    "INFO": [
        "Request processed successfully",
        "Cache hit for request_id",
        "Scaling up EC2 instances",
        "Index refresh completed",
        "Session saved to DynamoDB",
    ],
}


def handler(event: dict, context: Any) -> dict:
    """Generate and publish synthetic CloudWatch logs."""
    records = []
    timestamp = datetime.utcnow().isoformat() + "Z"

    # Generate at least 10 records per invocation
    for i in range(random.randint(10, 15)):
        service = random.choice(SERVICES)
        level = random.choice(["ERROR", "ERROR", "INFO"])  # More ERRORs for variety
        message = random.choice(MESSAGES[level])

        log_event = {
            "timestamp": timestamp,
            "service": service,
            "level": level,
            "message": message,
            "request_id": f"req-{i:05d}",
        }
        records.append(log_event)

    # Publish to CloudWatch Logs
    try:
        # Ensure log stream exists
        stream_name = f"synthetic-{datetime.utcnow().strftime('%Y-%m-%d')}"
        try:
            cloudwatch.create_log_stream(
                logGroupName=LOG_GROUP_NAME, logStreamName=stream_name
            )
        except cloudwatch.exceptions.ResourceAlreadyExistsException:
            pass

        # Put log events
        cloudwatch.put_log_events(
            logGroupName=LOG_GROUP_NAME,
            logStreamName=stream_name,
            logEvents=[
                {"timestamp": int(datetime.utcnow().timestamp() * 1000), "message": json.dumps(r)}
                for r in records
            ],
        )

        return {
            "statusCode": 200,
            "body": json.dumps(
                {"message": f"Generated {len(records)} log events", "count": len(records)}
            ),
        }
    except Exception as e:
        print(f"Error publishing logs: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
