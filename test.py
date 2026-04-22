import hashlib
import json
import os

import httpx
import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from main import app, engine

client = TestClient(app)


# ==========================================
# 1. TEST UNITARI (Engine & Intelligence)
# ==========================================

@pytest.mark.asyncio
async def test_engine_analyze_market_data_logic():
    """
    Verifica l'aggregazione corretta con la nuova struttura Phase 1.
    """
    mock_jobs = [
        {"organization_name": "Google", "title": "Dev", "location_code": "IT", "skills": ["s1"],
         "occupation_id": "occ_1"}
    ]
    # Prepariamo le mappe con la nuova struttura
    engine.sector_map = {"occ_1": "Tech"}
    engine.skill_map = {"s1": {"label": "Python", "is_green": False, "is_digital": True}}
    engine.stop_requested = False

    result = await engine.analyze_market_data(mock_jobs)

    assert result["total_jobs"] == 1
    # Verifica campi Intelligence Phase 1
    skill_entry = result["rankings"]["skills"][0]
    assert skill_entry["name"] == "Python"
    assert skill_entry["is_digital"] is True
    assert skill_entry["sector_spread"] == 1
    assert result["rankings"]["sectors"][0]["name"] == "Tech"


@pytest.mark.asyncio
async def test_fetch_skill_names_enriched_logic():
    """
    Verifica che la traduzione popoli il dizionario con i flag Twin Transition.
    """
    engine.skill_map = {}
    engine.token = "fake_token"  # FORZIAMO IL TOKEN per saltare il login

    test_uri = "s1"

    # Mock della risposta API del Tracker
    with patch.object(engine.client, 'post', new_callable=AsyncMock) as mock_post:
        # Configuriamo il mock per restituire un oggetto con status_code e json()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [{"id": test_uri, "label": "green software development"}]
        }
        mock_post.return_value = mock_response

        await engine.fetch_skill_names([test_uri])

        assert test_uri in engine.skill_map, "L'URI non è stato inserito nella mappa!"
        entry = engine.skill_map[test_uri]
        assert entry["label"] == "green software development"
        assert entry["is_green"] is True
        assert entry["is_digital"] is True




@pytest.mark.asyncio
async def test_fetch_occupation_labels():
    """Verifica popolamento sector_map forzando il reset degli stati."""
    # 1. RESET TOTALE DELLO STATO
    engine.sector_map = {}
    engine.token = "fake_token"
    engine.stop_requested = False  # <--- CRUCIALE: se è True, il metodo ritorna subito!
    occ_uri = "occ_1"

    # 2. MOCKING COMPLETO
    with patch.object(engine.client, 'post', new_callable=AsyncMock) as mock_post:
        # Costruiamo l'oggetto risposta che httpx aspetta
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [{"id": occ_uri, "label": "Energy Sector"}]
        }
        mock_post.return_value = mock_response

        # 3. ESECUZIONE
        await engine.fetch_occupation_labels([occ_uri])

        # 4. VERIFICA
        # Se fallisce qui, stamperà il contenuto della mappa per debuggare
        assert occ_uri in engine.sector_map, f"Mappa vuota! uris cercati erano {occ_uri}. Mappa: {engine.sector_map}"
        assert engine.sector_map[occ_uri] == "Energy Sector"


@pytest.mark.asyncio
async def test_fetch_occupation_labels():
    """Versione atomica: resetta tutto e forza il mock."""
    from main import engine

    # 1. Forza lo stato pulito
    engine.sector_map = {}
    engine.token = "fake_token"
    engine.stop_requested = False

    occ_uri = "occ_1"
    mock_data = {"items": [{"id": occ_uri, "label": "Energy Sector"}]}

    # 2. Mocking asincrono pulito
    with patch.object(engine.client, 'post') as mock_post:
        # Creiamo un oggetto che simula la risposta di httpx
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_data

        # Essendo una funzione async, il post deve ritornare una coroutine che risolve in mock_resp
        mock_post.return_value = mock_resp

        # 3. Esecuzione
        await engine.fetch_occupation_labels([occ_uri])

    # 4. Diagnostica se fallisce
    assert occ_uri in engine.sector_map, f"Fallimento! Mappa attuale: {engine.sector_map}"
    assert engine.sector_map[occ_uri] == "Energy Sector"


# ==========================================
# 2. TEST DI INTEGRAZIONE (Endpoints)
# ==========================================

@pytest.mark.integration
def test_endpoint_analyze_skills_consistency():
    """Verifica che le chiavi per la Dashboard siano sempre presenti."""
    form_data = {"keywords": ["test"], "min_date": "2024-01-01", "max_date": "2024-01-02"}

    # Mockiamo le chiamate interne per velocità
    with patch.object(engine, 'fetch_all_jobs', new_callable=AsyncMock) as m_fetch:
        m_fetch.return_value = []
        response = client.post("/projector/analyze-skills", data=form_data)

        assert response.status_code == 200
        data = response.json()
        assert "ranking" in data["insights"]
        assert "job_titles" in data["insights"]
        assert "employers" in data["insights"]
        assert "geo_breakdown" in data["dimension_summary"]


# ==========================================
# 3. RESILIENZA & UTILITY
# ==========================================

@pytest.mark.asyncio
async def test_engine_stop_signal():
    engine.request_stop()
    result = await engine.analyze_market_data([{"skills": ["s1"]}] * 5)
    assert len(result["rankings"]["skills"]) == 0
    engine.stop_requested = False


def test_cache_hashing():
    f1 = {"k": "a"}
    f2 = {"k": "b"}
    h1 = hashlib.md5(json.dumps(f1, sort_keys=True).encode()).hexdigest()
    h2 = hashlib.md5(json.dumps(f2, sort_keys=True).encode()).hexdigest()
    assert h1 != h2


# ==========================================
# 4. COVERAGE BOOSTER: TRENDS & LOGIC
# ==========================================

@pytest.mark.asyncio
async def test_calculate_smart_trends_logic():
    """Testa la logica matematica dei trend (Volume e Skill Growth)."""
    # Periodo A: 1 Job con 1 Skill
    mock_jobs_a = [{"occupation_id": "occ_1", "skills": ["s1"]}]
    # Periodo B: 2 Job diversi, ognuno con la Skill (Volume raddoppiato)
    mock_jobs_b = [
        {"occupation_id": "occ_1", "skills": ["s1"]},
        {"occupation_id": "occ_1", "skills": ["s1"]}
    ]

    engine.token = "fake"
    engine.sector_map = {"occ_1": "Tech"}
    engine.skill_map = {"s1": {"label": "Python", "is_green": False, "is_digital": True}}

    with patch.object(engine, 'fetch_all_jobs', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.side_effect = [mock_jobs_a, mock_jobs_b]

        result = await engine.calculate_smart_trends({}, "2024-01-01", "2024-01-04")

        # 1. Verifica Volume (da 1 a 2 job = +100%)
        assert result["market_health"]["volume_growth_percentage"] == 100.0
        assert result["market_health"]["status"] == "expanding"

        # 2. Verifica Skill Growth (da 1 occorrenza a 2 = +100%)
        python_trend = next(t for t in result["trends"] if t["name"] == "Python")
        assert python_trend["growth"] == 100.0
        assert python_trend["trend_type"] == "emerging"


@pytest.mark.asyncio
async def test_fetch_all_jobs_read_timeout_resilience():
    """Testa la gestione del ReadTimeout (Coverage del blocco except)."""
    engine.token = "fake"
    with patch.object(engine.client, 'post', side_effect=httpx.ReadTimeout("Timeout")):
        # Deve catturare l'errore, loggare e restituire i job accumulati finora (vuoti)
        result = await engine.fetch_all_jobs({"kw": "test"})
        assert result == []


@pytest.mark.asyncio
async def test_analyze_market_data_empty_jobs():
    """Testa il metodo _empty_res (Coverage dei rami edge)."""
    result = await engine.analyze_market_data([])
    assert result["total_jobs"] == 0
    assert result["rankings"]["skills"] == []


@pytest.mark.asyncio
async def test_analyze_market_data_unclassified_sector():
    """Verifica il fallback 'Settore non specificato' se manca occupation_id."""
    mock_jobs = [{"skills": ["s1"]}]  # Manca occupation_id
    engine.skill_map = {"s1": {"label": "Test", "is_green": False, "is_digital": False}}
    engine.sector_map = {}

    result = await engine.analyze_market_data(mock_jobs)
    assert result["rankings"]["sectors"][0]["name"] == "Settore non specificato"


# ==========================================
# 5. INTEGRATION: ENDPOINT EMERGING SKILLS
# ==========================================

@pytest.mark.integration
def test_endpoint_emerging_skills_structure():
    """Verifica la struttura JSON dell'endpoint trend."""
    with patch.object(engine, 'fetch_all_jobs', new_callable=AsyncMock) as m_fetch:
        m_fetch.return_value = []
        response = client.post("/projector/emerging-skills", data={
            "min_date": "2024-01-01", "max_date": "2024-01-31"
        })
        assert response.status_code == 200
        assert "market_health" in response.json()["insights"]


@pytest.mark.asyncio
async def test_fetch_skill_names_enriched_logic():
    """Verifica che il tagging riconosca parole tecniche come 'renewable'."""
    engine.skill_map = {}
    engine.token = "fake_token"

    with patch.object(engine.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [{"id": "s1", "label": "Renewable energy systems installation"}]
        }
        mock_post.return_value = mock_response

        await engine.fetch_skill_names(["s1"])

        entry = engine.skill_map["s1"]
        # Ora deve essere True perché 'renewable' e 'energy' sono nel set Green
        assert entry["is_green"] is True
        assert entry["label"] == "Renewable energy systems installation"


@pytest.mark.asyncio
async def test_calculate_smart_trends_intelligence_overlap():
    """Verifica che il settore primario sia presente nei risultati dei trend."""
    # Mock jobs con settori specifici
    mock_jobs_a = [{"occupation_id": "occ_1", "skills": ["s1"]}]
    mock_jobs_b = [{"occupation_id": "occ_1", "skills": ["s1"], "organization_name": "Test"}]

    engine.token = "fake"
    engine.sector_map = {"occ_1": "Automotive"}
    engine.skill_map = {"s1": {"label": "Battery Tech", "is_green": True, "is_digital": False}}

    with patch.object(engine, 'fetch_all_jobs', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.side_effect = [mock_jobs_a, mock_jobs_b]

        result = await engine.calculate_smart_trends({}, "2024-01-01", "2024-01-04")

        # Verifica che il trend contenga il settore automotive
        skill_trend = result["trends"][0]
        assert skill_trend["primary_sector"] == "Automotive"
        assert skill_trend["is_green"] is True


@pytest.mark.integration
def test_dashboard_phase1_contract():
    """
    TEST: Verifica che l'output per la Dashboard contenga
    i dati di Intelligence e la distribuzione settoriale.
    """
    form_data = {"keywords": ["data scientist"], "min_date": "2024-01-01", "max_date": "2024-01-02"}

    with patch.object(engine, 'fetch_all_jobs', new_callable=AsyncMock) as m_fetch:
        # Simulo un job con occupazione e skill
        m_fetch.return_value = [{"occupation_id": "occ_1", "skills": ["s1"]}]
        engine.sector_map = {"occ_1": "Information Technology"}
        engine.skill_map = {"s1": {"label": "AI", "is_green": False, "is_digital": True}}

        response = client.post("/projector/analyze-skills", data=form_data)
        res_data = response.json()

        # Verifica campi per Tabella Skill (Tab 1)
        skill_sample = res_data["insights"]["ranking"][0]
        assert "is_green" in skill_sample
        assert "is_digital" in skill_sample
        assert "sector_spread" in skill_sample

        # Verifica dati per Grafico Settori (Nuova Tab 4)
        assert "sectors" in res_data["insights"]
        assert res_data["insights"]["sectors"][0]["name"] == "Information Technology"


@pytest.mark.integration
def test_endpoint_analyze_skills_single_fetch_consistency():
    """Verifica che l'endpoint restituisca sia le skill che i trend in un'unica chiamata."""
    form_data = {
        "keywords": ["developer"],
        "min_date": "2024-01-01",
        "max_date": "2024-01-10"
    }

    # Mocking per evitare fetch reali
    with patch.object(engine, 'fetch_all_jobs', new_callable=AsyncMock) as m_fetch:
        m_fetch.return_value = [
            {"upload_date": "2024-01-02", "skills": ["s1"], "occupation_id": "occ_1"},
            {"upload_date": "2024-01-08", "skills": ["s1", "s1"], "occupation_id": "occ_1"}
        ]

        response = client.post("/projector/analyze-skills", data=form_data)
        assert response.status_code == 200

        data = response.json()
        # Verifica che i trend siano "dentro" la risposta di analyze-skills
        assert "trends" in data["insights"]
        assert data["insights"]["trends"]["market_health"]["volume_growth_percentage"] == 0.0


import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_fetch_occupation_labels_specific_esco():
    """
    Verifica che l'ID ESCO del Sales Account Manager venga
    correttamente tradotto e salvato nella sector_map.
    """
    target_uri = "http://data.europa.eu/esco/occupation/2eac08c2-a81a-46fc-8d75-eb0e0f3e0f6d"
    expected_label = "sales account manager"

    engine.sector_map = {}
    engine.token = "fake_token"
    engine.stop_requested = False

    mock_response_data = {"items": [{"id": target_uri, "label": expected_label}]}

    with patch.object(engine.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.json.return_value = mock_response_data
        mock_post.return_value = mock_res

        await engine.fetch_occupation_labels([target_uri])

        assert mock_post.called
        args, kwargs = mock_post.call_args
        # FIX: Cerchiamo 'json' invece di 'data' perché siamo passati a JSON in produzione
        assert target_uri in kwargs['data']['ids']
        assert engine.sector_map[target_uri] == expected_label


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("CI") == "true",
    reason="Skipping test in CI environment"
)
async def test_fetch_occupation_labels_integration_real():
    """
    INTEGRATION TEST (No Mock):
    Verifica il recupero reale dal server Tracker per l'ID ESCO specifico.
    """
    target_uri = "http://data.europa.eu/esco/occupation/2eac08c2-a81a-46fc-8d75-eb0e0f3e0f6d"
    expected_label = "sales account manager"

    # RESET TOTALE: Questo impedisce ai mock precedenti di rompere il test reale
    engine.sector_map = {}
    engine.token = None  # <--- CRUCIALE: forza l'engine a fare un login vero
    engine.stop_requested = False

    # Esecuzione
    await engine.fetch_occupation_labels([target_uri])

    # Verifica
    assert target_uri in engine.sector_map, "La mappa è vuota! Il login o la richiesta sono falliti."

    actual_label = engine.sector_map[target_uri].lower()
    assert actual_label == expected_label, f"Ricevuto '{actual_label}' invece di '{expected_label}'"


@pytest.mark.asyncio
async def test_regional_decomposition_logic():
    """
    Verifica che i job siano raggruppati correttamente sia nella
    strategia RAW che in quella NUTS gerarchica.
    """
    # Mock jobs con codici che simulano NUTS (ITC4C è NUTS3, ITC4 è NUTS2, ITC è NUTS1)
    mock_jobs = [
        {"location_code": "ITC4C", "skills": ["s1", "s2"]}, # Milano (NUTS3)
        {"location_code": "ITC4C", "skills": ["s1"]},      # Milano (NUTS3)
        {"location_code": "SOUTH", "skills": ["s2"]}       # Codice non NUTS (Raw)
    ]

    # Prepariamo la skill_map minima
    engine.skill_map = {
        "s1": {"label": "Python"},
        "s2": {"label": "SQL"}
    }

    # Esecuzione della nuova funzione duale
    results = engine.get_regional_projections(mock_jobs)

    # 1. VERIFICA STRATEGIA RAW (NORTH/SOUTH o codici completi)
    raw_results = results["raw"]

    # Check ITC4C (Raw)
    milano = next(r for r in raw_results if r["code"] == "ITC4C")
    assert milano["total_jobs"] == 2
    # Verifichiamo Python (s1) in ITC4C
    python_entry = next(s for s in milano["top_skills"] if s["skill"] == "Python")
    assert python_entry["count"] == 2

    # Check SOUTH (Raw)
    south = next(r for r in raw_results if r["code"] == "SOUTH")
    assert south["total_jobs"] == 1
    assert south["top_skills"][0]["skill"] == "SQL"

    # 2. VERIFICA STRATEGIA NUTS (Gerarchica)
    # ITC4C deve aver popolato anche NUTS2 (ITC4) e NUTS1 (ITC)

    # Check NUTS2 (Regione: ITC4 - Lombardia)
    nuts2_results = results["nuts2"]
    lombardia = next(r for r in nuts2_results if r["code"] == "ITC4")
    assert lombardia["total_jobs"] == 2

    # Check NUTS1 (Area: ITC - Nord-Ovest)
    nuts1_results = results["nuts1"]
    nord_ovest = next(r for r in nuts1_results if r["code"] == "ITC")
    assert nord_ovest["total_jobs"] == 2

    # 3. VERIFICA SPECIALIZZAZIONE (Location Quotient)
    # In questo mock, SQL compare 2 volte su 3 job totali (66%).
    # A SOUTH compare 1 volta su 1 job (100%).
    # LQ = 100% / 66% = ~1.5 (Specializzazione alta)
    sql_south = next(s for s in south["top_skills"] if s["skill"] == "SQL")
    assert sql_south["specialization"] >= 1.0
