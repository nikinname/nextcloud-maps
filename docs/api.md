# API

Riferimento sintetico delle API REST esposte dal backend.

Documenti collegati:

- [README principale](../README.md)
- [Installazione e configurazione](installation.md)
- [Manuale utente](user-manual.md)
- [Manuale admin](admin-manual.md)
- [Architettura software](architecture.md)

## Stato

```http
GET /api/health
```

Risponde:

```json
{"status": "ok"}
```

## Configurazione frontend

```http
GET /api/config
```

Restituisce URL tile mappa, coordinate iniziali e URL Nextcloud configurato.

## Autenticazione

```http
GET /api/auth/me
POST /api/auth/logout
POST /api/auth/nextcloud/start
POST /api/auth/nextcloud/poll
```

Il login usa Nextcloud Login Flow v2.

`GET /api/auth/me` restituisce anche:

- ruolo;
- base path;
- stato credenziali Nextcloud;
- eventuale messaggio di ricollegamento.

## Foto

```http
GET /api/photos/map
GET /api/photos/{photo_id}
GET /api/photos/{photo_id}/thumbnail
```

Parametri di `/api/photos/map`:

- `from_date`;
- `to_date`;
- `folder`;
- `limit`.

Tutte le query sono filtrate sull'utente corrente.

## Scansioni

```http
POST /api/admin/scan
POST /api/admin/scan/all
POST /api/admin/users/{user_id}/scan
GET /api/admin/report
```

Nota storica: alcuni endpoint hanno prefisso `/api/admin`, ma `POST /api/admin/scan` avvia la scansione dell'utente corrente e puo' essere usato da qualunque utente autenticato.

Richiedono ruolo admin:

- `POST /api/admin/scan/all`;
- `POST /api/admin/users/{user_id}/scan`;
- `GET /api/admin/report`;
- backup/import.

## Backup

```http
GET /api/admin/backup
POST /api/admin/backup/import?confirm=IMPORT
```

Il backup/import e' riservato agli admin.

Il backup contiene utenti e foto, non thumbnail e storico scansioni.
