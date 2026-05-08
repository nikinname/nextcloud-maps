# Nextcloud Photo Map

## 1. Scopo del progetto

Il progetto ha l'obiettivo di realizzare una web app autonoma rispetto a Nextcloud, capace di visualizzare su mappa le fotografie archiviate in una o più cartelle Nextcloud.

La necessità nasce dall'aggiornamento di Nextcloud alla versione 32, che rende non più utilizzabile o non più adeguata l'app Maps precedentemente impiegata per consultare le foto geolocalizzate.

La nuova applicazione dovrà:

- accedere alle fotografie presenti su Nextcloud tramite API;
- leggere le informazioni geografiche contenute nei metadati EXIF delle immagini;
- salvare in un proprio database locale le informazioni necessarie alla consultazione;
- visualizzare le foto su una mappa interattiva;
- ridurre al minimo il carico su Nextcloud;
- mantenere un collegamento verso il file originale presente su Nextcloud.

Il principio guida è che Nextcloud rimanga il sistema di archiviazione dei file, mentre la nuova applicazione gestisca autonomamente indicizzazione, ricerca, cache e visualizzazione geografica.

---

## 2. Obiettivi funzionali

### 2.1 Accesso alle foto archiviate su Nextcloud

L'applicazione dovrà essere in grado di collegarsi a Nextcloud e leggere il contenuto di una o più cartelle configurate.

L'accesso dovrà avvenire preferibilmente tramite WebDAV, usando le API standard esposte da Nextcloud.

L'applicazione dovrà poter configurare:

- URL del server Nextcloud;
- nome utente o account tecnico;
- app password o credenziali dedicate;
- cartelle da indicizzare;
- eventuali estensioni file ammesse;
- eventuali cartelle da escludere.

### 2.2 Indicizzazione delle immagini

L'applicazione dovrà eseguire una scansione delle cartelle configurate e identificare i file immagine.

Per ogni immagine rilevata dovranno essere raccolti almeno i seguenti dati:

- identificativo file Nextcloud, se disponibile;
- percorso completo del file;
- nome file;
- dimensione;
- MIME type;
- ETag o altro identificatore di modifica;
- data di ultima modifica;
- presenza o meno di anteprima;
- eventuali coordinate GPS presenti nei metadati EXIF;
- data e ora dello scatto, se presenti;
- marca e modello della fotocamera, se presenti;
- orientamento immagine, se presente.

L'indicizzazione dovrà evitare di rileggere inutilmente file già analizzati e non modificati.

### 2.3 Estrazione dei metadati EXIF

Per le immagini nuove o modificate, il backend dovrà leggere i metadati EXIF e verificare la presenza di coordinate GPS.

Le immagini prive di coordinate GPS potranno comunque essere registrate nel database, ma non saranno visualizzate sulla mappa salvo funzionalità future.

I dati geografici da salvare dovranno includere:

- latitudine;
- longitudine;
- eventuale altitudine;
- eventuale direzione di scatto, se presente;
- eventuale accuratezza, se disponibile.

### 2.4 Database locale

L'applicazione dovrà usare un proprio database, separato da quello di Nextcloud.

Il database dovrà servire per:

- evitare interrogazioni continue a Nextcloud;
- consentire ricerche rapide;
- conservare lo stato dell'indicizzazione;
- gestire cache e miniature;
- supportare filtri temporali e geografici.

Per la fase iniziale si potrà scegliere tra:

- SQLite, per un prototipo semplice;
- PostgreSQL con estensione PostGIS, per una soluzione più robusta e adatta a ricerche geografiche evolute.

La scelta consigliata per il progetto definitivo è PostgreSQL/PostGIS.

### 2.5 Visualizzazione su mappa

La web app dovrà offrire una mappa interattiva nella quale visualizzare le foto geolocalizzate.

La soluzione consigliata è l'uso di Leaflet con base cartografica OpenStreetMap o altro provider configurabile.

La mappa dovrà prevedere:

- marker per le singole foto;
- clustering dei marker;
- popup con miniatura;
- informazioni essenziali della foto;
- link per aprire il file originale in Nextcloud;
- filtri per data, cartella, anno, mese o intervallo temporale.

### 2.6 Miniature e anteprime

L'applicazione dovrà mostrare miniature delle foto senza scaricare ogni volta l'immagine originale.

In una prima fase si potrà usare l'anteprima generata da Nextcloud, se disponibile.

In una fase successiva dovrà essere prevista una cache locale delle miniature, in modo da:

- ridurre il carico su Nextcloud;
- migliorare la velocità di navigazione;
- rendere più fluida la consultazione della mappa.

### 2.7 Collegamento con Nextcloud

Ogni foto visualizzata dovrà mantenere un riferimento al file originale in Nextcloud.

La web app dovrà permettere, ove possibile, di aprire direttamente il file o la cartella corrispondente nell'interfaccia web di Nextcloud.

---

## 3. Obiettivi non funzionali

### 3.1 Separazione da Nextcloud

L'applicazione dovrà essere indipendente da Nextcloud.

Non dovrà installare componenti dentro Nextcloud e non dovrà modificare il database di Nextcloud.

Nextcloud dovrà essere trattato esclusivamente come sorgente dati tramite API.

### 3.2 Basso impatto sull'istanza Nextcloud

L'applicazione dovrà evitare scansioni troppo frequenti o massive.

La sincronizzazione dovrà essere incrementale, basata su identificativi di modifica come ETag, data di modifica o file ID.

Le operazioni più pesanti, come lettura EXIF e generazione miniature, dovranno essere eseguite localmente quando possibile.

### 3.3 Containerizzazione

Il progetto dovrà essere distribuibile tramite Docker Compose.

La configurazione consigliata prevede almeno i seguenti servizi:

- backend API;
- database;
- frontend web;
- eventuale servizio worker per l'indicizzazione;
- eventuale reverse proxy, se necessario.

### 3.4 Sicurezza

Le credenziali di accesso a Nextcloud non dovranno essere scritte nel codice sorgente.

Dovranno essere gestite tramite file `.env`, variabili d'ambiente o secret Docker.

L'applicazione dovrà prevedere almeno:

- autenticazione per l'accesso alla web app;
- protezione delle credenziali Nextcloud;
- possibilità di usare un account tecnico con permessi limitati;
- log privi di password o token;
- configurazione HTTPS tramite reverse proxy.

### 3.5 Manutenibilità

Il codice dovrà essere organizzato in modo modulare.

Le componenti principali dovranno essere separate:

- accesso Nextcloud;
- indicizzazione;
- estrazione EXIF;
- accesso database;
- API applicative;
- frontend mappa;
- gestione miniature;
- configurazione.

---

## 4. Architettura ipotizzata

### 4.1 Schema generale

```text
+--------------------+
|     Nextcloud      |
|  Archivio foto     |
+---------+----------+
          |
          | WebDAV / API
          |
+---------v----------+
|  Backend / Worker  |
|  Indicizzazione    |
|  Lettura EXIF      |
+---------+----------+
          |
          | Scrittura dati
          |
+---------v----------+
| Database locale    |
| PostgreSQL/PostGIS |
+---------+----------+
          |
          | API REST
          |
+---------v----------+
| Frontend Web       |
| Leaflet / Mappa    |
+--------------------+
```

### 4.2 Componenti principali

#### Backend

Il backend avrà il compito di:

- collegarsi a Nextcloud;
- elencare cartelle e file;
- rilevare immagini nuove, modificate o rimosse;
- leggere i metadati EXIF;
- popolare e aggiornare il database;
- esporre API REST al frontend;
- fornire informazioni sulle foto geolocalizzate;
- gestire eventuali miniature.

Tecnologie possibili:

- Python con FastAPI;
- Node.js con Express/NestJS;
- Go, se si desidera un binario leggero.

La soluzione consigliata inizialmente è Python/FastAPI, per la disponibilità di librerie mature per WebDAV, immagini ed EXIF.

#### Database

Il database dovrà contenere almeno:

- tabella delle foto;
- tabella delle cartelle indicizzate;
- tabella dello stato di scansione;
- eventuale tabella della cache miniature;
- eventuale tabella utenti della web app.

Per la versione definitiva è consigliato PostgreSQL con PostGIS.

#### Frontend

Il frontend dovrà visualizzare la mappa e interrogare le API del backend.

Tecnologie possibili:

- HTML/JavaScript semplice;
- Vue;
- React;
- Svelte.

Per un primo prototipo è sufficiente un frontend semplice con Leaflet.

#### Worker di indicizzazione

Il worker potrà essere integrato nel backend nella fase iniziale.

Successivamente potrà diventare un servizio separato, eseguito:

- manualmente;
- a intervalli pianificati;
- tramite coda di lavoro;
- tramite comando amministrativo.

---

## 5. Modello dati iniziale

Una possibile tabella `photos` potrebbe contenere:

```sql
CREATE TABLE photos (
    id BIGSERIAL PRIMARY KEY,
    nextcloud_file_id TEXT,
    path TEXT NOT NULL,
    filename TEXT NOT NULL,
    etag TEXT,
    mime_type TEXT,
    size_bytes BIGINT,
    last_modified TIMESTAMP,
    taken_at TIMESTAMP,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    altitude DOUBLE PRECISION,
    camera_make TEXT,
    camera_model TEXT,
    orientation TEXT,
    has_gps BOOLEAN DEFAULT FALSE,
    has_preview BOOLEAN DEFAULT FALSE,
    thumbnail_cache_path TEXT,
    nextcloud_url TEXT,
    indexed_at TIMESTAMP,
    last_seen_at TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE
);
```

Con PostGIS, le coordinate potranno essere gestite anche tramite un campo geografico:

```sql
ALTER TABLE photos
ADD COLUMN geom GEOGRAPHY(Point, 4326);
```

---

## 6. API applicative previste

### 6.1 API per la mappa

Esempio:

```http
GET /api/photos/map
```

Parametri possibili:

```text
from_date
to_date
folder
bbox
limit
has_gps
```

Risposta attesa:

```json
[
  {
    "id": 123,
    "filename": "IMG_0001.jpg",
    "latitude": 43.837,
    "longitude": 11.195,
    "taken_at": "2024-08-01T10:20:00",
    "thumbnail_url": "/api/photos/123/thumbnail",
    "nextcloud_url": "https://nextcloud.example.org/..."
  }
]
```

### 6.2 API dettaglio foto

```http
GET /api/photos/{id}
```

### 6.3 API miniatura

```http
GET /api/photos/{id}/thumbnail
```

### 6.4 API scansione

```http
POST /api/admin/scan
```

Oppure comando da terminale:

```bash
docker compose exec backend app scan
```

---

## 7. Strategia di sincronizzazione

La sincronizzazione dovrà essere incrementale.

### 7.1 Prima scansione

La prima scansione dovrà:

1. leggere ricorsivamente le cartelle configurate;
2. individuare i file immagine;
3. salvare i metadati base;
4. scaricare o leggere temporaneamente i file per estrarre EXIF;
5. salvare le coordinate GPS;
6. generare o recuperare le miniature.

### 7.2 Scansioni successive

Le scansioni successive dovranno:

1. interrogare Nextcloud via WebDAV;
2. confrontare file ID, percorso, dimensione, data modifica ed ETag;
3. ignorare i file invariati;
4. rianalizzare solo file nuovi o modificati;
5. marcare come rimossi i file non più presenti;
6. aggiornare miniature e metadati solo se necessario.

### 7.3 Frequenza

La frequenza di scansione potrà essere configurabile.

Ipotesi iniziali:

- scansione manuale per lo sviluppo;
- scansione schedulata ogni notte;
- scansione incrementale più frequente solo in cartelle specifiche.

---

## 8. Fasi di sviluppo

## Fase 1 - Analisi e progetto tecnico

Obiettivi:

- definire le cartelle Nextcloud da indicizzare;
- scegliere il linguaggio backend;
- scegliere il database;
- definire il formato di configurazione;
- verificare l'accesso WebDAV a Nextcloud 32;
- verificare la possibilità di leggere ETag, MIME type, file ID e anteprime;
- definire il modello dati minimo.

Deliverable:

- README di progetto;
- schema architetturale;
- file `.env.example`;
- bozza `docker-compose.yml`;
- modello dati iniziale.

---

## Fase 2 - Prototipo di accesso a Nextcloud

Obiettivi:

- implementare il collegamento WebDAV;
- leggere una cartella configurata;
- elencare file e sottocartelle;
- filtrare i file immagine;
- stampare a log i metadati base.

Deliverable:

- modulo client Nextcloud;
- comando manuale di test;
- log leggibile della scansione;
- gestione errori di autenticazione e connessione.

---

## Fase 3 - Estrazione EXIF

Obiettivi:

- scaricare temporaneamente una immagine;
- leggere i metadati EXIF;
- estrarre coordinate GPS;
- convertire coordinate in formato decimale;
- gestire immagini senza coordinate;
- gestire immagini con EXIF incompleti o corrotti.

Deliverable:

- modulo EXIF;
- test su immagini reali;
- output JSON dei metadati estratti.

---

## Fase 4 - Database locale

Obiettivi:

- creare lo schema database;
- salvare i file indicizzati;
- salvare coordinate e metadati;
- implementare aggiornamento basato su ETag;
- distinguere file nuovi, modificati, invariati e rimossi.

Deliverable:

- migrazioni database;
- repository dati;
- comando di scansione persistente;
- report finale della scansione.

---

## Fase 5 - API backend

Obiettivi:

- esporre API REST per il frontend;
- fornire elenco foto geolocalizzate;
- fornire dettaglio foto;
- fornire endpoint per miniature;
- prevedere filtri base.

Deliverable:

- API `/api/photos/map`;
- API `/api/photos/{id}`;
- API `/api/photos/{id}/thumbnail`;
- documentazione OpenAPI, se si usa FastAPI.

---

## Fase 6 - Frontend mappa

Obiettivi:

- creare interfaccia web;
- integrare Leaflet;
- mostrare marker sulla mappa;
- usare clustering;
- mostrare popup con miniatura;
- aprire il file originale su Nextcloud.

Deliverable:

- pagina mappa funzionante;
- popup foto;
- collegamento a Nextcloud;
- filtri minimi.

---

## Fase 7 - Cache miniature

Obiettivi:

- evitare il download ripetuto delle immagini originali;
- salvare miniature localmente;
- aggiornare la cache solo se il file cambia;
- configurare dimensioni e qualità delle miniature;
- prevedere pulizia cache per file rimossi.

Deliverable:

- directory cache;
- gestione thumbnail;
- endpoint thumbnail efficiente;
- job di pulizia cache.

---

## Fase 8 - Autenticazione e sicurezza

Obiettivi:

- proteggere l'accesso alla web app;
- proteggere le API amministrative;
- gestire credenziali Nextcloud tramite variabili ambiente;
- evitare log contenenti password;
- predisporre uso dietro reverse proxy HTTPS.

Deliverable:

- login base oppure integrazione con reverse proxy autenticato;
- protezione endpoint admin;
- `.env.example` senza credenziali reali;
- documentazione sicurezza.

---

## Fase 9 - Deploy Docker Compose

Obiettivi:

- predisporre avvio completo tramite Docker Compose;
- configurare volumi persistenti;
- configurare rete interna;
- configurare database;
- configurare backend e frontend;
- documentare backup e aggiornamento.

Deliverable:

- `docker-compose.yml`;
- Dockerfile backend;
- Dockerfile frontend, se necessario;
- script di inizializzazione;
- istruzioni di deploy.

---

## Fase 10 - Funzionalità evolute

Possibili sviluppi successivi:

- filtri avanzati per data e cartella;
- timeline fotografica;
- ricerca per area geografica;
- raggruppamento per viaggio o località;
- modifica manuale coordinate per foto senza GPS;
- ricerca delle foto prive di dati EXIF di geolocalizzazione, con filtri per data, cartella e intervallo temporale;
- assegnazione manuale della posizione alle foto senza GPS scegliendo un punto sulla mappa;
- anteprima della georeferenziazione proposta e richiesta di conferma esplicita prima di applicare modifiche;
- aggiornamento del file originale su Nextcloud, dopo conferma, scrivendo nei metadati EXIF le coordinate scelte;
- importazione di tracce GPX;
- associazione foto-traccia GPS per data e ora;
- supporto multiutente;
- permessi differenziati;
- esportazione GeoJSON;
- vista elenco oltre alla mappa;
- statistiche sulle foto indicizzate;
- supporto a video con metadati GPS;
- riconoscimento duplicati.

---

## 9. Configurazione prevista

Esempio di file `.env`:

```env
NEXTCLOUD_URL=https://nextcloud.example.org
NEXTCLOUD_USERNAME=utente
NEXTCLOUD_APP_PASSWORD=app-password
NEXTCLOUD_BASE_PATH=/Photos

DATABASE_URL=postgresql://photomap:photomap@db:5432/photomap

APP_BASE_URL=https://photomap.example.org
THUMBNAIL_CACHE_DIR=/data/thumbnails
SCAN_INTERVAL_HOURS=24

MAP_TILE_URL=https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png
MAP_DEFAULT_LAT=43.837
MAP_DEFAULT_LON=11.195
MAP_DEFAULT_ZOOM=10
```

---

## 10. Docker Compose ipotetico

Esempio indicativo:

```yaml
services:
  db:
    image: postgis/postgis:16-3.4
    environment:
      POSTGRES_DB: photomap
      POSTGRES_USER: photomap
      POSTGRES_PASSWORD: photomap
    volumes:
      - db_data:/var/lib/postgresql/data

  backend:
    build: ./backend
    env_file:
      - .env
    depends_on:
      - db
    volumes:
      - thumbnail_cache:/data/thumbnails

  frontend:
    build: ./frontend
    depends_on:
      - backend
    ports:
      - "8080:80"

volumes:
  db_data:
  thumbnail_cache:
```

---

## 11. Criteri di successo del primo MVP

Il primo MVP sarà considerato funzionante quando:

- l'applicazione si collega a Nextcloud;
- legge una cartella configurata;
- individua le immagini;
- estrae le coordinate GPS dalle foto;
- salva i dati nel database locale;
- espone una API con le foto geolocalizzate;
- visualizza le foto su una mappa;
- mostra una miniatura nel popup;
- consente di aprire la foto originale in Nextcloud;
- evita di rianalizzare file invariati.

---

## 12. Scelte tecniche iniziali consigliate

Per partire in modo pragmatico si propone:

- backend: Python + FastAPI;
- database: PostgreSQL + PostGIS;
- frontend: HTML/JavaScript o React leggero;
- mappa: Leaflet;
- accesso file: WebDAV Nextcloud;
- deploy: Docker Compose;
- autenticazione iniziale: protezione tramite reverse proxy o autenticazione base;
- scansione iniziale: comando manuale;
- scansione successiva: job schedulato.

---

## 13. Principi di sviluppo

Durante lo sviluppo si dovrà mantenere attenzione a questi principi:

- non modificare mai direttamente il database di Nextcloud;
- non installare plugin o app dentro Nextcloud;
- usare API documentate;
- minimizzare il numero di richieste verso Nextcloud;
- salvare localmente solo i dati necessari;
- separare chiaramente configurazione e codice;
- rendere il sistema facilmente eseguibile in Docker;
- produrre log chiari;
- consentire una scansione ripetibile e sicura;
- rendere possibile il ripristino tramite backup del database e della cache.

---

## 14. Struttura repository proposta

```text
nextcloud-photo-map/
├── README.md
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── nextcloud_client.py
│   │   ├── exif_reader.py
│   │   ├── scanner.py
│   │   ├── database.py
│   │   ├── models.py
│   │   └── api/
│   │       ├── photos.py
│   │       └── admin.py
│   └── requirements.txt
├── frontend/
│   ├── Dockerfile
│   ├── index.html
│   ├── app.js
│   └── style.css
├── migrations/
└── docs/
    ├── architecture.md
    └── api.md
```

---

## 15. Prossimi passi immediati

I prossimi passi consigliati sono:

1. creare il repository del progetto;
2. aggiungere questo README;
3. creare `.env.example`;
4. creare un primo `docker-compose.yml`;
5. implementare un piccolo script che elenca i file immagine da Nextcloud via WebDAV;
6. testare l'estrazione EXIF su alcune immagini reali;
7. salvare i primi dati in database;
8. realizzare una prima pagina Leaflet con marker caricati da JSON.
