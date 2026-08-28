"""
VLM Processor — Image OCR & feature extraction using Qwen3VL via Ollama.

Sends base64-encoded images to the local Ollama vision model for analysis.
"""

import base64
import os

import httpx

from aether.perception.tools.registry import BaseTool, ToolResult
from aether.config.settings import settings
from aether.core.logger import logger


class VLMProcessor(BaseTool):
    """Uses Qwen3VL via Ollama for image OCR and feature extraction."""

    def __init__(self):
        super().__init__(
            name="vlm_processor",
            description="Extracts text (OCR) and features from images using a vision LLM.",
        )

    async def execute(
        self,
        image_path: str = "",
        prompt: str = "",
        **kwargs,
    ) -> ToolResult:
        image_path = image_path or kwargs.get("file_path", "")
        if not image_path:
            return ToolResult(success=False, data={}, error="No image_path provided")

        if not os.path.exists(image_path):
            return ToolResult(success=False, data={}, error=f"File not found: {image_path}")

        if not prompt:
            prompt = (
                "Analyze this image thoroughly.  Extract ALL visible text (OCR).  "
                "Describe key objects, people, locations, logos, documents, and any "
                "identifying information that could be useful for an investigation."
            )

        logger.info(f"VLM processing: {image_path}")
        try:
            image_b64 = self._encode_image(image_path)

            async with httpx.AsyncClient(
                timeout=httpx.Timeout(connect=10.0, read=300.0, write=30.0, pool=10.0),
            ) as client:
                payload = {
                    "model": settings.MODEL_VLM,
                    "prompt": prompt,
                    "images": [image_b64],
                    "stream": False,
                    "options": {"temperature": 0.2},
                }
                resp = await client.post(
                    f"{settings.OLLAMA_BASE_URL}/api/generate", json=payload
                )
                resp.raise_for_status()
                analysis = resp.json().get("response", "")

            return ToolResult(
                success=True,
                data={"analysis": analysis, "source": image_path},
            )
        except Exception as exc:
            logger.error(f"VLM processing failed: {exc}")
            return ToolResult(success=False, data={}, error=str(exc))

    # ------------------------------------------------------------------

    @staticmethod
    def _encode_image(path: str) -> str:
        with open(path, "rb") as fh:
            return base64.b64encode(fh.read()).decode("utf-8")


vlm_processor = VLMProcessor()
