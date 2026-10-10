"""Property-based tests for retriever filter soundness.

Property 5: Retrieval Filters Are Sound
Validates: Requirements 6.2, 6.3, 6.4
"""

from datetime import datetime, timedelta
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st
import random

from agent.retriever import Retriever
from core.models import Chunk
from core.vector_store import VectorStore


class TestRetrieverFilters:
    """Test retrieval filter soundness."""

    @given(
        num_chunks=st.integers(min_value=5, max_value=20),
        service_filter=st.one_of(st.none(), st.just("lambda")),
        level_filter=st.one_of(st.none(), st.just("ERROR")),
    )
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    def test_retrieval_filters_are_sound(self, num_chunks, service_filter, level_filter):
        """All returned chunks should satisfy filter predicates."""
        # Create vector store with test chunks
        store = VectorStore(dimension=1024)
        
        base_time = datetime.now()
        vectors = [[random.random() for _ in range(1024)] for _ in range(num_chunks)]
        chunks = []
        
        for i, vec in enumerate(vectors):
            chunk = Chunk(
                chunk_id=f"chunk-{i}",
                text=f"Log message {i}",
                service="lambda" if i % 2 == 0 else "ec2",
                level="ERROR" if i % 3 == 0 else "INFO",
                time_start=base_time + timedelta(seconds=i*10),
                time_end=base_time + timedelta(seconds=i*10+60),
                record_ids=[f"log-{i}"],
            )
            chunks.append(chunk)

        store.add(vectors, chunks)

        # Create retriever
        retriever = Retriever(store)

        # Search with filters
        query_vec = vectors[0]
        results = retriever.retrieve(
            query_vec, 
            k=5, 
            service_filter=service_filter,
            level_filter=level_filter,
        )

        # Verify all results match filters
        for result in results:
            if service_filter:
                assert result["service"].lower() == service_filter.lower(), \
                    f"Service {result['service']} doesn't match filter {service_filter}"
            
            if level_filter:
                assert result["level"].lower() == level_filter.lower(), \
                    f"Level {result['level']} doesn't match filter {level_filter}"
