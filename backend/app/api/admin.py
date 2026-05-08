from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from app.backup import export_backup, import_backup, inspect_backup
from app.scanner import scan

router = APIRouter(prefix="/api/admin", tags=["admin"])
BACKUP_DIR = Path("/data/backups")


@router.post("/scan")
def start_scan(background_tasks: BackgroundTasks):
    background_tasks.add_task(scan)
    return {"status": "started"}


@router.get("/backup")
def download_backup():
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
