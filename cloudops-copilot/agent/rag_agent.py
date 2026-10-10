"""RAG agent for generating answers from retrieved logs."""

import logging
import os
from typing import Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class RAGAgent:
    """Generate grounded answers from retrieved log chunks using Bedrock."""

    def __init__(self, model_id: Optional[str] = None, region: str = "us-east-1"):
        """Initialize RAG Agent.
        
        Args:
            model_id: Bedrock model ID (default from SSM)
            region: AWS region
        """
        self.region = region
        self.ssm_client = boto3.client("ssm", region_name=region)
        self.bedrock_client = boto3.client("bedrock-runtime", region_name=region)

        # Get model ID from SSM if not provided
        if not model_id:
            try:
                response = self.ssm_client.get_parameter(Name="/cloudops/bedrock/model-id")
                model_id = response["Parameter"]["Value"]
            except Exception as e:
                logger.warning(f"Failed to load model ID from SSM: {e}")
                model_id = "amazon.nova-lite-v1:0"  # Default

        self.model_id = model_id

    def answer(
        self,
        question: str,
        chunks: list[dict],
        history: list[dict] = None,
        similarity_threshold: float = 0.5,
    ) -> tuple[str, list[str]]:
        """Generate an answer from retrieved chunks.
        
        Args:
            question: User's natural language question
            chunks: Retrieved chunk dicts with 'text', 'chunk_id', 'score'
            history: Conversation history (last 6 turns)
            similarity_threshold: Score threshold for considering evidence present
            
        Returns:
            (answer_text, cited_log_ids)
        """
        history = history or []

        # Check if we have sufficient evidence
        has_evidence = any(chunk.get("score", 0) > similarity_threshold for chunk in chunks)

        if not has_evidence or not chunks:
            return (
                "The available logs do not contain information to answer this question. "
                "Please check if the relevant services were active during the time period in question.",
                [],
            )

        # Build context from chunks
        context = self._build_context(chunks)

        # Build conversation history context
        history_text = self._build_history_context(history)

        # Build prompt
        prompt = self._build_prompt(question, context, history_text)

        # Call Bedrock
        try:
            answer_text, cited_ids = self._call_bedrock(prompt, chunks)
            return answer_text, cited_ids

        except ClientError as e:
            logger.error(f"Bedrock error: {e.response['Error']['Code']}")
            return (
                "Answer generation failed. Please try again.",
                [],
            )

    def _build_context(self, chunks: list[dict]) -> str:
        """Build context from retrieved chunks."""
        lines = ["=== Log Evidence ==="]
        for i, chunk in enumerate(chunks, 1):
            lines.append(f"\n[Log {i}] ({chunk.get('service', 'unknown')} / {chunk.get('level', 'unknown')})")
            lines.append(f"ID: {chunk.get('chunk_id', 'unknown')}")
            lines.append(f"Time: {chunk.get('time_start', 'unknown')}")
            lines.append(f"Message:\n{chunk.get('text', '')[:500]}")

        return "\n".join(lines)

    def _build_history_context(self, history: list[dict]) -> str:
        """Build conversation history context."""
        if not history:
            return ""

        lines = ["=== Conversation History ==="]
        for turn in history[-6:]:  # Last 6 turns
            role = turn.get("role", "unknown")
            content = turn.get("content", "")
            lines.append(f"\n{role.upper()}: {content[:200]}")

        return "\n".join(lines)

    def _build_prompt(self, question: str, context: str, history: str) -> str:
        """Build the prompt for the model."""
        return f"""You are a CloudOps assistant helping analyze AWS logs.

{history}

=== Current Question ===
{question}

{context}

=== Instructions ===
1. Answer ONLY based on the provided log evidence above.
2. If the logs contain the answer, cite the specific Log IDs that support your answer.
3. If the logs don't contain enough information, say so explicitly.
4. Be concise but precise.

Answer:"""

    def _call_bedrock(self, prompt: str, chunks: list[dict]) -> tuple[str, list[str]]:
        """Call Bedrock Converse API and extract answer and citations."""
        import json

        try:
            response = self.bedrock_client.converse(
                modelId=self.model_id,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt,
                            }
                        ],
                    }
                ],
            )

            # Extract answer
            answer_text = ""
            if response.get("output") and response["output"].get("message"):
                for content in response["output"]["message"].get("content", []):
                    if content.get("type") == "text":
                        answer_text = content.get("text", "")
                        break

            # Extract citations (referenced log IDs)
            cited_ids = self._extract_citations(answer_text, chunks)

            return answer_text, cited_ids

        except ClientError as e:
            logger.error(f"Bedrock Converse API error: {e.response['Error']['Code']}")
            raise

    def _extract_citations(self, answer_text: str, chunks: list[dict]) -> list[str]:
        """Extract log IDs cited in the answer."""
        cited = []

        # Look for chunk IDs in the answer text
        for chunk in chunks:
            chunk_id = chunk.get("chunk_id", "")
            if chunk_id and chunk_id in answer_text:
                cited.append(chunk_id)

        # Also look for record IDs
        for chunk in chunks:
            for record_id in chunk.get("record_ids", []):
                if record_id in answer_text:
                    cited.append(record_id)

        # Return up to 20 unique IDs
        return list(set(cited))[:20]
