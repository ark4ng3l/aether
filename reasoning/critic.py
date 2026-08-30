"""
RedTeamCritic — Adversarial Fact Verification with Deterministic Pre-Filtering.

Uses fast deterministic pattern checks first to save latency and VRAM,
escalating only ambiguous claims to adversarial LLM refutation.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

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
    Two-stage adversarial critic:
      Stage 1: Fast deterministic syntax & structure checks.
      Stage 2: Adversarial LLM verification by refutation.
    """

    async def evaluate_finding(
        self,
        finding_description: str,
        is_heavy: bool = False,
        source_tool: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Returns ``{"verdict": "CONFIRMED"|"PLAUSIBLE"|"REJECTED",
                    "reasoning": "…", "confidence": 0.0-1.0}``.
        """
        # ── Stage 1: Deterministic Pre-Filtering ──
        quick_verdict = self._deterministic_check(finding_description, source_tool)
        if quick_verdict is not None:
            return quick_verdict

        # ── Stage 2: Adversarial LLM Refutation ──
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

        target_model = settings.MODEL_CRITIC if is_heavy else settings.MODEL_FAST

        try:
            result = await model_manager.call_model(
                prompt,
                model=target_model,
                is_heavy=is_heavy,
                response_format=CriticVerdict,
                temperature=settings.CRITIC_TEMPERATURE,
                task_label="Adversarial Refutation",
            )
            if isinstance(result, CriticVerdict):
                return result.model_dump()
        except Exception:
            pass

        # Fallback: raw text JSON extraction
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

    def _deterministic_check(
        self, text: str, source_tool: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Fast rule-based sanity checks before LLM invocation.
        Returns a CriticVerdict dict if deterministic, else None.
        """
        # Reject empty or minimal noise
        if not text or len(text.strip()) < 5:
            return {
                "verdict": "REJECTED",
                "reasoning": "Empty or meaningless payload",
                "confidence": 0.0,
            }

        # Deterministic tools providing direct technical telemetry
        technical_tools = {
            "subdomain_finder", "ip_geolocate", "network_recon",
            "image_osint", "metadata_extractor", "whois_lookup", "shodan_lookup",
            "wayback_lookup", "favicon_fingerprint", "tech_stack_fingerprint",
            "typosquat_recon", "asn_lookup", "ssl_cert_inspector",
            "cloud_bucket_recon", "robots_sitemap_recon",
        }
        lower_text = text.lower()
        if source_tool in technical_tools:
            if "error" not in lower_text and "not found" not in lower_text and "failed" not in lower_text:
                # Direct technical records are confirmed by nature of protocol response
                return {
                    "verdict": "CONFIRMED",
                    "reasoning": f"Direct technical record verified via {source_tool}",
                    "confidence": 0.95,
                }

        # Garbage or error page patterns
        lower = text.lower()
        if any(bad in lower for bad in ["404 not found", "access denied", "blocked by cloudflare", "captcha"]):
            return {
                "verdict": "REJECTED",
                "reasoning": "Output indicates error page or CAPTCHA block",
                "confidence": 0.1,
            }

        return None

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
