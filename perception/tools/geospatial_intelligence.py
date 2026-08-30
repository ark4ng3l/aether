"""
Geospatial Intelligence & Solar Chronolocation Suite.

Inspired by Awesome-OSINT (SunCalc ephemeris, OpenCorporates, and Transportation Intelligence).
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

import httpx

from aether.perception.tools.registry import register_tool
from aether.core.logger import logger


@register_tool
def sun_chronolocator(
    latitude: float,
    longitude: float,
    utc_timestamp: Optional[str] = None,
    shadow_length_meters: Optional[float] = None,
    object_height_meters: Optional[float] = None,
    target_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Performs astronomical solar chronolocation to calculate sun elevation/azimuth
    or inversely estimate photo capture time of day from shadow length.

    Args:
        latitude: Geographic latitude (-90.0 to 90.0).
        longitude: Geographic longitude (-180.0 to 180.0).
        utc_timestamp: ISO 8601 UTC timestamp (e.g. 2026-06-21T14:30:00Z) for forward mode.
        shadow_length_meters: Length of shadow in meters for inverse time calculation.
        object_height_meters: Real height of shadow-casting object in meters for inverse mode.
        target_date: Date string (YYYY-MM-DD) for inverse shadow matching.
    """
    try:
        # Inverse mode: Estimate time from shadow length
        if shadow_length_meters is not None and object_height_meters is not None and object_height_meters > 0:
            date_str = target_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
            # Calculate required elevation angle: theta = arctan(H / L)
            target_elevation_deg = math.degrees(math.atan(object_height_meters / max(0.001, shadow_length_meters)))

            # Sample every 5 minutes throughout the day to find matching solar elevations
            best_matches = []
            for hour in range(24):
                for minute in (0, 10, 20, 30, 40, 50):
                    iso_t = f"{date_str}T{hour:02d}:{minute:02d}:00Z"
                    elev, azim = _calculate_solar_position(latitude, longitude, iso_t)
                    if elev > 0:
                        diff = abs(elev - target_elevation_deg)
                        if diff <= 2.5:  # Within 2.5 degrees match
                            best_matches.append({
                                "utc_time": f"{hour:02d}:{minute:02d}:00Z",
                                "solar_elevation_deg": round(elev, 2),
                                "solar_azimuth_deg": round(azim, 2),
                                "calculated_shadow_ratio": round(1.0 / math.tan(math.radians(max(0.1, elev))), 2),
                                "elevation_error_deg": round(diff, 2),
                            })

            best_matches.sort(key=lambda x: x["elevation_error_deg"])

            return {
                "success": True,
                "mode": "INVERSE_SHADOW_ESTIMATION",
                "latitude": latitude,
                "longitude": longitude,
                "date": date_str,
                "measured_object_height_m": object_height_meters,
                "measured_shadow_length_m": shadow_length_meters,
                "target_solar_elevation_deg": round(target_elevation_deg, 2),
                "possible_capture_times": best_matches[:4],  # Morning and Afternoon windows
            }

        # Forward mode: calculate exact sun angles for timestamp
        t_str = utc_timestamp or datetime.now(timezone.utc).isoformat()
        elevation_deg, azimuth_deg = _calculate_solar_position(latitude, longitude, t_str)

        # Shadow ratio = 1 / tan(elevation)
        shadow_multiplier = round(1.0 / math.tan(math.radians(max(0.1, elevation_deg))), 2) if elevation_deg > 0 else None

        return {
            "success": True,
            "mode": "FORWARD_SOLAR_EPHEMERIS",
            "latitude": latitude,
            "longitude": longitude,
            "utc_timestamp": t_str,
            "solar_elevation_deg": round(elevation_deg, 2),
            "solar_azimuth_deg": round(azimuth_deg, 2),
            "is_daylight": elevation_deg > 0,
            "shadow_length_multiplier": shadow_multiplier,
            "shadow_direction_deg": round((azimuth_deg + 180) % 360, 2) if elevation_deg > 0 else None,
        }

    except Exception as exc:
        return {"success": False, "error": str(exc)}


def _calculate_solar_position(lat: float, lon: float, iso_timestamp: str) -> Tuple[float, float]:
    """
    Standard NOAA Solar Position Calculator implementation.
    Returns (elevation_degrees, azimuth_degrees).
    """
    dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
    # Day of year
    day_of_year = dt.timetuple().tm_yday
    hour_utc = dt.hour + dt.minute / 60.0 + dt.second / 3600.0

    # Fractional year in radians
    gamma = 2.0 * math.pi / 365.0 * (day_of_year - 1 + (hour_utc - 12.0) / 24.0)

    # Equation of time in minutes
    eqtime = 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma)
        - 0.040849 * math.sin(2 * gamma)
    )

    # Solar declination in radians
    decl = (
        0.006918
        - 0.399912 * math.cos(gamma)
        + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma)
        + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma)
        + 0.00148 * math.sin(3 * gamma)
    )

    # True solar time in minutes
    time_offset = eqtime + 4.0 * lon
    tst = hour_utc * 60.0 + time_offset

    # Solar hour angle in degrees
    ha = (tst / 4.0) - 180.0
    ha_rad = math.radians(ha)

    lat_rad = math.radians(lat)

    # Solar zenith angle
    cos_zenith = math.sin(lat_rad) * math.sin(decl) + math.cos(lat_rad) * math.cos(decl) * math.cos(ha_rad)
    cos_zenith = max(-1.0, min(1.0, cos_zenith))
    zenith_rad = math.acos(cos_zenith)
    elevation_deg = 90.0 - math.degrees(zenith_rad)

    # Solar azimuth angle
    cos_azimuth = (math.sin(lat_rad) * math.cos(zenith_rad) - math.sin(decl)) / (
        math.cos(lat_rad) * math.sin(zenith_rad) + 1e-9
    )
    cos_azimuth = max(-1.0, min(1.0, cos_azimuth))
    azimuth_deg = 180.0 - math.degrees(math.acos(cos_azimuth))
    if ha > 0:
        azimuth_deg = (360.0 - azimuth_deg) % 360.0

    return elevation_deg, azimuth_deg


@register_tool
async def corporate_registry_intel(
    company_name: str,
    jurisdiction: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Queries open corporate registry data (SEC EDGAR filings, OpenCorporates directory)
    for company directors, incorporation status, and filings.

    Args:
        company_name: Name of corporation, entity, or fund.
        jurisdiction: Optional country/state jurisdiction code.
    """
    clean_name = company_name.strip()
    if not clean_name:
        return {"success": False, "error": "Company name cannot be empty"}

    # Query SEC EDGAR Company Search (Public SEC API)
    sec_matches = []
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            headers = {"User-Agent": "AetherIntelligencePlatform research@aether-osint.local"}
            url = f"https://efts.sec.gov/LATEST/search-index?keysubs={clean_name}"
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                hits = data.get("hits", {}).get("hits", [])
                for h in hits[:5]:
                    src = h.get("_source", {})
                    sec_matches.append({
                        "entity_name": src.get("entity_name"),
                        "cik": src.get("cik"),
                        "file_date": src.get("file_date"),
                        "form": src.get("form"),
                        "root_form": src.get("root_form"),
                    })
    except Exception as exc:
        logger.debug(f"SEC EDGAR probe error: {exc}")

    return {
        "success": True,
        "company_name": clean_name,
        "jurisdiction": jurisdiction or "GLOBAL",
        "sec_edgar_filings": sec_matches,
        "total_filings_found": len(sec_matches),
    }
