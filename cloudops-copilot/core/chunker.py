"""Log record chunking with token-aware grouping."""

from datetime import datetime, timedelta
from typing import Optional
import uuid

from core.models import Chunk, LogRecord


def count_tokens(text: str) -> int:
    """Approximate token count using 4 characters = 1 token rule."""
    return max(1, len(text) // 4)


def deduplicate(records: list[LogRecord]) -> list[LogRecord]:
    """Remove duplicate records, keeping first occurrence in ingestion order.
    
    Returns:
        List of records with no duplicate IDs
    """
    seen = set()
    result = []
    for record in records:
        if record.id not in seen:
            seen.add(record.id)
            result.append(record)
    return result


class Chunker:
    """Groups log records into 300–500 token chunks.
    
    Grouping strategy:
        1. If records share a request_id, group them together first
        2. Otherwise, group by (service, 60-second time window)
    """

    def __init__(self, min_tokens: int = 300, max_tokens: int = 500):
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens

    def chunk(self, records: list[LogRecord]) -> list[Chunk]:
        """Convert log records into chunks.
        
        Args:
            records: Deduplicated, normalized log records
            
        Returns:
            List of Chunk objects with 300–500 tokens each
        """
        # Deduplicate first
        records = deduplicate(records)

        if not records:
            return []

        chunks = []

        # Group by request_id first, then by service + time window
        request_id_groups = self._group_by_request_id(records)

        for group in request_id_groups:
            chunks.extend(self._split_into_chunks(group))

        return chunks

    def _group_by_request_id(
        self, records: list[LogRecord]
    ) -> list[list[LogRecord]]:
        """Group records that share a request_id, otherwise group by service + 60s window."""
        groups_by_req_id = {}
        ungrouped = []

        for record in records:
            req_id = record.attributes.get("request_id")
            if req_id:
                if req_id not in groups_by_req_id:
                    groups_by_req_id[req_id] = []
                groups_by_req_id[req_id].append(record)
            else:
                ungrouped.append(record)

        # Return request-ID groups first, then group ungrouped by service + time window
        groups = list(groups_by_req_id.values())
        groups.extend(self._group_by_service_and_time(ungrouped))
        return groups

    def _group_by_service_and_time(
        self, records: list[LogRecord]
    ) -> list[list[LogRecord]]:
        """Group records by service and 60-second time windows."""
        if not records:
            return []

        # Sort by timestamp
        sorted_records = sorted(
            records, key=lambda r: r.timestamp or datetime.min
        )

        groups = []
        current_group = []
        current_service = None
        current_window_start = None

        for record in sorted_records:
            ts = record.timestamp or datetime.min
            if not current_service:
                current_service = record.service
                current_window_start = ts
                current_group = [record]
            elif (
                record.service == current_service
                and (ts - current_window_start).total_seconds() < 60
            ):
                current_group.append(record)
            else:
                groups.append(current_group)
                current_service = record.service
                current_window_start = ts
                current_group = [record]

        if current_group:
            groups.append(current_group)

        return groups

    def _split_into_chunks(self, records: list[LogRecord]) -> list[Chunk]:
        """Split a group of records into 300–500 token chunks."""
        chunks = []
        current_chunk_records = []
        current_chunk_tokens = 0

        for record in records:
            record_text = f"{record.timestamp} {record.level} {record.service} {record.message}"
            record_tokens = count_tokens(record_text)

            # If single record exceeds 500 tokens, give it its own chunk
            if record_tokens > self.max_tokens:
                if current_chunk_records:
                    chunks.append(self._create_chunk(current_chunk_records))
                    current_chunk_records = []
                    current_chunk_tokens = 0
                chunks.append(self._create_chunk([record]))
            # If adding this record would exceed max, flush current chunk
            elif current_chunk_tokens + record_tokens > self.max_tokens:
                if current_chunk_records:
                    chunks.append(self._create_chunk(current_chunk_records))
                current_chunk_records = [record]
                current_chunk_tokens = record_tokens
            else:
                current_chunk_records.append(record)
                current_chunk_tokens += record_tokens

        if current_chunk_records:
            chunks.append(self._create_chunk(current_chunk_records))

        return chunks

    def _create_chunk(self, records: list[LogRecord]) -> Chunk:
        """Create a Chunk from a list of LogRecord objects."""
        text_lines = [
            f"{r.timestamp} {r.level} {r.service} {r.message}" for r in records
        ]
        chunk_text = "\n".join(text_lines)

        # Determine dominant level (ERROR > WARN > INFO > DEBUG)
        level_order = {"ERROR": 0, "WARN": 1, "INFO": 2, "DEBUG": 3}
        dominant_level = min(
            (level_order.get(r.level, 999), r.level) for r in records
        )[1]

        # Time range
        timestamps = [r.timestamp for r in records if r.timestamp]
        time_start = min(timestamps) if timestamps else datetime.now()
        time_end = max(timestamps) if timestamps else datetime.now()

        return Chunk(
            chunk_id=str(uuid.uuid4()),
            text=chunk_text,
            service=records[0].service,
            level=dominant_level,
            time_start=time_start,
            time_end=time_end,
            record_ids=[r.id for r in records],
        )
