# Architettura software

Questo documento descrive componenti e flusso dati di Nextcloud Maps Companion.

Documenti collegati:

- [README principale](../README.md)
- [Installazione e configurazione](installation.md)
- [Manuale utente](user-manual.md)
- [Manuale admin](admin-manual.md)
- [API](api.md)

## Vista generale

```text
+---------------------+
|      Nextcloud      |
|  File foto utenti   |
+----------+----------+
           |
           | WebDAV + Login Flow v2
           |
+----------v----------+
|       Backend       |
| FastAPI + scanner   |
+----------+----------+
           |
           | SQL
           |
+----------v----------+
| PostgreSQL/PostGIS  |
| app_users, photos   |
+----------+----------+
           |
           | REST API
           |
+----------v----------+
|      Frontend       |
| Nginx + Leaflet     |
+---------------------+
```

## Servizi Docker Compose

### db

PostgreSQL con estensione PostGIS.

Contiene:

- utenti applicativi;
- foto indicizzate;
- stato scansioni;
- geometrie GPS.

### backend

Applicazione Python/FastAPI.

Responsabilita':

- inizializzazione schema;
- login Nextcloud Login Flow v2;
- sessioni applicative;
- cifratura app password;
- scanner WebDAV;
- lettura EXIF;
- generazione thumbnail;
- API REST;
- backup/import applicativo.

### frontend

Nginx statico con HTML, CSS e JavaScript.

Responsabilita':

- servire UI HTTPS;
- proxy verso backend su `/api`;
- mappa Leaflet;
- report admin.

### certbot

Servizio opzionale.

Con `CERT_MODE=selfsigned` resta disattivo.

Con `CERT_MODE=letsencrypt` richiede e rinnova certificati usando challenge HTTP-01. La porta pubblica 80 deve essere raggiungibile.

## Database

Tabelle principali:

- `app_users`: utenti Companion collegati a Nextcloud;
- `photos`: metadati foto e coordinate;
- `scan_jobs`: scansioni accodate, in corso, completate o fallite.

Le foto sono associate agli utenti tramite:

```text
photos.user_id -> app_users.id
```

Il vincolo di unicita' foto e':

```text
(user_id, path)
```

## Autenticazione

Companion usa Nextcloud Login Flow v2.

Flusso:

1. il frontend chiede al backend di iniziare il login;
2. il backend chiama Nextcloud `/index.php/login/v2`;
3. l'utente autorizza su Nextcloud;
4. il backend riceve `loginName` e `appPassword`;
5. Companion salva la app password cifrata;
6. Companion crea una sessione locale HTTP-only.

La password principale Nextcloud non viene mai salvata.

## Cifratura credenziali

Le app password Nextcloud sono cifrate con `APP_SECRET_KEY`.

Se `APP_SECRET_KEY` cambia, le app password gia salvate non sono piu decifrabili e gli utenti devono ricollegare Nextcloud.

## Scanner

Lo scanner:

1. legge i file Nextcloud via WebDAV;
2. filtra per estensioni immagine;
3. usa `etag` e path per aggiornamenti incrementali;
4. scarica immagini nuove o modificate;
5. legge EXIF;
6. salva metadati in `photos`;
7. marca come cancellate le foto non piu viste nel `base_path`.

Le scansioni sono accodate in un executor interno.

Il limite di concorrenza e':

```env
MAX_CONCURRENT_SCANS=2
```

## Stato scansioni

`scan_jobs.status` puo' essere:

- `queued`;
- `running`;
- `completed`;
- `failed`.

Al riavvio del backend, eventuali job `queued` o `running` lasciati a meta vengono marcati `failed`.

## Thumbnail

Le thumbnail vengono generate dal backend al primo accesso.

Sono salvate nel volume:

```text
thumbnail_cache
```

Non sono incluse nel backup applicativo.

## Backup

Il backup applicativo esporta:

- `app_users`;
- `photos`.

Non esporta:

- thumbnail;
- `scan_jobs`;
- dump completo PostgreSQL.

Per disaster recovery completo usare anche `pg_dump`. Vedere [Manuale admin](admin-manual.md).
