"""Abstract base class for log source plugins."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Iterator

from core.models import LogRecord


class LogPlugin(ABC):
    """Base class for all log source adapters.
    
    Every concrete plugin must define a non-empty 'name' attribute
    and implement the fetch() method.
    """

    name: str

    def __init_subclass__(cls, **kwargs):
        """Enforce that every subclass defines a non-empty 'name' attribute."""
        super().__init_subclass__(**kwargs)
        name = getattr(cls, "name", None)
        if not isinstance(name, str) or not name.strip():
            raise TypeError(
                f"LogPlugin subclass '{cls.__name__}' must define a non-empty 'name' attribute"
            )

    @abstractmethod
    def fetch(self, since: datetime, until: datetime) -> Iterator[LogRecord]:
        """Fetch and yield log records from this source within the given time window.
        
        Args:
            since: Start of time window (inclusive)
            until: End of time window (inclusive)
            
        Yields:
            LogRecord objects normalized to a consistent schema
        """
        ...
