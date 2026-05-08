import gzip
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.database import get_conn, init_db


BACKUP_VERSION = 1
PHOTO_COLUMNS = [
    "id",
    "nextcloud_file_id",
    "path",
    "filename",
    "etag",
    "mime_type",
    "size_bytes",
    "last_modified",
    "taken_at",
    "latitude",
    "longitude",
    "altitude",
    "camera_make",
    "camera_model",
    "orientation",
    "has_gps",
    "has_preview",
    "thumbnail_cache_path",
    "nextcloud_url",
    "indexed_at",
    "last_seen_at",
    "deleted",
]


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def export_backup(path: str | Path) -> dict[str, Any]:
    init_db()
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    columns_sql = ", ".join(PHOTO_COLUMNS)
    with get_conn() as conn:
        photos = conn.execute(f"SELECT {columns_sql} FROM photos ORDER BY id").fetchall()

    payload = {
        "metadata": {
            "version": BACKUP_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "table": "photos",
            "count": len(photos),
        },
        "photos": photos,
    }
    backup_json = json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default)
    _write_text(output_path, backup_json)
    return {"path": str(output_path), "photos": len(photos), "compressed": _is_gzip_path(output_path)}


def inspect_backup(path: str | Path) -> dict[str, Any]:
    payload = _load_payload(path)
    metadata = payload["metadata"]
    return {
        "path": str(Path(path)),
        "version": metadata["version"],
        "created_at": metadata.get("created_at"),
        "photos": len(payload["photos"]),
    }


def import_backup(path: str | Path, confirmed: bool = False) -> dict[str, Any]:
    if not confirmed:
        raise RuntimeError("Import requires explicit confirmation because current data will be deleted.")

    payload = _load_payload(path)
    photos = payload["photos"]
    init_db()

    columns_sql = ", ".join(PHOTO_COLUMNS)
    placeholders = ", ".join([f"%({column})s" for column in PHOTO_COLUMNS])

    with get_conn() as conn:
        conn.execute("TRUNCATE photos RESTART IDENTITY")
        if photos:
            with conn.cursor() as cursor:
                cursor.executemany(
                    f"""
                    INSERT INTO photos ({columns_sql}, geom)
                    VALUES (
                        {placeholders},
                        CASE
                          WHEN %(latitude)s::double precision IS NOT NULL AND %(longitude)s::double precision IS NOT NULL
                          THEN ST_SetSRID(
                            ST_MakePoint(%(longitude)s::double precision, %(latitude)s::double precision),
                            4326
                          )::geography
                          ELSE NULL
                        END
                    )
                    """,
                    photos,
                )
            max_id = max(photo["id"] for photo in photos)
            conn.execute("SELECT setval(pg_get_serial_sequence('photos', 'id'), %s, true)", (max_id,))
        conn.commit()

    return {"path": str(Path(path)), "photos": len(photos)}


def _load_payload(path: str | Path) -> dict[str, Any]:
    input_path = Path(path)
    payload = json.loads(_read_text(input_path))
    if payload.get("metadata", {}).get("version") != BACKUP_VERSION:
        raise ValueError("Unsupported backup version")
    if not isinstance(payload.get("photos"), list):
        raise ValueError("Invalid backup: photos must be a list")
    return payload


def _is_gzip_path(path: Path) -> bool:
    return path.suffix == ".gz"


def _read_text(path: Path) -> str:
    if _is_gzip_path(path):
        with gzip.open(path, "rt", encoding="utf-8") as backup_file:
            return backup_file.read()
    return path.read_text(encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    if _is_gzip_path(path):
        with gzip.open(path, "wt", encoding="utf-8") as backup_file:
            backup_file.write(content)
        return
    path.write_text(content, encoding="utf-8")
