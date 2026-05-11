from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, auth, photos
from app.config import get_settings
from app.database import init_db, mark_interrupted_scan_jobs

settings = get_settings()

app = FastAPI(title="Nextcloud Photo Map")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(photos.router)
app.include_router(admin.router)
app.include_router(auth.router)


@app.on_event("startup")
def startup() -> None:
    init_db()
    mark_interrupted_scan_jobs()


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/config")
def frontend_config():
    return {
        "tileUrl": settings.map_tile_url,
        "defaultLat": settings.map_default_lat,
        "defaultLon": settings.map_default_lon,
        "defaultZoom": settings.map_default_zoom,
        "nextcloudUrl": str(settings.nextcloud_url).rstrip("/"),
    }
