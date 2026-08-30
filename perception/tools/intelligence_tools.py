"""
Intelligence & Forensic Reasoning Tools for AETHER Perception Registry.

Exposes:
- entity_matcher: Resolves whether two cross-platform handles/profiles belong to the same person.
- stylometry_analyzer: Compares writing habits, linguistic fingerprint, and authorship likelihood between texts.
- temporal_rhythm_profiler: Analyzes timestamps of events/posts to infer sleep cycles and geographic timezone.
"""

from __future__ import annotations

import time
from typing import Dict, Any, List

from aether.perception.tools.registry import BaseTool, ToolResult
from aether.reasoning.entity_resolver import (
    entity_resolver,
    stylometry_analyzer,
    temporal_estimator,
    AdmiraltyRating,
)


class EntityResolutionTool(BaseTool):
    """
    Performs multi-dimensional cross-platform entity matching and disambiguation.
    """

    def __init__(self):
        super().__init__(
            name="entity_matcher",
            description="Computes multi-dimensional cross-platform identity match probability between two online profiles.",
            category="Identity & Entity Resolution",
            icon="fingerprint",
            default_param_key="profile_a",
            example_input='{"profile_a": {"username": "alice_sec"}, "profile_b": {"username": "alicesec_dev"}}',
            params={
                "profile_a": {"type": "object", "description": "Profile dict (username, name, bio, location)"},
                "profile_b": {"type": "object", "description": "Profile dict (username, name, bio, location)"},
            },
        )

    async def execute(self, **kwargs) -> ToolResult:
        t0 = time.perf_counter()
        prof_a = kwargs.get("profile_a") or {}
        prof_b = kwargs.get("profile_b") or {}

        if not prof_a or not prof_b:
            # Check for fallback flat args
            handle_a = kwargs.get("handle_a") or kwargs.get("username_a") or kwargs.get("query")
            handle_b = kwargs.get("handle_b") or kwargs.get("username_b") or kwargs.get("target")
            if handle_a and handle_b:
                prof_a = {"username": handle_a}
                prof_b = {"username": handle_b}
            else:
                return ToolResult(success=False, data={}, error="Requires profile_a and profile_b objects")

        result = entity_resolver.resolve_profiles(prof_a, prof_b)
        elapsed = (time.perf_counter() - t0) * 1000
        return ToolResult(success=True, data=result.to_dict(), execution_time_ms=elapsed)


class StylometryTool(BaseTool):
    """
    Compares writing styles and forensic linguistics between two text corpora.
    """

    def __init__(self):
        super().__init__(
            name="stylometry_analyzer",
            description="Forensically compares writing habits, vocabulary entropy, and authorship attribution between texts.",
            category="Linguistic & Stylometric Forensics",
            icon="article",
            default_param_key="sample_a",
            example_input='{"sample_a": "First text sample...", "sample_b": "Second text sample..."}',
            params={
                "sample_a": {"type": "string", "description": "First text sample from suspect or target"},
                "sample_b": {"type": "string", "description": "Second text sample to attribute/compare"},
            },
        )

    async def execute(self, **kwargs) -> ToolResult:
        t0 = time.perf_counter()
        sample_a = kwargs.get("sample_a") or kwargs.get("text_a") or ""
        sample_b = kwargs.get("sample_b") or kwargs.get("text_b") or ""

        if not sample_a or not sample_b:
            return ToolResult(success=False, data={}, error="Requires sample_a and sample_b text strings")

        res = stylometry_analyzer.compare_authorship(sample_a, sample_b)
        elapsed = (time.perf_counter() - t0) * 1000
        return ToolResult(success=True, data=res, execution_time_ms=elapsed)


class TemporalRhythmTool(BaseTool):
    """
    Infers target circadian cycle, daily rest window, and geographical UTC timezone from event timestamps.
    """

    def __init__(self):
        super().__init__(
            name="temporal_rhythm_profiler",
            description="Deduces bio-timezone and human sleep/wake rhythm from a list of post/commit/message timestamps.",
            category="Temporal & Behavioral Analytics",
            icon="schedule",
            default_param_key="timestamps",
            example_input='{"timestamps": ["2026-08-30T10:00:00Z", "2026-08-30T14:30:00Z"]}',
            params={
                "timestamps": {"type": "array", "description": "Array of ISO-8601 strings or epoch integers"},
            },
        )

    async def execute(self, **kwargs) -> ToolResult:
        t0 = time.perf_counter()
        timestamps = kwargs.get("timestamps") or []
        if isinstance(timestamps, str):
            import json
            try:
                timestamps = json.loads(timestamps)
            except Exception:
                timestamps = [timestamps]

        if not timestamps:
            return ToolResult(success=False, data={}, error="Requires timestamps array parameter")

        res = temporal_estimator.estimate_timezone(timestamps)
        elapsed = (time.perf_counter() - t0) * 1000
        return ToolResult(success=True, data=res, execution_time_ms=elapsed)
