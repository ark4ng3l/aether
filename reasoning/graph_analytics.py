"""
Graph Centrality & Hidden Linkage Analytics Engine for AETHER.

Computes topological network metrics (Betweenness Centrality, Degree Centrality,
Closeness Centrality, and Shortest-Path Bridges) across entity graphs to identify
hidden coordinators, critical infrastructure hubs, and key intelligence nodes.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
import networkx as nx

from aether.core.logger import logger


class GraphCentralityEngine:
    """Calculates network centrality metrics and topological bridges for intelligence graphs."""

    @staticmethod
    def analyze_graph(entities: Dict[str, Any], relationships: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyzes the intelligence entity graph and computes centrality scores.

        Args:
            entities: Dict of entity_id -> entity data dict.
            relationships: List of relationship dicts with 'source_id', 'target_id', 'relation_type'.
        """
        G = nx.Graph()

        # Add nodes
        for eid, ent in entities.items():
            ename = ent.get("name", eid)
            etype = ent.get("type", "UNKNOWN")
            G.add_node(eid, name=ename, type=etype)

        # Add edges
        for rel in relationships:
            src = rel.get("source_id")
            dst = rel.get("target_id")
            rtype = rel.get("relation_type", "RELATED_TO")
            if src and dst and src in entities and dst in entities:
                G.add_edge(src, dst, relation=rtype)

        total_nodes = G.number_of_nodes()
        total_edges = G.number_of_edges()

        if total_nodes == 0:
            return {
                "total_nodes": 0,
                "total_edges": 0,
                "centrality_rankings": [],
                "key_brokers": [],
                "clusters_count": 0,
            }

        # Calculate metrics
        degree_cen = nx.degree_centrality(G)
        betweenness_cen = nx.betweenness_centrality(G) if total_nodes > 2 else {n: 0.0 for n in G.nodes()}
        closeness_cen = nx.closeness_centrality(G) if total_nodes > 1 else {n: 0.0 for n in G.nodes()}

        # Identify connected components (clusters)
        components = list(nx.connected_components(G))

        rankings = []
        for node_id in G.nodes():
            ent = entities.get(node_id, {})
            name = ent.get("name", node_id)
            etype = ent.get("type", "UNKNOWN")
            deg = degree_cen.get(node_id, 0.0)
            bet = betweenness_cen.get(node_id, 0.0)
            clo = closeness_cen.get(node_id, 0.0)

            composite_influence = round((deg * 0.4 + bet * 0.4 + clo * 0.2) * 100, 1)

            rankings.append({
                "id": node_id,
                "name": name,
                "type": etype,
                "degree_centrality": round(deg, 3),
                "betweenness_centrality": round(bet, 3),
                "closeness_centrality": round(clo, 3),
                "composite_influence_score": composite_influence,
                "is_key_broker": bet > 0.15,
            })

        # Sort by composite influence
        rankings.sort(key=lambda x: x["composite_influence_score"], reverse=True)

        key_brokers = [r for r in rankings if r["is_key_broker"]]

        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "clusters_count": len(components),
            "centrality_rankings": rankings,
            "key_brokers": key_brokers,
            "most_influential_node": rankings[0] if rankings else None,
        }
