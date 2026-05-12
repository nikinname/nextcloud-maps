from hashlib import sha256
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image, ImageOps

from app.config import get_settings
from app.database import get_conn
from app.nextcloud_client import NextcloudClient
from app.users import mark_credentials_invalid, get_account


THUMBNAIL_SIZE = (320, 320)
THUMBNAIL_QUALITY = 82


def get_or_create_thumbnail(photo_id: int, user_id: int) -> Path | None:
    settings = get_settings()
    with get_conn() as conn:
        photo = conn.execute(
            """
            SELECT id, path, etag, thumbnail_cache_path
            FROM photos
            WHERE id = %s AND user_id = %s AND deleted = false
            """,
            (photo_id, user_id),
        ).fetchone()
        if not photo:
            return None

        expected_path = _thumbnail_path(photo["id"], photo["path"], photo["etag"])
        cached_path = Path(photo["thumbnail_cache_path"]) if photo["thumbnail_cache_path"] else None
        if cached_path == expected_path and cached_path.exists():
            return cached_path

        client = NextcloudClient(get_account(user_id))
        try:
            image_bytes = client.download(photo["path"])
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (401, 403):
                mark_credentials_invalid(user_id, "Nextcloud authorization was rejected. Reconnect Nextcloud.")
            raise
        _write_thumbnail(image_bytes, expected_path)
        conn.execute(
            "UPDATE photos SET thumbnail_cache_path = %s, has_preview = true WHERE id = %s",
            (str(expected_path), photo_id),
        )
        conn.commit()
        return expected_path


def _thumbnail_path(photo_id: int, path: str, etag: str | None) -> Path:
    settings = get_settings()
    cache_dir = Path(settings.thumbnail_cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    fingerprint = sha256(f"{photo_id}:{path}:{etag or ''}".encode("utf-8")).hexdigest()[:20]
    return cache_dir / f"{photo_id}-{fingerprint}.jpg"


def _write_thumbnail(image_bytes: bytes, output_path: Path) -> None:
    with Image.open(BytesIO(image_bytes)) as image:
        image = ImageOps.exif_transpose(image)
        image.thumbnail(THUMBNAIL_SIZE)
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        image.save(output_path, format="JPEG", quality=THUMBNAIL_QUALITY, optimize=True)
