import hashlib
import os
import json
from collections import defaultdict, Counter

import httpx
import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.container import ProjectorEngine
from app.core.container import engine, tracker, loader, occupations, regional, market, trends, sectoral, service
from app.main import  app
from app.services.esco_loader import EscoLoader
from app.services.analytics.occupations import OccupationAnalytics
from app.services.analytics.sectoral import SectoralAnalytics

from dotenv import load_dotenv
load_dotenv()

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

    result = await market.analyze_market_data(mock_jobs)

    assert result["total_jobs"] == 1
    # Verifica campi Intelligence Phase 1
    skill_entry = result["rankings"]["skills"][0]
    assert skill_entry["name"] == "Python"
    assert skill_entry["is_digital"] is True
    assert skill_entry["sector_spread"] == 1
    assert result["rankings"]["sectors"][0]["name"] == "Tech"







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
        await tracker.fetch_occupation_labels([occ_uri])

        # 4. VERIFICA
        # Se fallisce qui, stamperà il contenuto della mappa per debuggare
        assert occ_uri in engine.sector_map, f"Mappa vuota! uris cercati erano {occ_uri}. Mappa: {engine.sector_map}"
        assert engine.sector_map[occ_uri] == "Energy Sector"


@pytest.mark.asyncio
async def test_fetch_occupation_labels_2():
    """Versione atomica: resetta tutto e forza il mock."""
    from app.core.container import engine

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
        await tracker.fetch_occupation_labels([occ_uri])

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
    with patch.object(tracker, 'fetch_all_jobs', new_callable=AsyncMock) as m_fetch:
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
    result = await market.analyze_market_data([{"skills": ["s1"]}] * 5)
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

    with patch.object(tracker, 'fetch_all_jobs', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.side_effect = [mock_jobs_a, mock_jobs_b]

        result = await trends.calculate_smart_trends({}, "2024-01-01", "2024-01-04")

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
        result = await tracker.fetch_all_jobs({"kw": "test"})
        assert result == []


@pytest.mark.asyncio
async def test_analyze_market_data_empty_jobs():
    """Testa il metodo _empty_res (Coverage dei rami edge)."""
    result = await market.analyze_market_data([])
    assert result["total_jobs"] == 0
    assert result["rankings"]["skills"] == []


@pytest.mark.asyncio
async def test_analyze_market_data_unclassified_sector():
    """Verifica il fallback 'Settore non specificato' se manca occupation_id."""
    mock_jobs = [{"skills": ["s1"]}]  # Manca occupation_id
    engine.skill_map = {"s1": {"label": "Test", "is_green": False, "is_digital": False}}
    engine.sector_map = {}

    result = await market.analyze_market_data(mock_jobs)
    assert result["rankings"]["sectors"] == []

# ==========================================
# 5. INTEGRATION: ENDPOINT EMERGING SKILLS
# ==========================================

@pytest.mark.integration
def test_endpoint_emerging_skills_structure():
    """Verifica la struttura JSON dell'endpoint trend."""
    with patch.object(tracker, 'fetch_all_jobs', new_callable=AsyncMock) as m_fetch:
        m_fetch.return_value = []
        response = client.post("/projector/emerging-skills", data={
            "min_date": "2024-01-01", "max_date": "2024-01-31"
        })
        assert response.status_code == 200
        assert "market_health" in response.json()["insights"]


import csv
from pathlib import Path

# ==========================================
# 1.b TWIN TRANSITION CSV LOOKUP
# ==========================================

def test_load_skill_uris_from_csv_reads_concept_uri(tmp_path):
    """
    Verifica che il loader legga correttamente la colonna conceptUri
    e costruisca il set degli URI.
    """
    csv_file = tmp_path / "green_skills.csv"
    csv_file.write_text(
        "conceptType,conceptUri,preferredLabel\n"
        "KnowledgeSkillCompetence,http://data.europa.eu/esco/skill/g1,green skill one\n"
        "KnowledgeSkillCompetence,http://data.europa.eu/esco/skill/g2,green skill two\n",
        encoding="utf-8"
    )

    uris = loader._load_skill_uris_from_csv(str(csv_file))

    assert uris == {
        "http://data.europa.eu/esco/skill/g1",
        "http://data.europa.eu/esco/skill/g2",
    }


def test_load_skill_uris_from_csv_missing_file_returns_empty_set():
    """
    Se il CSV non esiste, il loader deve restituire un set vuoto.
    """
    uris = loader._load_skill_uris_from_csv("path/that/does/not/exist.csv")
    assert uris == set()


def test_load_skill_uris_from_csv_ignores_empty_concept_uri(tmp_path):
    """
    Le righe senza conceptUri valido devono essere ignorate.
    """
    csv_file = tmp_path / "digital_skills.csv"
    csv_file.write_text(
        "conceptType,conceptUri,preferredLabel\n"
        "KnowledgeSkillCompetence,,missing uri\n"
        "KnowledgeSkillCompetence,http://data.europa.eu/esco/skill/d1,digital skill one\n",
        encoding="utf-8"
    )

    uris = loader._load_skill_uris_from_csv(str(csv_file))

    assert uris == {"http://data.europa.eu/esco/skill/d1"}


@pytest.mark.asyncio
@pytest.mark.skip("Green and Digital Skill Not Implemented")
async def test_fetch_skill_names_uses_csv_lookup_green_only():
    """
    Verifica che fetch_skill_names assegni i flag usando gli URI caricati dal CSV:
    skill presente solo nel set green.
    """
    engine.skill_map = {}
    engine.token = "fake_token"
    engine.stop_requested = False

    engine.green_skill_uris = {"http://data.europa.eu/esco/skill/s1"}
    engine.digital_skill_uris = set()

    target_uri = "http://data.europa.eu/esco/skill/s1"

    with patch.object(engine.client, "post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [{"id": target_uri, "label": "Some label not used for tagging"}]
        }
        mock_post.return_value = mock_response

        await tracker.fetch_skill_names([target_uri])

        assert target_uri in engine.skill_map
        entry = engine.skill_map[target_uri]
        assert entry["label"] == "Some label not used for tagging"
        assert entry["is_green"] is True
        assert entry["is_digital"] is False


@pytest.mark.asyncio
@pytest.mark.skip("Green and Digital Skill Not Implemented")
async def test_fetch_skill_names_uses_csv_lookup_digital_only():
    """
    Skill presente solo nel set digital.
    """
    engine.skill_map = {}
    engine.token = "fake_token"
    engine.stop_requested = False

    engine.green_skill_uris = set()
    engine.digital_skill_uris = {"http://data.europa.eu/esco/skill/s2"}

    target_uri = "http://data.europa.eu/esco/skill/s2"

    with patch.object(engine.client, "post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [{"id": target_uri, "label": "Another label"}]
        }
        mock_post.return_value = mock_response

        await tracker.fetch_skill_names([target_uri])

        entry = engine.skill_map[target_uri]
        assert entry["is_green"] is False
        assert entry["is_digital"] is True


@pytest.mark.asyncio
@pytest.mark.skip("Green and Digital Skill Not Implemented")
async def test_fetch_skill_names_uses_csv_lookup_both_green_and_digital():
    """
    Skill presente in entrambi i set.
    """
    engine.skill_map = {}
    engine.token = "fake_token"
    engine.stop_requested = False

    target_uri = "http://data.europa.eu/esco/skill/s3"
    engine.green_skill_uris = {target_uri}
    engine.digital_skill_uris = {target_uri}

    with patch.object(engine.client, "post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [{"id": target_uri, "label": "Hybrid skill"}]
        }
        mock_post.return_value = mock_response

        await tracker.fetch_skill_names([target_uri])

        entry = engine.skill_map[target_uri]
        assert entry["is_green"] is True
        assert entry["is_digital"] is True


@pytest.mark.asyncio
@pytest.mark.skip("Green and Digital Skill Not Implemented")
async def test_fetch_skill_names_returns_false_false_when_uri_not_in_any_csv():
    """
    Se l'URI non è presente né nel CSV green né in quello digital,
    i flag devono andare a False/False.
    """
    engine.skill_map = {}
    engine.token = "fake_token"
    engine.stop_requested = False

    engine.green_skill_uris = set()
    engine.digital_skill_uris = set()

    target_uri = "http://data.europa.eu/esco/skill/s4"

    with patch.object(engine.client, "post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [{"id": target_uri, "label": "Unclassified skill"}]
        }
        mock_post.return_value = mock_response

        await tracker.fetch_skill_names([target_uri])

        entry = engine.skill_map[target_uri]
        assert entry["is_green"] is False
        assert entry["is_digital"] is False


@pytest.mark.asyncio
async def test_fetch_skill_names_does_not_requery_already_cached_skill():
    """
    Se una skill è già in skill_map, non deve essere richiesta di nuovo.
    """
    target_uri = "http://data.europa.eu/esco/skill/s5"

    engine.skill_map = {
        target_uri: {
            "label": "Already cached",
            "is_green": False,
            "is_digital": True,
        }
    }
    engine.token = "fake_token"
    engine.stop_requested = False
    engine.green_skill_uris = set()
    engine.digital_skill_uris = {target_uri}

    with patch.object(engine.client, "post", new_callable=AsyncMock) as mock_post:
        await tracker.fetch_skill_names([target_uri])

        mock_post.assert_not_called()
        assert engine.skill_map[target_uri]["label"] == "Already cached"


@pytest.mark.asyncio
async def test_engine_analyze_market_data_logic_with_csv_based_tags():
    """
    Verifica end-to-end che analyze_market_data propaghi correttamente
    i flag derivati dal lookup CSV.
    """
    mock_jobs = [
        {
            "organization_name": "Google",
            "title": "Dev",
            "location_code": "IT",
            "skills": ["http://data.europa.eu/esco/skill/s1"],
            "occupation_id": "occ_1",
        }
    ]

    engine.sector_map = {"occ_1": "Tech"}
    engine.skill_map = {
        "http://data.europa.eu/esco/skill/s1": {
            "label": "Python",
            "is_green": False,
            "is_digital": True,
        }
    }
    engine.stop_requested = False

    result = await market.analyze_market_data(mock_jobs)

    skill_entry = result["rankings"]["skills"][0]
    assert skill_entry["name"] == "Python"
    assert skill_entry["is_green"] is False
    assert skill_entry["is_digital"] is True

@pytest.mark.asyncio
@pytest.mark.skip
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

        await tracker.fetch_skill_names(["s1"])

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

    with patch.object(tracker, 'fetch_all_jobs', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.side_effect = [mock_jobs_a, mock_jobs_b]

        result = await trends.calculate_smart_trends({}, "2024-01-01", "2024-01-04")

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

    with patch.object(tracker, 'fetch_all_jobs', new_callable=AsyncMock) as m_fetch:
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
    with patch.object(tracker, 'fetch_all_jobs', new_callable=AsyncMock) as m_fetch:
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

        await tracker.fetch_occupation_labels([target_uri])

        assert mock_post.called
        args, kwargs = mock_post.call_args
        # FIX: Cerchiamo 'json' invece di 'data' perché siamo passati a JSON in produzione
        assert target_uri in kwargs['data']['ids']
        assert engine.sector_map[target_uri] == expected_label


@pytest.mark.asyncio
async def test_fetch_occupation_labels_integration_real():
    load_dotenv()
    if not os.getenv("TRACKER_API") or not os.getenv("TRACKER_USERNAME") or not os.getenv("TRACKER_PASSWORD"):
        pytest.skip("Real Tracker integration requires TRACKER_* environment variables")
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
    await tracker.fetch_occupation_labels([target_uri])

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
    results = regional.get_regional_projections(mock_jobs)

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

    # ==========================================
    # 6. LOCAL ESCO SUPPORT LOADING
    # ==========================================

def test_load_local_esco_support_populates_maps(monkeypatch, tmp_path):
    """
    Verifica che il loader locale popoli correttamente:
    - occupation_meta
    - skill_hierarchy
    - occ_skill_relations
    - occupation_group_labels
    """
    from app.core.container import ProjectorEngine

    # --- 1. Creo la cartella corretta ---
    data_dir = tmp_path / "complementary_data"
    data_dir.mkdir()

    # --- 2. Creo file CSV minimi di test ---
    occupations_file = data_dir / "occupations_en.csv"
    occupations_file.write_text(
        "conceptUri,preferredLabel,iscoGroup,naceCode\n"
        "occ_1,Software developer,isco_2512,J62\n"
        "occ_2,Data analyst,isco_2421,J62\n",
        encoding="utf-8"
    )

    skills_hierarchy_file = data_dir / "skillsHierarchy_en.csv"
    skills_hierarchy_file.write_text(
        "conceptUri,ESCO Level 1,ESCO Level 2,ESCO Level 3\n"
        "skill_1,S5,S5.1,S5.1.1\n"
        "skill_2,S2,S2.3,S2.3.4\n",
        encoding="utf-8"
    )

    occ_skill_rel_file = data_dir / "occupationSkillRelations_en.csv"
    occ_skill_rel_file.write_text(
        "occupationUri,skillUri\n"
        "occ_1,skill_1\n"
        "occ_1,skill_2\n"
        "occ_2,skill_2\n",
        encoding="utf-8"
    )

    isco_groups_file = data_dir / "ISCOGroups_en.csv"
    isco_groups_file.write_text(
        "conceptUri,preferredLabel\n"
        "isco_2512,Software developers\n"
        "isco_2421,Business professionals\n",
        encoding="utf-8"
    )

    monkeypatch.chdir(tmp_path)

    engine = ProjectorEngine()
    loader = EscoLoader(engine)
    engine.occupation_meta = {}
    engine.skill_hierarchy = {}
    engine.occ_skill_relations = defaultdict(set)
    engine.occupation_group_labels = {}
    engine.matrix_profiles = {}

    loader.load_local_esco_support()

    assert "occ_1" in engine.occupation_meta
    assert engine.occupation_meta["occ_1"]["label"] == "Software developer"
    assert engine.occupation_meta["occ_1"]["isco_group"] == "isco_2512"
    assert engine.occupation_meta["occ_1"]["nace_code"] == "J62"

    assert "occ_2" in engine.occupation_meta
    assert engine.occupation_meta["occ_2"]["label"] == "Data analyst"

    assert "skill_1" in engine.skill_hierarchy
    assert engine.skill_hierarchy["skill_1"]["level_1"] == "S5"
    assert engine.skill_hierarchy["skill_1"]["level_2"] == "S5.1"
    assert engine.skill_hierarchy["skill_1"]["level_3"] == "S5.1.1"

    assert "skill_2" in engine.skill_hierarchy
    assert engine.skill_hierarchy["skill_2"]["level_1"] == "S2"

    assert "occ_1" in engine.occ_skill_relations
    assert engine.occ_skill_relations["occ_1"] == {"skill_1", "skill_2"}

    assert "occ_2" in engine.occ_skill_relations
    assert engine.occ_skill_relations["occ_2"] == {"skill_2"}

    assert engine.occupation_group_labels["isco_2512"] == "Software developers"
    assert engine.occupation_group_labels["isco_2421"] == "Business professionals"

def test_load_local_esco_support_missing_files_is_safe(monkeypatch, tmp_path):
    """
    Verifica che il loader non fallisca se i CSV non esistono.
    """
    from app.core.container import ProjectorEngine

    monkeypatch.chdir(tmp_path)

    engine = ProjectorEngine()
    loader = EscoLoader(engine)
    engine.occupation_meta = {}
    engine.skill_hierarchy = {}
    engine.occ_skill_relations = defaultdict(set)
    engine.occupation_group_labels = {}
    engine.matrix_profiles = {}

    # Non deve alzare eccezioni
    loader.load_local_esco_support()

    assert engine.occupation_meta == {}
    assert engine.skill_hierarchy == {}
    assert dict(engine.occ_skill_relations) == {}
    assert engine.occupation_group_labels == {}

def test_load_local_esco_support_ignores_incomplete_rows(monkeypatch, tmp_path):
    """
    Verifica che righe incomplete o senza ID vengano ignorate.
    """
    from app.core.container import ProjectorEngine

    data_dir = tmp_path / "complementary_data"
    data_dir.mkdir()

    occupations_file = data_dir / "occupations_en.csv"
    occupations_file.write_text(
        "conceptUri,preferredLabel,iscoGroup,naceCode\n"
        ",Missing ID,isco_x,J00\n"
        "occ_valid,Valid occupation,isco_ok,J62\n",
        encoding="utf-8"
    )

    skills_hierarchy_file = data_dir / "skillsHierarchy_en.csv"
    skills_hierarchy_file.write_text(
        "conceptUri,ESCO Level 1,ESCO Level 2,ESCO Level 3\n"
        ",S1,S1.1,S1.1.1\n"
        "skill_valid,S2,S2.1,S2.1.1\n",
        encoding="utf-8"
    )

    occ_skill_rel_file = data_dir / "occupationSkillRelations_en.csv"
    occ_skill_rel_file.write_text(
        "occupationUri,skillUri\n"
        ",skill_x\n"
        "occ_valid,\n"
        "occ_valid,skill_valid\n",
        encoding="utf-8"
    )

    monkeypatch.chdir(tmp_path)

    engine = ProjectorEngine()
    loader = EscoLoader(engine)
    engine.occupation_meta = {}
    engine.skill_hierarchy = {}
    engine.occ_skill_relations = defaultdict(set)
    engine.occupation_group_labels = {}
    engine.matrix_profiles = {}

    loader.load_local_esco_support()

    assert list(engine.occupation_meta.keys()) == ["occ_valid"]
    assert list(engine.skill_hierarchy.keys()) == ["skill_valid"]
    assert engine.occ_skill_relations["occ_valid"] == {"skill_valid"}

def test_load_local_esco_support_accepts_alternative_column_names(monkeypatch, tmp_path):
    """
    Verifica i fallback sui nomi colonna alternativi previsti nel loader.
    """
    from app.core.container import ProjectorEngine

    data_dir = tmp_path / "complementary_data"
    data_dir.mkdir()

    occupations_file = data_dir / "occupations_en.csv"
    occupations_file.write_text(
        "id,label,iscoGroup,naceCode\n"
        "occ_alt,Alt occupation,isco_alt,J63\n",
        encoding="utf-8"
    )

    skills_hierarchy_file = data_dir / "skillsHierarchy_en.csv"
    skills_hierarchy_file.write_text(
        "id,level1,level2,level3\n"
        "skill_alt,S9,S9.1,S9.1.1\n",
        encoding="utf-8"
    )

    occ_skill_rel_file = data_dir / "occupationSkillRelations_en.csv"
    occ_skill_rel_file.write_text(
        "occupation,skill\n"
        "occ_alt,skill_alt\n",
        encoding="utf-8"
    )

    isco_groups_file = data_dir / "ISCOGroups_en.csv"
    isco_groups_file.write_text(
        "id,label\n"
        "isco_alt,Alt group label\n",
        encoding="utf-8"
    )

    monkeypatch.chdir(tmp_path)

    engine = ProjectorEngine()
    loader = EscoLoader(engine)
    engine.occupation_meta = {}
    engine.skill_hierarchy = {}
    engine.occ_skill_relations = defaultdict(set)
    engine.occupation_group_labels = {}
    engine.matrix_profiles = {}

    loader.load_local_esco_support()

    assert engine.occupation_meta["occ_alt"]["label"] == "Alt occupation"
    assert engine.skill_hierarchy["skill_alt"]["level_1"] == "S9"
    assert engine.occ_skill_relations["occ_alt"] == {"skill_alt"}
    assert engine.occupation_group_labels["isco_alt"] == "Alt group label"

# ==========================================
# 7. OCCUPATION -> SECTOR RESOLUTION
# ==========================================

def test_get_primary_occupation_id_prefers_occupations_list():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)

    job = {
        "occupations": ["occ_new"],
        "occupation_id": "occ_old"
    }

    assert occupations.get_primary_occupation_id(job) == "occ_new"


def test_get_primary_occupation_id_falls_back_to_legacy_field():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)

    job = {
        "occupation_id": "occ_legacy"
    }

    assert occupations.get_primary_occupation_id(job) == "occ_legacy"


def test_get_primary_occupation_id_returns_empty_string_when_missing():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)

    job = {"title": "No occupation"}

    assert occupations.get_primary_occupation_id(job) == ""


def test_get_sector_from_occupation_uses_local_isco_group_label():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    engine.occupation_meta = {
        "occ_1": {
            "label": "Software developer",
            "isco_group": "isco_2512",
            "nace_code": "J62"
        }
    }
    engine.occupation_group_labels = {
        "isco_2512": "Software developers"
    }
    engine.sector_map = {}

    result = occupations.get_sector_from_occupation("occ_1", level="isco_group")
    assert result == "Software developers"


def test_get_sector_from_occupation_falls_back_to_isco_group_code():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    engine.occupation_meta = {
        "occ_1": {
            "label": "Software developer",
            "isco_group": "isco_2512",
            "nace_code": "J62"
        }
    }
    engine.occupation_group_labels = {}
    engine.sector_map = {}

    result = occupations.get_sector_from_occupation("occ_1", level="isco_group")
    assert result == "isco_2512"


def test_get_sector_from_occupation_can_return_label():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    engine.occupation_meta = {
        "occ_1": {
            "label": "Software developer",
            "isco_group": "isco_2512",
            "nace_code": "J62"
        }
    }
    engine.occupation_group_labels = {}
    engine.sector_map = {}

    result = occupations.get_sector_from_occupation("occ_1", level="label")
    assert result == "Software developer"


def test_get_sector_from_occupation_can_return_nace_code():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    engine.occupation_meta = {
        "occ_1": {
            "label": "Software developer",
            "isco_group": "isco_2512",
            "nace_code": "J62"
        }
    }
    engine.occupation_group_labels = {}
    engine.sector_map = {}

    result = occupations.get_sector_from_occupation("occ_1", level="nace_code")
    assert result == "J62"


def test_get_sector_from_occupation_can_return_nace_hierarchy_levels():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    engine.occupation_meta = {
        "occ_1": {
            "label": "Food processor",
            "isco_group": "isco_8160",
            "nace_code": "C10.11"
        }
    }
    engine.occupation_group_labels = {}
    engine.sector_map = {}

    assert occupations.get_sector_from_occupation("occ_1", level="nace_division") == "C10"
    assert occupations.get_sector_from_occupation("occ_1", level="nace_group") == "C101"
    assert occupations.get_sector_from_occupation("occ_1", level="nace_class") == "C1011"


def test_get_sector_from_occupation_nace_hierarchy_falls_back_when_code_is_short():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    engine.occupation_meta = {
        "occ_1": {
            "label": "Software developer",
            "isco_group": "isco_2512",
            "nace_code": "J62"
        }
    }
    engine.occupation_group_labels = {}
    engine.sector_map = {}

    assert occupations.get_sector_from_occupation("occ_1", level="nace_division") == "J62"
    assert occupations.get_sector_from_occupation("occ_1", level="nace_group") == "J62"
    assert occupations.get_sector_from_occupation("occ_1", level="nace_class") == "J62"


def test_get_sector_from_occupation_falls_back_to_tracker_sector_map():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    engine.occupation_meta = {}
    engine.occupation_group_labels = {}
    engine.sector_map = {
        "occ_tracker": "ICT professionals"
    }

    result = occupations.get_sector_from_occupation("occ_tracker")
    assert result == "ICT professionals"


def test_get_sector_from_occupation_returns_default_when_unknown():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    engine.occupation_meta = {}
    engine.occupation_group_labels = {}
    engine.sector_map = {}

    result = occupations.get_sector_from_occupation("unknown_occ")
    assert result == "Sector not specified"

# ==========================================
# 8. OBSERVED OCCUPATION -> SKILL MATRIX
# ==========================================

def test_build_observed_occupation_skill_matrix_counts_correctly():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.occ_skill_observed = defaultdict(Counter)

    jobs = [
        {"occupation_id": "occ_1", "skills": ["skill_a", "skill_b"]},
        {"occupation_id": "occ_1", "skills": ["skill_a"]},
        {"occupation_id": "occ_2", "skills": ["skill_b"]},
    ]

    matrix = sectoral.build_observed_occupation_skill_matrix(jobs)

    assert matrix["occ_1"]["skill_a"] == 2
    assert matrix["occ_1"]["skill_b"] == 1
    assert matrix["occ_2"]["skill_b"] == 1


def test_build_observed_occupation_skill_matrix_prefers_occupations_list():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.occ_skill_observed = defaultdict(Counter)

    jobs = [
        {"occupations": ["occ_new"], "occupation_id": "occ_old", "skills": ["skill_x"]},
    ]

    matrix = sectoral.build_observed_occupation_skill_matrix(jobs)

    assert "occ_new" in matrix
    assert "occ_old" in matrix
    assert matrix["occ_new"]["skill_x"] == 1


def test_build_observed_occupation_skill_matrix_skips_jobs_without_occupation():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.occ_skill_observed = defaultdict(Counter)

    jobs = [
        {"skills": ["skill_a"]},
        {"occupation_id": "", "skills": ["skill_b"]},
    ]

    matrix = sectoral.build_observed_occupation_skill_matrix(jobs)

    assert dict(matrix) == {}


def test_build_observed_occupation_skill_matrix_skips_empty_skill_ids():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.occ_skill_observed = defaultdict(Counter)

    jobs = [
        {"occupation_id": "occ_1", "skills": ["skill_a", "", "   "]},
    ]

    matrix = sectoral.build_observed_occupation_skill_matrix(jobs)

    assert matrix["occ_1"]["skill_a"] == 1
    assert "" not in matrix["occ_1"]


def test_get_observed_skills_for_occupation_returns_sorted_counts():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.occ_skill_observed = defaultdict(Counter)
    engine.occ_skill_observed["occ_1"]["skill_a"] = 3
    engine.occ_skill_observed["occ_1"]["skill_b"] = 1

    result = sectoral.get_observed_skills_for_occupation("occ_1")

    assert result[0]["skill_id"] == "skill_a"
    assert result[0]["count"] == 3
    assert result[1]["skill_id"] == "skill_b"
    assert result[1]["count"] == 1


def test_get_observed_skills_for_occupation_can_resolve_labels():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.occ_skill_observed = defaultdict(Counter)
    engine.skill_map = {
        "skill_a": {"label": "Python"}
    }
    engine.occ_skill_observed["occ_1"]["skill_a"] = 2

    result = sectoral.get_observed_skills_for_occupation("occ_1", resolve_labels=True)

    assert result[0]["skill_id"] == "skill_a"
    assert result[0]["label"] == "Python"
    assert result[0]["count"] == 2


def test_build_observed_sector_skill_matrix_counts_correctly():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skill_observed = defaultdict(Counter)

    engine.occupation_meta = {
        "occ_1": {"label": "Software developer", "isco_group": "isco_2512", "nace_code": "J62"},
        "occ_2": {"label": "Data analyst", "isco_group": "isco_2512", "nace_code": "J62"},
    }
    engine.occupation_group_labels = {
        "isco_2512": "Software developers"
    }
    engine.sector_map = {}

    jobs = [
        {"occupation_id": "occ_1", "skills": ["skill_a", "skill_b"]},
        {"occupation_id": "occ_2", "skills": ["skill_a"]},
    ]

    matrix = sectoral.build_observed_sector_skill_matrix(jobs, sector_level="isco_group")

    assert matrix["Software developers"]["skill_a"] == 2
    assert matrix["Software developers"]["skill_b"] == 1


def test_get_observed_skills_for_sector_returns_sorted_counts():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skill_observed = defaultdict(Counter)
    engine.sector_skill_observed["ICT"]["skill_x"] = 4
    engine.sector_skill_observed["ICT"]["skill_y"] = 1

    result = sectoral.get_observed_skills_for_sector("ICT")

    assert result[0]["skill_id"] == "skill_x"
    assert result[0]["count"] == 4
    assert result[1]["skill_id"] == "skill_y"
    assert result[1]["count"] == 1

# ==========================================
# 9. OBSERVED SECTOR SKILL SUMMARIES
# ==========================================

def test_summarize_observed_sector_skills_returns_sorted_sectors():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skill_observed = defaultdict(Counter)

    engine.sector_skill_observed["Sector A"]["skill_1"] = 5
    engine.sector_skill_observed["Sector A"]["skill_2"] = 1
    engine.sector_skill_observed["Sector B"]["skill_3"] = 2

    result = sectoral.summarize_observed_sector_skills()

    assert result[0]["sector"] == "Sector A"
    assert result[0]["total_skill_mentions"] == 6
    assert result[1]["sector"] == "Sector B"
    assert result[1]["total_skill_mentions"] == 2


def test_summarize_observed_sector_skills_computes_frequencies():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skill_observed = defaultdict(Counter)

    engine.sector_skill_observed["ICT"]["skill_a"] = 3
    engine.sector_skill_observed["ICT"]["skill_b"] = 1

    result = sectoral.summarize_observed_sector_skills(top_k=10)

    ict = result[0]
    assert ict["sector"] == "ICT"
    assert ict["total_skill_mentions"] == 4
    assert ict["unique_skills"] == 2

    top_skills = ict["top_skills"]
    assert top_skills[0]["skill_id"] == "skill_a"
    assert top_skills[0]["count"] == 3
    assert top_skills[0]["frequency"] == 0.75

    assert top_skills[1]["skill_id"] == "skill_b"
    assert top_skills[1]["count"] == 1
    assert top_skills[1]["frequency"] == 0.25


def test_summarize_observed_sector_skills_can_resolve_labels_and_flags():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skill_observed = defaultdict(Counter)
    engine.skill_map = {
        "skill_a": {"label": "Python", "is_green": False, "is_digital": True},
        "skill_b": {"label": "Solar design", "is_green": True, "is_digital": False},
    }

    engine.sector_skill_observed["ICT"]["skill_a"] = 2
    engine.sector_skill_observed["ICT"]["skill_b"] = 1

    result = sectoral.summarize_observed_sector_skills(resolve_labels=True)

    top_skills = result[0]["top_skills"]

    assert top_skills[0]["label"] == "Python"
    assert top_skills[0]["is_digital"] is True
    assert top_skills[0]["is_green"] is False

    assert top_skills[1]["label"] == "Solar design"
    assert top_skills[1]["is_green"] is True
    assert top_skills[1]["is_digital"] is False


def test_build_and_summarize_observed_sector_skills_from_jobs():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skill_observed = defaultdict(Counter)

    engine.occupation_meta = {
        "occ_1": {"label": "Software developer", "isco_group": "isco_2512", "nace_code": "J62"},
        "occ_2": {"label": "Data analyst", "isco_group": "isco_2512", "nace_code": "J62"},
    }
    engine.occupation_group_labels = {
        "isco_2512": "Software developers"
    }
    engine.skill_map = {
        "skill_a": {"label": "Python", "is_green": False, "is_digital": True},
        "skill_b": {"label": "SQL", "is_green": False, "is_digital": True},
    }

    jobs = [
        {"occupation_id": "occ_1", "skills": ["skill_a", "skill_b"]},
        {"occupation_id": "occ_2", "skills": ["skill_a"]},
    ]

    result = sectoral.build_and_summarize_observed_sector_skills(
        jobs=jobs,
        sector_level="isco_group",
        resolve_labels=True,
        top_k=10
    )

    assert len(result) == 1
    sector = result[0]

    assert sector["sector"] == "Software developers"
    assert sector["total_skill_mentions"] == 3
    assert sector["unique_skills"] == 2

    assert sector["top_skills"][0]["skill_id"] == "skill_a"
    assert sector["top_skills"][0]["label"] == "Python"
    assert sector["top_skills"][0]["count"] == 2
    assert sector["top_skills"][0]["frequency"] == round(2 / 3, 6)


def test_summarize_single_sector_returns_one_sector_summary():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skill_observed = defaultdict(Counter)
    engine.skill_map = {
        "skill_x": {"label": "Docker", "is_green": False, "is_digital": True}
    }

    engine.sector_skill_observed["ICT"]["skill_x"] = 4

    result = sectoral.summarize_single_sector("ICT", resolve_labels=True)

    assert result["sector"] == "ICT"
    assert result["total_skill_mentions"] == 4
    assert result["unique_skills"] == 1
    assert result["top_skills"][0]["skill_id"] == "skill_x"
    assert result["top_skills"][0]["label"] == "Docker"
    assert result["top_skills"][0]["count"] == 4
    assert result["top_skills"][0]["frequency"] == 1.0

# ==========================================
# 10. CANONICAL SECTOR SKILLS
# ==========================================

def test_get_canonical_skills_for_occupation_returns_csv_skills():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.occ_skill_relations = defaultdict(set)
    engine.occ_skill_relations["occ_1"] = {"skill_a", "skill_b"}

    result = sectoral.get_canonical_skills_for_occupation("occ_1")

    returned_ids = {x["skill_id"] for x in result}
    assert returned_ids == {"skill_a", "skill_b"}


def test_get_canonical_skills_for_occupation_can_resolve_labels():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.occ_skill_relations = defaultdict(set)
    engine.occ_skill_relations["occ_1"] = {"skill_a"}
    engine.skill_map = {
        "skill_a": {"label": "Python", "is_green": False, "is_digital": True}
    }

    result = sectoral.get_canonical_skills_for_occupation("occ_1", resolve_labels=True)

    assert result[0]["skill_id"] == "skill_a"
    assert result[0]["label"] == "Python"
    assert result[0]["is_digital"] is True
    assert result[0]["is_green"] is False


def test_build_canonical_sector_skill_matrix_counts_correctly():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skill_canonical = defaultdict(Counter)

    engine.occupation_meta = {
        "occ_1": {"label": "Software developer", "isco_group": "isco_2512", "nace_code": "J62"},
        "occ_2": {"label": "Data analyst", "isco_group": "isco_2512", "nace_code": "J62"},
    }
    engine.occupation_group_labels = {
        "isco_2512": "Software developers"
    }
    engine.occ_skill_relations = defaultdict(set)
    engine.occ_skill_relations["occ_1"] = {"skill_a", "skill_b"}
    engine.occ_skill_relations["occ_2"] = {"skill_a"}

    jobs = [
        {"occupation_id": "occ_1", "skills": ["skill_x"]},
        {"occupation_id": "occ_2", "skills": ["skill_y"]},
    ]

    matrix = sectoral.build_canonical_sector_skill_matrix(jobs, sector_level="isco_group")

    assert matrix["Software developers"]["skill_a"] == 2
    assert matrix["Software developers"]["skill_b"] == 1


def test_get_canonical_skills_for_sector_returns_sorted_counts():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skill_canonical = defaultdict(Counter)
    engine.sector_skill_canonical["ICT"]["skill_a"] = 4
    engine.sector_skill_canonical["ICT"]["skill_b"] = 1

    result = sectoral.get_canonical_skills_for_sector("ICT")

    assert result[0]["skill_id"] == "skill_a"
    assert result[0]["count"] == 4
    assert result[1]["skill_id"] == "skill_b"
    assert result[1]["count"] == 1


def test_summarize_canonical_sector_skills_computes_frequencies():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skill_canonical = defaultdict(Counter)
    engine.sector_skill_canonical["ICT"]["skill_a"] = 3
    engine.sector_skill_canonical["ICT"]["skill_b"] = 1

    result = sectoral.summarize_canonical_sector_skills(top_k=10)

    ict = result[0]
    assert ict["sector"] == "ICT"
    assert ict["total_skill_mentions"] == 4
    assert ict["unique_skills"] == 2

    assert ict["top_skills"][0]["skill_id"] == "skill_a"
    assert ict["top_skills"][0]["frequency"] == 0.75
    assert ict["top_skills"][1]["skill_id"] == "skill_b"
    assert ict["top_skills"][1]["frequency"] == 0.25


def test_build_and_summarize_canonical_sector_skills_from_jobs():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skill_canonical = defaultdict(Counter)

    engine.occupation_meta = {
        "occ_1": {"label": "Software developer", "isco_group": "isco_2512", "nace_code": "J62"},
    }
    engine.occupation_group_labels = {
        "isco_2512": "Software developers"
    }
    engine.occ_skill_relations = defaultdict(set)
    engine.occ_skill_relations["occ_1"] = {"skill_a", "skill_b"}
    engine.skill_map = {
        "skill_a": {"label": "Python", "is_green": False, "is_digital": True},
        "skill_b": {"label": "SQL", "is_green": False, "is_digital": True},
    }

    jobs = [
        {"occupation_id": "occ_1", "skills": ["skill_x"]},
        {"occupation_id": "occ_1", "skills": ["skill_y"]},
    ]

    result = sectoral.build_and_summarize_canonical_sector_skills(
        jobs=jobs,
        sector_level="isco_group",
        resolve_labels=True,
        top_k=10
    )

    assert len(result) == 1
    sector = result[0]

    assert sector["sector"] == "Software developers"
    assert sector["total_skill_mentions"] == 4
    assert sector["unique_skills"] == 2


def test_compare_observed_and_canonical_for_sector_returns_both_views():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skill_observed = defaultdict(Counter)
    engine.sector_skill_canonical = defaultdict(Counter)
    engine.skill_map = {
        "skill_a": {"label": "Python", "is_green": False, "is_digital": True},
        "skill_b": {"label": "SQL", "is_green": False, "is_digital": True},
    }

    engine.sector_skill_observed["ICT"]["skill_a"] = 3
    engine.sector_skill_canonical["ICT"]["skill_b"] = 2

    result = sectoral.compare_observed_and_canonical_for_sector(
        "ICT",
        resolve_labels=True,
        top_k=10
    )

    assert result["sector"] == "ICT"
    assert result["observed"]["sector"] == "ICT"
    assert result["canonical"]["sector"] == "ICT"

    assert result["observed"]["top_skills"][0]["skill_id"] == "skill_a"
    assert result["canonical"]["top_skills"][0]["skill_id"] == "skill_b"

    # ==========================================
    # 11. SECTOR -> SKILL GROUP MATRICES
    # ==========================================

def test_get_skill_group_returns_level_2_by_default():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.skill_hierarchy = {
        "skill_a": {
            "level_1": "S5",
            "level_2": "S5.1",
            "level_3": "S5.1.2"
        }
    }

    result = sectoral.get_skill_group("skill_a")
    assert result == "S5.1"

def test_get_skill_group_can_return_level_1():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.skill_hierarchy = {
        "skill_a": {
            "level_1": "S5",
            "level_2": "S5.1",
            "level_3": "S5.1.2"
        }
    }

    result = sectoral.get_skill_group("skill_a", level=1)
    assert result == "S5"

def test_get_skill_group_falls_back_to_label():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.skill_hierarchy = {}
    engine.skill_map = {
        "skill_a": {"label": "Python"}
    }

    result = sectoral.get_skill_group("skill_a", level=2)
    assert result == "Python"

def test_build_observed_sector_skillgroup_matrix_counts_correctly():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skillgroup_observed = defaultdict(Counter)

    engine.occupation_meta = {
        "occ_1": {"label": "Software developer", "isco_group": "isco_2512", "nace_code": "J62"},
    }
    engine.occupation_group_labels = {
        "isco_2512": "Software developers"
    }
    engine.skill_hierarchy = {
        "skill_a": {"level_1": "S5", "level_2": "S5.1", "level_3": "S5.1.2"},
        "skill_b": {"level_1": "S5", "level_2": "S5.1", "level_3": "S5.1.3"},
        "skill_c": {"level_1": "S2", "level_2": "S2.4", "level_3": "S2.4.1"},
    }

    jobs = [
        {"occupation_id": "occ_1", "skills": ["skill_a", "skill_b", "skill_c"]},
        {"occupation_id": "occ_1", "skills": ["skill_a"]},
    ]

    matrix = sectoral.build_observed_sector_skillgroup_matrix(
        jobs=jobs,
        sector_level="isco_group",
        skill_group_level=2
    )

    assert matrix["Software developers"]["S5.1"] == 3
    assert matrix["Software developers"]["S2.4"] == 1

def test_build_canonical_sector_skillgroup_matrix_counts_correctly():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skillgroup_canonical = defaultdict(Counter)

    engine.occupation_meta = {
        "occ_1": {"label": "Software developer", "isco_group": "isco_2512", "nace_code": "J62"},
    }
    engine.occupation_group_labels = {
        "isco_2512": "Software developers"
    }
    engine.occ_skill_relations = defaultdict(set)
    engine.occ_skill_relations["occ_1"] = {"skill_a", "skill_b"}
    engine.skill_hierarchy = {
        "skill_a": {"level_1": "S5", "level_2": "S5.1", "level_3": "S5.1.2"},
        "skill_b": {"level_1": "S2", "level_2": "S2.4", "level_3": "S2.4.1"},
    }

    jobs = [
        {"occupation_id": "occ_1", "skills": ["skill_x"]},
        {"occupation_id": "occ_1", "skills": ["skill_y"]},
    ]

    matrix = sectoral.build_canonical_sector_skillgroup_matrix(
        jobs=jobs,
        sector_level="isco_group",
        skill_group_level=2
    )

    assert matrix["Software developers"]["S5.1"] == 2
    assert matrix["Software developers"]["S2.4"] == 2

def test_summarize_observed_sector_skillgroups_returns_frequencies():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skillgroup_observed = defaultdict(Counter)
    engine.sector_skillgroup_observed["ICT"]["S5.1"] = 3
    engine.sector_skillgroup_observed["ICT"]["S2.4"] = 1

    result = sectoral.summarize_observed_sector_skillgroups(top_k=10)

    ict = result[0]
    assert ict["sector"] == "ICT"
    assert ict["total_group_mentions"] == 4
    assert ict["unique_groups"] == 2
    assert ict["top_groups"][0]["group_id"] == "S5.1"
    assert ict["top_groups"][0]["frequency"] == 0.75

def test_summarize_canonical_sector_skillgroups_returns_frequencies():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skillgroup_canonical = defaultdict(Counter)
    engine.sector_skillgroup_canonical["ICT"]["S5.1"] = 2
    engine.sector_skillgroup_canonical["ICT"]["S2.4"] = 2

    result = sectoral.summarize_canonical_sector_skillgroups(top_k=10)

    ict = result[0]
    assert ict["sector"] == "ICT"
    assert ict["total_group_mentions"] == 4
    assert ict["unique_groups"] == 2
    assert ict["top_groups"][0]["frequency"] == 0.5

def test_compare_observed_and_canonical_groups_for_sector_returns_both_views():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skillgroup_observed = defaultdict(Counter)
    engine.sector_skillgroup_canonical = defaultdict(Counter)

    engine.sector_skillgroup_observed["ICT"]["S5.1"] = 3
    engine.sector_skillgroup_canonical["ICT"]["S2.4"] = 2

    result = sectoral.compare_observed_and_canonical_groups_for_sector("ICT", top_k=10)

    assert result["sector"] == "ICT"
    assert result["observed_groups"]["top_groups"][0]["group_id"] == "S5.1"
    assert result["canonical_groups"]["top_groups"][0]["group_id"] == "S2.4"

# ==========================================
# 12. OFFICIAL ESCO MATRIX
# ==========================================

def test_get_esco_matrix_sheet_name():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)

    assert occupations.get_esco_matrix_sheet_name(1, 1) == "Matrix 1.1"
    assert occupations.get_esco_matrix_sheet_name(2, 3) == "Matrix 2.3"

def test_get_occupation_group_id_for_matrix_reduces_to_requested_level():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    engine.occupation_meta = {
        "occ_1": {
            "label": "Software developer",
            "isco_group": "C2512",
            "nace_code": "J62"
        }
    }

    assert occupations.get_occupation_group_id_for_matrix("occ_1", occupation_level=1) == "C2"
    assert occupations.get_occupation_group_id_for_matrix("occ_1", occupation_level=2) == "C25"
    assert occupations.get_occupation_group_id_for_matrix("occ_1", occupation_level=3) == "C251"
    assert occupations.get_occupation_group_id_for_matrix("occ_1", occupation_level=4) == "C2512"

def test_get_official_esco_profile_for_occupation_returns_profile():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    engine.occupation_meta = {
        "occ_1": {"label": "Software developer", "isco_group": "C2", "nace_code": "J62"}
    }
    engine.esco_matrix_profiles = {
        ("Matrix 1.1", "http://data.europa.eu/esco/isco/C2"): {
            "occupation_group_label": "Professionals",
            "profile": {
                "skill_group_a": 0.4,
                "skill_group_b": 0.6
            }
        }
    }

    result = occupations.get_official_esco_profile_for_occupation(
        "occ_1",
        skill_group_level=1,
        occupation_level=1
    )

    assert result["sheet_name"] == "Matrix 1.1"
    assert result["occupation_group_label"] == "Professionals"
    assert result["profile"]["skill_group_a"] == 0.4

def test_build_official_matrix_sector_skillgroup_profile_counts_correctly():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.matrix_profiles = defaultdict(Counter)

    engine.occupation_meta = {
        "occ_1": {"label": "Software developer", "isco_group": "C2", "nace_code": "J62"},
        "occ_2": {"label": "Data analyst", "isco_group": "C2", "nace_code": "J62"},
    }
    engine.occupation_group_labels = {
        "C2": "Professionals"
    }
    engine.esco_matrix_profiles = {
        ("Matrix 1.1", "http://data.europa.eu/esco/isco/C2"): {
            "occupation_group_label": "Professionals",
            "profile": {
                "group_x": 0.3,
                "group_y": 0.7
            }
        }
    }

    jobs = [
        {"occupation_id": "occ_1", "skills": ["skill_a"]},
        {"occupation_id": "occ_2", "skills": ["skill_b"]},
    ]

    matrix = sectoral.build_official_matrix_sector_skillgroup_profile(
        jobs=jobs,
        sector_level="isco_group",
        skill_group_level=1,
        occupation_level=1
    )

    assert matrix["Professionals"]["group_x"] == 0.6
    assert matrix["Professionals"]["group_y"] == 1.4

def test_summarize_official_matrix_sector_skillgroups_returns_sorted_groups():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.matrix_profiles = defaultdict(Counter)
    engine.matrix_profiles["ICT"]["group_a"] = 0.9
    engine.matrix_profiles["ICT"]["group_b"] = 0.1

    result = sectoral.summarize_official_matrix_sector_skillgroups(top_k=10)

    ict = result[0]
    assert ict["sector"] == "ICT"
    assert ict["top_groups"][0]["group_id"] == "group_a"
    assert ict["top_groups"][0]["frequency"] == 0.9

def test_compare_all_group_profiles_for_sector_returns_three_views():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skillgroup_observed = defaultdict(Counter)
    engine.sector_skillgroup_canonical = defaultdict(Counter)
    engine.matrix_profiles = defaultdict(Counter)

    engine.sector_skillgroup_observed["ICT"]["obs_group"] = 3
    engine.sector_skillgroup_canonical["ICT"]["can_group"] = 2
    engine.matrix_profiles["ICT"]["off_group"] = 1.5

    result = sectoral.compare_all_group_profiles_for_sector("ICT", top_k=10)

    assert result["sector"] == "ICT"
    assert result["observed_groups"]["top_groups"][0]["group_id"] == "obs_group"
    assert result["canonical_groups"]["top_groups"][0]["group_id"] == "can_group"
    assert result["official_matrix_groups"]["top_groups"][0]["group_id"] == "off_group"

# ==========================================
# 13. UNIFIED SECTORAL INTELLIGENCE
# ==========================================

def test_build_single_sector_intelligence_returns_all_sections():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.skill_map = {
        "skill_a": {"label": "Python", "is_green": False, "is_digital": True},
        "skill_b": {"label": "SQL", "is_green": False, "is_digital": True},
    }

    engine.sector_skill_observed = defaultdict(Counter)
    engine.sector_skill_canonical = defaultdict(Counter)
    engine.sector_skillgroup_observed = defaultdict(Counter)
    engine.sector_skillgroup_canonical = defaultdict(Counter)
    engine.matrix_profiles = defaultdict(Counter)

    engine.sector_skill_observed["ICT"]["skill_a"] = 3
    engine.sector_skill_canonical["ICT"]["skill_b"] = 2
    engine.sector_skillgroup_observed["ICT"]["S5.1"] = 3
    engine.sector_skillgroup_canonical["ICT"]["S2.4"] = 2
    engine.matrix_profiles["ICT"]["S1"] = 1.5

    result = sectoral.build_single_sector_intelligence(
        sector_name="ICT",
        resolve_labels=True,
        top_k_skills=10,
        top_k_groups=10
    )

    assert result["sector"] == "ICT"
    assert "observed_skills" in result
    assert "canonical_skills" in result
    assert "observed_groups" in result
    assert "canonical_groups" in result
    assert "matrix_groups" in result

    assert result["observed_skills"]["top_skills"][0]["skill_id"] == "skill_a"
    assert result["canonical_skills"]["top_skills"][0]["skill_id"] == "skill_b"
    assert result["observed_groups"]["top_groups"][0]["group_id"] == "S5.1"
    assert result["canonical_groups"]["top_groups"][0]["group_id"] == "S2.4"
    assert result["matrix_groups"]["top_groups"][0]["group_id"] == "S1"


def test_build_sectoral_intelligence_from_jobs_builds_all_layers():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)

    engine.occupation_meta = {
        "occ_1": {"label": "Software developer", "isco_group": "C2", "nace_code": "J62"},
    }
    engine.occupation_group_labels = {
        "C2": "C2"
    }

    engine.occ_skill_relations = defaultdict(set)
    engine.occ_skill_relations["occ_1"] = {"skill_a", "skill_b"}

    engine.skill_map = {
        "skill_a": {"label": "Python", "is_green": False, "is_digital": True},
        "skill_b": {"label": "SQL", "is_green": False, "is_digital": True},
        "skill_obs": {"label": "Docker", "is_green": False, "is_digital": True},
    }

    engine.skill_hierarchy = {
        "skill_a": {"level_1": "S1", "level_2": "S1.1", "level_3": "S1.1.1"},
        "skill_b": {"level_1": "S2", "level_2": "S2.2", "level_3": "S2.2.1"},
        "skill_obs": {"level_1": "S3", "level_2": "S3.1", "level_3": "S3.1.1"},
    }

    engine.esco_matrix_profiles = {
        ("Matrix 1.1", "http://data.europa.eu/esco/isco/C2"): {
            "occupation_group_label": "Professionals",
            "profile": {
                "S1": 0.4,
                "S2": 0.6
            }
        }
    }

    jobs = [
        {"occupation_id": "occ_1", "skills": ["skill_obs"]},
        {"occupation_id": "occ_1", "skills": ["skill_obs", "skill_a"]},
    ]

    result = sectoral.build_sectoral_intelligence(
        jobs=jobs,
        sector_level="isco_group",
        skill_group_level=1,
        occupation_level=1,
        resolve_labels=True,
        top_k_skills=10,
        top_k_groups=10,
        reset=True
    )

    assert len(result) == 1
    sector = result[0]

    assert sector["sector"] == "C2"

    # observed skills
    assert sector["observed_skills"]["total_skill_mentions"] == 3
    assert sector["observed_skills"]["top_skills"][0]["label"] == "Docker"

    # canonical skills
    assert sector["canonical_skills"]["unique_skills"] == 2

    # groups
    assert len(sector["observed_groups"]["top_groups"]) > 0
    assert len(sector["canonical_groups"]["top_groups"]) > 0
    assert len(sector["matrix_groups"]["top_groups"]) > 0

# ==========================================
# 14. MATRIX / SCHEMA CONTRACT / EDGE CASES
# ==========================================

def test_get_occupation_group_id_for_matrix_accepts_numeric_isco_group():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    engine.occupation_meta = {
        "occ_1": {
            "label": "Numerical ISCO occupation",
            "isco_group": "2654",
            "nace_code": "J59"
        }
    }

    assert occupations.get_occupation_group_id_for_matrix("occ_1", occupation_level=1) == "C2"
    assert occupations.get_occupation_group_id_for_matrix("occ_1", occupation_level=2) == "C26"
    assert occupations.get_occupation_group_id_for_matrix("occ_1", occupation_level=3) == "C265"
    assert occupations.get_occupation_group_id_for_matrix("occ_1", occupation_level=4) == "C2654"


def test_get_official_esco_profile_for_occupation_accepts_numeric_isco_group():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    engine.occupation_meta = {
        "occ_1": {
            "label": "Numerical ISCO occupation",
            "isco_group": "2654",
            "nace_code": "J59"
        }
    }
    engine.esco_matrix_profiles = {
        ("Matrix 1.1", "http://data.europa.eu/esco/isco/C2"): {
            "occupation_group_label": "Professionals",
            "profile": {"S1": 0.8}
        }
    }

    result = occupations.get_official_esco_profile_for_occupation(
        "occ_1",
        skill_group_level=1,
        occupation_level=1
    )

    assert result is not None
    assert result["occupation_group_id"] == "http://data.europa.eu/esco/isco/C2"
    assert result["profile"]["S1"] == 0.8


def test_build_official_matrix_sector_skillgroup_profile_uses_sector_label_key():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.matrix_profiles = defaultdict(Counter)

    engine.occupation_meta = {
        "occ_1": {"label": "Software developer", "isco_group": "C2", "nace_code": "J62"},
        "occ_2": {"label": "Data analyst", "isco_group": "C2", "nace_code": "J62"},
    }
    engine.occupation_group_labels = {
        "C2": "Professionals"
    }
    engine.esco_matrix_profiles = {
        ("Matrix 1.1", "http://data.europa.eu/esco/isco/C2"): {
            "occupation_group_label": "Professionals",
            "profile": {
                "group_x": 0.3,
                "group_y": 0.7
            }
        }
    }

    jobs = [
        {"occupation_id": "occ_1", "skills": ["skill_a"]},
        {"occupation_id": "occ_2", "skills": ["skill_b"]},
    ]

    matrix = sectoral.build_official_matrix_sector_skillgroup_profile(
        jobs=jobs,
        sector_level="isco_group",
        skill_group_level=1,
        occupation_level=1
    )

    assert "Professionals" in matrix
    assert "C2" not in matrix
    assert matrix["Professionals"]["group_x"] == 0.6
    assert matrix["Professionals"]["group_y"] == 1.4


def test_get_skill_group_label_resolves_short_code_and_uri():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.skill_group_labels = {
        "S4.8": "working with computers",
        "http://data.europa.eu/esco/skill-group/S4.8": "working with computers",
    }

    assert sectoral.get_skill_group_label("S4.8") == "working with computers"
    assert sectoral.get_skill_group_label("http://data.europa.eu/esco/skill-group/S4.8") == "working with computers"


def test_read_group_counter_includes_group_label():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.skill_group_labels = {
        "S1": "communication",
        "S2": "information skills",
    }

    counter = Counter({"S1": 3, "S2": 1})
    result = sectoral._read_group_counter(counter, top_k=10)

    assert result["total_mentions"] == 4
    assert result["unique_groups"] == 2
    assert result["top_groups"][0]["group_id"] == "S1"
    assert result["top_groups"][0]["group_label"] == "communication"
    assert result["top_groups"][0]["frequency"] == 0.75


def test_get_official_matrix_groups_for_sector_returns_group_labels():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.matrix_profiles = defaultdict(Counter)
    engine.skill_group_labels = {
        "S1": "communication",
        "S2": "information skills",
    }

    engine.matrix_profiles["ICT"]["S1"] = 0.8
    engine.matrix_profiles["ICT"]["S2"] = 0.2

    result = sectoral.get_official_matrix_groups_for_sector("ICT", top_k=10)

    assert result["sector"] == "ICT"
    assert result["total_group_mentions"] == 1.0
    assert result["unique_groups"] == 2
    assert result["top_groups"][0]["group_id"] == "S1"
    assert result["top_groups"][0]["group_label"] == "communication"


def test_compare_all_group_profiles_for_sector_returns_group_labels_in_all_views():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.skill_group_labels = {
        "S1": "communication",
        "S2": "information skills",
        "S3": "management",
    }

    engine.sector_skillgroup_observed = defaultdict(Counter)
    engine.sector_skillgroup_canonical = defaultdict(Counter)
    engine.matrix_profiles = defaultdict(Counter)

    engine.sector_skillgroup_observed["ICT"]["S1"] = 3
    engine.sector_skillgroup_canonical["ICT"]["S2"] = 2
    engine.matrix_profiles["ICT"]["S3"] = 1.5

    result = sectoral.compare_all_group_profiles_for_sector("ICT", top_k=10)

    assert result["observed_groups"]["top_groups"][0]["group_label"] == "communication"
    assert result["canonical_groups"]["top_groups"][0]["group_label"] == "information skills"
    assert result["official_matrix_groups"]["top_groups"][0]["group_label"] == "management"


def test_build_single_sector_intelligence_contains_sector_label_and_matrix_groups():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.occupation_group_labels = {"ICT": "Information and communication technologies"}
    engine.skill_map = {
        "skill_a": {"label": "Python", "is_green": False, "is_digital": True},
        "skill_b": {"label": "SQL", "is_green": False, "is_digital": True},
    }

    engine.sector_skill_observed = defaultdict(Counter)
    engine.sector_skill_canonical = defaultdict(Counter)
    engine.sector_skillgroup_observed = defaultdict(Counter)
    engine.sector_skillgroup_canonical = defaultdict(Counter)
    engine.matrix_profiles = defaultdict(Counter)

    engine.sector_skill_observed["ICT"]["skill_a"] = 3
    engine.sector_skill_canonical["ICT"]["skill_b"] = 2
    engine.sector_skillgroup_observed["ICT"]["S5.1"] = 3
    engine.sector_skillgroup_canonical["ICT"]["S2.4"] = 2
    engine.matrix_profiles["ICT"]["S1"] = 1.5

    result = sectoral.build_single_sector_intelligence(
        sector_name="ICT",
        resolve_labels=True,
        top_k_skills=10,
        top_k_groups=10
    )

    assert result["sector"] == "ICT"
    assert "sector_label" in result
    assert "matrix_groups" in result


@pytest.mark.integration
def test_endpoint_analyze_skills_sectoral_contract_with_matrix_groups():
    form_data = {
        "keywords": ["developer"],
        "min_date": "2024-01-01",
        "max_date": "2024-01-10",
        "include_sectoral": True,
        "skill_group_level": 1,
        "occupation_level": 1,
    }

    fake_jobs = [
        {
            "occupation_id": "occ_1",
            "skills": ["skill_obs"],
            "upload_date": "2024-01-02",
        },
        {
            "occupation_id": "occ_1",
            "skills": ["skill_obs", "skill_a"],
            "upload_date": "2024-01-08",
        },
    ]

    with patch.object(tracker, "fetch_all_jobs", new_callable=AsyncMock) as m_fetch, \
         patch.object(tracker, "fetch_skill_names", new_callable=AsyncMock) as m_fetch_skills, \
         patch.object(tracker, "fetch_occupation_labels", new_callable=AsyncMock) as m_fetch_occ:

        m_fetch.return_value = fake_jobs
        m_fetch_skills.return_value = None
        m_fetch_occ.return_value = None

        engine.occupation_meta = {
            "occ_1": {"label": "Software developer", "isco_group": "C2", "nace_code": "J62"},
        }
        engine.occupation_group_labels = {"C2": "C2"}
        engine.occ_skill_relations = defaultdict(set)
        engine.occ_skill_relations["occ_1"] = {"skill_a", "skill_b"}
        engine.skill_map = {
            "skill_a": {"label": "Python", "is_green": False, "is_digital": True},
            "skill_b": {"label": "SQL", "is_green": False, "is_digital": True},
            "skill_obs": {"label": "Docker", "is_green": False, "is_digital": True},
        }
        engine.skill_hierarchy = {
            "skill_a": {"level_1": "S1", "level_2": "S1.1", "level_3": "S1.1.1"},
            "skill_b": {"level_1": "S2", "level_2": "S2.2", "level_3": "S2.2.1"},
            "skill_obs": {"level_1": "S3", "level_2": "S3.1", "level_3": "S3.1.1"},
        }
        engine.esco_matrix_profiles = {
            ("Matrix 1.1", "http://data.europa.eu/esco/isco/C2"): {
                "occupation_group_label": "Professionals",
                "profile": {"S1": 0.4, "S2": 0.6}
            }
        }

        response = client.post("/projector/analyze-skills", data=form_data)
        assert response.status_code == 200

        data = response.json()
        assert "sectoral" in data["insights"]
        assert isinstance(data["insights"]["sectoral"], list)
        assert len(data["insights"]["sectoral"]) == 1

        sector = data["insights"]["sectoral"][0]
        assert "sector" in sector
        assert "sector_label" in sector
        assert "observed_skills" in sector
        assert "canonical_skills" in sector
        assert "observed_groups" in sector
        assert "canonical_groups" in sector
        assert "matrix_groups" in sector


@pytest.mark.integration
def test_endpoint_analyze_skills_sectoral_top_groups_include_group_label():
    form_data = {
        "keywords": ["developer"],
        "min_date": "2024-01-01",
        "max_date": "2024-01-10",
        "include_sectoral": True,
        "skill_group_level": 1,
        "occupation_level": 1,
    }

    fake_jobs = [
        {
            "occupation_id": "occ_1",
            "skills": ["skill_obs"],
            "upload_date": "2024-01-02",
        }
    ]

    with patch.object(tracker, "fetch_all_jobs", new_callable=AsyncMock) as m_fetch, \
         patch.object(tracker, "fetch_skill_names", new_callable=AsyncMock) as m_fetch_skills, \
         patch.object(tracker, "fetch_occupation_labels", new_callable=AsyncMock) as m_fetch_occ:

        m_fetch.return_value = fake_jobs
        m_fetch_skills.return_value = None
        m_fetch_occ.return_value = None

        engine.occupation_meta = {
            "occ_1": {"label": "Software developer", "isco_group": "C2", "nace_code": "J62"},
        }
        engine.occupation_group_labels = {"C2": "C2"}
        engine.occ_skill_relations = defaultdict(set)
        engine.occ_skill_relations["occ_1"] = {"skill_a"}
        engine.skill_map = {
            "skill_a": {"label": "Python", "is_green": False, "is_digital": True},
            "skill_obs": {"label": "Docker", "is_green": False, "is_digital": True},
        }
        engine.skill_hierarchy = {
            "skill_a": {"level_1": "S1", "level_2": "S1.1", "level_3": "S1.1.1"},
            "skill_obs": {"level_1": "S3", "level_2": "S3.1", "level_3": "S3.1.1"},
        }
        engine.skill_group_labels = {
            "S1": "communication",
            "S3": "digital content creation",
        }
        engine.esco_matrix_profiles = {
            ("Matrix 1.1", "http://data.europa.eu/esco/isco/C2"): {
                "occupation_group_label": "Professionals",
                "profile": {"S1": 1.0}
            }
        }

        response = client.post("/projector/analyze-skills", data=form_data)
        assert response.status_code == 200

        data = response.json()
        sector = data["insights"]["sectoral"][0]

        assert "group_label" in sector["observed_groups"]["top_groups"][0]
        assert "group_label" in sector["canonical_groups"]["top_groups"][0]
        assert "group_label" in sector["matrix_groups"]["top_groups"][0]


@pytest.mark.integration
def test_endpoint_analyze_skills_sectoral_supports_nace_hierarchy_selection():
    form_data = {
        "keywords": ["developer"],
        "min_date": "2024-01-01",
        "max_date": "2024-01-10",
        "include_sectoral": True,
        "sector_system": "nace",
        "sector_level": "nace_class",
        "skill_group_level": 1,
        "occupation_level": 1,
    }

    fake_jobs = [
        {
            "occupation_id": "occ_1",
            "skills": ["skill_obs"],
            "upload_date": "2024-01-02",
        }
    ]

    with patch.object(tracker, "fetch_all_jobs", new_callable=AsyncMock) as m_fetch, \
         patch.object(tracker, "fetch_skill_names", new_callable=AsyncMock) as m_fetch_skills, \
         patch.object(tracker, "fetch_occupation_labels", new_callable=AsyncMock) as m_fetch_occ:

        m_fetch.return_value = fake_jobs
        m_fetch_skills.return_value = None
        m_fetch_occ.return_value = None

        engine.occupation_meta = {
            "occ_1": {"label": "Software developer", "isco_group": "C2", "nace_code": "C10.11"},
        }
        engine.occupation_group_labels = {"C2": "C2"}
        engine.occ_skill_relations = defaultdict(set)
        engine.occ_skill_relations["occ_1"] = {"skill_a"}
        engine.skill_map = {
            "skill_a": {"label": "Python", "is_green": False, "is_digital": True},
            "skill_obs": {"label": "Docker", "is_green": False, "is_digital": True},
        }
        engine.skill_hierarchy = {
            "skill_a": {"level_1": "S1", "level_2": "S1.1", "level_3": "S1.1.1"},
            "skill_obs": {"level_1": "S3", "level_2": "S3.1", "level_3": "S3.1.1"},
        }
        engine.esco_matrix_profiles = {
            ("Matrix 1.1", "http://data.europa.eu/esco/isco/C2"): {
                "occupation_group_label": "Professionals",
                "profile": {"S1": 1.0}
            }
        }

        response = client.post("/projector/analyze-skills", data=form_data)
        assert response.status_code == 200

        data = response.json()
        sector = data["insights"]["sectoral"][0]
        assert sector["sector"] == "C1011"


@pytest.mark.integration
def test_endpoint_analyze_skills_sectoral_uses_isco_when_sector_system_is_isco():
    form_data = {
        "keywords": ["developer"],
        "min_date": "2024-01-01",
        "max_date": "2024-01-10",
        "include_sectoral": True,
        "sector_system": "isco",
        "sector_level": "nace_class",
        "skill_group_level": 1,
        "occupation_level": 1,
    }

    fake_jobs = [
        {
            "occupation_id": "occ_1",
            "skills": ["skill_obs"],
            "upload_date": "2024-01-02",
        }
    ]

    with patch.object(tracker, "fetch_all_jobs", new_callable=AsyncMock) as m_fetch, \
         patch.object(tracker, "fetch_skill_names", new_callable=AsyncMock) as m_fetch_skills, \
         patch.object(tracker, "fetch_occupation_labels", new_callable=AsyncMock) as m_fetch_occ:

        m_fetch.return_value = fake_jobs
        m_fetch_skills.return_value = None
        m_fetch_occ.return_value = None

        engine.occupation_meta = {
            "occ_1": {"label": "Software developer", "isco_group": "C2", "nace_code": "C10.11"},
        }
        engine.occupation_group_labels = {"C2": "C2"}
        engine.occ_skill_relations = defaultdict(set)
        engine.occ_skill_relations["occ_1"] = {"skill_a"}
        engine.skill_map = {
            "skill_a": {"label": "Python", "is_green": False, "is_digital": True},
            "skill_obs": {"label": "Docker", "is_green": False, "is_digital": True},
        }
        engine.skill_hierarchy = {
            "skill_a": {"level_1": "S1", "level_2": "S1.1", "level_3": "S1.1.1"},
            "skill_obs": {"level_1": "S3", "level_2": "S3.1", "level_3": "S3.1.1"},
        }
        engine.esco_matrix_profiles = {
            ("Matrix 1.1", "http://data.europa.eu/esco/isco/C2"): {
                "occupation_group_label": "Professionals",
                "profile": {"S1": 1.0}
            }
        }

        response = client.post("/projector/analyze-skills", data=form_data)
        assert response.status_code == 200

        data = response.json()
        sector = data["insights"]["sectoral"][0]
        assert sector["sector"] == "C2"


def test_build_observed_occupation_skill_matrix_accumulates_when_reset_false():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.occ_skill_observed = defaultdict(Counter)

    jobs_a = [{"occupation_id": "occ_1", "skills": ["skill_a"]}]
    jobs_b = [{"occupation_id": "occ_1", "skills": ["skill_a", "skill_b"]}]

    sectoral.build_observed_occupation_skill_matrix(jobs_a, reset=True)
    sectoral.build_observed_occupation_skill_matrix(jobs_b, reset=False)

    assert engine.occ_skill_observed["occ_1"]["skill_a"] == 2
    assert engine.occ_skill_observed["occ_1"]["skill_b"] == 1


def test_build_official_matrix_sector_skillgroup_profile_accumulates_when_reset_false():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.matrix_profiles = defaultdict(Counter)

    engine.occupation_meta = {
        "occ_1": {"label": "Software developer", "isco_group": "C2", "nace_code": "J62"},
    }
    engine.occupation_group_labels = {"C2": "Professionals"}
    engine.esco_matrix_profiles = {
        ("Matrix 1.1", "http://data.europa.eu/esco/isco/C2"): {
            "occupation_group_label": "Professionals",
            "profile": {"group_x": 0.3}
        }
    }

    jobs = [{"occupation_id": "occ_1", "skills": ["skill_a"]}]

    sectoral.build_official_matrix_sector_skillgroup_profile(
        jobs=jobs,
        sector_level="isco_group",
        skill_group_level=1,
        occupation_level=1,
        reset=True
    )
    sectoral.build_official_matrix_sector_skillgroup_profile(
        jobs=jobs,
        sector_level="isco_group",
        skill_group_level=1,
        occupation_level=1,
        reset=False
    )

    assert engine.matrix_profiles["Professionals"]["group_x"] == 0.6


def test_build_sectoral_intelligence_and_single_sector_are_consistent():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)

    engine.occupation_meta = {
        "occ_1": {"label": "Software developer", "isco_group": "C2", "nace_code": "J62"},
    }
    engine.occupation_group_labels = {"C2": "C2"}
    engine.occ_skill_relations = defaultdict(set)
    engine.occ_skill_relations["occ_1"] = {"skill_a", "skill_b"}
    engine.skill_map = {
        "skill_a": {"label": "Python", "is_green": False, "is_digital": True},
        "skill_b": {"label": "SQL", "is_green": False, "is_digital": True},
        "skill_obs": {"label": "Docker", "is_green": False, "is_digital": True},
    }
    engine.skill_hierarchy = {
        "skill_a": {"level_1": "S1", "level_2": "S1.1", "level_3": "S1.1.1"},
        "skill_b": {"level_1": "S2", "level_2": "S2.2", "level_3": "S2.2.1"},
        "skill_obs": {"level_1": "S3", "level_2": "S3.1", "level_3": "S3.1.1"},
    }
    engine.esco_matrix_profiles = {
        ("Matrix 1.1", "http://data.europa.eu/esco/isco/C2"): {
            "occupation_group_label": "Professionals",
            "profile": {"S1": 0.4, "S2": 0.6}
        }
    }

    jobs = [
        {"occupation_id": "occ_1", "skills": ["skill_obs"]},
        {"occupation_id": "occ_1", "skills": ["skill_obs", "skill_a"]},
    ]

    result = sectoral.build_sectoral_intelligence(
        jobs=jobs,
        sector_level="isco_group",
        skill_group_level=1,
        occupation_level=1,
        resolve_labels=True,
        top_k_skills=10,
        top_k_groups=10,
        reset=True
    )

    assert len(result) == 1
    sector = result[0]
    single = sectoral.build_single_sector_intelligence(
        sector_name=sector["sector"],
        resolve_labels=True,
        top_k_skills=10,
        top_k_groups=10
    )

    assert single["sector"] == sector["sector"]
    assert single["observed_skills"]["total_skill_mentions"] == sector["observed_skills"]["total_skill_mentions"]
    assert single["canonical_skills"]["unique_skills"] == sector["canonical_skills"]["unique_skills"]
    assert single["matrix_groups"]["unique_groups"] == sector["matrix_groups"]["unique_groups"]
