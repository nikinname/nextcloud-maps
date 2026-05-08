CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS photos (
    id BIGSERIAL PRIMARY KEY,
    nextcloud_file_id TEXT,
    path TEXT NOT NULL UNIQUE,
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

CREATE INDEX IF NOT EXISTS idx_photos_has_gps ON photos(has_gps);
CREATE INDEX IF NOT EXISTS idx_photos_taken_at ON photos(taken_at);
CREATE INDEX IF NOT EXISTS idx_photos_geom ON photos USING GIST(geom);
