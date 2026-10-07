# Guida alle query della demo Projector

Questa guida raccoglie query ripetibili per ogni sezione della dashboard. Lo scopo è mostrare una storia leggibile del mercato del lavoro sintetico, evitando combinazioni casuali o filtri che producono risultati poco significativi.

## 1. Perimetro del dataset

Il dataset sintetico contiene 8.000 annunci nel periodo compreso tra il 1 gennaio 2020 e il 7 ottobre 2026.

| Anno | Annunci previsti |
|---|---:|
| 2020 | 640 |
| 2021 | 720 |
| 2022 | 800 |
| 2023 | 960 |
| 2024 | 1.280 |
| 2025 | 1.600 |
| 2026 | 2.000 |

Le sei regioni disponibili sono:

| Paese | NUTS1 | NUTS2 | NUTS3 presenti | Regione | Caratterizzazione prevalente |
|---|---|---|---|---|---|
| `IT` | `ITF` | `ITF4` | `ITF47`, `ITF45`, `ITF43` | Puglia | turismo, sanità, pubblica amministrazione |
| `IT` | `ITC` | `ITC4` | `ITC4C`, `ITC46`, `ITC47` | Lombardia | software, finanza, manifattura |
| `DE` | `DE3` | `DE30` | `DE300` | Berlino | software, intelligenza artificiale, cloud |
| `DE` | `DE2` | `DE21` | `DE212`, `DE211`, `DE213` | Oberbayern | automotive, manifattura, automazione |
| `FR` | `FR1` | `FR10` | `FR101`, `FR105` | Île-de-France | finanza, dati, consulenza |
| `FR` | `FRK` | `FRK2` | `FRK26`, `FRK24`, `FRK25` | Rhône-Alpes | manifattura, sostenibilità, energia rinnovabile |

Tutti i settori sono comunque presenti in tutte le regioni. La caratterizzazione dipende soltanto dalla loro frequenza relativa.

## 2. Regole generali per costruire una query

- Le keyword non distinguono tra maiuscole e minuscole.
- La ricerca considera titolo, descrizione, azienda e località.
- Tutte le skill assegnate a un annuncio sono riportate anche nella descrizione e sono quindi ricercabili.
- Usare preferibilmente una keyword significativa per volta.
- Evitare abbreviazioni molto brevi come `AI` o `IT`: essendo una ricerca per sottostringa, possono produrre corrispondenze ambigue.
- Usare `artificial intelligence` invece di `AI`.
- Usare i codici NUTS2 della tabella precedente per le analisi regionali. Ogni job conserva l'intera gerarchia geografica: `location_code`/`country_code` per il paese, `nuts1`, `nuts2` e `nuts3`.
- Lasciare vuota la località quando lo scopo è confrontare tutte le regioni.
- Per confrontare due aree usare sempre lo stesso livello NUTS e lo stesso intervallo temporale.
- Le date sono inclusive.

## 3. Keyword consigliate

### Digitale e dati

- `software development`
- `Python`
- `SQL`
- `data analysis`
- `artificial intelligence`
- `machine learning`
- `PyTorch`
- `cloud computing`
- `Docker`
- `Kubernetes`
- `cybersecurity`

### Industria

- `manufacturing processes`
- `automotive engineering`
- `industrial automation`
- `quality control`
- `computer-aided design`

### Transizione verde

- `sustainability`
- `renewable energy`
- `carbon accounting`
- `circular economy`

### Servizi e settore pubblico

- `financial analysis`
- `management consulting`
- `healthcare management`
- `patient care`
- `public administration`
- `policy analysis`
- `tourism management`
- `hospitality operations`

### Skill trasversali

- `project management`
- `stakeholder management`
- `communication`
- `teamwork`
- `problem solving`
- `Microsoft Excel`

## 4. Job Demand Overview

Questa sezione risponde alla domanda: **quali skill, titoli, settori e aziende caratterizzano il sottoinsieme selezionato?**

### Query A — domanda digitale complessiva

| Campo | Valore |
|---|---|
| Keyword | `software development` |
| Location | lasciare vuoto |
| Periodo | `2024-01-01` – `2026-10-07` |

Risultato atteso: prevalenza di Berlino e Lombardia, con Python, Git, Docker e metodi Agile tra le skill principali.

### Query B — economia turistica pugliese

| Campo | Valore |
|---|---|
| Keyword | `tourism management` |
| Location | `ITF4` |
| Periodo | `2024-01-01` – `2026-10-07` |

Risultato atteso: Tourism Operations Manager, hospitality, customer service, English e project management.

### Query C — industria bavarese

| Campo | Valore |
|---|---|
| Keyword | `industrial automation` |
| Location | `DE21` |
| Periodo | `2024-01-01` – `2026-10-07` |

Risultato atteso: Automotive Engineer e Manufacturing Engineer, con quality control, CAD e manufacturing processes.

### Query D — sostenibilità trasversale

| Campo | Valore |
|---|---|
| Keyword | `sustainability` |
| Location | lasciare vuoto |
| Periodo | `2022-01-01` – `2026-10-07` |

Risultato atteso: maggiore concentrazione in Rhône-Alpes, senza assenza totale nelle altre regioni.

## 5. Temporal Analysis

Questa sezione risponde alla domanda: **come cambia nel tempo il volume degli annunci e delle skill?**

Per intervalli superiori a due anni usare granularità annuale o trimestrale. La granularità mensile è più utile su un singolo anno.

### Query A — crescita dell'intelligenza artificiale

| Campo | Valore |
|---|---|
| Keyword | `artificial intelligence` |
| Location | lasciare vuoto |
| Periodo | `2020-01-01` – `2026-10-07` |
| Granularità | Annuale |
| Periodi di forecast | `1` |
| Numero skill | `10` |

Risultato atteso: crescita progressiva della quota di intelligenza artificiale, machine learning, Python, PyTorch e cloud computing.

### Query B — cloud a Berlino

| Campo | Valore |
|---|---|
| Keyword | `cloud computing` |
| Location | `DE30` |
| Periodo | `2022-01-01` – `2026-10-07` |
| Granularità | Trimestrale |
| Periodi di forecast | `2` |
| Numero skill | `10` |

Risultato atteso: crescita di cloud computing, Docker, Kubernetes, cybersecurity e Python.

### Query C — trasformazione verde

| Campo | Valore |
|---|---|
| Keyword | `renewable energy` |
| Location | `FRK2` |
| Periodo | `2020-01-01` – `2026-10-07` |
| Granularità | Annuale |
| Periodi di forecast | `1` |

Risultato atteso: crescita di sostenibilità, energia rinnovabile, carbon accounting e circular economy.

### Query D — automotive maturo

| Campo | Valore |
|---|---|
| Keyword | `automotive engineering` |
| Location | `DE21` |
| Periodo | `2020-01-01` – `2026-10-07` |
| Granularità | Annuale |

Risultato atteso: crescita assoluta legata all'aumento del mercato, ma quota relativa meno dinamica rispetto ad AI, cloud e sostenibilità.

## 6. Regional Temporal Analysis

Questa sezione risponde alla domanda: **in quali regioni e in quali periodi cresce la domanda associata a una keyword?**

Per confrontare le sei regioni, lasciare sempre vuoto il campo Location.

### Query A — diffusione del software

| Campo | Valore |
|---|---|
| Keyword | `software development` |
| Location | lasciare vuoto |
| Periodo | `2023-01-01` – `2026-10-07` |
| Granularità | Trimestrale |
| Numero regioni | `6` |
| Numero skill | `10` |

Risultato atteso: Berlino e Lombardia in testa, con presenza minore ma non nulla nelle altre regioni.

### Query B — geografia della sostenibilità

| Campo | Valore |
|---|---|
| Keyword | `sustainability` |
| Location | lasciare vuoto |
| Periodo | `2020-01-01` – `2026-10-07` |
| Granularità | Annuale |
| Numero regioni | `6` |

Risultato atteso: Rhône-Alpes e Oberbayern più specializzate, con crescita diffusa nel tempo.

### Query C — ripresa del turismo

| Campo | Valore |
|---|---|
| Keyword | `tourism management` |
| Location | lasciare vuoto |
| Periodo | `2020-01-01` – `2026-10-07` |
| Granularità | Annuale |
| Numero regioni | `6` |

Risultato atteso: Puglia in testa e crescita successiva ai primi anni del periodo.

## 7. Confronto tra regioni

Questa sezione risponde alla domanda: **come differiscono due regioni nello stesso periodo per annunci, skill, settori, titoli e aziende?**

Usare due codici NUTS2 di quattro caratteri. Non confrontare, per esempio, `ITF` con `DE30`, perché appartengono a livelli diversi.

### Query A — software: Puglia contro Berlino

| Campo | Valore |
|---|---|
| Regione A | `ITF4` |
| Regione B | `DE30` |
| Periodo | `2024-01-01` – `2026-10-07` |
| Keyword | `software development` |

Risultato atteso: maggiore volume e specializzazione digitale a Berlino; presenza software comunque visibile in Puglia.

### Query B — finanza: Lombardia contro Île-de-France

| Campo | Valore |
|---|---|
| Regione A | `ITC4` |
| Regione B | `FR10` |
| Periodo | `2024-01-01` – `2026-10-07` |
| Keyword | `financial analysis` |

Risultato atteso: entrambe le regioni rilevanti, con differenze nelle skill associate e nelle aziende.

### Query C — manifattura: Oberbayern contro Rhône-Alpes

| Campo | Valore |
|---|---|
| Regione A | `DE21` |
| Regione B | `FRK2` |
| Periodo | `2024-01-01` – `2026-10-07` |
| Keyword | `manufacturing processes` |

Risultato atteso: maggiore componente automotive in Oberbayern e maggiore componente green in Rhône-Alpes.

### Query D — confronto generale senza keyword

| Campo | Valore |
|---|---|
| Regione A | `ITF4` |
| Regione B | `ITC4` |
| Periodo | `2024-01-01` – `2026-10-07` |
| Keyword | lasciare vuoto |

Risultato atteso: confronto dell'intero mix economico regionale, non di un singolo mercato professionale.

## 8. Sector Overview

Questa sezione usa gli snapshot annuali PostgreSQL e risponde alla domanda: **quali settori dominano in un anno e come cambiano rispetto all'anno precedente?**

Prima di usare questa vista, attendere che il servizio `projector-snapshot-refresh` abbia popolato gli snapshot.

Per la demo usare preferibilmente `GLOBAL`. Le analisi territoriali dettagliate sono gestite meglio dalla sezione Regional Sector Distribution.

### Query A — fotografia 2024

| Campo | Valore |
|---|---|
| Vista settore | Snapshot |
| Anno | `2024` |
| Regione | `GLOBAL` |

Usare la tabella completa per identificare i settori effettivamente presenti e le rispettive skill principali.

### Query B — evoluzione 2020–2024

| Campo | Valore |
|---|---|
| Vista settore | Sector Evolution |
| Da | `2020` |
| A | `2024` |
| Regione | `GLOBAL` |

Risultato atteso: crescita relativa dei settori digitali e della consulenza ingegneristica; dinamica più moderata per automotive e pubblica amministrazione.

I dieci settori contenuti nei job sintetici sono:

- Computer programming activities
- Computer consultancy activities
- Other monetary intermediation
- Business and other management consultancy activities
- Engineering activities and related technical consultancy
- Manufacture of motor vehicles
- Manufacture of other general-purpose machinery
- Hospital activities
- General public administration activities
- Hotels and similar accommodation

## 9. Sector Skills Comparison

Questa sezione risponde alla domanda: **quali skill distinguono i settori e con quale intensità?**

Per il dataset sintetico, cancellare le selezioni predefinite in **Settori da confrontare**. Con il campo vuoto, il backend seleziona automaticamente i cinque settori più rappresentati realmente presenti nello snapshot.

### Query A — matrice delle quote

| Campo | Valore |
|---|---|
| Anno | `2024` |
| Regione | `GLOBAL` |
| Metrica | Share in sector |
| Settori | lasciare vuoto |
| Skill | lasciare vuoto |

Risultato atteso: heatmap delle 15 skill principali nei cinque settori più rappresentati.

### Query B — skill digitali

| Campo | Valore |
|---|---|
| Anno | `2024` |
| Regione | `GLOBAL` |
| Metrica | Count oppure Share in sector |
| Settori | lasciare vuoto |
| Skill | `Python`, `SQL`, `cloud computing` |

### Query C — crescita delle skill

| Campo | Valore |
|---|---|
| Da | `2023` |
| A | `2024` |
| Regione | `GLOBAL` |
| Metrica | Growth between years |
| Settori | lasciare vuoto |
| Skill | `artificial intelligence`, `cloud computing`, `sustainability` |

## 10. Regional Sector Distribution

Questa sezione risponde alla domanda: **quali settori sono più forti in ogni regione e come cambia il loro peso?**

Per ottenere le sei regioni sintetiche usare:

- Country filter: `ALL REGIONS`
- Region level: `nuts2`
- Sectors to include: lasciare vuoto per non escludere settori
- Sectors per area: `10`

### Query A — distribuzione regionale 2024

| Campo | Valore |
|---|---|
| Modalità | Snapshot |
| Anno | `2024` |
| Country filter | `ALL REGIONS` |
| Livello | `nuts2` |
| Metrica | Share in region |
| Settori | lasciare vuoto |
| Top K | `10` |

Risultato atteso: tutte le regioni contengono tutti i settori, ma con ordinamenti differenti.

### Query B — evoluzione regionale

| Campo | Valore |
|---|---|
| Modalità | Evolution |
| Da | `2020` |
| A | `2024` |
| Country filter | `ALL REGIONS` |
| Livello | `nuts2` |
| Metrica | Growth between years |
| Settori | lasciare vuoto |

### Query C — serie storica regionale

| Campo | Valore |
|---|---|
| Modalità | Time series |
| Inizio | `2020` |
| Fine | `2024` |
| Country filter | `ALL REGIONS` |
| Livello | `nuts2` |
| Metrica | Share in region |
| Top K | `10` |

## 11. Skill Explorer

Questa sezione risponde alla domanda: **in quali settori e regioni compare una skill e come evolve nel tempo?**

La ricerca per label richiede il nome completo della skill. È la modalità consigliata.

### Query A — Python negli snapshot

| Campo | Valore |
|---|---|
| Cerca per | Skill label |
| Valore | `Python` |
| Fonte | Snapshot DB |
| Finestra | Intervallo anni |
| Da | `2020` |
| A | `2024` |
| Location | lasciare vuoto |

### Query B — sostenibilità live

| Campo | Valore |
|---|---|
| Cerca per | Skill label |
| Valore | `sustainability` |
| Fonte | Tracker live |
| Periodo | `2020-01-01` – `2026-10-07` |
| Location | lasciare vuoto |
| Granularità | Annuale |

Risultato atteso: crescita temporale e maggiore concentrazione in `FRK2`.

### Query C — automotive in Oberbayern

| Campo | Valore |
|---|---|
| Cerca per | Skill label |
| Valore | `automotive engineering` |
| Fonte | Tracker live |
| Periodo | `2020-01-01` – `2026-10-07` |
| Location | `DE21` |
| Granularità | Annuale |

### Query D — ricerca per ID

| Campo | Valore |
|---|---|
| Cerca per | Skill ID |
| Valore | `http://data.europa.eu/esco/skill/demo-python` |
| Fonte | Tracker live oppure Snapshot DB |

## 12. Sequenza consigliata per una demo completa

Per raccontare il dataset in modo coerente, eseguire le viste in questo ordine:

1. **Job Demand Overview** — `software development`, tutte le regioni, 2024–2026.
2. **Temporal Analysis** — `artificial intelligence`, tutte le regioni, 2020–2026, annuale.
3. **Regional Temporal Analysis** — `sustainability`, tutte le regioni, 2020–2026, annuale.
4. **Confronto tra regioni** — `DE21` contro `FRK2`, keyword `manufacturing processes`.
5. **Sector Overview** — snapshot globale 2024 con riferimento 2023.
6. **Sector Skills Comparison** — globale 2024, settori vuoti, skill vuote, metrica share.
7. **Regional Sector Distribution** — 2024, tutte le regioni, NUTS2, metrica share.
8. **Skill Explorer** — `Python` oppure `sustainability`, intervallo 2020–2024.

Questa sequenza passa dalla domanda complessiva alle differenze temporali, geografiche, settoriali e infine alla traiettoria di una singola skill.
