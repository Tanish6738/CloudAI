"""DynamoDB-backed session memory for multi-turn conversations."""

import json
import logging
from datetime import datetime
from typing import Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class Memory:
    """Manage conversation history in DynamoDB."""

    def __init__(self, table_name: str = None, region: str = "us-east-1"):
        """Initialize Memory component.
        
        Args:
            table_name: DynamoDB table name
            region: AWS region
        """
        self.region = region
        self.dynamodb = boto3.resource("dynamodb", region_name=region)

        # Get table name from parameter or SSM
        if not table_name:
            ssm = boto3.client("ssm", region_name=region)
            try:
                response = ssm.get_parameter(Name="/cloudops/dynamodb/table-name")
                table_name = response["Parameter"]["Value"]
            except Exception as e:
                logger.warning(f"Failed to load table name from SSM: {e}")
                table_name = "cloudops-chat-history"

        self.table = self.dynamodb.Table(table_name)

    def load_history(self, session_id: str) -> list[dict]:
        """Load conversation history for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of turn dicts with 'role', 'content', 'timestamp'
            
        Raises:
            MemoryReadError: If DynamoDB read fails
        """
        try:
            response = self.table.query(
                KeyConditionExpression="session_id = :sid",
                ExpressionAttributeValues={":sid": session_id},
                ScanIndexForward=True,  # Sort by turn_index ascending
            )

            turns = []
            for item in response.get("Items", []):
                turns.append({
                    "role": item.get("role", "assistant"),
                    "content": item.get("content", ""),
                    "timestamp": item.get("timestamp", ""),
                })

            return turns

        except ClientError as e:
            logger.error(f"DynamoDB read error: {e}")
            raise MemoryReadError(f"Failed to load session history: {e}")

    def save_turn(self, session_id: str, question: str, answer: str) -> bool:
        """Save a turn to the session history.
        
        Args:
            session_id: Session identifier
            question: User's question
            answer: Assistant's answer
            
        Returns:
            True if successful, False if write failed
        """
        try:
            # Load current turns to determine next turn_index
            turns = self.load_history(session_id)
            turn_index = len(turns)

            # If we already have 6 turns, delete the oldest (turn_index 0)
            if turn_index >= 6:
                self.table.delete_item(
                    Key={
                        "session_id": session_id,
                        "turn_index": 0,
                    }
                )

                # Decrement all other turn indices
                for i in range(1, 6):
                    turn = self.table.get_item(
                        Key={"session_id": session_id, "turn_index": i}
                    )
                    if "Item" in turn:
                        item = turn["Item"]
                        # Re-create with lower index
                        self.table.put_item(
                            Item={
                                "session_id": session_id,
                                "turn_index": i - 1,
                                "role": item.get("role"),
                                "content": item.get("content"),
                                "timestamp": item.get("timestamp"),
                            }
                        )
                        self.table.delete_item(
                            Key={"session_id": session_id, "turn_index": i}
                        )

                turn_index = 5

            # Save user question
            self.table.put_item(
                Item={
                    "session_id": session_id,
                    "turn_index": turn_index,
                    "role": "user",
                    "content": question,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

            # Save assistant answer
            self.table.put_item(
                Item={
                    "session_id": session_id,
                    "turn_index": turn_index + 1,
                    "role": "assistant",
                    "content": answer,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

            return True

        except ClientError as e:
            logger.error(f"DynamoDB write error: {e}")
            return False


class MemoryReadError(Exception):
    """Raised when DynamoDB read fails."""
    pass
