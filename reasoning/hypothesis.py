"""
HypothesisEngine — Abductive reasoning for dead-end recovery.

When the investigation stalls (low information gain) this module uses
the deep model (Hermes 35B) to brainstorm unobserved connections conditioned
on the target briefing context.
"""

from typing import List, Dict, Any, Optional

from aether.core.model_manager import model_manager
from aether.core.logger import logger
from aether.config.settings import settings


class HypothesisEngine:
    """
    Generates abductive hypotheses — probabilistic guesses about what
    information is missing and where the next connection might lie.
    """

    async def generate_abductive_hypotheses(
        self,
        evidence: List[Dict[str, Any]],
        context_briefing: str = "",
        target_seed: str = "",
    ) -> List[str]:
        """
        Given evidence and user briefing context, returns up to 3 actionable hypotheses.
        Each hypothesis is a search-ready string.
        """
        briefing_section = ""
        if context_briefing:
            briefing_section = f"\nTARGET BRIEFING / BACKGROUND:\n{context_briefing}\n"

        prompt = (
            "You are an OSINT intelligence analyst performing abductive reasoning.\n"
            f"TARGET: {target_seed}\n"
            f"{briefing_section}\n"
            "Given the observed evidence below, hypothesize what unobserved entities, "
            "aliases, infrastructure, or relationships are likely missing.\n\n"
            f"OBSERVED EVIDENCE:\n{evidence}\n\n"
            "Generate exactly 3 distinct, actionable hypotheses/search queries to investigate next.\n"
            "Format each on its own line starting with 'POSSIBLE:'\n"
            "Each must be a concrete search query, username, or domain investigation step."
        )

        try:
            response = await model_manager.call_model(
                prompt,
                model=settings.MODEL_DEEP,
                is_heavy=True,
                temperature=settings.REASONING_TEMPERATURE,
            )
            return self._parse(str(response))
        except Exception as exc:
            logger.error(f"Hypothesis generation failed: {exc}")
            seed_ref = target_seed or (evidence[0].get("desc", "target") if evidence else "target")
            return [f"search deeper OSINT footprints for {seed_ref}"]

    @staticmethod
    def _parse(text: str) -> List[str]:
        """Extract lines containing 'POSSIBLE:' and strip the prefix."""
        lines = []
        for line in text.splitlines():
            if "POSSIBLE:" in line:
                cleaned = line.split("POSSIBLE:", 1)[1].strip()
                if cleaned:
                    lines.append(cleaned)
        return lines[:3] if lines else [text.strip()[:200]]
