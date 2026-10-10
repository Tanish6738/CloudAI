"""Property-based tests for vector store round-trip persistence.

Property 4: Vector Store Round-Trip Preserves Query Results
Validates: Requirement 5.13
"""

from datetime import datetime, timedelta
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st
from moto import mock_aws
import boto3

from core.vector_store import VectorStore
from core.models import Chunk


class TestVectorStoreRoundTrip:
    """Test FAISS index save/load preserves search results."""

    @mock_aws
    @given(num_chunks=st.integers(min_value=1, max_value=50))
    @settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_vector_store_round_trip_preserves_top_5(self, num_chunks):
        """Reloaded index should return same top-5 results."""
        # Create S3 bucket
        s3 = boto3.client("s3", region_name="us-east-1")
        bucket = "test-bucket"
        s3.create_bucket(Bucket=bucket)

        # Create store and add vectors
        store = VectorStore(dimension=1024)
        
        # Generate test vectors
        import random
        vectors = [[random.random() for _ in range(1024)] for _ in range(num_chunks)]
        chunks = []
        for i, vec in enumerate(vectors):
            chunk = Chunk(
                chunk_id=f"chunk-{i}",
                text=f"Log message {i}",
                service="test-service",
                level="INFO",
                time_start=datetime.now(),
                time_end=datetime.now() + timedelta(seconds=60),
                record_ids=[f"log-{i}"],
            )
            chunks.append(chunk)

        store.add(vectors, chunks)

        # Save to S3
        version_path = store.save_to_s3(bucket, "index/")
        assert version_path.startswith("index/v")

        # Create new store and load from S3
        store2 = VectorStore(dimension=1024)
        store2.s3_client = s3
        loaded = store2.load_from_s3(bucket, "index/")
        assert loaded

        # Query both stores with same vector
        if num_chunks > 0:
            query_vec = vectors[0]
            results1 = store.search(query_vec, k=5)
            results2 = store2.search(query_vec, k=5)

            # Extract chunk IDs (should be same order)
            ids1 = [r["chunk_id"] for r in results1]
            ids2 = [r["chunk_id"] for r in results2]

            assert ids1 == ids2, f"Results differ after round-trip: {ids1} vs {ids2}"
