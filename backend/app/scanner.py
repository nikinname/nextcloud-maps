from pathlib import PurePosixPath

from app.config import get_settings
from app.database import get_conn, init_db
from app.exif_reader import read_exif
from app.nextcloud_client import NextcloudClient, NextcloudFile


def _is_allowed_image(item: NextcloudFile) -> bool:
    settings = get_settings()
    suffix = PurePosixPath(item.path).suffix.lower()
    if item.is_collection or suffix not in settings.allowed_extensions:
        return False
    return not any(item.path.startswith(excluded) for excluded in settings.excluded_paths)


def scan(limit: int | None = None) -> dict[str, int]:
    settings = get_settings()
    init_db()
    client = NextcloudClient(settings)
    items = [item for item in client.list_recursive(settings.nextcloud_base_path) if _is_allowed_image(item)]
    if limit is not None:
        items = items[:limit]
    seen_paths = [item.path for item in items]
    stats = {"seen": len(items), "inserted_or_updated": 0, "unchanged": 0, "exif_errors": 0}

    with get_conn() as conn:
        for item in items:
            current = conn.execute("SELECT etag FROM photos WHERE path = %s", (item.path,)).fetchone()
            if current and current["etag"] == item.etag:
                conn.execute(
                    """
                    UPDATE photos
                    SET nextcloud_file_id = %s,
                        nextcloud_url = %s,
                        last_seen_at = now(),
                        deleted = false
                    WHERE path = %s
                    """,
                    (item.file_id, client.web_url(item.path, item.file_id), item.path),
                )
                stats["unchanged"] += 1
                continue

            exif = {
                "taken_at": None,
                "latitude": None,
                "longitude": None,
                "altitude": None,
                "camera_make": None,
                "camera_model": None,
                "orientation": None,
                "has_gps": False,
            }
            try:
                exif = read_exif(client.download(item.path))
            except Exception:
                stats["exif_errors"] += 1

            conn.execute(
                """
                INSERT INTO photos (
                    nextcloud_file_id, path, filename, etag, mime_type, size_bytes,
                    last_modified, taken_at, latitude, longitude, altitude,
                    camera_make, camera_model, orientation, has_gps, has_preview,
                    nextcloud_url, indexed_at, last_seen_at, deleted, geom
                )
                VALUES (
                    %(file_id)s, %(path)s, %(filename)s, %(etag)s, %(mime_type)s, %(size_bytes)s,
                    %(last_modified)s, %(taken_at)s, %(latitude)s, %(longitude)s, %(altitude)s,
                    %(camera_make)s, %(camera_model)s, %(orientation)s, %(has_gps)s, false,
                    %(nextcloud_url)s, now(), now(), false,
                    CASE
                      WHEN %(latitude)s::double precision IS NOT NULL AND %(longitude)s::double precision IS NOT NULL
                      THEN ST_SetSRID(
                        ST_MakePoint(%(longitude)s::double precision, %(latitude)s::double precision),
                        4326
                      )::geography
                      ELSE NULL
                    END
                )
                ON CONFLICT (path) DO UPDATE SET
                    nextcloud_file_id = EXCLUDED.nextcloud_file_id,
                    filename = EXCLUDED.filename,
                    etag = EXCLUDED.etag,
                    mime_type = EXCLUDED.mime_type,
                    size_bytes = EXCLUDED.size_bytes,
                    last_modified = EXCLUDED.last_modified,
                    taken_at = EXCLUDED.taken_at,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    altitude = EXCLUDED.altitude,
                    camera_make = EXCLUDED.camera_make,
                    camera_model = EXCLUDED.camera_model,
                    orientation = EXCLUDED.orientation,
                    has_gps = EXCLUDED.has_gps,
                    nextcloud_url = EXCLUDED.nextcloud_url,
                    indexed_at = now(),
                    last_seen_at = now(),
                    deleted = false,
                    geom = EXCLUDED.geom
                """,
                {
                    "file_id": item.file_id,
                    "path": item.path,
                    "filename": item.filename,
                    "etag": item.etag,
                    "mime_type": item.mime_type,
                    "size_bytes": item.size_bytes,
                    "last_modified": item.last_modified,
                    "nextcloud_url": client.web_url(item.path, item.file_id),
                    **exif,
                },
            )
            stats["inserted_or_updated"] += 1
        conn.execute(
            "UPDATE photos SET deleted = true WHERE path LIKE %s AND NOT (path = ANY(%s::text[]))",
            (f"{settings.nextcloud_base_path.rstrip('/')}%", seen_paths),
        )
        conn.commit()
    return stats
