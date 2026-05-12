# Nextcloud Maps Companion

Nextcloud Maps Companion e' una web app autonoma che indicizza le foto archiviate su Nextcloud, legge le coordinate GPS dai metadati EXIF e le visualizza su una mappa interattiva.

L'app nasce come sostituto/companion dell'app Maps di Nextcloud quando questa non e' piu aggiornata o non risponde alle esigenze di consultazione delle foto geolocalizzate.

Nextcloud resta il sistema di archiviazione dei file. Companion gestisce indicizzazione, database locale, cache thumbnail, login utenti e visualizzazione su mappa.

## Documentazione

- [Installazione e configurazione](docs/installation.md)
- [Manuale utente](docs/user-manual.md)
- [Manuale admin](docs/admin-manual.md)
- [Architettura software](docs/architecture.md)
- [API](docs/api.md)
- [Contesto e requisiti iniziali](README_nextcloud_photo_map.md)

## Funzioni principali

- Login tramite Nextcloud Login Flow v2.
- Nessuna password Nextcloud salvata: viene salvata solo una app password dedicata, cifrata localmente.
- Supporto multiutente.
- Admin configurato tramite `ADMIN_NC_USERNAME`.
- Scansione WebDAV delle foto Nextcloud.
- Lettura EXIF e coordinate GPS.
- Mappa Leaflet con clustering marker.
- Thumbnail generate localmente.
- Report admin su utenti, foto indicizzate e scansioni.
- Backup/import applicativo di utenti e foto.
- Frontend HTTPS con certificato self-signed o Let's Encrypt.

## Avvio rapido

1. Copiare `.env.example` in `.env`.
2. Configurare almeno:

```env
NEXTCLOUD_URL=https://cloud.example.org
ADMIN_NC_USERNAME=utente-admin-nextcloud
APP_SECRET_KEY=una-stringa-lunga-random
```

3. Avviare:

```bash
docker compose up -d --build
```

4. Aprire:

```text
https://localhost:8443
```

Con `CERT_MODE=selfsigned` il browser mostrera' un avviso sul certificato. E' normale in ambiente locale.

Per dettagli completi vedere [Installazione e configurazione](docs/installation.md).

## Stato versione

Versione applicativa corrente: `2.1`.

Nome versione 2.0: `Bold Baboon`.
