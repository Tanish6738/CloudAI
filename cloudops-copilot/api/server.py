"""FastAPI server for the CloudOps Copilot RAG pipeline."""

import logging
import os
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Import RAG pipeline components
from core.embedder import Embedder, normalize_vectors
from agent.memory import Memory, MemoryReadError
from agent.rag_agent import RAGAgent
from agent.retriever import Retriever
from core.vector_store import VectorStore

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="CloudOps Copilot", version="0.1.0")

# Initialize RAG pipeline components (lazy load on first request)
_embedder: Optional[Embedder] = None
_vector_store: Optional[VectorStore] = None
_retriever: Optional[Retriever] = None
_rag_agent: Optional[RAGAgent] = None
_memory: Optional[Memory] = None
_s3_bucket: str = os.getenv("S3_BUCKET", "cloudops-copilot-index-763103708154")
_aws_region: str = os.getenv("AWS_REGION", "us-east-1")


# Pydantic models
class ChatRequest(BaseModel):
    """Chat request schema."""
    session_id: str = Field(min_length=1, max_length=128)
    question: str = Field(min_length=1, max_length=1000)


class ChatResponse(BaseModel):
    """Chat response schema."""
    answer: str
    cited_log_ids: list[str] = Field(max_length=20)
    warning: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str


def _initialize_rag_components() -> tuple[Embedder, VectorStore, Retriever, RAGAgent, Memory]:
    """Initialize RAG pipeline components (lazy load once on first request)."""
    global _embedder, _vector_store, _retriever, _rag_agent, _memory

    if _embedder is None:
        logger.info("Initializing RAG components...")
        
        # Initialize Embedder
        _embedder = Embedder(region=_aws_region)
        logger.info("✓ Embedder initialized")

        # Initialize VectorStore and load from S3
        _vector_store = VectorStore(dimension=1024)
        loaded = _vector_store.load_from_s3(_s3_bucket, "index/")
        if not loaded:
            logger.warning(f"Could not load vector index from S3 ({_s3_bucket}/index/). Index may be empty.")
        else:
            logger.info(f"✓ VectorStore loaded from S3 ({_vector_store.index.ntotal} chunks)")

        # Initialize Retriever
        _retriever = Retriever(_vector_store)
        logger.info("✓ Retriever initialized")

        # Initialize RAGAgent
        _rag_agent = RAGAgent(region=_aws_region)
        logger.info("✓ RAGAgent initialized")

        # Initialize Memory
        _memory = Memory(region=_aws_region)
        logger.info("✓ Memory initialized")

    return _embedder, _vector_store, _retriever, _rag_agent, _memory


# Routes
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="ok")


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Chat endpoint for RAG pipeline.
    
    Args:
        request: ChatRequest with session_id and question
        
    Returns:
        ChatResponse with answer and cited_log_ids
    """
    try:
        # Validate request
        if not request.session_id or not request.question:
            raise HTTPException(status_code=422, detail="session_id and question required")

        # Initialize RAG components
        embedder, vector_store, retriever, rag_agent, memory = _initialize_rag_components()

        warning = None

        # Step 1: Load conversation history
        history = []
        try:
            history = memory.load_history(request.session_id)
            logger.debug(f"Loaded {len(history)} turns of history")
        except MemoryReadError as e:
            logger.warning(f"Could not load history: {e}")
            # Continue without history (graceful degradation)
        except Exception as e:
            logger.warning(f"Unexpected error loading history: {e}")

        # Step 2: Embed the question
        try:
            question_embeddings = embedder.embed_batch([request.question])
            query_vector = normalize_vectors(question_embeddings)[0]
            logger.debug(f"Question embedded (dim={len(query_vector)})")
        except Exception as e:
            logger.error(f"Failed to embed question: {e}")
            raise HTTPException(status_code=503, detail="Embedding service unavailable")

        # Step 3: Retrieve relevant chunks
        try:
            chunks = retriever.retrieve(query_vector, k=8)
            logger.info(f"Retrieved {len(chunks)} chunks (scores: {[round(c.get('score', 0), 3) for c in chunks]})")
        except Exception as e:
            logger.error(f"Failed to retrieve chunks: {e}")
            raise HTTPException(status_code=503, detail="Vector search service unavailable")

        # Step 4: Generate answer from chunks
        try:
            answer, cited_log_ids = rag_agent.answer(request.question, chunks, history)
            logger.info(f"Answer generated (citations: {cited_log_ids})")
        except Exception as e:
            logger.error(f"Failed to generate answer: {e}")
            raise HTTPException(status_code=503, detail="Answer generation service unavailable")

        # Step 5: Save turn to history (graceful degradation if fails)
        try:
            memory.save_turn(request.session_id, request.question, answer)
            logger.debug(f"Saved turn to session {request.session_id}")
        except MemoryReadError as e:
            # Read failure during save_turn
            raise HTTPException(status_code=503, detail="Session history temporarily unavailable")
        except Exception as e:
            # Write failure - return answer with warning
            warning = "Session history could not be saved"
            logger.warning(f"Failed to save turn: {e}")

        return ChatResponse(
            answer=answer,
            cited_log_ids=cited_log_ids,
            warning=warning,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
