# Manuale admin

Questo documento descrive le operazioni di amministrazione di Nextcloud Maps Companion.

Documenti collegati:

- [README principale](../README.md)
- [Installazione e configurazione](installation.md)
- [Manuale utente](user-manual.md)
- [Architettura software](architecture.md)
- [API](api.md)

## Primo admin

L'utente configurato in `.env` con:

```env
ADMIN_NC_USERNAME=utente-nextcloud
```

diventa admin quando completa il primo login tramite Nextcloud.

## Report utenti

Gli admin vedono il pulsante:

```text
Report utenti
```

Il report mostra:

- utenti registrati;
- ruolo;
- numero foto indicizzate;
- numero foto con GPS;
- ultimo login;
- ultimo indice;
- stato credenziali;
- scansioni in corso;
- scansioni recenti.

## Scansionare un utente

Nel report utenti, ogni riga ha il pulsante:

```text
Scansiona
```

Questo accoda una scansione per quell'utente.

Le scansioni concorrenti sono limitate da:

```env
MAX_CONCURRENT_SCANS=2
```

## Scansionare tutti gli utenti

Endpoint disponibile per admin:

```http
POST /api/admin/scan/all
```

Accoda una scansione per tutti gli utenti attivi.

## Base path utenti

Ogni utente ha un `base_path` salvato in `app_users`. Cambiare `NEXTCLOUD_BASE_PATH` in `.env` influenza i nuovi utenti, non necessariamente quelli gia registrati.

Per cambiare tutti gli utenti a `/`:

```bash
docker compose exec db psql -U photomap -d photomap -c "UPDATE app_users SET base_path = '/', updated_at = now();"
```

## Stato credenziali

Un utente viene marcato come da ricollegare se:

- la app password salvata non e' decifrabile;
- Nextcloud risponde `401 Unauthorized`;
- Nextcloud risponde `403 Forbidden`.

L'utente puo' correggere il problema con `Ricollega Nextcloud`.

## Backup applicativo

Il backup JSON applicativo include:

- utenti;
- app password cifrate;
- configurazioni utente;
- foto indicizzate;
- metadati foto.

Non include:

- thumbnail;
- storico scansioni;
- dump completo PostgreSQL;
- indici/schema generali.

Creare backup:

```bash
docker compose exec backend python -m app.cli backup /data/backups/photomap-backup.json.gz
```

Importare backup:

```bash
docker compose exec backend python -m app.cli import /data/backups/photomap-backup.json.gz
```

Per ripristinare le app password cifrate serve lo stesso:

```env
APP_SECRET_KEY
```

## Backup completo PostgreSQL

Per disaster recovery e' consigliato anche un dump completo:

```bash
docker compose exec db pg_dump -U photomap -d photomap -Fc -f /tmp/photomap.dump
docker compose cp db:/tmp/photomap.dump ./photomap.dump
```

## Log

Log backend:

```bash
docker compose logs -f backend
```

Stato servizi:

```bash
docker compose ps
```

Ultimi job:

```bash
docker compose exec db psql -U photomap -d photomap -c "SELECT id, user_id, status, total_files, processed_files, error_message FROM scan_jobs ORDER BY id DESC LIMIT 20;"
```
