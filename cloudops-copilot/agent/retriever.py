"""Retrieval component with optional filtering."""

import logging
from datetime import datetime
from typing import Optional

from core.vector_store import VectorStore

logger = logging.getLogger(__name__)


class Retriever:
    """Retrieve relevant chunks from the vector store with optional filtering."""

    def __init__(self, vector_store: VectorStore):
        """Initialize Retriever.
        
        Args:
            vector_store: VectorStore instance to query
        """
        self.store = vector_store

    def retrieve(
        self,
        query_vector: list[float],
        k: int = 8,
        service_filter: Optional[str] = None,
        level_filter: Optional[str] = None,
        time_start: Optional[datetime] = None,
        time_end: Optional[datetime] = None,
    ) -> list[dict]:
        """Retrieve top-k chunks matching the query and filters.
        
        Args:
            query_vector: Normalized query embedding
            k: Number of results to return (default 8)
            service_filter: Optional service name filter (case-insensitive)
            level_filter: Optional log level filter (case-insensitive)
            time_start: Optional start time for time range filter
            time_end: Optional end time for time range filter
            
        Returns:
            List of chunk results matching filters, up to k items
        """
        # If index has fewer than k chunks, return all
        k_adjusted = min(k, self.store.index.ntotal) if self.store.index.ntotal > 0 else k

        # Search for more than k to account for filtering
        search_k = min(k * 2, max(self.store.index.ntotal, k))

        # Get candidates from FAISS
        candidates = self.store.search(query_vector, k=search_k)

        # Apply filters
        filtered = []
        for chunk in candidates:
            # Service filter (case-insensitive exact match)
            if service_filter:
                if chunk["service"].lower() != service_filter.lower():
                    continue

            # Level filter (case-insensitive exact match)
            if level_filter:
                if chunk["level"].lower() != level_filter.lower():
                    continue

            # Time range filter (any overlap)
            if time_start or time_end:
                chunk_start = datetime.fromisoformat(chunk["time_start"])
                chunk_end = datetime.fromisoformat(chunk["time_end"])

                if time_start and time_end:
                    # Check for overlap: [time_start, time_end] ∩ [chunk_start, chunk_end]
                    if chunk_end < time_start or chunk_start > time_end:
                        continue
                elif time_start:
                    if chunk_end < time_start:
                        continue
                elif time_end:
                    if chunk_start > time_end:
                        continue

            filtered.append(chunk)

            # Stop when we have k results
            if len(filtered) >= k:
                break

        return filtered[:k]
