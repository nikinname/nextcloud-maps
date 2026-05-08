# API iniziali

## Stato

```http
GET /api/health
```

## Configurazione frontend

```http
GET /api/config
```

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
```
