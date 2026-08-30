"""
HybridStore — Unified Vector and GraphRAG Knowledge Interface for AETHER v4.0.
Blends semantic dense embeddings search with multi-hop topological graph reasoning.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from aether.core.state import Entity, EntityType
from aether.core.logger import logger
from aether.memory.vector_store import VectorStore
from aether.memory.graph_rag import GraphRAGKnowledgeEngine


@dataclass
class FusedContext:
    query: str
    semantic_matches: List[Dict[str, Any]]
    relational_triplets: List[str]
    central_pivots: List[Dict[str, Any]]
    synthesized_prompt_context: str


class HybridKnowledgeStore:
    """
    Hybrid Knowledge Store:
    Coordinates Vector Store (dense embeddings) + GraphRAG (relational property graph)
    to power deep multi-agent intelligence queries.
    """

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        graph_engine: Optional[GraphRAGKnowledgeEngine] = None,
    ):
        self.vector_store = vector_store or VectorStore()
        self.graph_engine = graph_engine or GraphRAGKnowledgeEngine()

    def ingest_finding(
        self,
        finding_id: str,
        text: str,
        entity: Optional[Entity] = None,
        related_entities: Optional[List[tuple[str, str, str]]] = None,
    ) -> None:
        """
        Ingests a finding into both Vector Store (semantic search)
        and Graph Store (relational edges).
        
        related_entities is a list of tuples: (source_id, target_id, relation_type)
        """
        # 1. Ingest into Vector Store
        try:
            if self.vector_store:
                import asyncio
                # Add text point
                if hasattr(self.vector_store, "add_text"):
                    try:
                        loop = asyncio.get_running_loop()
                    except RuntimeError:
                        loop = None
                    if loop and loop.is_running():
                        asyncio.create_task(self.vector_store.add_text(text=text, metadata={"id": finding_id}))
                    else:
                        # Synchronous embed
                        vector = self.vector_store._embed_single(text)
                        import uuid
                        point_id = abs(hash(text)) % (2**63)
                        from qdrant_client.models import PointStruct
                        self.vector_store.client.upsert(
                            collection_name=self.vector_store.COLLECTION,
                            points=[PointStruct(id=point_id, vector=vector, payload={"text": text, "id": finding_id})],
                        )
        except Exception as exc:
            logger.debug(f"Vector upsert warning: {exc}")

        # 2. Ingest into GraphRAG
        if entity:
            self.graph_engine.add_entity(entity)

        if related_entities:
            for src, tgt, rel in related_entities:
                self.graph_engine.add_relation(src, tgt, rel)

    def query_fused_context(
        self,
        query: str,
        root_entity_id: Optional[str] = None,
        vector_top_k: int = 4,
        graph_hops: int = 2,
    ) -> FusedContext:
        """
        Performs dual-retrieval:
        1. Dense semantic search via Vector Store.
        2. K-hop relational expansion via GraphRAG.
        Returns a unified FusedContext block ready for LLM prompt injection.
        """
        # 1. Semantic Search
        semantic_results = []
        try:
            if self.vector_store:
                vector_matches = self.vector_store.search_text(query, limit=vector_top_k)
                for m in vector_matches:
                    payload = getattr(m, "payload", {}) or {}
                    score = getattr(m, "score", 0.0)
                    semantic_results.append({
                        "id": payload.get("id"),
                        "text": payload.get("text", str(payload)),
                        "score": score,
                    })
        except Exception as exc:
            logger.debug(f"Semantic search fallback: {exc}")

        # 2. Relational Subgraph Search
        relational_data = {}
        triplets = []
        if root_entity_id:
            relational_data = self.graph_engine.get_multihop_subgraph(root_entity_id, max_hops=graph_hops)
            triplets = relational_data.get("triplets", [])

        # 3. Key Pivots
        pivots = self.graph_engine.get_central_pivots(top_k=3)

        # 4. Synthesize unified prompt context
        context_parts = []
        if triplets:
            context_parts.append("### RELATIONAL KNOWLEDGE GRAPH (GraphRAG Multi-Hop):")
            context_parts.extend(f"  - {t}" for t in triplets[:10])

        if semantic_results:
            context_parts.append("\n### SEMANTIC VECTOR MEMORY (Dense Context):")
            for sr in semantic_results:
                context_parts.append(f"  - {sr.get('text', '')}")

        if pivots:
            context_parts.append("\n### KEY CENTRAL ENTITY PIVOTS:")
            for p in pivots:
                context_parts.append(f"  - {p['name']} ({p['type']}) [Degree: {p['degree']}, Centrality: {p['centrality_score']}]")

        synthesized = "\n".join(context_parts) if context_parts else "No background intelligence available."

        return FusedContext(
            query=query,
            semantic_matches=semantic_results,
            relational_triplets=triplets,
            central_pivots=pivots,
            synthesized_prompt_context=synthesized,
        )

    def clear(self) -> None:
        """Wipes both Vector Store and Graph Knowledge Engine."""
        self.graph_engine.clear()
