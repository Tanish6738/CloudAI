"""CloudWatch Logs plugin for fetching Lambda logs with pagination and checkpointing."""

import json
import logging
from datetime import datetime
from typing import Iterator, Optional

import boto3
from botocore.exceptions import ClientError

from core.models import LogRecord
from plugins.base import LogPlugin

logger = logging.getLogger(__name__)


class CloudWatchPlugin(LogPlugin):
    """Fetch logs from CloudWatch Logs with checkpoint-based resume capability."""

    name = "cloudwatch"

    def __init__(self, log_group_names: list[str], s3_client=None, s3_bucket: str = None):
        """Initialize CloudWatch plugin.
        
        Args:
            log_group_names: List of log groups to fetch from
            s3_client: boto3 S3 client for checkpoint persistence
            s3_bucket: S3 bucket for checkpoint storage
        """
        self.log_group_names = log_group_names
        self.cloudwatch_client = boto3.client("logs")
        self.s3_client = s3_client or boto3.client("s3")
        self.s3_bucket = s3_bucket

    def fetch(self, since: datetime, until: datetime) -> Iterator[LogRecord]:
        """Fetch logs from CloudWatch with pagination.
        
        Args:
            since: Start of time window (strictly greater than checkpoint)
            until: End of time window (max 24 hours)
            
        Yields:
            Normalized LogRecord objects
        """
        for log_group in self.log_group_names:
            # Load checkpoint for this log group
            checkpoint = self._load_checkpoint(log_group)
            
            # Resume from checkpoint or use 'since' parameter
            start_time = int((checkpoint or since).timestamp() * 1000)
            end_time = int(until.timestamp() * 1000)

            # Fetch with pagination
            next_token = None
            try:
                while True:
                    kwargs = {
                        "logGroupName": log_group,
                        "startTime": start_time,
                        "endTime": end_time,
                    }
                    if next_token:
                        kwargs["nextToken"] = next_token

                    response = self.cloudwatch_client.filter_log_events(**kwargs)

                    # Yield each event as a LogRecord
                    for event in response.get("events", []):
                        record = self._parse_log_event(event, log_group)
                        if record:
                            yield record

                    # Check for pagination
                    next_token = response.get("nextToken")
                    if not next_token:
                        break

                # Save checkpoint after successful fetch
                self._save_checkpoint(log_group, until)

            except ClientError as e:
                logger.error(
                    f"CloudWatch API error for log group {log_group}: {e.response['Error']['Code']}"
                )
                # Leave checkpoint unchanged on error

    def _parse_log_event(self, event: dict, log_group: str) -> Optional[LogRecord]:
        """Parse a CloudWatch log event into a LogRecord."""
        try:
            timestamp = datetime.fromtimestamp(event["timestamp"] / 1000)
            message = event.get("message", "")

            # Try to parse JSON message for structured logs
            attributes = {}
            try:
                log_data = json.loads(message)
                if isinstance(log_data, dict):
                    message = log_data.get("message", message)
                    attributes = {k: v for k, v in log_data.items() if k != "message"}
            except (json.JSONDecodeError, TypeError):
                pass

            return LogRecord(
                id=event.get("eventId", ""),
                timestamp=timestamp,
                source="cloudwatch",
                service=log_group.replace("/aws/lambda/", ""),
                level=self._extract_level(message),
                message=message,
                attributes=attributes,
            )
        except Exception as e:
            logger.warning(f"Failed to parse log event: {e}")
            return None

    def _extract_level(self, message: str) -> str:
        """Extract log level from message text."""
        message_upper = message.upper()
        for level in ["ERROR", "WARN", "WARNING", "INFO", "DEBUG"]:
            if level in message_upper:
                return level
        return "INFO"

    def _load_checkpoint(self, log_group: str) -> Optional[datetime]:
        """Load checkpoint from S3 for this log group."""
        if not self.s3_bucket:
            return None

        checkpoint_key = f"checkpoints/{log_group}.json"
        try:
            response = self.s3_client.get_object(Bucket=self.s3_bucket, Key=checkpoint_key)
            data = json.loads(response["Body"].read().decode("utf-8"))
            timestamp_str = data.get("last_timestamp")
            if timestamp_str:
                return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except self.s3_client.exceptions.NoSuchKey:
            pass
        except Exception as e:
            logger.warning(f"Failed to load checkpoint for {log_group}: {e}")

        return None

    def _save_checkpoint(self, log_group: str, timestamp: datetime) -> None:
        """Save checkpoint to S3 for this log group."""
        if not self.s3_bucket:
            return

        checkpoint_key = f"checkpoints/{log_group}.json"
        try:
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=checkpoint_key,
                Body=json.dumps({"last_timestamp": timestamp.isoformat()}),
                ContentType="application/json",
            )
        except Exception as e:
            logger.error(f"Failed to save checkpoint for {log_group}: {e}")
