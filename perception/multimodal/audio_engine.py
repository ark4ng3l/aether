"""
AudioEngine — Whisper-based Speech-to-Text & Acoustic Intelligence Extraction.
Transcribes voice recordings, podcasts, intercepted audio, and video soundtracks into structured text.
"""

from __future__ import annotations

import os
from typing import Dict, Any, List, Optional
from aether.core.logger import logger

try:
    import whisper
    _HAS_WHISPER = True
except ImportError:
    _HAS_WHISPER = False


class WhisperAudioPipeline:
    """Acoustic intelligence pipeline powered by OpenAI Whisper."""

    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self._model = None

    def _get_model(self):
        if not _HAS_WHISPER:
            return None
        if self._model is None:
            logger.info(f"Loading Whisper model: '{self.model_size}'...")
            self._model = whisper.load_model(self.model_size)
        return self._model

    async def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Transcribes an audio file into timestamped text segments.
        Returns:
            {"success": bool, "transcript": str, "language": str, "segments": list, ...}
        """
        if not os.path.exists(audio_path):
            return {
                "success": False,
                "error": f"Audio file does not exist: {audio_path}",
            }

        if not _HAS_WHISPER:
            logger.warning("openai-whisper not installed. Returning fallback indicator.")
            return {
                "success": True,
                "transcript": f"[Audio Intelligence] Simulated transcription for {os.path.basename(audio_path)} (Install openai-whisper for local neural STT).",
                "language": "en",
                "segments": [],
                "engine": "fallback_stub",
            }

        try:
            import asyncio
            loop = asyncio.get_event_loop()
            model = self._get_model()
            
            options = {}
            if language:
                options["language"] = language

            result = await loop.run_in_executor(
                None,
                lambda: model.transcribe(audio_path, **options)
            )

            raw_segments = result.get("segments", [])
            formatted_segments: List[Dict[str, Any]] = []
            for seg in raw_segments:
                formatted_segments.append({
                    "id": seg.get("id"),
                    "start": round(seg.get("start", 0.0), 2),
                    "end": round(seg.get("end", 0.0), 2),
                    "text": seg.get("text", "").strip(),
                })

            full_text = result.get("text", "").strip()
            detected_lang = result.get("language", "unknown")

            return {
                "success": True,
                "transcript": full_text,
                "language": detected_lang,
                "duration_seconds": round(raw_segments[-1]["end"], 2) if raw_segments else 0.0,
                "segments_count": len(formatted_segments),
                "segments": formatted_segments,
                "engine": f"whisper-{self.model_size}",
            }

        except Exception as exc:
            logger.error(f"Whisper transcription failed on {audio_path}: {exc}")
            return {
                "success": False,
                "error": str(exc),
            }


audio_pipeline = WhisperAudioPipeline()
