from fastapi import APIRouter, BackgroundTasks

from app.scanner import scan

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/scan")
def start_scan(background_tasks: BackgroundTasks):
    background_tasks.add_task(scan)
    return {"status": "started"}
