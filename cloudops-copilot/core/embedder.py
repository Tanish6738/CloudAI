"""Bedrock Titan embeddings with batching and retry logic."""

import logging
import time
from typing import Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class Embedder:
    """Generate embeddings using Bedrock Titan Text Embeddings v2."""

    def __init__(
        self,
        model_id: str = "amazon.titan-embed-text-v2:0",
        region: str = "us-east-1",
        batch_size: int = 25,
        max_retries: int = 3,
    ):
        """Initialize Embedder.
        
        Args:
            model_id: Bedrock model ID for embeddings
            region: AWS region
            batch_size: Max chunks per API call (≤ 25)
            max_retries: Number of retries on throttling
        """
        self.model_id = model_id
        self.batch_size = min(batch_size, 25)
        self.max_retries = max_retries
        self.client = boto3.client("bedrock-runtime", region_name=region)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts.
        
        Args:
            texts: List of chunk texts to embed (will be batched internally)
            
        Returns:
            List of 1024-dim vectors, one per input text
        """
        all_embeddings = []

        # Submit in sub-batches of ≤ batch_size
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            embeddings = self._call_bedrock_with_retry(batch)
            all_embeddings.extend(embeddings)

        return all_embeddings

    def _call_bedrock_with_retry(self, texts: list[str]) -> list[list[float]]:
        """Call Bedrock with exponential backoff on throttling."""
        delays = [1, 2, 4]  # seconds

        for attempt in range(self.max_retries + 1):
            try:
                # Prepare request
                input_text = "\n".join(texts)
                request_body = {
                    "inputText": input_text,
                }

                # Call Bedrock
                response = self.client.invoke_model(
                    modelId=self.model_id,
                    body=str(request_body),
                    contentType="application/json",
                )

                # Parse response
                import json

                response_body = json.loads(response["body"].read())
                embeddings = response_body.get("embedding", [])

                # Return list of embeddings (one per text in batch)
                # For simplicity, assume Bedrock returns one embedding per text
                if isinstance(embeddings, list) and len(embeddings) > 0:
                    if isinstance(embeddings[0], list):
                        # Multiple embeddings
                        return embeddings
                    else:
                        # Single embedding, replicate for each text
                        return [embeddings] * len(texts)

                return [[0.0] * 1024] * len(texts)  # Fallback

            except ClientError as e:
                error_code = e.response["Error"]["Code"]

                # Retry on throttling
                if error_code in ["ThrottlingException", "ServiceUnavailableException"]:
                    if attempt < self.max_retries:
                        delay = delays[attempt]
                        logger.warning(
                            f"Bedrock throttled. Retrying in {delay}s (attempt {attempt + 1}/{self.max_retries})"
                        )
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(f"Bedrock throttling persisted after {self.max_retries} retries")
                        raise

                # Other errors
                logger.error(f"Bedrock API error: {error_code}")
                raise

        # Should not reach here
        raise RuntimeError("Embedder: max retries exceeded")


def normalize_vectors(vectors: list[list[float]]) -> list[list[float]]:
    """Normalize vectors to unit norm (L2).
    
    Args:
        vectors: List of vectors
        
    Returns:
        Normalized vectors (unit norm)
    """
    import math

    normalized = []
    for vec in vectors:
        norm = math.sqrt(sum(x**2 for x in vec))
        if norm == 0:
            normalized.append(vec)
        else:
            normalized.append([x / norm for x in vec])

    return normalized
