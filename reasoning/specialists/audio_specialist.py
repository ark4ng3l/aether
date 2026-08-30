"""
AudioSpecialist — Acoustic Intelligence & Speech-to-Text Transcription Agent.
"""

from __future__ import annotations

from typing import Dict, Any, Optional
from aether.reasoning.specialists.base_specialist import BaseSpecialist
from aether.perception.multimodal.audio_engine import audio_pipeline
from aether.core.logger import logger


class AudioSpecialist(BaseSpecialist):
    """Specialist agent for audio transcription, speaker parsing, and acoustic intelligence extraction."""

    def __init__(self):
        super().__init__(
            name="audio_specialist",
            domain="Audio Intelligence & Speech Transcription",
            description="Transcribes audio streams and intercepts into actionable text intelligence using Whisper.",
        )

    async def execute_specialized_task(
        self,
        instruction: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        logger.info(f"AudioSpecialist executing instruction: {instruction}")
        audio_path = context.get("audio_path") or context.get("file_path") or context.get("target") or ""

        if not audio_path:
            return {
                "success": False,
                "error": "No audio_path provided in context for AudioSpecialist.",
                "data": {},
                "summary": "Missing audio input file",
            }

        language = context.get("language")
        transcription_res = await audio_pipeline.transcribe(audio_path, language=language)

        return {
            "success": transcription_res.get("success", False),
            "data": transcription_res,
            "summary": f"Audio transcription complete ({transcription_res.get('duration_seconds', 0)}s, lang={transcription_res.get('language', 'unknown')})",
            "error": transcription_res.get("error"),
            "tool_used": "whisper_audio_pipeline",
        }


audio_specialist = AudioSpecialist()
