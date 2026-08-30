"""
EntityResolver — Probabilistic Identity Resolution & Multi-Signal Confidence Modeling.

Combines:
  • Deterministic ID & Normalized Name matching (handles @usernames, punctuation, emails)
  • Property overlap & cross-tool corroboration scoring
  • Source reliability weighting
  • Multi-signal confidence explanation for high-trust analyst UI
"""

from __future__ import annotations

import json
import re
from typing import Optional, Dict, Any, Tuple, List

from aether.core.state import Entity, EntityType, ConfidenceSignal
from aether.memory.graph_store import GraphStore
from aether.core.logger import logger

# Source reliability weights (0.0 - 1.0)
SOURCE_RELIABILITY: Dict[str, float] = {
    "whois_lookup": 0.95,
    "ip_geolocate": 0.92,
    "subdomain_finder": 0.90,
    "network_recon": 0.88,
    "shodan_lookup": 0.90,
    "image_osint": 0.85,
    "breach_lookup": 0.82,
    "social_recon": 0.78,
    "github_dorker": 0.80,
    "web_search": 0.70,
    "stealth_crawler": 0.75,
}
DEFAULT_SOURCE_RELIABILITY = 0.75


class EntityResolver:
    """
    Performs identity resolution and multi-signal confidence modeling
    to correlate disparate entities discovered across OSINT data sources.
    """

    MERGE_THRESHOLD = 0.70

    def __init__(self, graph_store: GraphStore, vector_store: Optional[Any] = None):
        self.graph_store = graph_store
        self.vector_store = vector_store

    @staticmethod
    def normalize_identifier(identifier: str) -> str:
        """Normalizes handles, emails, domains for comparison."""
        clean = identifier.strip().lower()
        if clean.startswith("@"):
            clean = clean[1:]
        return re.sub(r"[._\-]", "", clean)

    def calculate_confidence(
        self,
        source_tool: str,
        corroboration_count: int = 1,
        critic_confidence: float = 0.5,
        deterministic_format_score: float = 1.0,
    ) -> Tuple[float, List[ConfidenceSignal], Dict[str, Any]]:
        """
        Calculates multi-signal confidence score with exact §A.2 weighting:
          (critic * 0.4) + (format * 0.2) + (corroboration * 0.3) + (reliability * 0.1)
        """
        source_weight = SOURCE_RELIABILITY.get(source_tool, DEFAULT_SOURCE_RELIABILITY)
        corroboration_bonus = min(0.3, max(0.0, (corroboration_count - 1) * 0.15))

        raw_confidence = (
            (critic_confidence * 0.4)
            + (deterministic_format_score * 0.2)
            + (corroboration_bonus * 0.3)
            + (source_weight * 0.1)
        )
        final_score = round(min(1.0, max(0.0, raw_confidence)), 2)

        signals = [
            ConfidenceSignal(source_tool=source_tool, weight=source_weight, note=f"Source reliability: {source_tool}"),
            ConfidenceSignal(source_tool="deterministic_format", weight=deterministic_format_score, note="Regex & syntax validation"),
            ConfidenceSignal(source_tool="corroboration", weight=corroboration_bonus, note=f"Corroboration count: {corroboration_count}"),
            ConfidenceSignal(source_tool="llm_critic", weight=critic_confidence, note="Adversarial refutation verdict"),
        ]

        breakdown = {
            "source_tool": source_tool,
            "source_reliability": source_weight,
            "deterministic_format_score": deterministic_format_score,
            "corroboration_count": corroboration_count,
            "corroboration_bonus": round(corroboration_bonus, 2),
            "critic_confidence": round(critic_confidence, 2),
            "final_score": final_score,
            "tier": "CONFIRMED" if final_score >= 0.70 else "PLAUSIBLE" if final_score >= 0.40 else "REJECTED",
        }
        return final_score, signals, breakdown

    def calculate_similarity(self, entity_a: Entity, entity_b: Entity) -> float:
        """
        Weighted similarity score between two entities.
        """
        # 1. Exact ID match
        if entity_a.id == entity_b.id:
            return 1.0

        # Normalized handle/name match
        norm_a = self.normalize_identifier(entity_a.id)
        norm_b = self.normalize_identifier(entity_b.id)
        if norm_a and norm_a == norm_b and entity_a.type == entity_b.type:
            return 0.95

        score = 0.0

        # 2. Property overlap — weight 0.6
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
                bigrams_a = {name_a[i : i + 2] for i in range(len(name_a) - 1)}
                bigrams_b = {name_b[i : i + 2] for i in range(len(name_b) - 1)}
                if bigrams_a or bigrams_b:
                    jaccard = len(bigrams_a & bigrams_b) / len(bigrams_a | bigrams_b)
                    score += jaccard * 0.4

        return min(score, 1.0)

    def resolve(self, new_entity: Entity) -> Optional[Entity]:
        """
        Find the most-likely existing entity in graph_store matching new_entity.
        """
        existing_nodes = self.graph_store.query_all_nodes()

        best_match: Optional[Entity] = None
        highest_score = 0.0

        for node in existing_nodes:
            props = node.get("properties", {})
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

        if highest_score >= self.MERGE_THRESHOLD and best_match:
            logger.info(
                f"Entity resolved: {new_entity.id} → {best_match.id} (score={highest_score:.2f})"
            )
            return best_match
        return None
