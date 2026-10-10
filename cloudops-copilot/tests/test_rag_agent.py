"""Property-based tests for RAG agent behavior.

Property 8: No Fabricated Citations When Evidence Is Absent
Validates: Requirements 6.7, 7.6
"""

from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from agent.rag_agent import RAGAgent


class TestRAGAgentNoFabrication:
    """Test RAG agent doesn't cite evidence when absent."""

    @given(num_chunks=st.integers(min_value=0, max_value=5))
    @settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_no_citations_when_no_evidence(self, num_chunks):
        """When all chunks score < 0.5, should not cite any IDs."""
        # Create low-scoring chunks
        chunks = []
        for i in range(num_chunks):
            chunks.append({
                "chunk_id": f"chunk-{i}",
                "text": "Unrelated log message",
                "service": "service",
                "level": "INFO",
                "time_start": "2026-01-01T00:00:00",
                "time_end": "2026-01-01T00:01:00",
                "record_ids": [f"log-{i}"],
                "score": 0.1,  # Below threshold
            })

        agent = RAGAgent()
        answer, cited_ids = agent.answer("What happened?", chunks)

        # Should have no citations
        assert len(cited_ids) == 0, f"Got citations when none should exist: {cited_ids}"
        
        # Answer should indicate no evidence
        assert "not contain" in answer.lower() or "no information" in answer.lower(), \
            f"Answer doesn't indicate lack of evidence: {answer}"
