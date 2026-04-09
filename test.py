from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from main import app, engine  # Assicurati che il tuo file principale si chiami main.py

# Inizializziamo il client di test
client = TestClient(app)


# ==========================================
# TEST UNITARI (Logica interna del Motore)
# ==========================================

from unittest.mock import patch


# ==========================================
# TEST UNITARI (Logica interna del Motore)
# ==========================================
def test_geo_dimension_presence():
    response = client.post("/projector/analyze-skills", data={"keywords": ["software"]})
    data = response.json()
    assert "geo_breakdown" in data["dimension_summary"]
    assert len(data["dimension_summary"]["geo_breakdown"]) > 0

def test_engine_decompose_and_count_skills():
    """
    Test Unitario: Verifica conteggio e TRADUZIONE delle competenze.
    Usa 'patch' per non contaminare gli altri test!
    """
    mock_raw_jobs = [
        {"id": 1, "skills": ["http://esco/skill/A", "http://esco/skill/B"]},
        {"id": 2, "skills": ["http://esco/skill/A"]},
        {"id": 3, "skills": ["http://esco/skill/C", "http://esco/skill/B", "http://esco/skill/A"]},
        {"id": 4, "skills": []},
        {"id": 5, "skills": ["", "http://esco/skill/A"]}
    ]

    # Usiamo il context manager "with patch.object" così il mock svanisce a fine test
    with patch.object(engine, 'fetch_skill_names') as mock_fetch:
        def mock_side_effect(uris):
            engine.skill_map["http://esco/skill/A"] = "Sviluppo Java"
            engine.skill_map["http://esco/skill/B"] = "Sviluppo Python"

        mock_fetch.side_effect = mock_side_effect

        # Esecuzione
        result = engine.decompose_and_count_skills(mock_raw_jobs)

        # Asserzioni
        assert result["total_skills_extracted"] == 7
        assert result["unique_skills"] == 3

        ranking = result["ranking"]

        assert ranking[0]["skill_id"] == "http://esco/skill/A"
        assert ranking[0]["name"] == "Sviluppo Java"

        assert ranking[1]["skill_id"] == "http://esco/skill/B"
        assert ranking[1]["name"] == "Sviluppo Python"

        assert ranking[2]["skill_id"] == "http://esco/skill/C"
        assert ranking[2]["name"] == "C"

        mock_fetch.assert_called_once()


# ==========================================
# TEST DI INTEGRAZIONE (Chiamate API Reali)
# ==========================================

@pytest.mark.integration
def test_collect_data_endpoint():
    """
    Test di Integrazione: Verifica che /collect-data chiami il Tracker API
    e restituisca la struttura corretta.
    """
    # Svuotiamo il token per forzare il login
    engine.token = None

    form_data = {
        "keywords": ["software"],
        "min_date": "2024-09-09",
        "max_date": "2024-09-09"
    }

    print("\n[Test] Invocazione /projector/collect-data...")
    response = client.post("/projector/collect-data", data=form_data)

    assert response.status_code == 200
    data = response.json()

    # Verifica della struttura della risposta
    assert data["status"] == "data_collected"
    assert "dimension_summary" in data
    assert "preview" in data

    # Verifica che i filtri logici siano stati applicati automaticamente dal tuo endpoint
    applied_filters = data["dimension_summary"]["filters_applied"]
    assert applied_filters["keywords_logic"] == "or"
    assert "software" in applied_filters["keywords"]

    # Verifichiamo che abbia trovato dei record
    assert data["dimension_summary"]["total_records"] > 0


@pytest.mark.integration
def test_analyze_skills_endpoint_pagination():
    """
    Test di Integrazione: Verifica che /analyze-skills processi i dati
    e rispetti strettamente i parametri di paginazione forniti.
    """
    form_data = {
        "keywords": ["software"],
        "min_date": "2024-09-09",
        "max_date": "2024-09-09",
        "page": 1,
        "page_size": 3  # Chiediamo solo 3 risultati per testare la paginazione
    }

    print("\n[Test] Invocazione /projector/analyze-skills (Pagina 1)...")
    response = client.post("/projector/analyze-skills", data=form_data)

    assert response.status_code == 200
    data = response.json()

    # Verifica Struttura Base
    assert data["status"] == "analysis_completed"
    assert "insights" in data
    assert "pagination" in data

    # Verifica Paginazione
    assert data["pagination"]["current_page"] == 1
    assert data["pagination"]["page_size"] == 3
    assert data["pagination"]["total_unique_skills"] > 0

    ranking = data["insights"]["ranking"]
    assert len(ranking) <= 3  # La lunghezza dell'array non deve superare page_size

    # Test della Pagina 2 (per verificare lo slicing)
    if data["pagination"]["total_pages"] > 1:
        form_data["page"] = 2
        print("\n[Test] Invocazione /projector/analyze-skills (Pagina 2)...")
        response_page_2 = client.post("/projector/analyze-skills", data=form_data)
        data_page_2 = response_page_2.json()

        ranking_page_2 = data_page_2["insights"]["ranking"]

        # Le prime skill della pagina 2 devono essere diverse da quelle della pagina 1
        assert ranking[0]["skill_id"] != ranking_page_2[0]["skill_id"]


@pytest.mark.integration
def test_analyze_skills_endpoint_pagination_and_translation():
    """
    Test di Integrazione: Verifica paginazione e che le traduzioni ESCO
    siano REALI e non dei semplici ID di fallback.
    """
    engine.token = None
    engine.skill_map = {}  # Svuotiamo la cache per forzare la chiamata all'API /skills

    form_data = {
        "keywords": ["software"],
        "min_date": "2024-09-09",
        "max_date": "2024-09-09",
        "page": 1,
        "page_size": 3
    }

    print("\n[Test] Invocazione /projector/analyze-skills (Pagina 1)...")
    response = client.post("/projector/analyze-skills", data=form_data)

    assert response.status_code == 200
    data = response.json()

    ranking = data["insights"]["ranking"]
    assert len(ranking) > 0, "Nessuna skill restituita dall'analisi!"
    assert len(ranking) <= 3

    # --- VERIFICA ROBUSTA DELLA TRADUZIONE ---
    first_skill = ranking[0]
    assert "name" in first_skill

    # Calcoliamo quale sarebbe la stringa di fallback (l'ID finale dell'URI)
    uri_parts = first_skill["skill_id"].split('/')
    fallback_string = uri_parts[-1]

    actual_name = first_skill["name"]

    # Il test DEVE FALLIRE se il nome restituito è uguale all'ID di fallback
    assert actual_name != fallback_string, (
        f"\n[ERRORE TRADUZIONE] Il motore non ha tradotto la skill! "
        f"Ha restituito il fallback: '{actual_name}' invece del vero nome."
    )

    print(f"\n[Successo Reale] Skill '{first_skill['skill_id']}' tradotta correttamente in: '{actual_name}'")


@pytest.mark.integration
def test_debug_single_skill_translation():
    """
    Test di Integrazione Mirato: Testa ESATTAMENTE l'URI che ha dato problemi
    per forzare l'API /skills e analizzare la risposta.
    """
    # 1. Puliamo lo stato del motore
    engine.token = None
    engine.skill_map = {}

    # 2. L'URI esatto della tua cURL
    test_uri = "http://data.europa.eu/esco/skill/d4789070-2ff7-4bbb-94ca-8bb1739826a9"
    expected_label = "authoring software"

    print("\n--- INIZIO TEST MIRATO TRADUZIONE ---")

    # 3. Chiamiamo DIRETTAMENTE il metodo del motore
    try:
        engine.fetch_skill_names([test_uri])
    except Exception as e:
        pytest.fail(f"Il metodo ha lanciato un'eccezione: {str(e)}")

    # 4. Debug in caso di fallimento
    if test_uri not in engine.skill_map:
        # Se arriviamo qui, l'API non ha mappato l'ID. Vogliamo sapere perché.
        print(f"\n[FALLIMENTO] La skill_map è vuota o non contiene l'URI.")
        print(f"Stato attuale della mappa: {engine.skill_map}")
        pytest.fail("Traduzione fallita: URI non inserito nella skill_map.")

    # 5. Asserzione finale
    actual_label = engine.skill_map[test_uri]
    print(f"\n[SUCCESSO] Valore trovato in mappa: '{actual_label}'")

    assert actual_label == expected_label, f"Mi aspettavo '{expected_label}', ma ho ottenuto '{actual_label}'"


def test_engine_calculate_trends():
    """

    Test Unitario: Verifica che il motore calcoli correttamente

    i trend tra due periodi temporali distinti.

    """

    # Dati del Periodo A (Passato)

    jobs_period_a = [

        {"id": 1, "skills": ["http://esco/skill/Java", "http://esco/skill/SQL"]},

        {"id": 2, "skills": ["http://esco/skill/Java"]}

    ]  # Java: 2, SQL: 1

    # Dati del Periodo B (Recente)

    jobs_period_b = [

        {"id": 3, "skills": ["http://esco/skill/Java", "http://esco/skill/Python"]},

        {"id": 4, "skills": ["http://esco/skill/Python"]},

        {"id": 5, "skills": ["http://esco/skill/Python"]}

    ]  # Python: 3, Java: 1, SQL: 0

    with patch.object(engine, 'fetch_skill_names') as mock_fetch:
        # Simuliamo la traduzione

        def mock_side_effect(uris):
            engine.skill_map["http://esco/skill/Java"] = "Java"

            engine.skill_map["http://esco/skill/Python"] = "Python"

            engine.skill_map["http://esco/skill/SQL"] = "SQL"

        mock_fetch.side_effect = mock_side_effect

        # Chiamiamo il NUOVO metodo che dobbiamo ancora creare

        trend_result = engine.calculate_trends(jobs_period_a, jobs_period_b)

        # Asserzioni Matematiche

        assert len(trend_result) == 3  # Java, SQL, Python

        # Python: 0 nel passato, 3 nel presente -> "New Entry"

        python_trend = next(s for s in trend_result if s["name"] == "Python")

        assert python_trend["trend_type"] == "emerging"

        assert python_trend["growth"] == "new_entry"

        # Java: 2 nel passato, 1 nel presente -> In calo (-50%)

        java_trend = next(s for s in trend_result if s["name"] == "Java")

        assert java_trend["trend_type"] == "declining"

        assert java_trend["growth"] == -50.0

        # SQL: 1 nel passato, 0 nel presente -> Scomparsa (-100%)

        sql_trend = next(s for s in trend_result if s["name"] == "SQL")

        assert sql_trend["trend_type"] == "declining"

        assert sql_trend["growth"] == -100.0


@pytest.mark.integration
def test_emerging_skills_endpoint_date_math():
    """
    Test di Integrazione: Verifica che l'endpoint calcoli i trend temporali,
    dividendo correttamente il periodo a metà e restituendo la struttura corretta.
    """
    # Per non appesantire le chiamate API durante i test,
    # analizziamo un periodo cortissimo di soli 4 giorni totali.
    form_data = {
        "keywords": ["developer"],
        "min_date": "2024-01-01",
        "max_date": "2024-01-04"
    }

    print("\n[Test] Invocazione /projector/emerging-skills...")
    response = client.post("/projector/emerging-skills", data=form_data)

    assert response.status_code == 200
    data = response.json()

    # 1. Verifica Struttura Base
    assert data["status"] == "trends_calculated"
    assert "insights" in data

    insights = data["insights"]
    assert "period_a" in insights
    assert "period_b" in insights
    assert "trends" in insights

    # 2. La Prova del Nove: La Matematica delle Date
    # Da 2024-01-01 a 2024-01-04 sono 3 giorni di differenza (delta).
    # Diviso 2 fa 1 (divisione intera).
    # Quindi il Periodo A deve finire il 02, e il Periodo B iniziare il 03.

    assert insights[
               "period_a"] == "2024-01-01 to 2024-01-02", f"Errore nel calcolo del Periodo A: {insights['period_a']}"
    assert insights[
               "period_b"] == "2024-01-03 to 2024-01-04", f"Errore nel calcolo del Periodo B: {insights['period_b']}"

    trends = insights["trends"]
    if trends:
        top_trend = trends[0]
        print(f"\n[Successo Trend] Trovate {len(trends)} skill in evoluzione.")
        print(
            f"[Esempio] {top_trend['name']} - Crescita: {top_trend['growth']}% (da {top_trend['frequency_past']} a {top_trend['frequency_recent']})")
    else:
        print("\n[Info] Il test è passato, ma non c'erano job per 'developer' in quei 4 giorni esatti.")