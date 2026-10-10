"""FAISS vector store with S3 persistence and versioning."""

import json
import logging
from datetime import datetime
from typing import Optional

import boto3
import faiss
import numpy as np

logger = logging.getLogger(__name__)


class VectorMetadata:
    """Metadata for chunks stored alongside FAISS index."""

    def __init__(self):
        self.chunks = []

    def add(self, faiss_id: int, chunk_id: str, text: str, service: str, level: str, 
            time_start: datetime, time_end: datetime, record_ids: list[str]):
        """Add metadata for a chunk."""
        self.chunks.append({
            "faiss_id": faiss_id,
            "chunk_id": chunk_id,
            "text": text,
            "service": service,
            "level": level,
            "time_start": time_start.isoformat(),
            "time_end": time_end.isoformat(),
            "record_ids": record_ids,
        })

    def to_json(self):
        """Serialize to JSON."""
        return {
            "version": f"v{datetime.utcnow().isoformat().replace(':', '').replace('-', '')}",
            "created_at": datetime.utcnow().isoformat(),
            "chunk_count": len(self.chunks),
            "chunks": self.chunks,
        }

    @staticmethod
    def from_json(data: dict) -> "VectorMetadata":
        """Deserialize from JSON."""
        metadata = VectorMetadata()
        metadata.chunks = data.get("chunks", [])
        return metadata


class VectorStore:
    """FAISS-backed vector store with S3 persistence."""

    def __init__(self, dimension: int = 1024):
        """Initialize vector store.
        
        Args:
            dimension: Vector dimension (default 1024 for Titan v2)
        """
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)  # Inner product for normalized vectors
        self.metadata = VectorMetadata()
        self.s3_client = boto3.client("s3")

    def add(self, vectors: list[list[float]], chunks: list) -> None:
        """Add vectors and their metadata to the store.
        
        Args:
            vectors: List of normalized vectors (1024-dim)
            chunks: List of Chunk objects with metadata
        """
        # Convert to numpy
        vectors_array = np.array(vectors, dtype=np.float32)

        # Add to FAISS
        faiss_ids = np.arange(
            self.index.ntotal, self.index.ntotal + len(vectors), dtype=np.int64
        )
        self.index.add(vectors_array)

        # Track metadata
        for faiss_id, chunk in zip(faiss_ids, chunks):
            self.metadata.add(
                faiss_id=int(faiss_id),
                chunk_id=chunk.chunk_id,
                text=chunk.text,
                service=chunk.service,
                level=chunk.level,
                time_start=chunk.time_start,
                time_end=chunk.time_end,
                record_ids=chunk.record_ids,
            )

    def search(self, query_vector: list[float], k: int = 8) -> list[dict]:
        """Search for top-k similar chunks.
        
        Args:
            query_vector: Normalized query vector
            k: Number of results to return
            
        Returns:
            List of {chunk_id, text, service, level, score} dicts
        """
        if self.index.ntotal == 0:
            return []

        # Adjust k if fewer chunks available
        k = min(k, self.index.ntotal)

        # Search
        query_array = np.array([query_vector], dtype=np.float32)
        distances, indices = self.index.search(query_array, k)

        # Build results
        results = []
        for distance, idx in zip(distances[0], indices[0]):
            if idx == -1:  # Invalid result
                continue

            chunk_meta = self.metadata.chunks[int(idx)]
            results.append({
                "chunk_id": chunk_meta["chunk_id"],
                "text": chunk_meta["text"],
                "service": chunk_meta["service"],
                "level": chunk_meta["level"],
                "time_start": chunk_meta["time_start"],
                "time_end": chunk_meta["time_end"],
                "record_ids": chunk_meta["record_ids"],
                "score": float(distance),
            })

        return results

    def save_to_s3(self, bucket: str, prefix: str) -> str:
        """Save index and metadata to S3 with versioning.
        
        Args:
            bucket: S3 bucket name
            prefix: S3 prefix (e.g., "index/")
            
        Returns:
            Version path (e.g., "index/v20261009T140000Z")
        """
        import io
        import tempfile
        import os

        # Create version path
        version_path = f"{prefix}v{datetime.utcnow().isoformat().replace(':', '').replace('-', '')}"

        try:
            # Save FAISS index to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".index") as f:
                temp_path = f.name
            
            try:
                faiss.write_index(self.index, temp_path)
                with open(temp_path, "rb") as idx_file:
                    self.s3_client.put_object(
                        Bucket=bucket,
                        Key=f"{version_path}/faiss.index",
                        Body=idx_file.read(),
                    )
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

            # Save metadata
            metadata_json = json.dumps(self.metadata.to_json())
            self.s3_client.put_object(
                Bucket=bucket,
                Key=f"{version_path}/metadata.json",
                Body=metadata_json,
                ContentType="application/json",
            )

            # Update latest pointer
            self.s3_client.put_object(
                Bucket=bucket,
                Key=f"{prefix}latest",
                Body=version_path,
                ContentType="text/plain",
            )

            logger.info(f"Saved index to {version_path}")
            return version_path

        except Exception as e:
            logger.error(f"Failed to save index to S3: {e}")
            raise

    def load_from_s3(self, bucket: str, prefix: str) -> bool:
        """Load index and metadata from S3 using latest pointer.
        
        Args:
            bucket: S3 bucket name
            prefix: S3 prefix
            
        Returns:
            True if successful
        """
        import tempfile

        try:
            # Read latest pointer
            response = self.s3_client.get_object(Bucket=bucket, Key=f"{prefix}latest")
            version_path = response["Body"].read().decode("utf-8").strip()

            # Load FAISS index
            with tempfile.NamedTemporaryFile(delete=False) as f:
                index_response = self.s3_client.get_object(Bucket=bucket, Key=f"{version_path}/faiss.index")
                f.write(index_response["Body"].read())
                f.flush()
                self.index = faiss.read_index(f.name)

            # Load metadata
            metadata_response = self.s3_client.get_object(Bucket=bucket, Key=f"{version_path}/metadata.json")
            metadata_json = json.loads(metadata_response["Body"].read().decode("utf-8"))
            self.metadata = VectorMetadata.from_json(metadata_json)

            logger.info(f"Loaded index from {version_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to load index from S3: {e}")
            return False
