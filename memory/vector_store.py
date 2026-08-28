"""
VectorStore — semantic memory layer using Qdrant (embedded/local) + fastembed.

Key fixes over the original:
  • ``FastEmbed`` class does not exist — uses ``TextEmbedding`` (fastembed ≥ 0.2).
  • ``embed()`` returns a generator — properly consumed.
  • Added ``search_text(query)`` so callers don't need to embed manually.
  • Graceful initialisation with optional in-memory fallback for tests.
"""

import os
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

from aether.config.settings import settings
from aether.core.logger import logger

# fastembed's public class is TextEmbedding (not FastEmbed)
from fastembed import TextEmbedding


class VectorStore:
    """
    Handles semantic memory using Qdrant in local/embedded mode.
    Uses fastembed ``TextEmbedding`` for efficient on-device vectors.
    """

    COLLECTION = "aether_semantic_memory"
    EMBED_MODEL = "BAAI/bge-small-en-v1.5"
    EMBED_DIM = 384  # BGE-small output dimension

    def __init__(self, path: Optional[str] = None, in_memory: bool = False):
        """
        Parameters
        ----------
        path : str, optional
            Disk path for persistent storage.  Defaults to ``settings.VECTOR_DB_PATH``.
        in_memory : bool
            When *True* the entire DB lives in RAM (handy for tests).
        """
        try:
            if in_memory:
                self.client = QdrantClient(location=":memory:")
            else:
                disk_path = path or settings.VECTOR_DB_PATH
                os.makedirs(disk_path, exist_ok=True)
                self.client = QdrantClient(path=disk_path)

            self._ensure_collection()
            self.embedder = TextEmbedding(model_name=self.EMBED_MODEL)
            logger.success("Vector Store initialised")
        except Exception as exc:
            logger.error(f"Failed to initialise Vector Store: {exc}")
            raise

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _ensure_collection(self):
        existing = {c.name for c in self.client.get_collections().collections}
        if self.COLLECTION not in existing:
            self.client.create_collection(
                collection_name=self.COLLECTION,
                vectors_config=VectorParams(
                    size=self.EMBED_DIM, distance=Distance.COSINE
                ),
            )
            logger.info(f"Created collection: {self.COLLECTION}")

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def add_text(self, text: str, metadata: Optional[Dict[str, Any]] = None):
        """Embeds *text* and upserts the point into Qdrant."""
        vector = self._embed_single(text)
        point_id = abs(hash(text + datetime.now(timezone.utc).isoformat())) % (2**63)
        payload = {"text": text, **(metadata or {})}
        self.client.upsert(
            collection_name=self.COLLECTION,
            points=[PointStruct(id=point_id, vector=vector, payload=payload)],
        )

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def search(self, query_vector: List[float], limit: int = 5):
        """Raw vector similarity search."""
        return self.client.search(
            collection_name=self.COLLECTION,
            query_vector=query_vector,
            limit=limit,
        )

    def search_text(self, query: str, limit: int = 5):
        """Convenience: embeds *query* then performs similarity search."""
        vector = self._embed_single(query)
        return self.search(vector, limit=limit)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _embed_single(self, text: str) -> List[float]:
        """Embed a single string and return the vector as a plain list."""
        vectors = list(self.embedder.embed([text]))  # generator → list
        return np.asarray(vectors[0]).tolist()
