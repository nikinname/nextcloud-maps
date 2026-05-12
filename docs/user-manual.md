# Manuale utente

Questo documento descrive l'uso quotidiano di Nextcloud Maps Companion.

Documenti collegati:

- [README principale](../README.md)
- [Installazione e configurazione](installation.md)
- [Manuale admin](admin-manual.md)
- [Architettura software](architecture.md)

## Accesso

Aprire l'URL dell'applicazione, per esempio:

```text
https://localhost:8443
```

Premere `Accedi` e completare l'autorizzazione su Nextcloud.

Companion non salva la password principale Nextcloud. Nextcloud restituisce una app password dedicata, che Companion cifra e usa per:

- scansioni WebDAV;
- generazione thumbnail;
- operazioni schedulate o in background.

## Ricollegare Nextcloud

Se l'app password non e' piu valida, e' stata revocata, oppure `APP_SECRET_KEY` non permette piu di decifrarla, la UI mostra un avviso:

```text
Account Nextcloud da ricollegare
```

Premere `Ricollega Nextcloud` e autorizzare di nuovo l'app su Nextcloud.

Alla nuova autorizzazione Companion sostituisce la chiave precedente con quella nuova.
Quando possibile, Companion revoca automaticamente la vecchia app password salvata prima di usare quella nuova.
Eventuali chiavi duplicate create da versioni precedenti devono essere eliminate una volta dalla pagina sicurezza di Nextcloud.

## Mappa

Dopo il login la schermata principale mostra:

- mappa Leaflet;
- marker delle foto con coordinate GPS;
- clustering dei marker;
- popup con thumbnail, data e link a Nextcloud.

Solo le foto con coordinate GPS vengono mostrate sulla mappa. Le foto senza GPS possono comunque essere indicizzate e conteggiate.

## Filtri

Nel pannello laterale sono disponibili:

- data iniziale;
- data finale;
- cartella;
- pulsante `Filtra`.

La cartella deve essere indicata come path Nextcloud, per esempio:

```text
/Photos
/Vacanze/2024
```

## Scansione personale

Ogni utente autenticato puo' lanciare una scansione delle proprie foto con:

```text
Avvia scansione
```

La scansione viene accodata in background. La UI risponde subito; il lavoro continua nel backend.

Le scansioni usano la app password salvata per quell'utente.

## Link a Nextcloud

Nel popup di una foto e' disponibile il link per aprire il file o la cartella in Nextcloud.

## Thumbnail

Le thumbnail vengono generate al primo accesso e salvate localmente. Se il file cambia, la thumbnail viene rigenerata.
