"""
VLMEngine — Vision-Language Model Analysis, Satellite Imagery & Visual OSINT.
Performs semantic visual description, logo/brand detection, terrain reconnaissance, and visual OCR.
"""

from __future__ import annotations

import base64
import os
from typing import Dict, Any, List, Optional
from PIL import Image

from aether.core.logger import logger
from aether.core.model_manager import model_manager
from aether.config.settings import settings


class VisionLanguageIntelligenceEngine:
    """Multimodal Vision-Language analyzer for OSINT and visual threat assessment."""

    @staticmethod
    def _encode_image(image_path: str) -> Optional[str]:
        """Encodes an image to Base64 string."""
        if not os.path.exists(image_path):
            return None
        try:
            with open(image_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception as exc:
            logger.warning(f"Failed to base64 encode {image_path}: {exc}")
            return None

    async def analyze_image(
        self,
        image_path: str,
        custom_prompt: Optional[str] = None,
        task_mode: str = "general_osint",
    ) -> Dict[str, Any]:
        """
        Runs Vision-Language inference on an image file.
        Modes:
            - general_osint: Object, logo, text, and scene understanding
            - satellite_terrain: Environmental, coastal, urban layout, and coordinate cues
            - forensic_ocr: Text extraction, placards, signs, documents
        """
        if not os.path.exists(image_path):
            return {"success": False, "error": f"Image file not found: {image_path}"}

        b64_image = self._encode_image(image_path)
        if not b64_image:
            return {"success": False, "error": "Unable to read image bytes"}

        # Determine prompt based on task mode
        if custom_prompt:
            prompt_text = custom_prompt
        elif task_mode == "satellite_terrain":
            prompt_text = (
                "Examine this satellite or aerial image for OSINT investigation:\n"
                "1. Identify infrastructure (airfields, roads, power lines, naval docks, military or industrial structures).\n"
                "2. Analyze geographic and terrain indicators (vegetation, coastlines, sun angle, architectural style).\n"
                "3. Estimate potential geographical region, climate zone, or landmark matches."
            )
        elif task_mode == "forensic_ocr":
            prompt_text = (
                "Extract all visible text, license plates, badges, usernames, watermarks, "
                "or signboards in this image. List every string clearly."
            )
        else:
            prompt_text = (
                "Perform an exhaustive OSINT visual forensic analysis of this image:\n"
                "1. Key entities, faces/personnel, uniform/logos, brands, or vehicles.\n"
                "2. Background environment, landmark clues, visible text, or technical artifacts.\n"
                "3. High-confidence analytical observations."
            )

        try:
            # Query multimodal model via ModelManager
            vlm_model = getattr(settings, "MODEL_VISION", "llava:latest")
            raw_response = await model_manager.call_model(
                prompt=prompt_text,
                model=vlm_model,
                task_label=f"VLM Visual Intelligence ({task_mode})",
            )
            
            description = str(raw_response).strip()
            return {
                "success": True,
                "image_path": image_path,
                "task_mode": task_mode,
                "visual_intelligence_report": description,
                "model_used": vlm_model,
            }

        except Exception as exc:
            logger.warning(f"VLM neural inference failed, using fallback visual summary: {exc}")
            # Basic PIL metadata fallback
            try:
                with Image.open(image_path) as img:
                    width, height = img.size
                    fmt = img.format
                    mode = img.mode
                return {
                    "success": True,
                    "image_path": image_path,
                    "task_mode": task_mode,
                    "visual_intelligence_report": f"Image format: {fmt}, Dimensions: {width}x{height}, Color Mode: {mode}. (Neural VLM offline)",
                    "model_used": "pil_fallback",
                }
            except Exception as pil_exc:
                return {"success": False, "error": str(pil_exc)}


vlm_engine = VisionLanguageIntelligenceEngine()
