"""
VisionSpecialist — Visual Forensics, Satellite Imagery, and Geospatial Intelligence Agent.
"""

from __future__ import annotations

from typing import Dict, Any, Optional
from aether.reasoning.specialists.base_specialist import BaseSpecialist
from aether.perception.multimodal.vlm_engine import vlm_engine
from aether.perception.multimodal.geo_correlator import GeoCorrelator
from aether.perception.tools.registry import registry
from aether.core.logger import logger


class VisionSpecialist(BaseSpecialist):
    """Specialist agent for visual forensics, satellite terrain matching, OCR, and EXIF geospatial analysis."""

    def __init__(self):
        super().__init__(
            name="vision_specialist",
            domain="Visual Forensics & Geospatial OSINT",
            description="Analyzes imagery, satellite tiles, OCR text, and EXIF coordinates using VLM and geospatial engines.",
        )

    async def execute_specialized_task(
        self,
        instruction: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        logger.info(f"VisionSpecialist executing instruction: {instruction}")
        image_path = context.get("image_path") or context.get("file_path") or context.get("target") or ""
        
        if not image_path:
            return {
                "success": False,
                "error": "No image_path provided in context for VisionSpecialist.",
                "data": {},
                "summary": "Missing image input",
            }

        lower = instruction.lower()
        
        # 1. Check for EXIF GPS extraction request
        if "gps" in lower or "exif" in lower or "coordinate" in lower or "location" in lower:
            gps_res = GeoCorrelator.extract_gps(image_path)
            return {
                "success": gps_res.get("found", False) or "metadata" in gps_res,
                "data": gps_res,
                "summary": f"EXIF extraction completed: Coordinates {gps_res.get('lat')}, {gps_res.get('lon')}" if gps_res.get("found") else "No GPS tags located in EXIF header.",
                "tool_used": "geo_correlator",
            }

        # 2. Check for Satellite Imagery Reconnaissance
        task_mode = "general_osint"
        if "satellite" in lower or "terrain" in lower or "aerial" in lower:
            task_mode = "satellite_terrain"
        elif "ocr" in lower or "text" in lower or "plate" in lower or "badge" in lower:
            task_mode = "forensic_ocr"

        # 3. Execute VLM Analysis
        vlm_res = await vlm_engine.analyze_image(
            image_path=image_path,
            custom_prompt=context.get("custom_prompt"),
            task_mode=task_mode,
        )

        return {
            "success": vlm_res.get("success", False),
            "data": vlm_res,
            "summary": vlm_res.get("visual_intelligence_report", "")[:200],
            "error": vlm_res.get("error"),
            "tool_used": "vlm_engine",
        }


vision_specialist = VisionSpecialist()
