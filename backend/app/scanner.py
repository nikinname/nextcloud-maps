import logging
from pathlib import PurePosixPath

from app.database import get_conn, init_db
from app.exif_reader import read_exif
from app.nextcloud_client import NextcloudClient, NextcloudFile
from app.users import NextcloudAccount, get_account, get_default_account


logger = logging.getLogger(__name__)


def _is_allowed_image(item: NextcloudFile, account: NextcloudAccount) -> bool:
    suffix = PurePosixPath(item.path).suffix.lower()
    from app.config import get_settings

    if item.is_collection or suffix not in get_settings().allowed_extensions:
        return False
    return not any(item.path.startswith(excluded) for excluded in account.exclude_paths)


def scan(user_id: int | None = None, limit: int | None = None, progress_every: int = 100) -> dict[str, int]:
    logger.info("Initializing database")
    init_db()
    account = get_account(user_id) if user_id is not None else get_default_account()
    client = NextcloudClient(account)
    logger.info("Listing Nextcloud files for user %s under %s", account.login_name, account.base_path)
    items = [item for item in client.list_recursive(account.base_path) if _is_allowed_image(item, account)]
    if limit is not None:
        items = items[:limit]
    seen_paths = [item.path for item in items]
    stats = {
        "seen": len(items),
        "inserted_or_updated": 0,
        "unchanged": 0,
        "with_gps": 0,
        "without_gps": 0,
        "exif_errors": 0,
    }
    logger.info("Scan started: %s image files queued%s", len(items), f" (limit {limit})" if limit else "")

    with get_conn() as conn:
        for index, item in enumerate(items, start=1):
            current = conn.execute(
                "SELECT etag, has_gps FROM photos WHERE user_id = %s AND path = %s",
                (account.user_id, item.path),
            ).fetchone()
            if current and current["etag"] == item.etag:
                conn.execute(
                    """
                    UPDATE photos
                    SET nextcloud_file_id = %s,
                        nextcloud_url = %s,
                        last_seen_at = now(),
                        deleted = false
                    WHERE user_id = %s AND path = %s
                    """,
                    (item.file_id, client.web_url(item.path, item.file_id), account.user_id, item.path),
                )
                stats["unchanged"] += 1
                if current["has_gps"]:
                    stats["with_gps"] += 1
                else:
                    stats["without_gps"] += 1
                if progress_every > 0 and (index == 1 or index % progress_every == 0 or index == len(items)):
                    logger.info(
                        "Scan progress: %s/%s processed, %s unchanged, %s inserted/updated, %s with GPS, %s without GPS, %s EXIF errors",
                        index,
                        len(items),
                        stats["unchanged"],
                        stats["inserted_or_updated"],
                        stats["with_gps"],
                        stats["without_gps"],
                        stats["exif_errors"],
                    )
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
            except Exception as exc:
                stats["exif_errors"] += 1
                logger.warning("EXIF read failed for %s: %s", item.path, exc)

            if exif["has_gps"]:
                stats["with_gps"] += 1
            else:
                stats["without_gps"] += 1

            conn.execute(
                """
                INSERT INTO photos (
                    user_id, nextcloud_file_id, path, filename, etag, mime_type, size_bytes,
                    last_modified, taken_at, latitude, longitude, altitude,
                    camera_make, camera_model, orientation, has_gps, has_preview,
                    nextcloud_url, indexed_at, last_seen_at, deleted, geom
                )
                VALUES (
                    %(user_id)s, %(file_id)s, %(path)s, %(filename)s, %(etag)s, %(mime_type)s, %(size_bytes)s,
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
                ON CONFLICT (user_id, path) DO UPDATE SET
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
                    "user_id": account.user_id,
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
            if progress_every > 0 and (index == 1 or index % progress_every == 0 or index == len(items)):
                logger.info(
                    "Scan progress: %s/%s processed, %s unchanged, %s inserted/updated, %s with GPS, %s without GPS, %s EXIF errors",
                    index,
                    len(items),
                    stats["unchanged"],
                    stats["inserted_or_updated"],
                    stats["with_gps"],
                    stats["without_gps"],
                    stats["exif_errors"],
                )
        if limit is None:
            conn.execute(
                """
                UPDATE photos
                SET deleted = true
                WHERE user_id = %s
                  AND path LIKE %s
                  AND NOT (path = ANY(%s::text[]))
                """,
                (account.user_id, f"{account.base_path.rstrip('/')}%", seen_paths),
            )
        else:
            logger.info("Limited scan: deletion marking skipped")
        conn.commit()
    logger.info(
        "Scan completed: %s seen, %s unchanged, %s inserted/updated, %s with GPS, %s without GPS, %s EXIF errors",
        stats["seen"],
        stats["unchanged"],
        stats["inserted_or_updated"],
        stats["with_gps"],
        stats["without_gps"],
        stats["exif_errors"],
    )
    return stats
