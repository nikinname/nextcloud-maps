# Nextcloud Photo Map

Web app containerizzata per indicizzare foto da Nextcloud via WebDAV, leggere coordinate EXIF e visualizzarle su mappa Leaflet.

Il documento di progetto completo e' in `README_nextcloud_photo_map.md`.

## Avvio rapido

1. Copiare `.env.example` in `.env` e compilare i dati Nextcloud.
2. Avviare lo stack:

```bash
docker compose up -d --build
```

3. Aprire la web app:

```text
http://localhost:8080
```

4. Avviare una scansione manuale:

```bash
docker compose exec backend python -m app.cli
```

Per una prova piccola senza processare tutta la libreria:

```bash
docker compose exec backend python -m app.cli --limit 5
```

In alternativa, dalla UI si puo' usare il pulsante di scansione, che chiama `POST /api/admin/scan`.

## Servizi

- `db`: PostgreSQL/PostGIS.
- `backend`: FastAPI, API REST, scanner WebDAV, lettura EXIF.
- `frontend`: Nginx con pagina Leaflet e proxy `/api`.

## Stato MVP

Implementato:

- Docker Compose con backend, database e frontend.
- Schema iniziale `photos` con campo PostGIS `geom`.
- API `/api/health`, `/api/config`, `/api/photos/map`, `/api/photos/{id}`, `/api/admin/scan`.
- Scanner incrementale basato su `etag`.
- Frontend Leaflet con clustering, filtri minimi e link Nextcloud.

Ancora da completare:

- cache miniature locale;
- autenticazione/protezione endpoint admin;
- gestione avanzata errori e report scansioni persistenti.
