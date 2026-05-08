# Architettura iniziale

La prima versione usa tre servizi Docker Compose:

- `db`: PostgreSQL con PostGIS per dati foto e coordinate.
- `backend`: FastAPI per API, inizializzazione schema e scansione WebDAV.
- `frontend`: Nginx statico con Leaflet, proxy verso il backend su `/api`.

Il worker di indicizzazione e' integrato nel backend per il prototipo. Il comando manuale e':

```bash
docker compose exec backend python -m app.cli
```
