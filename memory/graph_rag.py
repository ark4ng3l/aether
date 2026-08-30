"""
GraphRAG — Multi-Hop Relational Knowledge Engine for AETHER v4.0.
Combines NetworkX directed graph analysis with persistent entity relational storage.
"""

from __future__ import annotations

import networkx as nx
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass

from aether.core.state import Entity, EntityType, RelationshipType
from aether.core.logger import logger
from aether.memory.graph_store import GraphStore


@dataclass
class Triplet:
    source: str
    relation: str
    target: str
    confidence: float = 1.0


class GraphRAGKnowledgeEngine:
    """
    GraphRAG Knowledge Engine:
    Maintains a directed property graph for fast topological traversal,
    multi-hop relationship reasoning, and contextual triplet extraction for LLM prompts.
    """

    def __init__(self, graph_store: Optional[GraphStore] = None):
        self._graph = nx.DiGraph()
        self.store = graph_store or GraphStore()
        self._sync_from_store()

    def _sync_from_store(self) -> None:
        """Loads existing nodes and edges from persistent GraphStore into NetworkX."""
        try:
            nodes = self.store.query_all_nodes()
            for node in nodes:
                node_id = node.get("id")
                if node_id:
                    props = node.get("properties", {})
                    if isinstance(props, str):
                        try:
                            import json
                            props = json.loads(props)
                        except Exception:
                            props = {}
                    self._graph.add_node(
                        node_id,
                        name=props.get("name", node_id),
                        entity_type=node.get("type", "UNKNOWN"),
                        confidence=node.get("confidence", 1.0),
                        properties=props,
                    )

            edges = self.store.query_all_edges()
            for edge in edges:
                src = edge.get("source_id") or edge.get("source")
                tgt = edge.get("target_id") or edge.get("target")
                rel = edge.get("rel_type") or edge.get("type", "RELATED_TO")
                if src and tgt:
                    self._graph.add_edge(
                        src,
                        tgt,
                        relation=rel,
                        confidence=edge.get("weight", edge.get("confidence", 1.0)),
                    )
        except Exception as exc:
            logger.warning(f"Error syncing GraphRAG from store: {exc}")

    def add_entity(self, entity: Entity) -> None:
        """Adds an Entity to both NetworkX graph and persistent store."""
        name = entity.properties.get("name", entity.id) if isinstance(entity.properties, dict) else entity.id
        self._graph.add_node(
            entity.id,
            name=name,
            entity_type=entity.type.value if hasattr(entity.type, "value") else str(entity.type),
            confidence=entity.confidence,
            properties=entity.properties,
        )
        try:
            self.store.add_entity(entity)
        except Exception as exc:
            logger.debug(f"Store add_entity error: {exc}")

    def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: str = "RELATED_TO",
        confidence: float = 1.0,
    ) -> None:
        """Creates a directed relationship edge between two entities."""
        self._graph.add_edge(
            source_id,
            target_id,
            relation=relation_type,
            confidence=confidence,
        )
        try:
            # Map string to RelationshipType enum or use general
            rel_enum = RelationshipType.RESOLVES_TO
            for r_type in RelationshipType:
                if r_type.value.lower() == relation_type.lower():
                    rel_enum = r_type
                    break
            self.store.add_relationship(
                rel=rel_enum,
                source_id=source_id,
                target_id=target_id,
                weight=confidence,
            )
        except Exception as exc:
            logger.debug(f"Store edge error: {exc}")

    def get_multihop_subgraph(
        self,
        root_entity_id: str,
        max_hops: int = 2,
    ) -> Dict[str, Any]:
        """
        Extracts an egocentric k-hop subgraph around root_entity_id,
        returning structured nodes, edges, and formatted text triplets.
        """
        if not self._graph.has_node(root_entity_id):
            return {
                "root_id": root_entity_id,
                "node_count": 0,
                "edge_count": 0,
                "nodes": [],
                "edges": [],
                "triplets": [],
                "prompt_context": "No relational graph connections found.",
            }

        # BFS traversal up to max_hops
        reachable_nodes = set(
            nx.single_source_shortest_path_length(
                self._graph.to_undirected(), root_entity_id, cutoff=max_hops
            ).keys()
        )

        subgraph = self._graph.subgraph(reachable_nodes)
        
        nodes_list = []
        for n, data in subgraph.nodes(data=True):
            nodes_list.append({
                "id": n,
                "name": data.get("name", n),
                "type": data.get("entity_type", "UNKNOWN"),
                "confidence": data.get("confidence", 1.0),
            })

        edges_list = []
        triplets: List[str] = []
        for u, v, data in subgraph.edges(data=True):
            u_name = self._graph.nodes[u].get("name", u)
            v_name = self._graph.nodes[v].get("name", v)
            rel = data.get("relation", "RELATED_TO")
            conf = data.get("confidence", 1.0)
            
            edges_list.append({
                "source": u,
                "target": v,
                "relation": rel,
                "confidence": conf,
            })
            triplets.append(f"({u_name}) --[{rel} (conf={conf:.2f})]--> ({v_name})")

        formatted_context = (
            f"Relational Subgraph Context for '{root_entity_id}' ({len(nodes_list)} nodes, {len(edges_list)} edges):\n"
            + "\n".join(f"  • {t}" for t in triplets)
        )

        return {
            "root_id": root_entity_id,
            "node_count": len(nodes_list),
            "edge_count": len(edges_list),
            "nodes": nodes_list,
            "edges": edges_list,
            "triplets": triplets,
            "prompt_context": formatted_context,
        }

    def get_central_pivots(self, top_k: int = 5) -> List[Dict[str, Any]]:
        """Identifies key pivot entities using degree and betweenness centrality."""
        if len(self._graph) < 2:
            return []

        degree_dict = dict(self._graph.degree())
        betweenness = nx.betweenness_centrality(self._graph)

        sorted_nodes = sorted(
            self._graph.nodes(),
            key=lambda n: (betweenness.get(n, 0.0), degree_dict.get(n, 0)),
            reverse=True,
        )

        pivots = []
        for n in sorted_nodes[:top_k]:
            data = self._graph.nodes[n]
            pivots.append({
                "id": n,
                "name": data.get("name", n),
                "type": data.get("entity_type", "UNKNOWN"),
                "degree": degree_dict.get(n, 0),
                "centrality_score": round(betweenness.get(n, 0.0), 4),
            })
        return pivots

    def clear(self) -> None:
        """Clears both in-memory graph and persistent store."""
        self._graph.clear()
        self.store.clear()
