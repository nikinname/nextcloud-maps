# Architettura iniziale

La prima versione usa tre servizi Docker Compose:

- `db`: PostgreSQL con PostGIS per dati foto e coordinate.
- `backend`: FastAPI per API, inizializzazione schema e scansione WebDAV.
- `frontend`: Nginx statico con Leaflet, proxy verso il backend su `/api`.

Il worker di indicizzazione e' integrato nel backend per il prototipo. Il comando manuale e':

```bash
docker compose exec backend python -m app.cli
```

## Multiutenza

Companion mantiene utenti locali nella tabella `app_users`. Ogni utente contiene il server Nextcloud, il login name, la cartella base e una app password cifrata con `APP_SECRET_KEY`. Le foto sono associate tramite `photos.user_id`, e tutte le API foto filtrano sul proprietario della sessione corrente.

Il primo utente viene creato automaticamente dai valori storici in `.env` ed e' admin. I nuovi utenti entrano con Nextcloud Login Flow v2: Companion non salva la password reale Nextcloud, ma solo la app password dedicata restituita dal flow.
