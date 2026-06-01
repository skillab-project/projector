import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import json
from requests import RequestException

# 1. Configurazione Pagina
st.set_page_config(page_title="SKILLAB Projector Intelligence", layout="wide")

# Inizializzazione Session State
if 'lang' not in st.session_state:
    st.session_state.lang = 'IT'

if 'all_data' not in st.session_state:
    st.session_state.all_data = None

if 'sectoral_data' not in st.session_state:
    st.session_state.sectoral_data = None

if 'sectoral_snapshot_data' not in st.session_state:
    st.session_state.sectoral_snapshot_data = None

if 'api_base_url' not in st.session_state:
    st.session_state.api_base_url = os.getenv("PROJECTOR_API_BASE_URL", "http://127.0.0.1:8000/projector")

def change_lang():
    if st.session_state.lang_choice == "Italiano":
        st.session_state.lang = 'IT'
    else:
        st.session_state.lang = 'EN'


translations = {
    'IT': {
        'title': "🚀 SKILLAB Projector: Intelligence Dashboard",
        'subtitle': "Analisi predittiva e monitoraggio in tempo reale dei Job Postings.",
        'filters_header': "Filtri di Ricerca",
        'keywords': "Keywords",
        'location': "Location Code (es. ITC4C)",
        'date_range': "Intervallo Temporale",
        'submit_general': "Lancia analisi generale",
        'submit_sectoral': "Lancia analisi settoriale",
        'sectoral_time_mode': "Finestra settoriale",
        'sector_filter': "Filtro settori (virgola)",
        'sectoral_data_source': "Sorgente dati settoriale",
        'sectoral_data_source_options': {
            "cache": "Cache statica",
            "live": "Live Tracker",
        },
        'sectoral_time_options': {
            "latest": "Ultimi 6 mesi",
            "selected_period": "Periodo selezionato",
            "year": "Snapshot anno",
            "comparison": "Confronto periodi",
        },
        'sectoral_snapshot_year': "Anno snapshot settoriale",
        'sectoral_snapshot_header': "Snapshot annuale settori",
        'sectoral_snapshot_help': "Vista aggregata annuale: una riga per settore Tracker con volume job, quota, skill più richieste e titoli più frequenti.",
        'sectoral_snapshot_table': "Overview settori",
        'sectoral_snapshot_detail': "Focus settore",
        'sectoral_job_share': "Quota job",
        'sectoral_top_skills': "Top skill settore",
        'sectoral_top_titles': "Top titoli settore",
        'technical_sectoral_detail': "Dettaglio tecnico sectoral intelligence",
        'sectoral_compare_a': "Periodo baseline",
        'sectoral_compare_b': "Periodo confronto",
        'sectoral_window': "Finestra settoriale",
        'sectoral_comparison': "Confronto settoriale",
        'submit': "Lancia Proiezione 🚀",
        'stop': "STOP ANALISI ⛔",
        'stop_toast': "Segnale di stop inviato!",
        'server_error': "Server non raggiungibile.",
        'server_timeout': "Il server ha impiegato troppo tempo a rispondere.",
        'server_http_error': "Il server ha risposto con errore.",
        'server_ok': "Backend raggiungibile.",
        'backend_url': "Backend URL",
        'backend_help': "Avvia FastAPI prima della dashboard. Esempio: `uvicorn app.main:app --reload`. Se Streamlit gira in container o su altra macchina, usa l'URL raggiungibile da Streamlit, non per forza 127.0.0.1.",
        'backend_timeout': "Timeout richiesta backend (secondi)",
        'check_backend': "Verifica backend",
        'tabs': ["📊 Analisi Competenze", "📈 Emerging Trends", "🗺️ Distribuzione Geografica", "🏭 Settori & Aziende"],
        'top_skills': "Top Skills più richieste",
        'jobs_analyzed': "Job Analizzati",
        'trends_header': "Emerging vs Declining Skills",
        'market_status': "Stato Mercato",
        'volume_var': "Variazione Volume Job",
        'delta_title': "Delta Percentuale Competenze",
        'new_entries': "🌟 New Entries (Comparse ora)",
        'geo_header': "Mappa Globale della Domanda",
        'map_title': "Intensità Job Postings per Nazione",
        'geo_detail': "Dettaglio Volumi",
        'no_geo': "Nessun dato geografico disponibile.",
        'jobs_emp_header': "Analisi Macro-Settori, Titles & Aziende",
        'top_titles': "Top Job Titles (Titoli Reali)",
        'jt_title': "Cosa scrivono le aziende negli annunci",
        'no_data': "Dati non disponibili.",
        'top_emp': "Top Employers (Chi assume?)",
        'active_emp': "Aziende più attive",
        'top_sectors': "Distribuzione Settoriale (Intelligence)",
        'sector_title': "Domanda per Macro-Settore",
        'welcome': "Configura i filtri a sinistra e clicca su 'Lancia Proiezione' per interrogare il Projector.",
        'intelligence_label': "Dettaglio Intelligence (Phase 1)",
        'sectoral_header': "🧠 Sectoral Intelligence",
        'sector_selector': "Seleziona settore",
        'observed_skills': "Observed Skills",
        'observed_groups': "Observed Skill Groups",
        'no_sectoral': "Dati di Sectoral Intelligence non disponibili.",
        'total_mentions': "Total mentions",
        'unique_items': "Unique items",
        'agg_level': "Fonte settori",
        'categories_found': "Categorie trovate",
        'loading': "Intelligence in caricamento...",
        'demo_settings': "Impostazioni demo",
        'demo_mode': "Abilita dati NUTS demo",
        'demo_mode_help': "Attiva l'iniezione di codici NUTS fittizi per testare la gerarchia del Task 3.5",
        'regional_task_header': "🌍 Intelligence regionale e proiezioni NUTS (Task 3.5)",
        'regional_strategy': "Seleziona granularità della proiezione:",
        'regional_strategy_help': "Scegli il livello di scomposizione dei dati come richiesto dal Task 3.5",
        'regional_options': ["Location Codes (Raw)", "NUTS 1 (Macro)", "NUTS 2 (Regioni)", "NUTS 3 (Province)"],
        'regional_select_area': "Seleziona area per analisi granulare",
        'market_share': "Quota di mercato",
        'key_skills_in': "Competenze chiave in",
        'workforce_profile': "Profilo della forza lavoro",
        'skill_label': "Competenza",
        'job_post_label': "Job Post",
        'specialization_label': "Specializzazione (LQ)",
        'regional_insight': "L'area **{target_code}** mostra una domanda focalizzata. Le barre più verdi indicano competenze con alta specializzazione regionale.",
        'regional_no_level': "Dati non disponibili per il livello {strategy}.",
        'regional_run_first': "Esegui una proiezione per visualizzare l'analisi regionale.",
        'observed_skills_per_sector': "Skill osservate per settore",
        'sector_metrics': "Metriche settore",
        'skill_transversality': "Transversalità skill (NACE)",
        'skill_coverage_unique': "Copertura skill (uniche)",
        'top10_skill_dominance': "Dominanza top-10 skill",
    },
    'EN': {
        'title': "🚀 SKILLAB Projector: Intelligence Dashboard",
        'subtitle': "Predictive analysis and real-time monitoring of Job Postings.",
        'filters_header': "Search Filters",
        'keywords': "Keywords",
        'location': "Location Code (e.g. ITC4C)",
        'date_range': "Time Range",
        'submit_general': "Run general analysis",
        'submit_sectoral': "Run sectoral analysis",
        'sectoral_time_mode': "Sectoral window",
        'sector_filter': "Sector filter (comma-separated)",
        'sectoral_data_source': "Sectoral data source",
        'sectoral_data_source_options': {
            "cache": "Static cache",
            "live": "Live Tracker",
        },
        'sectoral_time_options': {
            "latest": "Last 6 months",
            "selected_period": "Selected period",
            "year": "Year snapshot",
            "comparison": "Period comparison",
        },
        'sectoral_snapshot_year': "Sectoral snapshot year",
        'sectoral_snapshot_header': "Yearly sector snapshot",
        'sectoral_snapshot_help': "Aggregated yearly view: one row per Tracker sector with job volume, share, top requested skills, and most frequent job titles.",
        'sectoral_snapshot_table': "Sector overview",
        'sectoral_snapshot_detail': "Sector focus",
        'sectoral_job_share': "Job share",
        'sectoral_top_skills': "Top sector skills",
        'sectoral_top_titles': "Top sector job titles",
        'technical_sectoral_detail': "Technical sectoral intelligence detail",
        'sectoral_compare_a': "Baseline period",
        'sectoral_compare_b': "Comparison period",
        'sectoral_window': "Sectoral window",
        'sectoral_comparison': "Sector comparison",
        'submit': "Launch Projection 🚀",
        'stop': "STOP ANALYSIS ⛔",
        'stop_toast': "Stop signal sent!",
        'server_error': "Server unreachable.",
        'server_timeout': "Server took too long to respond.",
        'server_http_error': "Server returned an error.",
        'server_ok': "Backend reachable.",
        'backend_url': "Backend URL",
        'backend_help': "Start FastAPI before the dashboard. Example: `uvicorn app.main:app --reload`. If Streamlit runs in a container or another machine, use the URL reachable from Streamlit, not necessarily 127.0.0.1.",
        'backend_timeout': "Backend request timeout (seconds)",
        'check_backend': "Check backend",
        'tabs': ["📊 Skill Analysis", "📈 Emerging Trends", "🗺️ Geographic Distribution", "🏭 Sectors & Employers"],
        'top_skills': "Top Requested Skills",
        'jobs_analyzed': "Jobs Analyzed",
        'trends_header': "Emerging vs Declining Skills",
        'market_status': "Market Status",
        'volume_var': "Job Volume Change",
        'delta_title': "Skills Percentage Delta",
        'new_entries': "🌟 New Entries (Just appeared)",
        'geo_header': "Global Demand Map",
        'map_title': "Job Postings Intensity by Country",
        'geo_detail': "Volume Details",
        'no_geo': "No geographic data available.",
        'jobs_emp_header': "Macro-Sectors, Job Titles & Employer Analysis",
        'top_titles': "Top Job Titles (Actual Titles)",
        'jt_title': "What companies write in ads",
        'no_data': "Data not available.",
        'top_emp': "Top Employers (Who is hiring?)",
        'active_emp': "Most active companies",
        'top_sectors': "Sectoral Distribution (Intelligence)",
        'sector_title': "Demand by Macro-Sector",
        'welcome': "Configure the filters on the left and click 'Launch Projection' to query the Projector.",
        'intelligence_label': "Intelligence Detail (Phase 1)",
        'sectoral_header': "🧠 Sectoral Intelligence",
        'sector_selector': "Select sector",
        'observed_skills': "Observed Skills",
        'observed_groups': "Observed Skill Groups",
        'no_sectoral': "Sectoral Intelligence data not available.",
        'total_mentions': "Total mentions",
        'unique_items': "Unique items",
        'agg_level': "Sector source",
        'categories_found': "Categories found",
        'loading': "Intelligence is loading...",
        'demo_settings': "Demo Settings",
        'demo_mode': "Enable NUTS Demo Data",
        'demo_mode_help': "Injects synthetic NUTS codes to test Task 3.5 hierarchy.",
        'regional_task_header': "🌍 Regional Intelligence & NUTS Projections (Task 3.5)",
        'regional_strategy': "Select projection granularity:",
        'regional_strategy_help': "Choose the data decomposition level required by Task 3.5.",
        'regional_options': ["Location Codes (Raw)", "NUTS 1 (Macro)", "NUTS 2 (Regions)", "NUTS 3 (Provinces)"],
        'regional_select_area': "Select area for granular analysis",
        'market_share': "Market Share",
        'key_skills_in': "Key skills in",
        'workforce_profile': "Workforce profile",
        'skill_label': "Skill",
        'job_post_label': "Job posts",
        'specialization_label': "Specialization (LQ)",
        'regional_insight': "Area **{target_code}** shows focused demand. Greener bars indicate skills with high regional specialization.",
        'regional_no_level': "Data not available for level {strategy}.",
        'regional_run_first': "Run a projection to view regional analysis.",
        'observed_skills_per_sector': "Observed Skills per Sector",
        'sector_metrics': "Sector Metrics",
        'skill_transversality': "Skill Transversality (NACE)",
        'skill_coverage_unique': "Skill coverage (unique)",
        'top10_skill_dominance': "Top-10 skill dominance",
    }
}

T = translations[st.session_state.lang]

DEV_TEXT = {
    "IT": {
        "endpoint": "Endpoint",
        "example_request": "Esempio richiesta",
        "example_answer": "Esempio risposta",
        "data_used": "Dati usati qui",
    },
    "EN": {
        "endpoint": "Endpoint",
        "example_request": "Example request",
        "example_answer": "Example answer",
        "data_used": "Data used here",
    }
}

DEV_LABELS = {
    "IT": {
        "Backend connection": "Connessione backend",
        "Stop request": "Richiesta stop",
        "Skill ranking": "Ranking skill",
        "Trend view": "Vista trend",
        "Geographic summary": "Sintesi geografica",
        "Regional intelligence": "Intelligence regionale",
        "Sectors, titles, employers": "Settori, titoli, aziende",
        "Sector distribution chart": "Grafico distribuzione settori",
        "Sectoral snapshot": "Snapshot settoriale",
        "Sector comparison": "Confronto settoriale",
        "Job titles": "Titoli lavoro",
        "Employers": "Aziende",
        "Sectoral intelligence": "Intelligence settoriale",
        "Observed skills in selected sector": "Skill osservate nel settore selezionato",
        "Sector metrics": "Metriche settore",
        "Skill transversality": "Transversalità skill",
    },
    "EN": {}
}

STAT_HELP_BY_LANG = {
    "IT": {
        "jobs_analyzed": "Numero di job Tracker processati dopo i filtri. Formula: count(jobs).",
        "skill_frequency": "Numero di occorrenze della skill nei job analizzati. Una skill è contata una volta per job che la contiene.",
        "volume_growth": "Variazione volume job tra seconda metà e prima metà del periodo. Formula: (jobs_B - jobs_A) / jobs_A * 100.",
        "skill_growth": "Variazione percentuale della skill tra seconda metà e prima metà del periodo. Se prima metà = 0 e seconda > 0: new_entry.",
        "geo_job_count": "Numero di job per location_code. Formula: count(jobs where job.location_code = area).",
        "market_share": "Quota dell'area sul totale job analizzati. Formula: jobs_area / all_jobs * 100.",
        "sectoral_job_share": "Quota del settore sul totale delle assegnazioni settoriali. Formula: sector_jobs / sum(all_sector_jobs).",
        "regional_skill_count": "Numero di job nell'area che contengono quella skill.",
        "specialization": "Concentrazione relativa della skill nell'area. Formula: (skill_area/jobs_area) / (skill_global/all_jobs). Sopra 1 = sopra media.",
        "sector_mentions": "Totale menzioni skill nel settore. Formula: sum(sector_skill_count[sector].values()).",
        "title_count": "Numero di job con questo titolo. Formula: count(jobs where title = value).",
        "employer_count": "Numero di job pubblicati da questa azienda. Formula: count(jobs where organization = value).",
        "total_skill_mentions": "Totale menzioni skill nel settore selezionato. Formula: sum(count skill nel settore).",
        "unique_skills": "Numero di skill distinte nel settore selezionato. Formula: count(distinct skills in sector).",
        "observed_skill_count": "Numero di volte in cui la skill appare nel settore selezionato.",
        "observed_skill_frequency": "Peso della skill nel settore. Formula: skill_count_in_sector / total_skill_mentions_in_sector.",
        "coverage_unique_skills": "Copertura skill del settore. Formula: count(distinct skills in sector).",
        "dominance_top10_share": "Concentrazione delle top 10 skill. Formula: sum(top_10_skill_counts) / total_skill_mentions_in_sector.",
        "importance_in_sector": "Importanza della skill nel settore selezionato. Formula: skill_count_in_sector / total_skill_mentions_in_sector.",
        "sector_breadth": "Transversalità della skill. Formula: count(sectors where skill appears).",
        "dominant_share": "Quota della skill nel suo settore dominante. Formula: count_in_dominant_sector / count_in_all_sectors.",
        "categories_found": "Numero di settori Tracker API trovati nella risposta sectoral. Formula: count(items).",
    },
    "EN": {
        "jobs_analyzed": "Number of Tracker jobs processed after filters. Formula: count(jobs).",
        "skill_frequency": "Number of skill occurrences in analyzed jobs. A skill is counted once per job that contains it.",
        "volume_growth": "Job volume change between second half and first half of the period. Formula: (jobs_B - jobs_A) / jobs_A * 100.",
        "skill_growth": "Skill percentage change between second half and first half of the period. If first half = 0 and second half > 0: new_entry.",
        "geo_job_count": "Number of jobs by location_code. Formula: count(jobs where job.location_code = area).",
        "market_share": "Area share of all analyzed jobs. Formula: jobs_area / all_jobs * 100.",
        "sectoral_job_share": "Sector share of all sector assignments. Formula: sector_jobs / sum(all_sector_jobs).",
        "regional_skill_count": "Number of jobs in the area that contain that skill.",
        "specialization": "Relative concentration of the skill in the area. Formula: (skill_area/jobs_area) / (skill_global/all_jobs). Above 1 = above average.",
        "sector_mentions": "Total skill mentions in the sector. Formula: sum(sector_skill_count[sector].values()).",
        "title_count": "Number of jobs with this title. Formula: count(jobs where title = value).",
        "employer_count": "Number of jobs posted by this employer. Formula: count(jobs where organization = value).",
        "total_skill_mentions": "Total skill mentions in the selected sector. Formula: sum(skill counts in sector).",
        "unique_skills": "Number of distinct skills in the selected sector. Formula: count(distinct skills in sector).",
        "observed_skill_count": "Number of times the skill appears in the selected sector.",
        "observed_skill_frequency": "Skill weight inside the sector. Formula: skill_count_in_sector / total_skill_mentions_in_sector.",
        "coverage_unique_skills": "Sector skill coverage. Formula: count(distinct skills in sector).",
        "dominance_top10_share": "Top-10 skill concentration. Formula: sum(top_10_skill_counts) / total_skill_mentions_in_sector.",
        "importance_in_sector": "Skill importance in selected sector. Formula: skill_count_in_sector / total_skill_mentions_in_sector.",
        "sector_breadth": "Skill transversality. Formula: count(sectors where skill appears).",
        "dominant_share": "Skill share in its dominant sector. Formula: count_in_dominant_sector / count_in_all_sectors.",
        "categories_found": "Number of Tracker API sectors found in sectoral response. Formula: count(items).",
    }
}

STAT_HELP = STAT_HELP_BY_LANG[st.session_state.lang]

st.title(T['title'])
st.markdown(T['subtitle'])

def normalize_api_base_url(api_base_url: str) -> str:
    return str(api_base_url or "").strip().rstrip("/")


def check_backend(api_base_url: str, timeout_seconds: int):
    try:
        res = requests.get(
            f"{normalize_api_base_url(api_base_url)}/health",
            timeout=min(int(timeout_seconds), 10)
        )
    except requests.Timeout as exc:
        return {"_error": f"{T['server_timeout']} ({exc})"}
    except RequestException as exc:
        return {"_error": f"{T['server_error']} ({exc})"}

    if res.status_code == 200:
        return {"status": "ok"}

    return {"_error": f"{T['server_http_error']} [HTTP {res.status_code}] {res.text[:300]}"}


def get_analysis_data(api_base_url: str, payload: dict, timeout_seconds: int):
    try:
        res = requests.post(
            f"{normalize_api_base_url(api_base_url)}/analyze-skills",
            data=payload,
            timeout=timeout_seconds
        )
    except requests.Timeout as exc:
        return {"_error": f"{T['server_timeout']} ({exc})"}
    except RequestException as exc:
        return {"_error": f"{T['server_error']} ({exc})"}

    if res.status_code == 200:
        return res.json()

    return {"_error": f"{T['server_http_error']} [HTTP {res.status_code}] {res.text[:500]}"}


def get_sectoral_data(api_base_url: str, payload: dict, timeout_seconds: int):
    try:
        res = requests.post(
            f"{normalize_api_base_url(api_base_url)}/sectoral-intelligence",
            data=payload,
            timeout=timeout_seconds
        )
    except requests.Timeout as exc:
        return {"_error": f"{T['server_timeout']} ({exc})"}
    except RequestException as exc:
        return {"_error": f"{T['server_error']} ({exc})"}

    if res.status_code == 200:
        return res.json()

    return {"_error": f"{T['server_http_error']} [HTTP {res.status_code}] {res.text[:500]}"}


def get_sectoral_snapshot_data(api_base_url: str, payload: dict, timeout_seconds: int):
    try:
        res = requests.post(
            f"{normalize_api_base_url(api_base_url)}/sectoral-snapshot",
            data=payload,
            timeout=timeout_seconds
        )
    except requests.Timeout as exc:
        return {"_error": f"{T['server_timeout']} ({exc})"}
    except RequestException as exc:
        return {"_error": f"{T['server_error']} ({exc})"}

    if res.status_code == 200:
        return res.json()

    return {"_error": f"{T['server_http_error']} [HTTP {res.status_code}] {res.text[:500]}"}


def dev_info(label: str, endpoint: str, response_example: dict, used_fields: list[str], payload_example: dict | None = None):
    with st.popover("API", use_container_width=False):
        dev_text = DEV_TEXT[st.session_state.lang]
        translated_label = DEV_LABELS[st.session_state.lang].get(label, label)
        st.markdown(f"**{translated_label}**")
        st.markdown(dev_text["endpoint"])
        st.code(endpoint, language="http")
        if payload_example:
            st.markdown(dev_text["example_request"])
            st.code(json.dumps(payload_example, indent=2), language="json")
        st.markdown(dev_text["example_answer"])
        st.code(json.dumps(response_example, indent=2), language="json")
        st.markdown(dev_text["data_used"])
        for field in used_fields:
            st.markdown(f"- `{field}`")


def metric_with_info(label: str, value, info: str, **kwargs):
    st.metric(label, value, help=info, **kwargs)


ANALYZE_ENDPOINT = "POST /projector/analyze-skills"
SECTORAL_ENDPOINT = "POST /projector/sectoral-intelligence"
SECTORAL_SNAPSHOT_ENDPOINT = "POST /projector/sectoral-snapshot"
EMERGING_ENDPOINT = "POST /projector/emerging-skills"
HEALTH_ENDPOINT = "GET /projector/health"
STOP_ENDPOINT = "POST /projector/stop"


with st.sidebar:
    st.selectbox("Language / Lingua", ["Italiano", "English"],
                 index=0 if st.session_state.lang == 'IT' else 1,
                 on_change=change_lang, key="lang_choice")
    st.markdown("---")

    st.header(T['filters_header'])
    keywords = st.text_input(T['keywords'], "software")
    location = st.text_input(T['location'], "")
    date_range = st.date_input(T['date_range'], [pd.to_datetime("2024-01-01"), pd.to_datetime("2024-12-31")])

    submit_button = st.button(T["submit_general"], use_container_width=True)

    st.markdown("---")
    sectoral_keywords = st.text_input(T['keywords'], "software", key="sectoral_keywords")
    sectoral_location = st.text_input(T['location'], "", key="sectoral_location")
    sectoral_sector_filter = st.text_input(T["sector_filter"], "", key="sectoral_sector_filter")
    sectoral_source_options = T["sectoral_data_source_options"]
    sectoral_source_label = st.selectbox(T["sectoral_data_source"], list(sectoral_source_options.values()))
    sectoral_data_source = next(key for key, value in sectoral_source_options.items() if value == sectoral_source_label)
    sectoral_mode = "year"
    sectoral_snapshot_year = st.number_input(
        T["sectoral_snapshot_year"],
        min_value=2000,
        max_value=2100,
        value=2024,
        step=1,
    )
    sectoral_date_range = [
        pd.to_datetime(f"{int(sectoral_snapshot_year)}-01-01"),
        pd.to_datetime(f"{int(sectoral_snapshot_year)}-12-31"),
    ]
    compare_a_range = [pd.to_datetime("2023-01-01"), pd.to_datetime("2023-12-31")]
    compare_b_range = [pd.to_datetime("2024-01-01"), pd.to_datetime("2024-12-31")]
    sectoral_submit_button = st.button(T["submit_sectoral"], use_container_width=True)

    st.markdown("---")
    st.text_input(T["backend_url"], key="api_base_url")
    dev_info(
        "Backend connection",
        HEALTH_ENDPOINT,
        {"status": "ok"},
        ["status"]
    )
    timeout_kwargs = {}
    if "backend_timeout" not in st.session_state:
        timeout_kwargs["value"] = 600
    st.number_input(
        T["backend_timeout"],
        min_value=5,
        max_value=1800,
        step=60,
        key="backend_timeout",
        **timeout_kwargs
    )
    if st.button(T["check_backend"], use_container_width=True):
        health = check_backend(st.session_state.api_base_url, st.session_state.backend_timeout)
        if health.get("status") == "ok":
            st.success(T["server_ok"])
        else:
            st.error(health.get("_error", T["server_error"]))
    st.caption(T["backend_help"])
    st.markdown("---")

    dev_info(
        "Stop request",
        STOP_ENDPOINT,
        {"status": "signal_sent"},
        ["status"]
    )
    if st.button(T['stop'], type="primary", use_container_width=True):
        try:
            requests.post(
                f"{normalize_api_base_url(st.session_state.api_base_url)}/stop",
                timeout=st.session_state.backend_timeout
            )
            st.toast(T['stop_toast'])
        except RequestException as exc:
            st.error(f"{T['server_error']} ({exc})")

    st.markdown("---")
    st.subheader(f"🛠️ {T['demo_settings']}")
    demo_mode = st.checkbox(T["demo_mode"], value=False, help=T["demo_mode_help"])

# Costruzione Payload
payload = {
    "keywords": [keywords] if keywords else None,
    "locations": [location] if location else None,
    "min_date": date_range[0].strftime("%Y-%m-%d"),
    "max_date": date_range[1].strftime("%Y-%m-%d"),
    "demo": demo_mode,
}

sectoral_payload = {
    "keywords": [sectoral_keywords] if sectoral_keywords else None,
    "locations": [sectoral_location] if sectoral_location else None,
    "sectors": [s.strip() for s in sectoral_sector_filter.split(",") if s.strip()],
    "data_source": sectoral_data_source,
    "mode": sectoral_mode,
    "min_date": sectoral_date_range[0].strftime("%Y-%m-%d"),
    "max_date": sectoral_date_range[1].strftime("%Y-%m-%d"),
    "snapshot_year": int(sectoral_snapshot_year),
    "compare_a_min_date": compare_a_range[0].strftime("%Y-%m-%d"),
    "compare_a_max_date": compare_a_range[1].strftime("%Y-%m-%d"),
    "compare_b_min_date": compare_b_range[0].strftime("%Y-%m-%d"),
    "compare_b_max_date": compare_b_range[1].strftime("%Y-%m-%d"),
    "skill_group_level": 1,
    "occupation_level": 1
}

sectoral_snapshot_payload = {
    "year": int(sectoral_snapshot_year),
    "keywords": [sectoral_keywords] if sectoral_keywords else None,
    "locations": [sectoral_location] if sectoral_location else None,
    "sectors": [s.strip() for s in sectoral_sector_filter.split(",") if s.strip()],
    "data_source": sectoral_data_source,
}

# --- LOGICA DI ACQUISIZIONE DATI ---
if submit_button:
    with st.spinner(f"🚀 {T['loading']}"):
        data = get_analysis_data(
            st.session_state.api_base_url,
            payload,
            st.session_state.backend_timeout
        )
        if data and "_error" not in data:
            st.session_state.all_data = data
        else:
            error_msg = data.get("_error", T['server_error']) if isinstance(data, dict) else T['server_error']
            st.error(error_msg)

if sectoral_submit_button:
    with st.spinner(f"🚀 {T['loading']}"):
        sectoral_response = get_sectoral_snapshot_data(
            st.session_state.api_base_url,
            sectoral_snapshot_payload,
            st.session_state.backend_timeout
        )
        if sectoral_response and "_error" not in sectoral_response:
            st.session_state.sectoral_snapshot_data = sectoral_response
            st.session_state.sectoral_data = None
        else:
            error_msg = sectoral_response.get("_error", T['server_error']) if isinstance(sectoral_response, dict) else T['server_error']
            st.error(error_msg)

# --- LOGICA DI RENDERING ---
# Mostriamo i risultati se almeno una analisi è presente nello stato della sessione
if st.session_state.all_data or st.session_state.sectoral_data or st.session_state.sectoral_snapshot_data:
    all_data = st.session_state.all_data or {
        "insights": {
            "ranking": [],
            "sectors": [],
            "job_titles": [],
            "employers": [],
            "trends": {},
            "regional": {},
        },
        "dimension_summary": {
            "jobs_analyzed": 0,
            "geo_breakdown": [],
        },
    }
    sectoral_response = st.session_state.sectoral_data or {}
    sectoral_snapshot_response = st.session_state.sectoral_snapshot_data or {}
    ins = all_data["insights"]
    summary = all_data["dimension_summary"]

    tab1, tab2, tab3, tab4 = st.tabs(T['tabs'])

    # --- TAB 1: RANKING SKILLS ---
    with tab1:
        h_main, h_info = st.columns([8, 1])
        with h_main:
            st.header(T['top_skills'], help=STAT_HELP["skill_frequency"])
        with h_info:
            dev_info(
                "Skill ranking",
                ANALYZE_ENDPOINT,
                {
                    "insights": {
                        "ranking": [
                            {
                                "name": "Python",
                                "frequency": 120,
                                "primary_sector": "Information and communication",
                                "sector_spread": 4,
                                "is_green": False,
                                "is_digital": False
                            }
                        ]
                    },
                    "dimension_summary": {"jobs_analyzed": 1250}
                },
                [
                    "insights.ranking[].name",
                    "insights.ranking[].frequency",
                    "insights.ranking[].primary_sector",
                    "insights.ranking[].sector_spread",
                    "insights.ranking[].is_green",
                    "insights.ranking[].is_digital",
                    "dimension_summary.jobs_analyzed"
                ],
                payload
            )
        ranking = ins.get("ranking", [])
        if ranking:
            df_ranking = pd.DataFrame(ranking).head(15)

            # Tag Twin Transition
            df_ranking['Twin'] = df_ranking.apply(
                lambda x: ("🍃" if x.get('is_green') else "") + ("💻" if x.get('is_digital') else ""), axis=1
            )

            col1, col2 = st.columns([2, 1])
            with col1:
                fig = px.bar(df_ranking, x='frequency', y='name', orientation='h',
                             title=f"Top 15 Skills per '{keywords}'",
                             color='frequency', color_continuous_scale='Viridis',
                             hover_data=["primary_sector", "sector_spread"])
                fig.update_layout(yaxis={'categoryorder': 'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                metric_with_info(T['jobs_analyzed'], summary.get("jobs_analyzed", 0), STAT_HELP["jobs_analyzed"])
                st.subheader(T['intelligence_label'], help=STAT_HELP["skill_frequency"])
                st.dataframe(
                    df_ranking[['name', 'frequency', 'primary_sector', 'Twin']],
                    use_container_width=True,
                    column_config={
                        "frequency": st.column_config.NumberColumn(
                            "frequency (i)",
                            help=STAT_HELP["skill_frequency"]
                        )
                    }
                )

    # --- TAB 2: TRENDS ---
    with tab2:
        h_main, h_info = st.columns([8, 1])
        with h_main:
            st.header(T['trends_header'], help=f"{STAT_HELP['volume_growth']} {STAT_HELP['skill_growth']}")
        with h_info:
            dev_info(
                "Trend view",
                ANALYZE_ENDPOINT,
                {
                    "insights": {
                        "trends": {
                            "market_health": {
                                "status": "expanding",
                                "volume_growth_percentage": 12.5
                            },
                            "trends": [
                                {
                                    "name": "Python",
                                    "growth": 20.0,
                                    "trend_type": "emerging",
                                    "primary_sector": "Information and communication"
                                }
                            ]
                        }
                    }
                },
                [
                    "insights.trends.market_health.status",
                    "insights.trends.market_health.volume_growth_percentage",
                    "insights.trends.trends[].name",
                    "insights.trends.trends[].growth",
                    "insights.trends.trends[].trend_type",
                    "insights.trends.trends[].primary_sector"
                ],
                payload
            )
        trend_data = ins.get("trends", {})

        if trend_data:
            mh = trend_data.get("market_health", {})
            st.info(f"{T['market_status']}: **{mh.get('status', '').upper()}** | {T['volume_var']}: **{mh.get('volume_growth_percentage', 0)}%**")

            trends_list = trend_data.get("trends", [])
            if trends_list:
                df_trends = pd.DataFrame.from_records(trends_list)
                if 'growth' in df_trends.columns:
                    new_entries = df_trends[df_trends['growth'] == 'new_entry']
                    df_numeric = df_trends[df_trends['growth'] != 'new_entry'].copy()
                    df_numeric['growth'] = pd.to_numeric(df_numeric['growth'], errors='coerce')
                    df_numeric = df_numeric.dropna(subset=['growth'])

                    if not df_numeric.empty:
                        df_plot = pd.concat([df_numeric.head(10), df_numeric.tail(10)])
                        fig_trend = px.bar(df_plot, x='growth', y='name', orientation='h',
                                           color='trend_type',
                                           hover_data=["primary_sector"],
                                           color_discrete_map={'emerging': '#2ecc71', 'declining': '#e74c3c'},
                                           title=T['delta_title'])
                        st.plotly_chart(fig_trend, use_container_width=True)

                    if not new_entries.empty:
                        st.subheader(T['new_entries'])
                        st.success(", ".join(new_entries['name'].astype(str).tolist()))

    # --- TAB 3: GEOGRAFIA ---
    with tab3:
        h_main, h_info = st.columns([8, 1])
        with h_main:
            st.header(T['geo_header'], help=STAT_HELP["geo_job_count"])
        with h_info:
            dev_info(
                "Geographic summary",
                ANALYZE_ENDPOINT,
                {
                    "dimension_summary": {
                        "geo_breakdown": [
                            {"location": "IT", "job_count": 820}
                        ]
                    }
                },
                [
                    "dimension_summary.geo_breakdown[].location",
                    "dimension_summary.geo_breakdown[].job_count"
                ],
                payload
            )
        geo = summary.get("geo_breakdown", [])

        # --- PARTE A: Mappa Globale ---
        if geo:
            df_geo = pd.DataFrame(geo)
            iso_mapping = {"IT": "ITA", "FR": "FRA", "DE": "DEU", "ES": "ESP", "GB": "GBR", "EL": "GRC", "SE": "SWE"}
            df_geo['iso_alpha_3'] = df_geo['location'].map(iso_mapping).fillna(df_geo['location'])

            c_map, c_stat = st.columns([2, 1])
            with c_map:
                fig_map = px.choropleth(df_geo, locations="iso_alpha_3", color="job_count",
                                        hover_name="location", color_continuous_scale="Viridis",
                                        projection="natural earth", title=T['map_title'])
                st.plotly_chart(fig_map, use_container_width=True)
            with c_stat:
                st.plotly_chart(px.pie(df_geo, values='job_count', names='location', hole=0.4),
                                use_container_width=True)
        else:
            st.warning(T['no_geo'])

        # --- PARTE B: Task 3.5 - REGIONAL LANDSCAPE ---
        regional_dict = ins.get("regional", {})

        if regional_dict:
            st.markdown("---")
            h_main, h_info = st.columns([8, 1])
            with h_main:
                st.header(
                    T["regional_task_header"],
                    help=f"{STAT_HELP['market_share']} {STAT_HELP['specialization']}"
                )
            with h_info:
                dev_info(
                    "Regional intelligence",
                    ANALYZE_ENDPOINT,
                    {
                        "insights": {
                            "regional": {
                                "raw": [
                                    {
                                        "code": "IT",
                                        "total_jobs": 120,
                                        "market_share": 9.6,
                                        "top_skills": [
                                            {
                                                "skill": "Python",
                                                "count": 33,
                                                "specialization": 1.78
                                            }
                                        ]
                                    }
                                ],
                                "nuts1": [],
                                "nuts2": [],
                                "nuts3": []
                            }
                        }
                    },
                    [
                        "insights.regional.raw[]",
                        "insights.regional.nuts1[]",
                        "insights.regional.nuts2[]",
                        "insights.regional.nuts3[]",
                        "regional item.code",
                        "regional item.market_share",
                        "regional item.top_skills[].skill",
                        "regional item.top_skills[].count",
                        "regional item.top_skills[].specialization"
                    ],
                    payload
                )

            strategy = st.radio(
                T["regional_strategy"],
                T["regional_options"],
                horizontal=True,
                help=T["regional_strategy_help"]
            )

            strat_map = {
                T["regional_options"][0]: "raw",
                T["regional_options"][1]: "nuts1",
                T["regional_options"][2]: "nuts2",
                T["regional_options"][3]: "nuts3"
            }

            selected_list = regional_dict.get(strat_map[strategy], [])

            if selected_list:
                area_codes = [item["code"] for item in selected_list]
                col_sel, col_met = st.columns([2, 1])

                with col_sel:
                    target_code = st.selectbox(
                        f"{T['regional_select_area']} ({strategy}):",
                        area_codes
                    )

                target = next(i for i in selected_list if i["code"] == target_code)

                with col_met:
                    metric_with_info(T["market_share"], f"{target['market_share']}%", STAT_HELP["market_share"])

                st.subheader(
                    f"{T['key_skills_in']} {target_code}",
                    help=f"{STAT_HELP['regional_skill_count']} {STAT_HELP['specialization']}"
                )
                df_reg_skills = pd.DataFrame(target["top_skills"])

                fig_reg = px.bar(
                    df_reg_skills,
                    x="count",
                    y="skill",
                    orientation='h',
                    text="count",
                    color="specialization",
                    color_continuous_scale="RdYlGn",
                    labels={
                        "skill": T["skill_label"],
                        "count": T["job_post_label"],
                        "specialization": T["specialization_label"]
                    },
                    title=f"{T['workforce_profile']}: {target_code}"
                )
                fig_reg.update_layout(yaxis={'categoryorder': 'total ascending'}, height=400)
                st.plotly_chart(fig_reg, use_container_width=True)

                st.info(f"💡 **Insight Task 3.5**: {T['regional_insight'].format(target_code=target_code)}")
            else:
                st.warning(T["regional_no_level"].format(strategy=strategy))
        else:
            st.info(T["regional_run_first"])

    # --- TAB 4: SETTORI, JOBS & EMPLOYERS ---
    with tab4:
        h_main, h_info = st.columns([8, 1])
        with h_main:
            st.header(
                T['jobs_emp_header'],
                help=f"{STAT_HELP['sector_mentions']} {STAT_HELP['title_count']} {STAT_HELP['employer_count']}"
            )
        with h_info:
            dev_info(
                "Sectors, titles, employers",
                ANALYZE_ENDPOINT,
                {
                    "insights": {
                        "sectors": [{"name": "Education", "count": 42}],
                        "job_titles": [{"name": "Logistics Coordinator", "count": 8}],
                        "employers": [{"name": "Example Ltd", "count": 5}]
                    }
                },
                [
                    "insights.sectors[].name",
                    "insights.sectors[].count",
                    "insights.job_titles[].name",
                    "insights.job_titles[].count",
                    "insights.employers[].name",
                    "insights.employers[].count"
                ],
                payload
            )

        active_sectoral = sectoral_response.get("items", [])
        snapshot_sectors = sectoral_snapshot_response.get("sectors", [])
        sectoral_window = sectoral_response.get("window", {})
        snapshot_window = sectoral_snapshot_response.get("window", {})
        sectoral_mode_name = sectoral_response.get("mode", sectoral_payload.get("mode", "latest"))

        st.caption(
            f"Sector system: NACE | "
            f"{T['agg_level']}: Tracker API job sectors | "
            f"{T['categories_found']}: {len(snapshot_sectors) or len(active_sectoral)} | "
            f"{T['sectoral_window']}: "
            f"{snapshot_window.get('label') or sectoral_window.get('label', sectoral_mode_name)} "
            f"({snapshot_window.get('min_date') or sectoral_window.get('min_date', '-') } → "
            f"{snapshot_window.get('max_date') or sectoral_window.get('max_date', '-')})"
        )
        c1, c2, c3 = st.columns(3)

        with c1:
            st.subheader(T['top_sectors'], help=STAT_HELP["sector_mentions"])
            dev_info(
                "Sector distribution chart",
                SECTORAL_SNAPSHOT_ENDPOINT,
                {
                    "year": 2024,
                    "window": {
                        "label": "2024 snapshot",
                        "min_date": "2024-01-01",
                        "max_date": "2024-12-31"
                    },
                    "sectors": [
                        {
                            "sector": "Education",
                            "sector_label": "Education",
                            "job_count": 42,
                            "job_share": 0.18,
                            "total_skill_mentions": 100
                        }
                    ]
                },
                [
                    "sectors[].sector",
                    "sectors[].sector_label",
                    "sectors[].job_count",
                    "sectors[].job_share",
                    "sectors[].total_skill_mentions"
                ],
                sectoral_snapshot_payload
            )
            if snapshot_sectors:
                df_sec = pd.DataFrame([
                    {
                        "name": item.get("sector_label", item.get("sector")),
                        "count": item.get("job_count", 0)
                    }
                    for item in snapshot_sectors
                ])
                df_sec = df_sec[df_sec["count"] > 0]
                fig_sec = px.pie(
                    df_sec,
                    values='count',
                    names='name',
                    title=T["sector_title"],
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig_sec.update_traces(textposition='inside', textinfo='percent+label')
                fig_sec.update_layout(showlegend=False)
                st.plotly_chart(fig_sec, use_container_width=True)
            elif active_sectoral:
                df_sec = pd.DataFrame([
                    {
                        "name": item.get("sector_label", item.get("sector")),
                        "count": item.get("observed_skills", {}).get("total_skill_mentions", 0)
                    }
                    for item in active_sectoral
                ])
                df_sec = df_sec[df_sec["count"] > 0]
                fig_sec = px.pie(
                    df_sec,
                    values='count',
                    names='name',
                    title="Demand by Tracker API sectors",
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig_sec.update_traces(textposition='inside', textinfo='percent+label')
                fig_sec.update_layout(showlegend=False)
                st.plotly_chart(fig_sec, use_container_width=True)
            else:
                st.write(T['no_data'])

        with c2:
            st.subheader(T['top_titles'], help=STAT_HELP["title_count"])
            dev_info(
                "Job titles",
                ANALYZE_ENDPOINT,
                {
                    "insights": {
                        "job_titles": [
                            {"name": "Software Engineer", "count": 25}
                        ]
                    }
                },
                [
                    "insights.job_titles[].name",
                    "insights.job_titles[].count"
                ],
                payload
            )
            jt = ins.get("job_titles", [])
            if jt:
                st.plotly_chart(px.bar(pd.DataFrame(jt), x='count', y='name', orientation='h',
                                       title=T['jt_title'], color_discrete_sequence=['#3498db']))
            else:
                st.write(T['no_data'])

        with c3:
            st.subheader(T['top_emp'], help=STAT_HELP["employer_count"])
            dev_info(
                "Employers",
                ANALYZE_ENDPOINT,
                {
                    "insights": {
                        "employers": [
                            {"name": "Example Ltd", "count": 12}
                        ]
                    }
                },
                [
                    "insights.employers[].name",
                    "insights.employers[].count"
                ],
                payload
            )
            emp = ins.get("employers", [])
            if emp:
                st.plotly_chart(px.pie(pd.DataFrame(emp), values='count', names='name',
                                       title=T['active_emp'], hole=0.3))
            else:
                st.write(T['no_data'])

        if snapshot_sectors:
            st.markdown("---")
            h_main, h_info = st.columns([8, 1])
            with h_main:
                st.header(T["sectoral_snapshot_header"], help=T["sectoral_snapshot_help"])
            with h_info:
                dev_info(
                    "Sectoral snapshot",
                    SECTORAL_SNAPSHOT_ENDPOINT,
                    {
                        "year": 2024,
                        "total_jobs": 1200,
                        "sectors": [
                            {
                                "sector": "Education",
                                "job_count": 220,
                                "job_share": 0.18,
                                "top_skills": [{"label": "Python", "count": 35}],
                                "top_job_titles": [{"name": "Teacher", "count": 12}]
                            }
                        ]
                    },
                    [
                        "year",
                        "total_jobs",
                        "sectors[].sector",
                        "sectors[].job_count",
                        "sectors[].job_share",
                        "sectors[].top_skills[].label",
                        "sectors[].top_skills[].count",
                        "sectors[].top_job_titles[].name",
                        "sectors[].top_job_titles[].count"
                    ],
                    sectoral_snapshot_payload
                )

            df_snapshot = pd.DataFrame(snapshot_sectors)
            st.dataframe(
                df_snapshot[[
                    "sector_label",
                    "job_count",
                    "job_share",
                    "total_skill_mentions",
                    "unique_skills"
                ]],
                use_container_width=True,
                column_config={
                    "sector_label": st.column_config.TextColumn(T["agg_level"]),
                    "job_count": st.column_config.NumberColumn(
                        T["jobs_analyzed"],
                        help=STAT_HELP["jobs_analyzed"]
                    ),
                    "job_share": st.column_config.NumberColumn(
                        f"{T['sectoral_job_share']} (i)",
                        help=STAT_HELP["sectoral_job_share"]
                    ),
                    "total_skill_mentions": st.column_config.NumberColumn(
                        f"{T['total_mentions']} (i)",
                        help=STAT_HELP["total_skill_mentions"]
                    ),
                    "unique_skills": st.column_config.NumberColumn(
                        f"{T['unique_items']} (i)",
                        help=STAT_HELP["unique_skills"]
                    ),
                }
            )

            snapshot_options = {
                f"{item.get('sector_label', item['sector'])} ({item['job_count']})": item
                for item in snapshot_sectors
            }
            selected_snapshot = st.selectbox(T["sectoral_snapshot_detail"], list(snapshot_options.keys()))
            snapshot_target = snapshot_options[selected_snapshot]
            snap_skill_col, snap_title_col = st.columns(2)

            with snap_skill_col:
                st.subheader(T["sectoral_top_skills"], help=STAT_HELP["observed_skill_count"])
                top_skills = snapshot_target.get("top_skills", [])
                if top_skills:
                    df_top_skills = pd.DataFrame(top_skills)
                    label_col = "label" if "label" in df_top_skills.columns else "skill_id"
                    fig_top_skills = px.bar(
                        df_top_skills,
                        x="count",
                        y=label_col,
                        orientation="h",
                        labels={label_col: T["skill_label"], "count": T["total_mentions"]},
                    )
                    fig_top_skills.update_layout(yaxis={'categoryorder': 'total ascending'})
                    st.plotly_chart(fig_top_skills, use_container_width=True)
                else:
                    st.write(T["no_data"])

            with snap_title_col:
                st.subheader(T["sectoral_top_titles"], help=STAT_HELP["title_count"])
                top_titles = snapshot_target.get("top_job_titles", [])
                if top_titles:
                    df_top_titles = pd.DataFrame(top_titles)
                    fig_top_titles = px.bar(
                        df_top_titles,
                        x="count",
                        y="name",
                        orientation="h",
                        labels={"name": T["top_titles"], "count": T["jobs_analyzed"]},
                    )
                    fig_top_titles.update_layout(yaxis={'categoryorder': 'total ascending'})
                    st.plotly_chart(fig_top_titles, use_container_width=True)
                else:
                    st.write(T["no_data"])

        st.markdown("---")
        comparison = sectoral_response.get("comparison") or {}
        comparison_rows = comparison.get("sectors", [])
        if sectoral_response.get("mode") == "comparison" and comparison_rows:
            h_main, h_info = st.columns([8, 1])
            with h_main:
                st.subheader(T["sectoral_comparison"], help=STAT_HELP["sector_mentions"])
            with h_info:
                dev_info(
                    "Sector comparison",
                    SECTORAL_ENDPOINT,
                    {
                        "mode": "comparison",
                        "comparison": {
                            "period_a": {"min_date": "2023-01-01", "max_date": "2023-12-31"},
                            "period_b": {"min_date": "2024-01-01", "max_date": "2024-12-31"},
                            "sectors": [
                                {
                                    "sector": "Education",
                                    "period_a_total_skill_mentions": 20,
                                    "period_b_total_skill_mentions": 35,
                                    "delta_total_skill_mentions": 15,
                                    "growth_percentage": 75.0
                                }
                            ]
                        }
                    },
                    [
                        "comparison.period_a",
                        "comparison.period_b",
                        "comparison.sectors[].sector",
                        "comparison.sectors[].delta_total_skill_mentions",
                        "comparison.sectors[].growth_percentage"
                    ],
                    sectoral_payload
                )
            df_cmp = pd.DataFrame(comparison_rows)
            st.dataframe(df_cmp, use_container_width=True)
            st.markdown("---")

        sectoral = active_sectoral

        if sectoral:
            h_main, h_info = st.columns([8, 1])
            with h_main:
                st.header(
                    T['technical_sectoral_detail'],
                    help=f"{STAT_HELP['total_skill_mentions']} {STAT_HELP['importance_in_sector']} {STAT_HELP['sector_breadth']}"
                )
            with h_info:
                dev_info(
                    "Sectoral intelligence",
                    SECTORAL_ENDPOINT,
                    {
                        "sector_level": "tracker_sector",
                        "mode": "latest",
                        "items": [
                            {
                                "sector": "Education",
                                "sector_label": "Education",
                                "observed_skills": {},
                                "sector_metrics": {},
                                "skill_transversal_insights": []
                            }
                        ]
                    },
                    [
                        "sector_level",
                        "items[].sector",
                        "items[].sector_label",
                        "items[].observed_skills",
                        "items[].sector_metrics",
                        "items[].skill_transversal_insights"
                    ],
                    sectoral_payload
                )

            observed_title = T["observed_skills_per_sector"]
            sector_options = {
                f"{item.get('sector_label', item['sector'])} ({item['sector']})": item["sector"]
                for item in sectoral
            }
            selected_display = st.selectbox(T['sector_selector'], list(sector_options.keys()))
            selected_sector = sector_options[selected_display]
            target_sector = next((x for x in sectoral if x["sector"] == selected_sector), None)

            if target_sector:
                # =========================
                # A. OBSERVED SKILLS
                # =========================
                h_main, h_info = st.columns([8, 1])
                with h_main:
                    st.subheader(
                        observed_title,
                        help=f"{STAT_HELP['total_skill_mentions']} {STAT_HELP['unique_skills']} {STAT_HELP['observed_skill_frequency']}"
                    )
                with h_info:
                    dev_info(
                        "Observed skills in selected sector",
                        SECTORAL_ENDPOINT,
                        {
                            "observed_skills": {
                                "sector": "Education",
                                "total_skill_mentions": 100,
                                "unique_skills": 25,
                                "top_skills": [
                                    {
                                        "skill_id": "http://data.europa.eu/esco/skill/...",
                                        "label": "Python",
                                        "count": 10,
                                        "frequency": 0.1,
                                        "is_green": False,
                                        "is_digital": False
                                    }
                                ]
                            }
                        },
                        [
                            "selected sector.observed_skills.total_skill_mentions",
                            "selected sector.observed_skills.unique_skills",
                            "selected sector.observed_skills.top_skills[].skill_id",
                            "selected sector.observed_skills.top_skills[].label",
                            "selected sector.observed_skills.top_skills[].count",
                            "selected sector.observed_skills.top_skills[].frequency"
                        ],
                        sectoral_payload
                    )
                obs = target_sector.get("observed_skills", {})
                m1, m2 = st.columns(2)
                with m1:
                    metric_with_info(T['total_mentions'], obs.get("total_skill_mentions", 0), STAT_HELP["total_skill_mentions"])
                with m2:
                    metric_with_info(T['unique_items'], obs.get("unique_skills", 0), STAT_HELP["unique_skills"])

                obs_skills = obs.get("top_skills", [])
                if obs_skills:
                    df_obs = pd.DataFrame(obs_skills)
                    label_col = "label" if "label" in df_obs.columns else "skill_id"

                    fig_obs = px.bar(
                        df_obs,
                        x="count",
                        y=label_col,
                        orientation="h",
                        title=observed_title,
                        labels={label_col: "skill"}
                    )

                    fig_obs.update_layout(yaxis={'categoryorder': 'total ascending'})
                    st.plotly_chart(fig_obs, use_container_width=True)

                    display_cols = [c for c in ["skill_id", "label", "count", "frequency", "is_green", "is_digital"] if c in df_obs.columns]
                    st.dataframe(
                        df_obs[display_cols],
                        use_container_width=True,
                        column_config={
                            "count": st.column_config.NumberColumn(
                                "count (i)",
                                help=STAT_HELP["observed_skill_count"]
                            ),
                            "frequency": st.column_config.NumberColumn(
                                "frequency (i)",
                                help=STAT_HELP["observed_skill_frequency"]
                            )
                        }
                    )
                else:
                    st.write(T['no_data'])

                # =========================
                # B. OBSERVED GROUP PROFILE
                # =========================
                # st.markdown("---")
                # st.subheader(T['observed_groups'])
                # obs_groups = target_sector.get("observed_groups", {})
                # gm1, gm2 = st.columns(2)
                # with gm1:
                #     st.metric(T['total_mentions'], obs_groups.get("total_group_mentions", 0))
                # with gm2:
                #     st.metric(T['unique_items'], obs_groups.get("unique_groups", 0))
                #
                # top_groups = obs_groups.get("top_groups", [])
                # if top_groups:
                #     df_og = pd.DataFrame(top_groups)
                #     fig_og = px.bar(
                #         df_og,
                #         x="count",
                #         y="group_label" if "group_label" in df_og.columns else "group_id",
                #         orientation="h",
                #         title=T['observed_groups']
                #     )
                #     fig_og.update_layout(yaxis={'categoryorder': 'total ascending'})
                #     st.plotly_chart(fig_og, use_container_width=True)
                #     st.dataframe(df_og, use_container_width=True)
                # else:
                #     st.write(T['no_data'])
                #
                st.markdown("---")
                h_main, h_info = st.columns([8, 1])
                with h_main:
                    st.subheader(
                        T["sector_metrics"],
                        help=f"{STAT_HELP['coverage_unique_skills']} {STAT_HELP['dominance_top10_share']}"
                    )
                with h_info:
                    dev_info(
                        "Sector metrics",
                        SECTORAL_ENDPOINT,
                        {
                            "sector_metrics": {
                                "coverage_unique_skills": 25,
                                "dominance_top10_share": 0.62
                            }
                        },
                        [
                            "selected sector.sector_metrics.coverage_unique_skills",
                            "selected sector.sector_metrics.dominance_top10_share"
                        ],
                        sectoral_payload
                    )
                sec_metrics = target_sector.get("sector_metrics", {})
                sm1, sm2 = st.columns(2)
                with sm1:
                    metric_with_info(
                        T["skill_coverage_unique"],
                        sec_metrics.get("coverage_unique_skills", 0),
                        STAT_HELP["coverage_unique_skills"]
                    )
                with sm2:
                    metric_with_info(
                        T["top10_skill_dominance"],
                        sec_metrics.get("dominance_top10_share", 0.0),
                        STAT_HELP["dominance_top10_share"]
                    )

                h_main, h_info = st.columns([8, 1])
                with h_main:
                    st.subheader(
                        T["skill_transversality"],
                        help=f"{STAT_HELP['importance_in_sector']} {STAT_HELP['sector_breadth']} {STAT_HELP['dominant_share']}"
                    )
                with h_info:
                    dev_info(
                        "Skill transversality",
                        SECTORAL_ENDPOINT,
                        {
                            "skill_transversal_insights": [
                                {
                                    "label": "Python",
                                    "count": 10,
                                    "importance_in_sector": 0.1,
                                    "sector_breadth": 4,
                                    "dominant_sector_label": "Information and communication",
                                    "dominant_share": 0.52
                                }
                            ]
                        },
                        [
                            "selected sector.skill_transversal_insights[].label",
                            "selected sector.skill_transversal_insights[].count",
                            "selected sector.skill_transversal_insights[].importance_in_sector",
                            "selected sector.skill_transversal_insights[].sector_breadth",
                            "selected sector.skill_transversal_insights[].dominant_sector_label",
                            "selected sector.skill_transversal_insights[].dominant_share"
                        ],
                        sectoral_payload
                    )
                insights = target_sector.get("skill_transversal_insights", [])
                if insights:
                    df_ins = pd.DataFrame(insights)
                    cols = [c for c in ["label", "count", "importance_in_sector", "sector_breadth", "dominant_sector_label", "dominant_share"] if c in df_ins.columns]
                    st.dataframe(
                        df_ins[cols],
                        use_container_width=True,
                        column_config={
                            "count": st.column_config.NumberColumn(
                                "count (i)",
                                help=STAT_HELP["observed_skill_count"]
                            ),
                            "importance_in_sector": st.column_config.NumberColumn(
                                "importance_in_sector (i)",
                                help=STAT_HELP["importance_in_sector"]
                            ),
                            "sector_breadth": st.column_config.NumberColumn(
                                "sector_breadth (i)",
                                help=STAT_HELP["sector_breadth"]
                            ),
                            "dominant_share": st.column_config.NumberColumn(
                                "dominant_share (i)",
                                help=STAT_HELP["dominant_share"]
                            )
                        }
                    )
                else:
                    st.write(T['no_data'])
        elif not snapshot_sectors:
            st.info(T['no_sectoral'])

else:
    # Mostriamo il messaggio di benvenuto solo se non ci sono dati caricati
    st.info(T['welcome'])
