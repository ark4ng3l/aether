"""Tests for aether.memory.entity_resolver — probabilistic identity resolution."""

import pytest
from aether.core.state import Entity, EntityType
from aether.memory.graph_store import GraphStore
from aether.memory.entity_resolver import EntityResolver


@pytest.fixture
def resolver(tmp_path):
    store = GraphStore(db_path=str(tmp_path / "resolver_test.db"))
    return EntityResolver(graph_store=store), store


class TestEntityResolver:
    def test_exact_id_match(self, resolver):
        res, store = resolver
        e = Entity(id="same", type=EntityType.PERSON, properties={"name": "Alice"})
        assert res.calculate_similarity(e, e) == 1.0

    def test_name_exact_match(self, resolver):
        res, _ = resolver
        a = Entity(id="a1", type=EntityType.PERSON, properties={"name": "John Doe"})
        b = Entity(id="b2", type=EntityType.PERSON, properties={"name": "John Doe"})
        score = res.calculate_similarity(a, b)
        assert score >= 0.3  # Name match contributes 0.4

    def test_property_match(self, resolver):
        res, _ = resolver
        a = Entity(id="x", type=EntityType.EMAIL, properties={"email": "a@b.com", "name": "X"})
        b = Entity(id="y", type=EntityType.EMAIL, properties={"email": "a@b.com", "name": "Y"})
        score = res.calculate_similarity(a, b)
        assert score > 0.2  # Email property matches

    def test_no_match(self, resolver):
        res, _ = resolver
        a = Entity(id="p1", type=EntityType.PERSON, properties={"name": "Alice"})
        b = Entity(id="p2", type=EntityType.COMPANY, properties={"name": "Zebra Inc"})
        score = res.calculate_similarity(a, b)
        assert score < 0.7  # Should NOT meet threshold

    def test_resolve_finds_match(self, resolver):
        res, store = resolver
        existing = Entity(id="known", type=EntityType.PERSON, properties={"name": "Alice", "email": "alice@example.com"})
        store.add_entity(existing)

        new = Entity(id="new-id", type=EntityType.PERSON, properties={"name": "Alice", "email": "alice@example.com"})
        result = res.resolve(new)
        assert result is not None
        assert result.id == "known"

    def test_resolve_no_match(self, resolver):
        res, store = resolver
        store.add_entity(Entity(id="bob", type=EntityType.PERSON, properties={"name": "Bob"}))

        new = Entity(id="new", type=EntityType.COMPANY, properties={"name": "Acme Corp"})
        result = res.resolve(new)
        assert result is None

    def test_resolve_empty_store(self, resolver):
        res, _ = resolver
        new = Entity(id="orphan", type=EntityType.UNKNOWN)
        result = res.resolve(new)
        assert result is None
