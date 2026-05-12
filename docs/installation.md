# Installazione e configurazione

Questo documento spiega come installare Nextcloud Maps Companion con Docker Compose.

Documenti collegati:

- [README principale](../README.md)
- [Manuale utente](user-manual.md)
- [Manuale admin](admin-manual.md)
- [Architettura software](architecture.md)

## Prerequisiti

Servono:

- un server Nextcloud raggiungibile via HTTPS;
- un utente Nextcloud che diventera' admin di Companion;
- Docker e Docker Compose;
- una porta HTTPS disponibile per il frontend.

## Installare Docker

### Linux

Su Linux e' consigliato installare Docker Engine seguendo la documentazione ufficiale della propria distribuzione:

```text
https://docs.docker.com/engine/install/
```

Dopo l'installazione verificare:

```bash
docker --version
docker compose version
```

Se l'utente non puo' usare Docker senza `sudo`, seguire le istruzioni Docker per aggiungerlo al gruppo `docker`, poi uscire e rientrare nella sessione.

### Windows

Su Windows e' consigliato installare Docker Desktop:

```text
https://docs.docker.com/desktop/setup/install/windows-install/
```

Docker Desktop include Docker Compose. Dopo l'installazione aprire PowerShell e verificare:

```powershell
docker --version
docker compose version
```

## Installazione applicazione

Clonare il repository:

```bash
git clone <url-repository> nextcloud-maps
cd nextcloud-maps
```

Creare la configurazione:

```bash
cp .env.example .env
```

Modificare `.env`.

Configurazione minima:

```env
NEXTCLOUD_URL=https://cloud.example.org
ADMIN_NC_USERNAME=utente-admin-nextcloud
NEXTCLOUD_BASE_PATH=/Photos
APP_SECRET_KEY=una-stringa-lunga-random
```

`ADMIN_NC_USERNAME` deve essere lo username Nextcloud dell'utente che diventera' admin di Companion al primo login riuscito.

Generare una chiave applicativa:

```bash
openssl rand -base64 48
```

Inserire il valore in:

```env
APP_SECRET_KEY=...
```

Non cambiarlo dopo il primo utilizzo: serve a decifrare le app password Nextcloud salvate nel database.

## HTTPS locale con certificato self-signed

Per ambiente locale:

```env
APP_BASE_URL=https://localhost:8443
CERT_MODE=selfsigned
PUBLIC_HOSTNAME=localhost
HTTP_PORT=8080
HTTPS_PORT=8443
```

Avviare:

```bash
docker compose up -d --build
```

Aprire:

```text
https://localhost:8443
```

Il browser mostrera' un avviso sul certificato self-signed.

## HTTPS produzione con Let's Encrypt

Per Let's Encrypt servono:

- DNS del dominio puntato al server;
- porta pubblica `80` raggiungibile;
- porta pubblica `443` raggiungibile;
- email valida per Let's Encrypt.

Esempio `.env`:

```env
APP_BASE_URL=https://maps.example.org
CERT_MODE=letsencrypt
PUBLIC_HOSTNAME=maps.example.org
HTTP_PORT=80
HTTPS_PORT=443
LETSENCRYPT_EMAIL=admin@example.org
```

Avviare:

```bash
docker compose up -d --build
```

Nginx parte con un certificato temporaneo se quello Let's Encrypt non esiste ancora. Certbot richiede il certificato usando la webroot condivisa. Dopo l'emissione, Nginx ricarica periodicamente i certificati; per forzare subito:

```bash
docker compose restart frontend
```

## Variabili principali

```env
NEXTCLOUD_URL=https://cloud.example.org
ADMIN_NC_USERNAME=utente-admin-nextcloud
NEXTCLOUD_BASE_PATH=/Photos
NEXTCLOUD_EXCLUDE_PATHS=
IMAGE_EXTENSIONS=.jpg,.jpeg,.png,.heic,.webp

APP_SECRET_KEY=...
MAX_CONCURRENT_SCANS=2

POSTGRES_DB=photomap
POSTGRES_USER=photomap
POSTGRES_PASSWORD=photomap
DATABASE_URL=postgresql://photomap:photomap@db:5432/photomap

CERT_MODE=selfsigned
PUBLIC_HOSTNAME=localhost
HTTP_PORT=8080
HTTPS_PORT=8443
```

## Aggiornamento

Sul server:

```bash
cd /percorso/nextcloud-maps
git pull
docker compose up -d --build
```

Prima di aggiornamenti importanti e' consigliato un backup. Vedere [Manuale admin](admin-manual.md).
