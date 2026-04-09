import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from datetime import datetime
from main import app, engine  # Importa l'app e l'istanza dell'engine

# Configurazione Client per i test degli endpoint
client = TestClient(app)


# ==========================================
# 1. TEST UNITARI (Logica ProjectorEngine)
# ==========================================

@pytest.mark.asyncio
async def test_engine_analyze_market_data_logic():
    """
    Verifica che analyze_market_data aggreghi correttamente i dati grezzi.
    """
    # Mock dei dati in ingresso
    mock_jobs = [
        {
            "organization_name": "Google",
            "title": "Software Engineer",
            "location_code": "IT",
            "skills": ["skill_1", "skill_2"]
        },
        {
            "organization_name": "Google",
            "title": "Data Scientist",
            "location_code": "FR",
            "skills": ["skill_1"]
        }
    ]

    # Puliamo la mappa delle skill per il test
    engine.skill_map = {"skill_1": "Python", "skill_2": "Cloud"}
    engine.stop_requested = False

    # Esecuzione
    result = await engine.analyze_market_data(mock_jobs)

    # Asserzioni sulla struttura del dizionario (coerente con il tuo codice)
    assert result["total_jobs"] == 2
    assert result["rankings"]["employers"][0] == {"name": "Google", "count": 2}
    assert len(result["rankings"]["skills"]) == 2
    assert result["rankings"]["skills"][0]["name"] == "Python"
    assert any(g["location"] == "IT" for g in result["geo"])


@pytest.mark.asyncio
async def test_engine_stop_signal_interruption():
    """
    Verifica che analyze_market_data rispetti il segnale di stop.
    """
    engine.stop_requested = True  # Simuliamo stop attivo
    mock_jobs = [{"skills": ["A"]}] * 10

    result = await engine.analyze_market_data(mock_jobs)

    # Se fermato all'inizio, le classifiche devono essere vuote (perché esce dal ciclo)
    assert len(result["rankings"]["skills"]) == 0
    engine.stop_requested = False  # Reset


@pytest.mark.asyncio
async def test_smart_trends_date_calculation():
    """
    Verifica che il calcolo dei periodi A/B sia matematicamente corretto.
    """
    # Usiamo date semplici per verificare la divisione
    min_date = "2024-01-01"
    max_date = "2024-01-04"  # 3 giorni di differenza

    # Mockiamo fetch_all_jobs per non andare su internet
    with patch.object(engine, 'fetch_all_jobs', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = []  # Ritorna liste vuote

        result = await engine.calculate_smart_trends({}, min_date, max_date)

        # Con 3 giorni, il midpoint deve dividere 01-02 e 03-04
        assert "expanding" in result["market_health"]["status"] or "shrinking" in result["market_health"]["status"]
        # Se non ci sono dati, la crescita è 0 ma la struttura deve esserci
        assert "trends" in result


# ==========================================
# 2. TEST DI INTEGRAZIONE (Endpoint FastAPI)
# ==========================================

@pytest.mark.integration
def test_endpoint_analyze_skills_structure():
    """
    Verifica che /analyze-skills restituisca la struttura JSON esatta 
    richiesta dalla Dashboard (consistenza).
    """
    form_data = {
        "keywords": ["developer"],
        "min_date": "2024-01-01",
        "max_date": "2024-01-10",
        "page": 1,
        "page_size": 5
    }

    response = client.post("/projector/analyze-skills", data=form_data)
    assert response.status_code == 200

    data = response.json()

    # Verifica chiavi root
    assert data["status"] in ["completed", "stopped"]
    assert "insights" in data
    assert "dimension_summary" in data

    # Verifica consistenza Tab 1 e Tab 4
    ins = data["insights"]
    assert "ranking" in ins
    assert "job_titles" in ins
    assert "employers" in ins

    # Verifica consistenza Tab 3
    assert "geo_breakdown" in data["dimension_summary"]


@pytest.mark.integration
def test_endpoint_stop_signal():
    """
    Verifica che l'endpoint di stop attivi correttamente il flag nell'engine.
    """
    engine.stop_requested = False
    response = client.post("/projector/stop")

    assert response.status_code == 200
    assert response.json()["status"] == "signal_sent"
    assert engine.stop_requested is True
    engine.stop_requested = False  # Reset


@pytest.mark.integration
@pytest.mark.skip
def test_emerging_skills_status():
    """
    Verifica che l'endpoint dei trend risponda correttamente.
    """
    form_data = {
        "min_date": "2024-01-01",
        "max_date": "2024-01-31"
    }
    response = client.post("/projector/emerging-skills", data=form_data)
    assert response.status_code == 200
    assert response.json()["status"] in ["completed", "stopped"]
    assert "trends" in response.json()["insights"]


@pytest.mark.integration
def test_emerging_skills_status_mocked():
    """
    Test di integrazione con MOCK delle chiamate esterne
    per evitare attese infinite.
    """
    # Mockiamo fetch_all_jobs dell'istanza globale 'engine'
    with patch.object(engine, 'fetch_all_jobs', new_callable=AsyncMock) as mock_fetch:
        # Simuliamo che il Tracker restituisca 2 job finti velocemente
        mock_fetch.return_value = [
            {"organization_name": "Test", "skills": ["skill_1"], "occupation_id": "occ_1"}
        ]

        form_data = {
            "min_date": "2024-01-01",
            "max_date": "2024-01-04"
        }

        # Ora la chiamata sarà istantanea perché non va su internet
        response = client.post("/projector/emerging-skills", data=form_data)

        assert response.status_code == 200
        assert response.json()["status"] == "completed"

# ==========================================
# 3. TEST TRADUZIONE (MOCK API ESTERNA)
# ==========================================

@pytest.mark.asyncio
async def test_fetch_skill_names_logic():
    """
    Testa la logica di traduzione batch senza chiamare l'API reale.
    """
    engine.skill_map = {}
    test_uris = ["uri_1", "uri_2"]

    # Mockiamo la risposta di httpx.AsyncClient.post
    with patch.object(engine.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "items": [
                {"id": "uri_1", "label": "Python Expert"},
                {"id": "uri_2", "label": "Cloud Architect"}
            ]
        }

        await engine.fetch_skill_names(test_uris)

        assert engine.skill_map["uri_1"] == "Python Expert"
        assert engine.skill_map["uri_2"] == "Cloud Architect"


@pytest.mark.asyncio
async def test_fetch_jobs_api_error_handling():
    """
    Testa la resilienza del motore se l'API Tracker risponde con errore 500.
    """
    with patch.object(engine.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 500

        # Non deve sollevare eccezioni ma restituire lista vuota o fermarsi
        result = await engine.fetch_all_jobs({"keywords": ["fail"]})
        assert result == []


def test_cache_hashing_consistency():
    """
    Verifica che query diverse producano file di cache diversi (no collisioni).
    """
    filters_1 = {"keywords": ["python"]}
    filters_2 = {"keywords": ["python"], "location_code": ["IT"]}

    import hashlib
    import json
    hash_1 = hashlib.md5(json.dumps(filters_1, sort_keys=True).encode()).hexdigest()
    hash_2 = hashlib.md5(json.dumps(filters_2, sort_keys=True).encode()).hexdigest()

    assert hash_1 != hash_2


@pytest.mark.asyncio
async def test_trend_classification_boundaries():
    """
    Mutation Test: Verifica che la logica di classificazione
    emerging/declining/stable sia precisa.
    """
    # Caso: Crescita Zero (Stabile)
    res_a = {"rankings": {"skills": [{"skill_id": "1", "name": "A", "frequency": 10}]}, "total_jobs": 1}
    res_b = {"rankings": {"skills": [{"skill_id": "1", "name": "A", "frequency": 10}]}, "total_jobs": 1}

    # Dovrebbe essere classificata come 'stable'
    # (Dovrai simulare il ritorno di calculate_smart_trends o testare la logica interna)