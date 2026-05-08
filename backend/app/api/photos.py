from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.database import get_conn
from app.thumbnails import get_or_create_thumbnail

router = APIRouter(prefix="/api/photos", tags=["photos"])


@router.get("/map")
def map_photos(
    from_date: str | None = None,
    to_date: str | None = None,
    folder: str | None = None,
    limit: int = Query(default=10000, ge=1, le=10000),
):
    where = ["has_gps = true", "deleted = false"]
    params: list[object] = []
    if from_date:
        where.append("taken_at >= %s")
        params.append(from_date)
    if to_date:
        where.append("taken_at <= %s")
        params.append(to_date)
    if folder:
        where.append("path LIKE %s")
        params.append(f"{folder.rstrip('/')}%")
    params.append(limit)

    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT id, filename, path, latitude, longitude, taken_at, nextcloud_url,
                   '/api/photos/' || id || '/thumbnail' AS thumbnail_url
            FROM photos
            WHERE {' AND '.join(where)}
            ORDER BY COALESCE(taken_at, last_modified) DESC NULLS LAST
            LIMIT %s
            """,
            params,
        ).fetchall()
    return rows


@router.get("/{photo_id}")
def photo_detail(photo_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM photos WHERE id = %s AND deleted = false", (photo_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Photo not found")
    return row


@router.get("/{photo_id}/thumbnail")
def thumbnail(photo_id: int):
    try:
        thumbnail_path = get_or_create_thumbnail(photo_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Thumbnail generation failed: {exc}") from exc
    if not thumbnail_path:
        raise HTTPException(status_code=404, detail="Photo not found")
    return FileResponse(thumbnail_path, media_type="image/jpeg")
