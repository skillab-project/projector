# SKILLAB Projector

SKILLAB Projector è un servizio FastAPI che usa i dati dello SKILLAB Tracker per produrre intelligence sul mercato del lavoro.

Fornisce:
- ranking delle skill più richieste,
- distribuzione settoriale,
- aziende e job title più frequenti,
- trend emergenti o in calo,
- proiezioni geografiche e NUTS-like,
- viste settoriali opzionali ISCO e NACE.

## Avvio Rapido

Avvia il backend dalla root del repository:

```bash
uvicorn app.main:app --reload
```

Avvia la dashboard Streamlit in un secondo terminale:

```bash
streamlit run app/example_dashboard/demo_dashboard.py
```

La documentazione interattiva è disponibile su:

```text
http://127.0.0.1:8000/docs
```

## Configurazione

Crea un file `.env` nella root del progetto:

```env
TRACKER_API=https://your-tracker-url
TRACKER_USERNAME=your_username
TRACKER_PASSWORD=your_password
```

Installa le dipendenze:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Struttura Attuale

```text
app/main.py
app/api/routes/projector.py
app/services/projector_service.py
app/services/analytics/
app/client/tracker_client.py
app/schemas/responses.py
app/example_dashboard/demo_dashboard.py
```

I file root storici (`main.py`, `schemas.py`, `demo_dashboard.py`, `main_sectoral.py`) sono ancora presenti, ma il percorso mantenuto è quello nel package `app/`.

## Endpoint

- `POST /projector/analyze-skills`
- `POST /projector/emerging-skills`
- `POST /projector/stop`

Il contratto completo è in [docs/api-reference.md](docs/api-reference.md).

## Modalità Settoriale

Il servizio supporta:

- ISCO: vista basata su occupazioni e gruppi professionali.
- NACE: vista basata su attività economiche tramite crosswalk ESCO-NACE.
- Both: restituisce entrambe le viste per confronto in dashboard.

In modalità NACE un’occupazione può essere collegata a più codici NACE. Questo è intenzionale: la vista serve a scoprire relazioni skill-settore, non a fare contabilità uno-a-uno dei job.
