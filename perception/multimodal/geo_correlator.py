"""
GeoCorrelator — Geospatial Metadata & EXIF Coordinate Extraction.
Parses GPS tags from image files and normalizes them into decimal latitude/longitude.
"""

from __future__ import annotations

import os
from typing import Dict, Any, Optional
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

from aether.core.logger import logger


class GeoCorrelator:
    """Extracts and normalizes geographic coordinates and capture hardware metadata from image files."""

    @staticmethod
    def extract_gps(image_path: str) -> Dict[str, Any]:
        """
        Parses EXIF metadata and converts GPS coordinates to signed decimal degrees.
        Returns:
            {"found": bool, "lat": float, "lon": float, "timestamp": str, "device": str, ...}
        """
        if not os.path.exists(image_path):
            return {"found": False, "error": f"Image file not found: {image_path}"}

        try:
            with Image.open(image_path) as img:
                exif = img._getexif()
                if not exif:
                    return {"found": False, "reason": "No EXIF header segment present"}

                gps_raw: Dict[str, Any] = {}
                meta_raw: Dict[str, str] = {}

                for tag_id, val in exif.items():
                    name = TAGS.get(tag_id, str(tag_id))
                    if name == "GPSInfo" and isinstance(val, dict):
                        for sub_id, sub_val in val.items():
                            sub_name = GPSTAGS.get(sub_id, str(sub_id))
                            gps_raw[sub_name] = sub_val
                    else:
                        meta_raw[name] = str(val)[:120]

                if not gps_raw or "GPSLatitude" not in gps_raw or "GPSLongitude" not in gps_raw:
                    return {
                        "found": False,
                        "reason": "EXIF present but no GPS tags found",
                        "metadata": meta_raw,
                    }

                def _to_decimal(val, ref: str) -> float:
                    try:
                        d = float(val[0])
                        m = float(val[1]) / 60.0
                        s = float(val[2]) / 3600.0
                        dec = d + m + s
                        return -dec if ref in ("S", "W") else dec
                    except Exception:
                        return 0.0

                lat_ref = str(gps_raw.get("GPSLatitudeRef", "N")).upper()
                lon_ref = str(gps_raw.get("GPSLongitudeRef", "E")).upper()

                lat = _to_decimal(gps_raw["GPSLatitude"], lat_ref)
                lon = _to_decimal(gps_raw["GPSLongitude"], lon_ref)

                altitude = None
                if "GPSAltitude" in gps_raw:
                    try:
                        altitude = float(gps_raw["GPSAltitude"])
                    except Exception:
                        pass

                device = f"{meta_raw.get('Make', '')} {meta_raw.get('Model', '')}".strip() or "Unknown Device"

                return {
                    "found": True,
                    "lat": lat,
                    "lon": lon,
                    "altitude_meters": altitude,
                    "timestamp": meta_raw.get("DateTimeOriginal") or meta_raw.get("DateTime"),
                    "device": device,
                    "software": meta_raw.get("Software"),
                    "google_maps_url": f"https://www.google.com/maps?q={lat},{lon}",
                    "openstreetmap_url": f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}",
                }

        except Exception as exc:
            logger.warning(f"GeoCorrelator error for {image_path}: {exc}")
            return {"found": False, "error": str(exc)}
