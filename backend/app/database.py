from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from app.config import get_settings


SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS app_users (
    id BIGSERIAL PRIMARY KEY,
    nextcloud_server_url TEXT NOT NULL,
    nextcloud_login_name TEXT NOT NULL,
    nextcloud_user_id TEXT,
    display_name TEXT,
    role TEXT NOT NULL DEFAULT 'user',
    app_password_encrypted TEXT NOT NULL,
    base_path TEXT NOT NULL DEFAULT '/Photos',
    exclude_paths TEXT DEFAULT '',
    disabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    last_login_at TIMESTAMPTZ,
    UNIQUE (nextcloud_server_url, nextcloud_login_name)
);

CREATE TABLE IF NOT EXISTS photos (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES app_users(id),
    nextcloud_file_id TEXT,
    path TEXT NOT NULL,
    filename TEXT NOT NULL,
    etag TEXT,
    mime_type TEXT,
    size_bytes BIGINT,
    last_modified TIMESTAMPTZ,
    taken_at TIMESTAMPTZ,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    altitude DOUBLE PRECISION,
    camera_make TEXT,
    camera_model TEXT,
    orientation TEXT,
    has_gps BOOLEAN DEFAULT FALSE,
    has_preview BOOLEAN DEFAULT FALSE,
    thumbnail_cache_path TEXT,
    nextcloud_url TEXT,
    indexed_at TIMESTAMPTZ DEFAULT now(),
    last_seen_at TIMESTAMPTZ DEFAULT now(),
    deleted BOOLEAN DEFAULT FALSE,
    geom GEOGRAPHY(Point, 4326)
);

CREATE TABLE IF NOT EXISTS scan_jobs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES app_users(id),
    status TEXT NOT NULL DEFAULT 'running',
    started_by BIGINT REFERENCES app_users(id),
    started_at TIMESTAMPTZ DEFAULT now(),
    finished_at TIMESTAMPTZ,
    total_files INTEGER DEFAULT 0,
    processed_files INTEGER DEFAULT 0,
    inserted_or_updated INTEGER DEFAULT 0,
    unchanged INTEGER DEFAULT 0,
    with_gps INTEGER DEFAULT 0,
    without_gps INTEGER DEFAULT 0,
    exif_errors INTEGER DEFAULT 0,
    error_message TEXT
);

ALTER TABLE photos ADD COLUMN IF NOT EXISTS user_id BIGINT REFERENCES app_users(id);
ALTER TABLE app_users ADD COLUMN IF NOT EXISTS disabled BOOLEAN DEFAULT FALSE;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'photos_path_key' AND conrelid = 'photos'::regclass
    ) THEN
        ALTER TABLE photos DROP CONSTRAINT photos_path_key;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'photos_user_path_key' AND conrelid = 'photos'::regclass
    ) THEN
        ALTER TABLE photos ADD CONSTRAINT photos_user_path_key UNIQUE (user_id, path);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_photos_has_gps ON photos(has_gps);
CREATE INDEX IF NOT EXISTS idx_photos_taken_at ON photos(taken_at);
CREATE INDEX IF NOT EXISTS idx_photos_geom ON photos USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_photos_user_gps ON photos(user_id, has_gps, deleted);
CREATE INDEX IF NOT EXISTS idx_photos_user_taken_at ON photos(user_id, taken_at);
CREATE INDEX IF NOT EXISTS idx_scan_jobs_user_status ON scan_jobs(user_id, status, started_at DESC);
"""


@contextmanager
def get_conn() -> Iterator[psycopg.Connection]:
    settings = get_settings()
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        yield conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(SCHEMA_SQL)
        from app.users import promote_configured_admin

        user_id = promote_configured_admin(conn, get_settings())
        if user_id is not None:
            conn.execute("UPDATE photos SET user_id = %s WHERE user_id IS NULL", (user_id,))
        conn.commit()


def mark_interrupted_scan_jobs() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE scan_jobs
            SET status = 'failed',
                finished_at = now(),
                error_message = COALESCE(error_message, 'Interrupted by backend restart')
            WHERE status IN ('queued', 'running')
              AND finished_at IS NULL
            """
        )
        conn.commit()
