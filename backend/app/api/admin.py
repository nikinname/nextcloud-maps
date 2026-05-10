from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from app.auth import current_admin, current_user
from app.backup import export_backup, import_backup, inspect_backup
from app.scanner import scan

router = APIRouter(prefix="/api/admin", tags=["admin"])
BACKUP_DIR = Path("/data/backups")


@router.post("/scan")
def start_scan(background_tasks: BackgroundTasks, user: dict[str, Any] = Depends(current_user)):
    background_tasks.add_task(scan, int(user["id"]), started_by=int(user["id"]))
    return {"status": "started"}


@router.post("/scan/all")
def start_scan_all(background_tasks: BackgroundTasks, admin: dict[str, Any] = Depends(current_admin)):
    from app.database import get_conn

    with get_conn() as conn:
        users = conn.execute("SELECT id FROM app_users WHERE disabled = false ORDER BY id").fetchall()
    for user in users:
        background_tasks.add_task(scan, int(user["id"]), started_by=int(admin["id"]))
    return {"status": "started", "users": len(users), "admin": admin["id"]}


@router.get("/users")
def list_users(admin: dict[str, Any] = Depends(current_admin)):
    from app.database import get_conn

    with get_conn() as conn:
        users = conn.execute(
            """
            SELECT id, nextcloud_server_url, nextcloud_login_name, display_name,
                   role, base_path, disabled, created_at, last_login_at
            FROM app_users
            ORDER BY id
            """
        ).fetchall()
    return {"users": users, "admin": admin["id"]}


@router.get("/report")
def admin_report(admin: dict[str, Any] = Depends(current_admin)):
    from app.database import get_conn

    with get_conn() as conn:
        users = conn.execute(
            """
            SELECT
                u.id,
                u.nextcloud_server_url,
                u.nextcloud_login_name,
                u.display_name,
                u.role,
                u.base_path,
                u.disabled,
                u.created_at,
                u.last_login_at,
                count(p.id) FILTER (WHERE p.deleted = false) AS photos_total,
                count(p.id) FILTER (WHERE p.deleted = false AND p.has_gps = true) AS photos_with_gps,
                count(p.id) FILTER (WHERE p.deleted = true) AS photos_deleted,
                max(p.indexed_at) AS last_indexed_at
            FROM app_users u
            LEFT JOIN photos p ON p.user_id = u.id
            GROUP BY u.id
            ORDER BY u.id
            """
        ).fetchall()
        running_jobs = conn.execute(
            """
            SELECT
                j.id,
                j.user_id,
                u.nextcloud_login_name,
                j.status,
                j.started_at,
                j.total_files,
                j.processed_files,
                j.inserted_or_updated,
                j.unchanged,
                j.with_gps,
                j.without_gps,
                j.exif_errors
            FROM scan_jobs j
            JOIN app_users u ON u.id = j.user_id
            WHERE j.status = 'running'
            ORDER BY j.started_at DESC
            """
        ).fetchall()
        recent_jobs = conn.execute(
            """
            SELECT
                j.id,
                j.user_id,
                u.nextcloud_login_name,
                j.status,
                j.started_at,
                j.finished_at,
                j.total_files,
                j.processed_files,
                j.inserted_or_updated,
                j.unchanged,
                j.with_gps,
                j.without_gps,
                j.exif_errors,
                j.error_message
            FROM scan_jobs j
            JOIN app_users u ON u.id = j.user_id
            ORDER BY j.started_at DESC
            LIMIT 20
            """
        ).fetchall()
    return {
        "admin": admin["id"],
        "users": users,
        "runningJobs": running_jobs,
        "recentJobs": recent_jobs,
    }


@router.get("/backup")
def download_backup(admin: dict[str, Any] = Depends(current_admin)):
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = BACKUP_DIR / "photomap-backup.json.gz"
    result = export_backup(backup_path)
    return FileResponse(
        backup_path,
        media_type="application/gzip",
        filename=backup_path.name,
        headers={"X-Photo-Count": str(result["photos"]), "X-Backup-Compressed": "true"},
    )


@router.post("/backup/import")
async def upload_backup(
    backup: UploadFile = File(...),
    confirm: str = Query(default=""),
    admin: dict[str, Any] = Depends(current_admin),
):
    if confirm != "IMPORT":
        raise HTTPException(status_code=400, detail="Import requires confirm=IMPORT")
    if not backup.filename or not (backup.filename.endswith(".json") or backup.filename.endswith(".json.gz")):
        raise HTTPException(status_code=400, detail="Backup file must be a .json or .json.gz file")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    upload_path = BACKUP_DIR / ("uploaded-import.json.gz" if backup.filename.endswith(".gz") else "uploaded-import.json")
    try:
        with upload_path.open("wb") as output:
            while chunk := await backup.read(1024 * 1024):
                output.write(chunk)
        inspect_backup(upload_path)
        return import_backup(upload_path, confirmed=True)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Backup import failed: {exc}") from exc
