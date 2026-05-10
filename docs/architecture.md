# Architettura iniziale

La prima versione usa tre servizi Docker Compose:

- `db`: PostgreSQL con PostGIS per dati foto e coordinate.
- `backend`: FastAPI per API, inizializzazione schema e scansione WebDAV.
- `frontend`: Nginx statico con Leaflet, proxy verso il backend su `/api`.
- `certbot`: opzionale, resta disattivo con certificato self-signed e richiede/rinnova certificati con `CERT_MODE=letsencrypt`.

Il frontend serve HTTPS. Le porte pubbliche sono configurate da `.env` con `HTTP_PORT` e `HTTPS_PORT`. In modalita' Let's Encrypt la porta 80 deve essere raggiungibile pubblicamente per la challenge HTTP-01.

Il worker di indicizzazione e' integrato nel backend per il prototipo. Il comando manuale e':

```bash
docker compose exec backend python -m app.cli
```

## Multiutenza

Companion mantiene utenti locali nella tabella `app_users`. Ogni utente contiene il server Nextcloud, il login name, la cartella base e una app password cifrata con `APP_SECRET_KEY`. Le foto sono associate tramite `photos.user_id`, e tutte le API foto filtrano sul proprietario della sessione corrente.

L'utente indicato in `.env` con `ADMIN_NC_USERNAME` diventa admin quando completa il login Nextcloud. I nuovi utenti entrano con Nextcloud Login Flow v2: Companion non salva la password reale Nextcloud, ma solo la app password dedicata restituita dal flow.
