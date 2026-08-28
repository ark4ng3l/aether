"""
ImageOSINTTools — Image Forensics, GPS EXIF Extraction, Reverse Lookup & Vision AI.

Supports local image files and image URLs, extracting EXIF metadata, GPS coordinates,
perceptual hashes, and running OCR / Scene Analysis via Qwen3VL.
"""

from __future__ import annotations

import base64
import hashlib
import os
import re
import urllib.parse
from typing import Dict, Any, Optional, Tuple

import httpx
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

from aether.perception.tools.registry import BaseTool, ToolResult
from aether.config.settings import settings
from aether.core.logger import logger

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _convert_to_degrees(value) -> float:
    """Helper to convert the GPS coordinates stored in EXIF to decimal degrees."""
    try:
        if isinstance(value, (list, tuple)) and len(value) == 3:
            d = float(value[0])
            m = float(value[1])
            s = float(value[2])
            return d + (m / 60.0) + (s / 3600.0)
        return float(value)
    except Exception:
        return 0.0


def _extract_gps_coordinates(exif_dict: Dict[int, Any]) -> Tuple[Optional[float], Optional[float]]:
    """Extracts latitude and longitude from GPSInfo in EXIF."""
    gps_info = {}
    for tag_id, value in exif_dict.items():
        tag_name = TAGS.get(tag_id, tag_id)
        if tag_name == "GPSInfo":
            for key in value:
                sub_tag = GPSTAGS.get(key, key)
                gps_info[sub_tag] = value[key]

    if not gps_info:
        return None, None

    gps_lat = gps_info.get("GPSLatitude")
    gps_lat_ref = gps_info.get("GPSLatitudeRef", "N")
    gps_lon = gps_info.get("GPSLongitude")
    gps_lon_ref = gps_info.get("GPSLongitudeRef", "E")

    if gps_lat and gps_lon:
        lat = _convert_to_degrees(gps_lat)
        if gps_lat_ref != "N":
            lat = -lat

        lon = _convert_to_degrees(gps_lon)
        if gps_lon_ref != "E":
            lon = -lon

        return round(lat, 6), round(lon, 6)

    return None, None


def _calculate_dhash(image_path: str, hash_size: int = 8) -> str:
    """Calculates difference hash (dHash) of an image for visual duplicate matching."""
    try:
        with Image.open(image_path) as img:
            img = img.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
            pixels = list(img.getdata())
            diff = []
            for row in range(hash_size):
                for col in range(hash_size):
                    left = pixels[row * (hash_size + 1) + col]
                    right = pixels[row * (hash_size + 1) + col + 1]
                    diff.append(left > right)
            decimal_value = 0
            hex_string = []
            for index, value in enumerate(diff):
                if value:
                    decimal_value += 2 ** (index % 8)
                if (index % 8) == 7:
                    hex_string.append(hex(decimal_value)[2:].rjust(2, "0"))
                    decimal_value = 0
            return "".join(hex_string)
    except Exception:
        return ""


class ImageOSINTTool(BaseTool):
    """Full-Spectrum Image OSINT: Metadata, GPS, Perceptual Hashes, Reverse Lookup & Vision OCR."""

    def __init__(self):
        super().__init__(
            name="image_osint",
            description="Analyzes images for EXIF metadata, GPS location, reverse search URLs, hashes, and Vision OCR.",
        )

    async def execute(self, image_path: str = "", image_url: str = "", **kwargs) -> ToolResult:
        target = image_path or image_url or kwargs.get("query", "") or kwargs.get("file_path", "")
        if not target:
            return ToolResult(success=False, data={}, error="No image path or URL provided")

        local_path = target

        # 1. If target is a URL, download it temporarily
        if target.startswith(("http://", "https://")):
            try:
                ext = target.split(".")[-1].split("?")[0].lower()
                if ext not in ("jpg", "jpeg", "png", "webp", "gif"):
                    ext = "jpg"
                filename = f"img_{hashlib.md5(target.encode()).hexdigest()[:10]}.{ext}"
                local_path = os.path.join(UPLOAD_DIR, filename)

                async with httpx.AsyncClient(timeout=12.0) as client:
                    resp = await client.get(target, headers={"User-Agent": "Mozilla/5.0"})
                    resp.raise_for_status()
                    with open(local_path, "wb") as f:
                        f.write(resp.content)
            except Exception as exc:
                return ToolResult(success=False, data={}, error=f"Failed to download image URL: {exc}")

        if not os.path.exists(local_path):
            return ToolResult(success=False, data={}, error=f"Image file not found: {local_path}")

        logger.info(f"Performing Image OSINT on: {local_path}")
        results: Dict[str, Any] = {
            "source_path": local_path,
            "original_target": target,
            "file_size": os.path.getsize(local_path),
        }

        # 2. Cryptographic & Perceptual Hashes
        try:
            with open(local_path, "rb") as f:
                content = f.read()
                results["md5"] = hashlib.md5(content).hexdigest()
                results["sha256"] = hashlib.sha256(content).hexdigest()
            results["dhash"] = _calculate_dhash(local_path)
        except Exception:
            pass

        # 3. EXIF & Forensic Metadata
        try:
            with Image.open(local_path) as img:
                results["format"] = img.format
                results["width"], results["height"] = img.size
                results["mode"] = img.mode

                exif = img.getexif()
                if exif:
                    readable_exif: Dict[str, Any] = {}
                    for tag_id, val in exif.items():
                        tag_name = TAGS.get(tag_id, str(tag_id))
                        if tag_name != "GPSInfo":
                            readable_exif[tag_name] = str(val)[:150]

                    lat, lon = _extract_gps_coordinates(dict(exif))
                    if lat is not None and lon is not None:
                        results["gps"] = {
                            "lat": lat,
                            "lon": lon,
                            "maps_url": f"https://www.google.com/maps?q={lat},{lon}",
                            "openstreetmap_url": f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}",
                        }
                    results["exif"] = readable_exif
        except Exception as exc:
            results["exif_error"] = str(exc)

        # 4. Reverse Search URLs Generator
        query_target = target if target.startswith(("http://", "https://")) else ""
        if query_target:
            encoded_url = urllib.parse.quote(query_target)
            results["reverse_search_engines"] = {
                "google_lens": f"https://lens.google.com/uploadbyurl?url={encoded_url}",
                "yandex_images": f"https://yandex.com/images/search?rpt=imageview&url={encoded_url}",
                "bing_visual": f"https://www.bing.com/images/searchbyimage?cbir=sbi&imgurl={encoded_url}",
                "tineye": f"https://tineye.com/search?url={encoded_url}",
                "baidu_image": f"https://graph.baidu.com/details?isPageLoad=1&carousel=0&entrance=general&image={encoded_url}",
            }

        # 5. Local Vision AI (Qwen3VL-8B via Ollama)
        try:
            with open(local_path, "rb") as fh:
                img_b64 = base64.b64encode(fh.read()).decode("utf-8")

            prompt = (
                "You are an expert Image OSINT & forensic analyst. "
                "1. Extract ALL visible text (OCR verbatim).\n"
                "2. Identify any visible logos, badges, military insignia, clothing brands, signs, license plates, or documents.\n"
                "3. Describe landmarks, architectural styles, vegetation, weather, or geographical indicators.\n"
                "4. Identify any persons, uniforms, or notable visual entities."
            )

            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "model": settings.MODEL_VLM,
                    "prompt": prompt,
                    "images": [img_b64],
                    "stream": False,
                    "options": {"temperature": 0.2},
                }
                resp = await client.post(f"{settings.OLLAMA_BASE_URL}/api/generate", json=payload)
                if resp.status_code == 200:
                    results["vision_analysis"] = resp.json().get("response", "")
        except Exception as exc:
            results["vision_analysis_error"] = str(exc)

        return ToolResult(success=True, data=results)


image_tools = ImageOSINTTool()
