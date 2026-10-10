"""FastAPI server for the CloudOps Copilot RAG pipeline."""

import logging
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="CloudOps Copilot", version="0.1.0")


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

        # TODO: Load RAG pipeline components
        # from agent.retriever import Retriever
        # from agent.rag_agent import RAGAgent
        # from agent.memory import Memory
        # from core.embedder import Embedder

        # For now, return a mock response
        answer = f"Mock answer to: {request.question}"
        cited_log_ids = ["log-001", "log-002"]

        # TODO: In production, call Memory.load_history, Retriever.retrieve, RAG_Agent.answer
        # Try to save history, but don't fail if unavailable
        warning = None
        # try:
        #     memory.save_turn(request.session_id, request.question, answer)
        # except MemoryReadError as e:
        #     # Return 503 on read failure
        #     raise HTTPException(status_code=503, detail="Session history temporarily unavailable")
        # except Exception as e:
        #     # Return answer with warning on write failure
        #     warning = "Session history could not be saved"
        #     logger.warning(f"Failed to save turn: {e}")

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
