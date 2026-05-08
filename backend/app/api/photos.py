from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.database import get_conn

router = APIRouter(prefix="/api/photos", tags=["photos"])


@router.get("/map")
def map_photos(
    from_date: str | None = None,
    to_date: str | None = None,
    folder: str | None = None,
    limit: int = Query(default=2000, ge=1, le=10000),
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
                   CASE WHEN thumbnail_cache_path IS NULL THEN NULL ELSE '/api/photos/' || id || '/thumbnail' END AS thumbnail_url
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
    raise HTTPException(status_code=501, detail="Thumbnail cache is not implemented yet")
