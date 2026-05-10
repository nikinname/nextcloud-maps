from functools import lru_cache

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    nextcloud_url: AnyHttpUrl = "https://nextcloud.example.org"
    nextcloud_username: str = "utente"
    nextcloud_app_password: str = "app-password"
    nextcloud_base_path: str = "/Photos"
    nextcloud_exclude_paths: str = ""
    image_extensions: str = ".jpg,.jpeg,.png,.heic,.webp"

    database_url: str = "postgresql://photomap:photomap@db:5432/photomap"
    thumbnail_cache_dir: str = "/data/thumbnails"
    app_secret_key: str = "change-me-in-production"
    session_cookie_name: str = "companion_session"
    session_max_age_seconds: int = 60 * 60 * 24 * 30

    map_tile_url: str = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
    map_default_lat: float = 43.837
    map_default_lon: float = 11.195
    map_default_zoom: int = 10
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    @property
    def allowed_extensions(self) -> set[str]:
        return {item.strip().lower() for item in self.image_extensions.split(",") if item.strip()}

    @property
    def excluded_paths(self) -> tuple[str, ...]:
        return tuple(item.strip() for item in self.nextcloud_exclude_paths.split(",") if item.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
