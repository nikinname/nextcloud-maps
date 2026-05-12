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
    credentials_invalid BOOLEAN DEFAULT FALSE,
    credentials_error TEXT,
    credentials_checked_at TIMESTAMPTZ,
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

ALTER TABLE photos ADD CONSTRAINT photos_user_path_key UNIQUE (user_id, path);
CREATE INDEX IF NOT EXISTS idx_photos_has_gps ON photos(has_gps);
CREATE INDEX IF NOT EXISTS idx_photos_taken_at ON photos(taken_at);
CREATE INDEX IF NOT EXISTS idx_photos_geom ON photos USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_photos_user_gps ON photos(user_id, has_gps, deleted);
CREATE INDEX IF NOT EXISTS idx_photos_user_taken_at ON photos(user_id, taken_at);
CREATE INDEX IF NOT EXISTS idx_scan_jobs_user_status ON scan_jobs(user_id, status, started_at DESC);
