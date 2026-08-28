"""Tests for aether.core.state — Entity, AgentState, Enums."""

import pytest
from datetime import datetime, timezone
from aether.core.state import (
    Entity, EntityType, RelationshipType,
    AgentState, InvestigationStatus, Relationship,
)


class TestEntityType:
    def test_all_values_exist(self):
        expected = {
            "person", "company", "domain", "ip_address", "email",
            "social_handle", "image", "document", "artifact", "unknown",
        }
        assert {e.value for e in EntityType} == expected

    def test_string_enum(self):
        assert EntityType.PERSON == "person"
        assert isinstance(EntityType.DOMAIN, str)


class TestRelationshipType:
    def test_values(self):
        assert RelationshipType.OWNED_BY == "owned_by"
        assert RelationshipType.RESOLVES_TO == "resolves_to"


class TestEntity:
    def test_create_basic(self):
        e = Entity(id="test-1", type=EntityType.PERSON)
        assert e.id == "test-1"
        assert e.type == EntityType.PERSON
        assert e.confidence == 1.0
        assert e.properties == {}

    def test_create_with_properties(self):
        e = Entity(
            id="test-2",
            type=EntityType.DOMAIN,
            properties={"name": "example.com"},
            confidence=0.85,
        )
        assert e.properties["name"] == "example.com"
        assert e.confidence == 0.85

    def test_frozen(self):
        e = Entity(id="frozen-1", type=EntityType.EMAIL)
        with pytest.raises(Exception):
            e.id = "changed"  # Should fail because model is frozen


class TestRelationship:
    def test_create(self):
        r = Relationship(
            source_id="a", target_id="b",
            rel_type=RelationshipType.ASSOCIATED_WITH,
        )
        assert r.source_id == "a"
        assert r.confidence == 1.0


class TestAgentState:
    def test_initial_state(self):
        state = AgentState(investigation_id="inv-1", target_seed="@user")
        assert state.status == InvestigationStatus.IDLE
        assert len(state.discovered_entities) == 0
        assert state.last_error is None

    def test_add_entity(self):
        state = AgentState(investigation_id="inv-2", target_seed="example.com")
        e1 = Entity(id="e1", type=EntityType.DOMAIN)
        e2 = Entity(id="e2", type=EntityType.IP_ADDRESS)

        state.add_entity(e1)
        assert len(state.discovered_entities) == 1

        state.add_entity(e2)
        assert len(state.discovered_entities) == 2

    def test_no_duplicate_entities(self):
        state = AgentState(investigation_id="inv-3", target_seed="test")
        e = Entity(id="dup", type=EntityType.PERSON)

        state.add_entity(e)
        state.add_entity(e)  # Same ID
        assert len(state.discovered_entities) == 1

    def test_status_transitions(self):
        state = AgentState(investigation_id="inv-4", target_seed="x")
        assert state.status == InvestigationStatus.IDLE

        state.status = InvestigationStatus.PLANNING
        assert state.status == InvestigationStatus.PLANNING

        state.status = InvestigationStatus.COMPLETED
        assert state.status == InvestigationStatus.COMPLETED
