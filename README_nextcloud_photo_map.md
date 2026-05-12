# Contesto e requisiti iniziali

Questo documento conserva il contesto di progetto da cui e' nata l'applicazione.

Per la documentazione operativa aggiornata vedere:

- [README principale](README.md)
- [Installazione e configurazione](docs/installation.md)
- [Manuale utente](docs/user-manual.md)
- [Manuale admin](docs/admin-manual.md)
- [Architettura software](docs/architecture.md)

## Scopo originario

Nextcloud Maps Companion nasce per visualizzare su mappa le fotografie archiviate in Nextcloud quando l'app Maps di Nextcloud non e' disponibile, aggiornata o adeguata.

L'idea guida e':

- Nextcloud resta archivio dei file;
- Companion indicizza i file via WebDAV;
- Companion legge EXIF e coordinate GPS;
- Companion conserva un database locale;
- Companion mostra le foto su mappa;
- Companion mantiene link al file originale in Nextcloud.

## Requisiti funzionali iniziali

- collegarsi a Nextcloud tramite WebDAV;
- configurare cartelle da indicizzare;
- filtrare estensioni immagine;
- leggere EXIF;
- salvare coordinate GPS;
- evitare di rileggere file non modificati;
- visualizzare marker su mappa;
- mostrare thumbnail e link Nextcloud;
- supportare piu utenti.

## Requisiti non funzionali iniziali

- applicazione separata da Nextcloud;
- nessuna modifica al database Nextcloud;
- basso impatto sull'istanza Nextcloud;
- distribuzione Docker Compose;
- credenziali non salvate in chiaro;
- HTTPS in produzione.

## Evoluzione implementata

La versione attuale implementa:

- login Nextcloud Login Flow v2;
- app password cifrate localmente;
- multiutenza;
- admin configurato da `.env`;
- scanner concorrente con coda;
- report utenti e scansioni;
- stato credenziali e ricollegamento account;
- frontend HTTPS self-signed o Let's Encrypt.
