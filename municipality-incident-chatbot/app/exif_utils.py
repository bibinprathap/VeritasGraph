"""Photo ingest helpers — EXIF / GPS extraction (Validation Layer, step 1)."""

from __future__ import annotations

from typing import Any, Dict, Optional


def _to_degrees(value: Any) -> Optional[float]:
    """Convert an EXIF GPS coordinate (deg, min, sec) to decimal degrees."""
    try:
        d, m, s = value
        return float(d) + float(m) / 60.0 + float(s) / 3600.0
    except (TypeError, ValueError):
        return None


def extract_geo(image_path: str) -> Dict[str, Optional[float]]:
    """Best-effort extraction of GPS lat/lon and timestamp from a photo.

    Returns ``{"lat": .., "lon": .., "timestamp": ..}`` with ``None`` values when
    the data is unavailable. Never raises — a photo without EXIF simply yields
    an empty result (the fusion layer then relies on the citizen-stated
    location).
    """
    result: Dict[str, Optional[float]] = {"lat": None, "lon": None, "timestamp": None}
    try:
        from PIL import Image, ExifTags
    except Exception:  # noqa: BLE001 - Pillow not available
        return result

    try:
        with Image.open(image_path) as img:
            exif = img._getexif()  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 - not an image / no exif
        return result
    if not exif:
        return result

    tag_map = {ExifTags.TAGS.get(k, k): v for k, v in exif.items()}
    result["timestamp"] = tag_map.get("DateTimeOriginal") or tag_map.get("DateTime")

    gps = tag_map.get("GPSInfo")
    if isinstance(gps, dict):
        gps_map = {ExifTags.GPSTAGS.get(k, k): v for k, v in gps.items()}
        lat = _to_degrees(gps_map.get("GPSLatitude"))
        lon = _to_degrees(gps_map.get("GPSLongitude"))
        if lat is not None and gps_map.get("GPSLatitudeRef") == "S":
            lat = -lat
        if lon is not None and gps_map.get("GPSLongitudeRef") == "W":
            lon = -lon
        result["lat"], result["lon"] = lat, lon
    return result
