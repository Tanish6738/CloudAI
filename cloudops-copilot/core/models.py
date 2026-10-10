"""Data models for normalized logs and RAG pipeline."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class LogRecord:
    """Normalized log record with sentinel values for missing fields.
    
    Properties:
        - Sentinel for missing timestamp: None
        - Sentinel for missing string fields: ""
        - Sentinel for missing attributes: {}
    """

    id: str
    timestamp: Optional[datetime] = None
    source: str = ""
    service: str = ""
    level: str = ""
    message: str = ""
    attributes: dict = field(default_factory=dict)

    def __post_init__(self):
        """Normalize None values to sentinels."""
        # Normalize None attributes to empty dict
        if self.attributes is None:
            self.attributes = {}
        
        # Normalize None string fields to empty strings
        if self.source is None:
            self.source = ""
        if self.service is None:
            self.service = ""
        if self.level is None:
            self.level = ""
        if self.message is None:
            self.message = ""


@dataclass
class Chunk:
    """A chunk of logs ready for embedding.
    
    Properties:
        - Token range: 300–500 (except single-record oversized chunks)
        - Metadata includes service, level, and time range
        - record_ids preserves lineage back to original LogRecords
    """

    chunk_id: str
    text: str
    service: str
    level: str
    time_start: datetime
    time_end: datetime
    record_ids: list[str] = field(default_factory=list)


@dataclass
class ChatMessage:
    """A single turn in a conversation."""

    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
