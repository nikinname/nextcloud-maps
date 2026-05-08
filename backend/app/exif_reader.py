from datetime import datetime
from fractions import Fraction
from io import BytesIO
from typing import Any

from PIL import ExifTags, Image


GPS_TAGS = {value: key for key, value in ExifTags.GPSTAGS.items()}
TAGS = {value: key for key, value in ExifTags.TAGS.items()}


def _to_float(value: Any) -> float:
    if isinstance(value, Fraction):
        return float(value)
    if isinstance(value, tuple) and len(value) == 2:
        return float(Fraction(value[0], value[1]))
    return float(value)


def _dms_to_decimal(values: Any, ref: str) -> float:
    degrees, minutes, seconds = (_to_float(part) for part in values)
    decimal = degrees + minutes / 60 + seconds / 3600
    if ref in {"S", "W"}:
        decimal *= -1
    return decimal


def _parse_taken_at(value: Any) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(str(value), fmt)
        except ValueError:
            continue
    return None


def read_exif(image_bytes: bytes) -> dict[str, Any]:
    with Image.open(BytesIO(image_bytes)) as image:
        raw_exif = image.getexif()
        exif = {ExifTags.TAGS.get(key, key): value for key, value in raw_exif.items()}
        gps_ifd = raw_exif.get_ifd(TAGS["GPSInfo"]) if TAGS["GPSInfo"] in raw_exif else {}
        gps = {ExifTags.GPSTAGS.get(key, key): value for key, value in gps_ifd.items()}

    latitude = None
    longitude = None
    if gps.get("GPSLatitude") and gps.get("GPSLatitudeRef") and gps.get("GPSLongitude") and gps.get("GPSLongitudeRef"):
        latitude = _dms_to_decimal(gps["GPSLatitude"], gps["GPSLatitudeRef"])
        longitude = _dms_to_decimal(gps["GPSLongitude"], gps["GPSLongitudeRef"])

    altitude = None
    if gps.get("GPSAltitude") is not None:
        altitude = _to_float(gps["GPSAltitude"])
        if gps.get("GPSAltitudeRef") == 1:
            altitude *= -1

    return {
        "taken_at": _parse_taken_at(exif.get("DateTimeOriginal") or exif.get("DateTime")),
        "latitude": latitude,
        "longitude": longitude,
        "altitude": altitude,
        "camera_make": exif.get("Make"),
        "camera_model": exif.get("Model"),
        "orientation": str(exif.get("Orientation")) if exif.get("Orientation") else None,
        "has_gps": latitude is not None and longitude is not None,
    }
