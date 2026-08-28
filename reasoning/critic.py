"""
RedTeamCritic — Adversarial fact verification ("Verification by Refutation").
Uses uncensored Gemma4-26B to detect false positives, coincidences, and hallucinations.
"""

import json
from typing import Any, Dict

from pydantic import BaseModel, Field

from aether.core.model_manager import model_manager
from aether.core.logger import logger
from aether.config.settings import settings


class CriticVerdict(BaseModel):
    verdict: str = Field(
        ...,
        description="One of: CONFIRMED, PLAUSIBLE, REJECTED",
    )
    reasoning: str = ""
    confidence: float = Field(0.5, ge=0.0, le=1.0)


class RedTeamCritic:
    """
    The Red-Team adversarial critic using uncensored Gemma4-26B model.
    """

    async def evaluate_finding(self, finding_description: str) -> Dict[str, Any]:
        """
        Returns ``{"verdict": "CONFIRMED"|"PLAUSIBLE"|"REJECTED",
                    "reasoning": "…", "confidence": 0.0-1.0}``.
        """
        prompt = (
            "You are an expert OSINT skeptic performing adversarial verification.\n"
            f'FINDING: "{finding_description}"\n\n'
            "Tasks:\n"
            "1. Is there enough evidence to support this finding?\n"
            "2. Think of a reason why this might be a FALSE connection "
            "(e.g., name coincidence, bot account, recycled username, CDN artifact).\n"
            "3. Respond ONLY with a JSON object:\n"
            '{"verdict":"CONFIRMED|PLAUSIBLE|REJECTED",'
            '"reasoning":"...","confidence":0.0-1.0}\n'
        )

        try:
            result = await model_manager.call_model(
                prompt,
                model=settings.MODEL_CRITIC,
                is_heavy=True,
                response_format=CriticVerdict,
                temperature=settings.CRITIC_TEMPERATURE,
                task_label="Adversarial Refutation",
            )
            if isinstance(result, CriticVerdict):
                return result.model_dump()
        except Exception:
            pass

        # Fallback: try raw text → JSON extraction
        try:
            raw = await model_manager.call_model(
                prompt,
                model=settings.MODEL_CRITIC,
                is_heavy=True,
                temperature=0.2,
                task_label="Adversarial Refutation",
            )
            return self._extract_verdict(str(raw))
        except Exception as exc:
            logger.error(f"Critic failed: {exc}")
            return {"verdict": "PLAUSIBLE", "reasoning": "Critic unavailable", "confidence": 0.5}

    @staticmethod
    def _extract_verdict(text: str) -> Dict[str, Any]:
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            return json.loads(text[start:end])
        except (ValueError, json.JSONDecodeError):
            upper = text.upper()
            if "CONFIRMED" in upper:
                return {"verdict": "CONFIRMED", "reasoning": text[:200], "confidence": 0.8}
            if "REJECTED" in upper:
                return {"verdict": "REJECTED", "reasoning": text[:200], "confidence": 0.3}
            return {"verdict": "PLAUSIBLE", "reasoning": text[:200], "confidence": 0.5}
