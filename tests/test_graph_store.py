"""Tests for aether.memory.graph_store — SQLite property graph."""

import os
import tempfile
import pytest

from aether.core.state import Entity, EntityType, RelationshipType
from aether.memory.graph_store import GraphStore


@pytest.fixture
def store(tmp_path):
    """Fresh GraphStore backed by a temp SQLite file."""
    db_path = str(tmp_path / "test_graph.db")
    return GraphStore(db_path=db_path)


class TestGraphStore:
    def test_add_and_query_entity(self, store: GraphStore):
        entity = Entity(id="alice", type=EntityType.PERSON, properties={"name": "Alice"})
        store.add_entity(entity)

        nodes = store.query_all_nodes()
        assert len(nodes) == 1
        assert nodes[0]["id"] == "alice"
        assert nodes[0]["type"] == "person"
        assert nodes[0]["properties"]["name"] == "Alice"

    def test_get_entity(self, store: GraphStore):
        entity = Entity(id="bob", type=EntityType.EMAIL, properties={"email": "bob@test.com"})
        store.add_entity(entity)

        result = store.get_entity("bob")
        assert result is not None
        assert result["id"] == "bob"

    def test_get_entity_not_found(self, store: GraphStore):
        assert store.get_entity("nonexistent") is None

    def test_upsert_entity(self, store: GraphStore):
        e1 = Entity(id="carol", type=EntityType.PERSON, properties={"name": "Carol v1"})
        e2 = Entity(id="carol", type=EntityType.PERSON, properties={"name": "Carol v2"})

        store.add_entity(e1)
        store.add_entity(e2)

        nodes = store.query_all_nodes()
        assert len(nodes) == 1
        assert nodes[0]["properties"]["name"] == "Carol v2"

    def test_add_and_query_relationship(self, store: GraphStore):
        store.add_entity(Entity(id="a", type=EntityType.PERSON))
        store.add_entity(Entity(id="b", type=EntityType.COMPANY))

        store.add_relationship(
            RelationshipType.MEMBER_OF, source_id="a", target_id="b"
        )

        edges = store.query_all_edges()
        assert len(edges) == 1
        assert edges[0]["source_id"] == "a"
        assert edges[0]["target_id"] == "b"
        assert edges[0]["rel_type"] == "member_of"

    def test_get_neighbors(self, store: GraphStore):
        store.add_entity(Entity(id="x", type=EntityType.DOMAIN))
        store.add_entity(Entity(id="y", type=EntityType.IP_ADDRESS))

        store.add_relationship(
            RelationshipType.RESOLVES_TO, source_id="x", target_id="y"
        )

        neighbors = store.get_neighbors("x")
        assert len(neighbors) == 1
        assert neighbors[0]["id"] == "y"

    def test_empty_store(self, store: GraphStore):
        assert store.query_all_nodes() == []
        assert store.query_all_edges() == []
        assert store.get_neighbors("anything") == []
