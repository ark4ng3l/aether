"""
EntityResolver — probabilistic identity resolution.

Key fix: replaced dangerous ``eval()`` with ``json.loads()`` for property parsing.
"""

import json
from typing import Optional

from aether.core.state import Entity, EntityType
from aether.memory.graph_store import GraphStore
from aether.core.logger import logger


class EntityResolver:
    """
    Performs probabilistic identity resolution to correlate disparate
    entities discovered across different data sources.
    """

    MERGE_THRESHOLD = 0.70  # Minimum similarity to consider a match

    def __init__(self, graph_store: GraphStore):
        self.graph_store = graph_store

    # ------------------------------------------------------------------
    # Similarity
    # ------------------------------------------------------------------

    def calculate_similarity(self, entity_a: Entity, entity_b: Entity) -> float:
        """
        Weighted similarity score between two entities.
        Combines identity matching, property overlap, and name similarity.
        """
        # 1. Exact ID match — trivial case
        if entity_a.id == entity_b.id:
            return 1.0

        score = 0.0

        # 2. Property overlap (email, phone, etc.) — weight 0.6
        common_keys = set(entity_a.properties.keys()) & set(entity_b.properties.keys())
        if common_keys:
            matches = sum(
                1
                for k in common_keys
                if entity_a.properties[k] == entity_b.properties[k]
            )
            score += (matches / len(common_keys)) * 0.6

        # 3. Name similarity — weight 0.4
        name_a = str(entity_a.properties.get("name", "")).lower().strip()
        name_b = str(entity_b.properties.get("name", "")).lower().strip()
        if name_a and name_b:
            if name_a == name_b:
                score += 0.4
            else:
                # Jaccard on character bigrams for fuzzy matching
                bigrams_a = {name_a[i : i + 2] for i in range(len(name_a) - 1)}
                bigrams_b = {name_b[i : i + 2] for i in range(len(name_b) - 1)}
                if bigrams_a or bigrams_b:
                    jaccard = len(bigrams_a & bigrams_b) / len(bigrams_a | bigrams_b)
                    score += jaccard * 0.4

        return min(score, 1.0)

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------

    def resolve(self, new_entity: Entity) -> Optional[Entity]:
        """
        Find the most-likely existing entity that matches *new_entity*.
        Returns ``None`` if nothing exceeds ``MERGE_THRESHOLD``.
        """
        existing_nodes = self.graph_store.query_all_nodes()

        best_match: Optional[Entity] = None
        highest_score = 0.0

        for node in existing_nodes:
            props = node.get("properties", {})
            # SECURITY FIX: replaced eval() with json.loads()
            if isinstance(props, str):
                try:
                    props = json.loads(props)
                except (json.JSONDecodeError, TypeError):
                    props = {}

            candidate = Entity(
                id=node["id"],
                type=EntityType(node["type"]),
                properties=props,
                confidence=float(node.get("confidence", 1.0)),
            )

            score = self.calculate_similarity(new_entity, candidate)
            if score > highest_score:
                highest_score = score
                best_match = candidate

        if highest_score >= self.MERGE_THRESHOLD:
            logger.info(
                f"Entity resolved: {new_entity.id} → {best_match.id} "  # type: ignore[union-attr]
                f"(score={highest_score:.2f})"
            )
            return best_match
        return None
