# API iniziali

## Stato

```http
GET /api/health
```

## Configurazione frontend

```http
GET /api/config
```

## Autenticazione

```http
GET /api/auth/me
POST /api/auth/logout
POST /api/auth/nextcloud/start
POST /api/auth/nextcloud/poll
```

Il login usa Nextcloud Login Flow v2. La sessione applicativa e' salvata in un cookie HTTP-only.

## Foto su mappa

```http
GET /api/photos/map
```

Parametri opzionali:

- `from_date`
- `to_date`
- `folder`
- `limit`

## Dettaglio foto

```http
GET /api/photos/{id}
```

## Scansione

```http
POST /api/admin/scan
POST /api/admin/scan/all
```

`/api/admin/scan` scansiona l'utente corrente. `/api/admin/scan/all`, backup e import richiedono ruolo admin.
