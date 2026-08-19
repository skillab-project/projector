import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import json
from collections import Counter
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

if 'sector_skills_comparison_data' not in st.session_state:
    st.session_state.sector_skills_comparison_data = None

if 'regional_sectoral_data' not in st.session_state:
    st.session_state.regional_sectoral_data = None

if 'temporal_projection_data' not in st.session_state:
    st.session_state.temporal_projection_data = None

if 'api_base_url' not in st.session_state:
    st.session_state.api_base_url = os.getenv("PROJECTOR_API_BASE_URL", "http://127.0.0.1:8000/projector")

if 'sectoral_snapshot_year' not in st.session_state:
    st.session_state.sectoral_snapshot_year = 2024

if 'sectoral_reference_year' not in st.session_state:
    st.session_state.sectoral_reference_year = 2023
if 'sector_overview_mode' not in st.session_state:
    st.session_state.sector_overview_mode = "snapshot"
if 'sector_focus_choice' not in st.session_state:
    st.session_state.sector_focus_choice = "Information and communication"

SECTOR_SNAPSHOT_YEARS = [2020, 2021, 2022, 2023, 2024]
SECTOR_REGION_OPTIONS = {
    "GLOBAL": None,
    "IT": "IT",
    "DE": "DE",
    "FR": "FR",
}
REGIONAL_SECTORAL_REGION_OPTIONS = {
    "ALL REGIONS": None,
    "IT": "IT",
    "DE": "DE",
    "FR": "FR",
}
SECTOR_FOCUS_OPTIONS = [
    "Information and communication",
    "Education",
    "Manufacturing",
    "Professional, scientific and technical activities",
    "Administrative and support service activities",
]
SECTOR_SKILL_OPTIONS = [
    "Python",
    "SQL",
    "cloud computing",
    "deliver training",
    "quality control",
    "project management",
    "customer service",
    "communication",
    "Microsoft Excel",
    "sustainability",
]

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
        'dashboard_view': "Vista dashboard",
        'dashboard_view_options': {
            "skill": "Job Demand Overview",
            "temporal": "Temporal Analysis",
            "sector": "Sector Overview",
            "comparison": "Sector Skills Comparison",
            "regional_sectoral": "Regional Sector Distribution",
        },
        'keywords': "Keywords",
        'location': "Location Code (es. ITC4C)",
        'date_range': "Intervallo Temporale",
        'submit_general': "Lancia Job Demand Overview",
        'submit_temporal': "Lancia Temporal Analysis",
        'temporal_header': "Temporal Analysis",
        'temporal_help': "Aggrega le offerte per upload_date e mostra movimento skill per mese, trimestre o anno.",
        'temporal_granularity': "Granularità temporale",
        'temporal_granularity_options': {
            "monthly": "Mensile",
            "quarterly": "Trimestrale",
            "yearly": "Annuale",
        },
        'forecast_periods': "Periodi forecast",
        'top_k_skills': "Numero skill",
        'period_job_volume': "Volume job per periodo",
        'skill_time_series': "Serie temporale skill",
        'baseline_forecast': "Baseline forecast",
        'statistical_evidence': "Evidenza statistica",
        'statistical_evidence_help': "Test chi-square 2x2 sui conteggi osservati. Indica evidenza statistica per una differenza, non prova causalità o shortage.",
        'p_value': "p-value",
        'effect_size': "Effect size",
        'significant': "Significativo",
        'not_significant': "Non significativo",
        'submit_sectoral': "Lancia Sector Overview",
        'sectoral_time_mode': "Finestra settoriale",
        'sector_filter': "Filtro settori (virgola)",
        'sectoral_time_options': {
            "latest": "Ultimi 6 mesi",
            "selected_period": "Periodo selezionato",
            "year": "Snapshot anno",
            "comparison": "Confronto periodi",
        },
        'sectoral_snapshot_year': "Anno snapshot settoriale",
        'sectoral_reference_year': "Confronta crescita da",
        'comparison_years_prompt': "Scegli gli anni da confrontare",
        'comparison_from_year': "Da",
        'comparison_to_year': "A",
        'sectoral_year_bar_help': "Naviga lo storico degli snapshot settoriali annuali disponibili.",
        'sectoral_year_bar_caption': "Snapshot settoriale {year}",
        'region_filter': "Region",
        'region_filter_help': "Filtra lo snapshot settoriale per location_code. GLOBAL usa lo snapshot aggregato.",
        'regional_sectoral_country_filter': "Filtro paese",
        'regional_sectoral_region_help': "Filtra la distribuzione regionale. ALL REGIONS mostra tutte le regioni reali disponibili.",
        'sector_focus_help': "Scegli prima il settore da esplorare; anno e region filtrano il contesto storico.",
        'sector_overview_mode': "Vista settore",
        'sector_overview_mode_options': {
            "snapshot": "Snapshot",
            "evolution": "Sector Evolution",
        },
        'sectoral_snapshot_header': "Snapshot annuale settori",
        'sectoral_snapshot_help': "Vista aggregata annuale: una riga per settore Tracker con volume job, quota, skill più richieste e titoli più frequenti.",
        'sectoral_snapshot_table': "Overview settori",
        'sectoral_snapshot_detail': "Focus settore",
        'sectoral_job_share': "Quota job",
        'sector_evolution': "Evoluzione settore",
        'sector_evolution_help': "Confronta il settore selezionato con l'anno di partenza scelto.",
        'job_delta': "Nuovi job netti",
        'job_growth': "Crescita job",
        'new_skills': "Nuove skill",
        'disappeared_skills': "Skill scomparse",
        'growing_skills': "Skill in crescita",
        'declining_skills': "Skill in calo",
        'skill_churn': "Skill churn",
        'top_new_skills': "Top nuove skill",
        'top_disappeared_skills': "Top skill scomparse",
        'top_growing_skills': "Top skill in crescita",
        'top_declining_skills': "Top skill in calo",
        'no_new_skills': "Nessuna nuova skill rilevata.",
        'no_disappeared_skills': "Nessuna skill scomparsa.",
        'no_growing_skills': "Nessuna skill in crescita.",
        'no_declining_skills': "Nessuna skill in calo.",
        'refresh_failed': "Ultimo aggiornamento snapshot fallito.",
        'refresh_last_success': "Ultimo aggiornamento riuscito",
        'refresh_resume': "Ripartenza fetch",
        'refresh_jobs': "Job recuperati",
        'evolution_count': "Conteggio",
        'evolution_reference_count': "Conteggio confronto",
        'evolution_delta': "Delta",
        'sectoral_top_skills': "Top skill settore",
        'skill_portfolio': "Skill Portfolio",
        'skill_portfolio_help': "Mappa le skill del settore per importanza e trasversalità.",
        'sectoral_all_skills': "Tutte le skill del settore",
        'skill_search': "Cerca skill",
        'sectoral_top_titles': "Top titoli settore",
        'comparison_header': "Sector Skills Comparison",
        'comparison_help': "Confronta settori e skill con una heatmap annuale.",
        'regional_sectoral_header': "Distribuzione settoriale regionale",
        'regional_sectoral_help': "Mostra i settori più rappresentati per regione usando snapshot annuali PostgreSQL.",
        'regional_sectoral_level': "Livello regione",
        'regional_sectoral_area': "Scegli area specifica",
        'regional_sectoral_top_k': "Settori per area",
        'regional_sectoral_table': "Aree e settori principali",
        'regional_sectoral_chart': "Top settori in area",
        'regional_sectoral_overview': "Mappa distribuzione regionale",
        'regional_sectoral_visual': "Visualizzazione",
        'regional_sectoral_visual_options': {
            "auto": "Auto",
            "map": "Mappa geografica",
            "treemap": "Treemap aree",
        },
        'regional_sectoral_tabs': {
            "region_first": "Regions → Sectors",
            "sector_first": "Sector → Regions",
        },
        'sector_footprint_header': "Mappa impronta settore",
        'sector_footprint_help': "Scegli un settore e visualizza le aree dove quel settore pesa di più.",
        'sector_footprint_sector': "Settore",
        'sector_footprint_metric': "Metrica colore",
        'sector_footprint_metric_options': {
            "specialization": "Specializzazione",
            "share_in_region": "Quota nella regione",
            "count": "Conteggio",
        },
        'sector_footprint_note': "La vista usa i settori restituiti in top_sectors per ogni area. Aumenta top_k per copertura più ampia.",
        'submit_regional_sectoral': "Lancia Regional Sector Distribution",
        'sector_count': "Conteggio settore",
        'share_in_region': "Quota nella regione",
        'comparison_metric': "Metrica heatmap",
        'comparison_sectors': "Settori da confrontare",
        'comparison_skills': "Skill da confrontare",
        'comparison_metric_options': {
            "share": "Share in sector",
            "count": "Count",
            "rank": "Rank",
            "growth": "Growth between years",
        },
        'submit_comparison': "Lancia Sector Skills Comparison",
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
        'tabs': ["📊 Job Demand", "📈 Trend Summary", "🗺️ Distribuzione Geografica", "🏭 Settori & Aziende"],
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
        'sector_demo_mode': "Abilita snapshot settori demo",
        'sector_demo_mode_help': "Usa il dataset fake seedato nel database Docker per provare la Sector Overview senza dati Tracker reali.",
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
        'dashboard_view': "Dashboard view",
        'dashboard_view_options': {
            "skill": "Job Demand Overview",
            "temporal": "Temporal Analysis",
            "sector": "Sector Overview",
            "comparison": "Sector Skills Comparison",
            "regional_sectoral": "Regional Sector Distribution",
        },
        'keywords': "Keywords",
        'location': "Location Code (e.g. ITC4C)",
        'date_range': "Time Range",
        'submit_general': "Run Job Demand Overview",
        'submit_temporal': "Run Temporal Analysis",
        'temporal_header': "Temporal Analysis",
        'temporal_help': "Aggregates postings by upload_date and shows skill movement by month, quarter or year.",
        'temporal_granularity': "Temporal granularity",
        'temporal_granularity_options': {
            "monthly": "Monthly",
            "quarterly": "Quarterly",
            "yearly": "Yearly",
        },
        'forecast_periods': "Forecast periods",
        'top_k_skills': "Number of skills",
        'period_job_volume': "Job volume by period",
        'skill_time_series': "Skill time series",
        'baseline_forecast': "Baseline forecast",
        'statistical_evidence': "Statistical evidence",
        'statistical_evidence_help': "2x2 chi-square test on observed counts. It indicates statistical evidence for a difference, not causality or shortage proof.",
        'p_value': "p-value",
        'effect_size': "Effect size",
        'significant': "Significant",
        'not_significant': "Not significant",
        'submit_sectoral': "Run Sector Overview",
        'sectoral_time_mode': "Sectoral window",
        'sector_filter': "Sector filter (comma-separated)",
        'sectoral_time_options': {
            "latest": "Last 6 months",
            "selected_period": "Selected period",
            "year": "Year snapshot",
            "comparison": "Period comparison",
        },
        'sectoral_snapshot_year': "Sectoral snapshot year",
        'sectoral_reference_year': "Compare growth from",
        'comparison_years_prompt': "Choose the years to compare",
        'comparison_from_year': "From",
        'comparison_to_year': "To",
        'sectoral_year_bar_help': "Navigate available yearly sector snapshots.",
        'sectoral_year_bar_caption': "Sector snapshot {year}",
        'region_filter': "Region",
        'region_filter_help': "Filter the sector snapshot by location_code. GLOBAL uses the aggregated snapshot.",
        'regional_sectoral_country_filter': "Country filter",
        'regional_sectoral_region_help': "Filter regional distribution. ALL REGIONS shows all available real regions.",
        'sector_focus_help': "Choose the sector first; year and region filter the historical context.",
        'sector_overview_mode': "Sector view",
        'sector_overview_mode_options': {
            "snapshot": "Snapshot",
            "evolution": "Sector Evolution",
        },
        'sectoral_snapshot_header': "Yearly sector snapshot",
        'sectoral_snapshot_help': "Aggregated yearly view: one row per Tracker sector with job volume, share, top requested skills, and most frequent job titles.",
        'sectoral_snapshot_table': "Sector overview",
        'sectoral_snapshot_detail': "Sector focus",
        'sectoral_job_share': "Job share",
        'sector_evolution': "Sector Evolution",
        'sector_evolution_help': "Compares the selected sector with the chosen starting year.",
        'job_delta': "Net new jobs",
        'job_growth': "Job growth",
        'new_skills': "New skills",
        'disappeared_skills': "Disappeared skills",
        'growing_skills': "Growing skills",
        'declining_skills': "Declining skills",
        'skill_churn': "Skill churn",
        'top_new_skills': "Top new skills",
        'top_disappeared_skills': "Top disappeared skills",
        'top_growing_skills': "Top growing skills",
        'top_declining_skills': "Top declining skills",
        'no_new_skills': "No new skill detected.",
        'no_disappeared_skills': "No disappeared skill detected.",
        'no_growing_skills': "No growing skill detected.",
        'no_declining_skills': "No declining skill detected.",
        'refresh_failed': "Last snapshot refresh failed.",
        'refresh_last_success': "Last successful refresh",
        'refresh_resume': "Fetch resume",
        'refresh_jobs': "Fetched jobs",
        'evolution_count': "Count",
        'evolution_reference_count': "Reference count",
        'evolution_delta': "Delta",
        'sectoral_top_skills': "Top sector skills",
        'skill_portfolio': "Skill Portfolio",
        'skill_portfolio_help': "Maps sector skills by importance and transversality.",
        'sectoral_all_skills': "All sector skills",
        'skill_search': "Search skill",
        'sectoral_top_titles': "Top sector job titles",
        'comparison_header': "Sector Skills Comparison",
        'comparison_help': "Compare sectors and skills with a yearly heatmap.",
        'regional_sectoral_header': "Regional sector distribution",
        'regional_sectoral_help': "Shows the most represented sectors by region using yearly PostgreSQL snapshots.",
        'regional_sectoral_level': "Region level",
        'regional_sectoral_area': "Choose specific area",
        'regional_sectoral_top_k': "Sectors per area",
        'regional_sectoral_table': "Areas and top sectors",
        'regional_sectoral_chart': "Top sectors in area",
        'regional_sectoral_overview': "Regional distribution map",
        'regional_sectoral_visual': "Visualization",
        'regional_sectoral_visual_options': {
            "auto": "Auto",
            "map": "Geographic map",
            "treemap": "Area treemap",
        },
        'regional_sectoral_tabs': {
            "region_first": "Regions → Sectors",
            "sector_first": "Sector → Regions",
        },
        'sector_footprint_header': "Sector footprint map",
        'sector_footprint_help': "Choose a sector and see where that sector is strongest.",
        'sector_footprint_sector': "Sector",
        'sector_footprint_metric': "Color metric",
        'sector_footprint_metric_options': {
            "specialization": "Specialization",
            "share_in_region": "Share in region",
            "count": "Count",
        },
        'sector_footprint_note': "This view uses sectors returned in top_sectors for each area. Increase top_k for wider coverage.",
        'submit_regional_sectoral': "Run Regional Sector Distribution",
        'sector_count': "Sector count",
        'share_in_region': "Share in region",
        'comparison_metric': "Heatmap metric",
        'comparison_sectors': "Sectors to compare",
        'comparison_skills': "Skills to compare",
        'comparison_metric_options': {
            "share": "Share in sector",
            "count": "Count",
            "rank": "Rank",
            "growth": "Growth between years",
        },
        'submit_comparison': "Run Sector Skills Comparison",
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
        'tabs': ["📊 Job Demand", "📈 Trend Summary", "🗺️ Geographic Distribution", "🏭 Sectors & Employers"],
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
        'sector_demo_mode': "Enable demo sector snapshot",
        'sector_demo_mode_help': "Uses the fake dataset seeded in the Docker database to test Sector Overview without real Tracker data.",
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
        "Sector skills comparison": "Confronto settori-skill",
        "Selected sector focus": "Focus settore selezionato",
        "Statistical evidence": "Evidenza statistica",
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
        "skill_rank": "Posizione della skill nel settore selezionato ordinando per count decrescente.",
        "skill_reference_growth": "Variazione della skill tra anno selezionato e anno riferimento. Formula: (count_year - count_reference_year) / count_reference_year.",
        "sector_job_delta": "Differenza job del settore tra anno selezionato e anno di confronto. Formula: jobs_year - jobs_reference_year.",
        "sector_job_growth": "Crescita percentuale job del settore. Formula: (jobs_year - jobs_reference_year) / jobs_reference_year.",
        "sector_skill_churn": "Quanto cambia il portfolio skill del settore. Formula: (nuove skill + skill scomparse) / unione skill dei due anni.",
        "sector_new_skills": "Skill presenti nel settore nell'anno selezionato ma assenti nell'anno di confronto.",
        "sector_disappeared_skills": "Skill presenti nel settore nell'anno di confronto ma assenti nell'anno selezionato.",
        "sector_growing_skills": "Skill presenti in entrambi gli anni con count maggiore nell'anno selezionato.",
        "sector_declining_skills": "Skill presenti in entrambi gli anni con count minore nell'anno selezionato.",
        "coverage_unique_skills": "Copertura skill del settore. Formula: count(distinct skills in sector).",
        "dominance_top10_share": "Concentrazione delle top 10 skill. Formula: sum(top_10_skill_counts) / total_skill_mentions_in_sector.",
        "importance_in_sector": "Importanza della skill nel settore selezionato. Formula: skill_count_in_sector / total_skill_mentions_in_sector.",
        "sector_breadth": "Transversalità della skill. Formula: count(sectors where skill appears).",
        "dominant_share": "Quota della skill nel suo settore dominante. Formula: count_in_dominant_sector / count_in_all_sectors.",
        "categories_found": "Numero di settori Tracker API trovati nella risposta sectoral. Formula: count(items).",
        "regional_sector_count": "Numero di job del settore nella regione selezionata. Se un job ha più settori, contribuisce a ciascun settore.",
        "share_in_region": "Quota del settore nella regione. Formula: sector_jobs_region / total_jobs_region * 100.",
        "regional_sector_specialization": "Concentrazione settore-region rispetto al totale anno. Formula: sector_share_region / sector_share_global.",
        "temporal_forecast": "Proiezione baseline a breve termine. Formula: latest_count + media degli ultimi delta * step.",
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
        "skill_rank": "Skill position inside the selected sector sorted by descending count.",
        "skill_reference_growth": "Skill change between selected year and reference year. Formula: (count_year - count_reference_year) / count_reference_year.",
        "sector_job_delta": "Difference in sector jobs between selected year and comparison year. Formula: jobs_year - jobs_reference_year.",
        "sector_job_growth": "Sector job percentage growth. Formula: (jobs_year - jobs_reference_year) / jobs_reference_year.",
        "sector_skill_churn": "How much the sector skill portfolio changed. Formula: (new skills + disappeared skills) / union of skills across both years.",
        "sector_new_skills": "Skills present in the selected year but absent in the comparison year.",
        "sector_disappeared_skills": "Skills present in the comparison year but absent in the selected year.",
        "sector_growing_skills": "Skills present in both years with a higher count in the selected year.",
        "sector_declining_skills": "Skills present in both years with a lower count in the selected year.",
        "coverage_unique_skills": "Sector skill coverage. Formula: count(distinct skills in sector).",
        "dominance_top10_share": "Top-10 skill concentration. Formula: sum(top_10_skill_counts) / total_skill_mentions_in_sector.",
        "importance_in_sector": "Skill importance in selected sector. Formula: skill_count_in_sector / total_skill_mentions_in_sector.",
        "sector_breadth": "Skill transversality. Formula: count(sectors where skill appears).",
        "dominant_share": "Skill share in its dominant sector. Formula: count_in_dominant_sector / count_in_all_sectors.",
        "categories_found": "Number of Tracker API sectors found in sectoral response. Formula: count(items).",
        "regional_sector_count": "Number of sector jobs in the selected region. If a job has multiple sectors, it contributes to each sector.",
        "share_in_region": "Sector share inside the region. Formula: sector_jobs_region / total_jobs_region * 100.",
        "regional_sector_specialization": "Region-sector concentration versus the yearly total. Formula: sector_share_region / sector_share_global.",
        "temporal_forecast": "Short-term baseline projection. Formula: latest_count + average recent deltas * step.",
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


def get_sector_skills_comparison_data(api_base_url: str, payload: dict, timeout_seconds: int):
    try:
        res = requests.post(
            f"{normalize_api_base_url(api_base_url)}/sector-skills-comparison",
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


def get_regional_sectoral_data(api_base_url: str, payload: dict, timeout_seconds: int):
    try:
        res = requests.post(
            f"{normalize_api_base_url(api_base_url)}/regional-sectoral",
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


def get_temporal_projection_data(api_base_url: str, payload: dict, timeout_seconds: int):
    try:
        res = requests.post(
            f"{normalize_api_base_url(api_base_url)}/temporal-projections",
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


def get_statistical_comparison_data(api_base_url: str, payload: dict, timeout_seconds: int):
    try:
        res = requests.post(
            f"{normalize_api_base_url(api_base_url)}/statistical-comparison",
            data=payload,
            timeout=min(int(timeout_seconds), 60)
        )
    except requests.Timeout as exc:
        return {"_error": f"{T['server_timeout']} ({exc})"}
    except RequestException as exc:
        return {"_error": f"{T['server_error']} ({exc})"}

    if res.status_code == 200:
        return res.json()

    return {"_error": f"{T['server_http_error']} [HTTP {res.status_code}] {res.text[:500]}"}


def render_statistical_evidence(payload: dict):
    if not payload:
        return
    evidence = get_statistical_comparison_data(
        st.session_state.api_base_url,
        payload,
        st.session_state.backend_timeout,
    )
    with st.expander(T["statistical_evidence"], expanded=False):
        if not evidence or "_error" in evidence:
            st.info(evidence.get("_error", T["no_data"]) if isinstance(evidence, dict) else T["no_data"])
            return
        status_label = T["significant"] if evidence.get("significant") else T["not_significant"]
        c1, c2, c3 = st.columns(3)
        c1.metric(T["p_value"], evidence.get("p_value"))
        c2.metric(T["effect_size"], evidence.get("effect_size_label"))
        c3.metric(T["statistical_evidence"], status_label)
        st.caption(evidence.get("interpretation", ""))
        warnings = evidence.get("warnings") or []
        for warning in warnings:
            st.warning(warning)
        dev_info(
            "Statistical evidence",
            STATISTICAL_COMPARISON_ENDPOINT,
            {
                "method": "chi_square_2x2",
                "p_value": 0.013,
                "effect_size": 0.22,
                "effect_size_label": "small",
                "significant": True,
            },
            [
                "p_value",
                "statistic",
                "effect_size",
                "effect_size_label",
                "significant",
                "interpretation",
                "warnings[]",
            ],
            payload,
        )


def render_refresh_status_notice(response: dict):
    refresh_status = (response or {}).get("refresh_status") or {}
    if (response or {}).get("data_source") != "postgres":
        return
    if refresh_status.get("status") != "failed":
        return

    details = []
    if refresh_status.get("last_success_at"):
        details.append(f"{T['refresh_last_success']}: {refresh_status['last_success_at']}")
    if refresh_status.get("last_checkpoint_page"):
        details.append(f"{T['refresh_resume']}: page {refresh_status['last_checkpoint_page']}")
    fetched = refresh_status.get("fetched_jobs")
    expected = refresh_status.get("expected_jobs")
    if fetched or expected:
        details.append(f"{T['refresh_jobs']}: {fetched or 0}/{expected or 0}")
    if refresh_status.get("last_error"):
        details.append(str(refresh_status["last_error"])[:240])

    st.warning(f"{T['refresh_failed']} {' | '.join(details)}")


def build_skill_portfolio_rows(snapshot_sectors: list[dict], target_sector: dict):
    breadth = Counter()
    for sector in snapshot_sectors:
        for skill in sector.get("all_skills") or sector.get("top_skills", []):
            key = skill.get("skill_id") or skill.get("label")
            if key:
                breadth[key] += 1

    total_mentions = float(target_sector.get("total_skill_mentions") or 0)
    rows = []
    for skill in target_sector.get("all_skills") or target_sector.get("top_skills", []):
        key = skill.get("skill_id") or skill.get("label")
        count = int(skill.get("count", 0) or 0)
        category = "digital" if skill.get("is_digital") else "green" if skill.get("is_green") else "other"
        rows.append({
            "skill_id": key,
            "label": skill.get("label") or key,
            "count": count,
            "importance": skill.get("share_in_sector", round(count / total_mentions, 6) if total_mentions else 0.0),
            "sector_breadth": skill.get("sector_breadth", breadth.get(key, 1)),
            "category": category,
        })
    return rows


def format_growth_percentage(value):
    if value == "new_entry":
        return "new"
    if value is None:
        return "-"
    return f"{float(value) * 100:.1f}%"


def render_evolution_skill_table(title: str, rows: list[dict], help_text: str, key: str, empty_text: str):
    with st.expander(title, expanded=False):
        if not rows:
            st.write(empty_text)
            return
        df = pd.DataFrame(rows)
        display_cols = [c for c in ["label", "count", "reference_count", "delta"] if c in df.columns]
        st.dataframe(
            df[display_cols],
            width="stretch",
            column_config={
                "label": st.column_config.TextColumn(T["skill_label"]),
                "count": st.column_config.NumberColumn(T["evolution_count"], help=STAT_HELP["observed_skill_count"]),
                "reference_count": st.column_config.NumberColumn(T["evolution_reference_count"], help=help_text),
                "delta": st.column_config.NumberColumn(T["evolution_delta"], help=help_text),
            },
            key=key,
        )


def build_heatmap_tables(matrix_rows: list[dict]):
    df = pd.DataFrame(matrix_rows)
    if df.empty:
        return df, df, df
    z = df.pivot(index="sector_label", columns="label", values="value").fillna(0)
    text = df.pivot(index="sector_label", columns="label", values="display_value").fillna("")
    hover = df.pivot(index="sector_label", columns="label", values="skill_id").fillna("")
    return z, text, hover


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


def normalize_date_range(value, fallback):
    if isinstance(value, tuple) and len(value) == 2:
        return [pd.to_datetime(value[0]), pd.to_datetime(value[1])]
    if isinstance(value, list) and len(value) == 2:
        return [pd.to_datetime(value[0]), pd.to_datetime(value[1])]
    return fallback


ANALYZE_ENDPOINT = "POST /projector/analyze-skills"
SECTORAL_ENDPOINT = "POST /projector/sectoral-intelligence"
SECTORAL_SNAPSHOT_ENDPOINT = "POST /projector/sectoral-snapshot"
SECTOR_SKILLS_COMPARISON_ENDPOINT = "POST /projector/sector-skills-comparison"
REGIONAL_SECTORAL_ENDPOINT = "POST /projector/regional-sectoral"
EMERGING_ENDPOINT = "POST /projector/emerging-skills"
TEMPORAL_PROJECTIONS_ENDPOINT = "POST /projector/temporal-projections"
STATISTICAL_COMPARISON_ENDPOINT = "POST /projector/statistical-comparison"
HEALTH_ENDPOINT = "GET /projector/health"
STOP_ENDPOINT = "POST /projector/stop"


with st.sidebar:
    st.selectbox("Language / Lingua", ["Italiano", "English"],
                 index=0 if st.session_state.lang == 'IT' else 1,
                 on_change=change_lang, key="lang_choice")
    st.markdown("---")

    st.header(T['filters_header'])
    dashboard_options = T["dashboard_view_options"]
    dashboard_view_label = st.radio(
        T["dashboard_view"],
        list(dashboard_options.values()),
        horizontal=True,
    )
    dashboard_view = next(key for key, value in dashboard_options.items() if value == dashboard_view_label)

    keywords = ""
    location = ""
    date_range = [pd.to_datetime("2024-01-01"), pd.to_datetime("2024-12-31")]
    sectoral_location = None
    sectoral_mode = "year"
    sectoral_snapshot_year = int(st.session_state.sectoral_snapshot_year)
    sectoral_reference_year = int(st.session_state.sectoral_reference_year)
    sectoral_date_range = [pd.to_datetime("2024-01-01"), pd.to_datetime("2024-12-31")]
    sector_demo_mode = False
    compare_a_range = [pd.to_datetime("2023-01-01"), pd.to_datetime("2023-12-31")]
    compare_b_range = [pd.to_datetime("2024-01-01"), pd.to_datetime("2024-12-31")]
    submit_button = False
    sectoral_submit_button = False
    comparison_submit_button = False
    regional_sectoral_submit_button = False
    comparison_metric = "share"
    comparison_sectors = []
    comparison_skills = []
    regional_sectoral_level = "raw"
    regional_sectoral_top_k = 10
    regional_sectoral_visual = "auto"
    temporal_submit_button = False
    temporal_granularity = "monthly"
    temporal_forecast_periods = 1
    temporal_top_k = 10

    if dashboard_view == "skill":
        keywords = st.text_input(T['keywords'], "software")
        location = st.text_input(T['location'], "")
        date_range = normalize_date_range(st.date_input(T['date_range'], date_range), date_range)
        submit_button = st.button(T["submit_general"], use_container_width=True)
    elif dashboard_view == "temporal":
        keywords = st.text_input(T['keywords'], "software")
        location = st.text_input(T['location'], "")
        date_range = normalize_date_range(st.date_input(T['date_range'], date_range, key="temporal_date_range"), date_range)
        temporal_label = st.radio(
            T["temporal_granularity"],
            list(T["temporal_granularity_options"].values()),
            horizontal=True,
        )
        temporal_granularity = next(
            key for key, value in T["temporal_granularity_options"].items()
            if value == temporal_label
        )
        temporal_forecast_periods = st.number_input(
            T["forecast_periods"],
            min_value=0,
            max_value=12,
            value=1,
            step=1,
        )
        temporal_top_k = st.number_input(
            T["top_k_skills"],
            min_value=1,
            max_value=100,
            value=10,
            step=1,
        )
        temporal_submit_button = st.button(T["submit_temporal"], use_container_width=True)

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
    "include_sectoral": True,
    "sector_system": "nace",
    "sector_level": "nace_section",
    "sectoral_time_mode": "selected_period",
    "skill_group_level": 1,
    "occupation_level": 1,
}

sectoral_payload = {
    "locations": [sectoral_location] if sectoral_location else None,
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
    "reference_year": int(sectoral_reference_year),
    "locations": [sectoral_location] if sectoral_location else None,
}

comparison_payload = {
    "year": int(sectoral_snapshot_year),
    "reference_year": int(sectoral_reference_year),
    "locations": [sectoral_location] if sectoral_location else None,
    "sectors": comparison_sectors or None,
    "skills": comparison_skills or None,
    "metric": comparison_metric,
}

regional_sectoral_payload = {
    "year": int(sectoral_snapshot_year),
    "locations": [sectoral_location] if sectoral_location else None,
    "top_k": 10,
}

temporal_payload = {
    "keywords": [keywords] if keywords else None,
    "locations": [location] if location else None,
    "min_date": date_range[0].strftime("%Y-%m-%d"),
    "max_date": date_range[1].strftime("%Y-%m-%d"),
    "granularity": temporal_granularity,
    "forecast_periods": int(temporal_forecast_periods),
    "top_k": int(temporal_top_k),
}

if dashboard_view == "sector":
    current_year = int(st.session_state.sectoral_snapshot_year)
    default_reference = current_year - 1 if current_year - 1 in SECTOR_SNAPSHOT_YEARS else SECTOR_SNAPSHOT_YEARS[0]
    mode_options = T["sector_overview_mode_options"]
    current_mode = st.session_state.get("sector_overview_mode", "snapshot")
    top_sector, top_region, top_mode = st.columns([2, 1, 1])
    with top_sector:
        selected_sector_focus = st.selectbox(
            T["sectoral_snapshot_detail"],
            SECTOR_FOCUS_OPTIONS,
            index=SECTOR_FOCUS_OPTIONS.index(st.session_state.sector_focus_choice)
            if st.session_state.sector_focus_choice in SECTOR_FOCUS_OPTIONS else 0,
            help=T["sector_focus_help"],
            key="sector_focus_choice",
        )
    with top_region:
        selected_region = st.selectbox(
            T["region_filter"],
            list(REGIONAL_SECTORAL_REGION_OPTIONS.keys()),
            help=T["regional_sectoral_region_help"],
        )
    with top_mode:
        selected_mode_label = st.radio(
            T["sector_overview_mode"],
            list(mode_options.values()),
            index=list(mode_options.keys()).index(current_mode) if current_mode in mode_options else 0,
        )
    sector_overview_mode = next(key for key, value in mode_options.items() if value == selected_mode_label)

    sectoral_location = REGIONAL_SECTORAL_REGION_OPTIONS[selected_region]
    previous_region = st.session_state.get("sectoral_snapshot_region")
    previous_mode = st.session_state.get("sector_overview_mode", "snapshot")

    if sector_overview_mode == "snapshot":
        selected_year = st.select_slider(
            T["sectoral_snapshot_year"],
            options=SECTOR_SNAPSHOT_YEARS,
            value=current_year if current_year in SECTOR_SNAPSHOT_YEARS else SECTOR_SNAPSHOT_YEARS[-1],
            help=T["sectoral_year_bar_help"],
        )
        selected_reference_year = int(selected_year) - 1 if int(selected_year) - 1 in SECTOR_SNAPSHOT_YEARS else default_reference
        st.caption(T["sectoral_year_bar_caption"].format(year=int(selected_year)))
    else:
        st.caption(T["comparison_years_prompt"])
        c_from, c_to = st.columns(2)
        with c_from:
            selected_reference_year = st.selectbox(
                T["comparison_from_year"],
                SECTOR_SNAPSHOT_YEARS,
                index=SECTOR_SNAPSHOT_YEARS.index(default_reference),
            )
        with c_to:
            selected_year = st.selectbox(
                T["comparison_to_year"],
                SECTOR_SNAPSHOT_YEARS,
                index=SECTOR_SNAPSHOT_YEARS.index(current_year if current_year in SECTOR_SNAPSHOT_YEARS else SECTOR_SNAPSHOT_YEARS[-1]),
            )
        if int(selected_reference_year) == int(selected_year):
            st.warning(T["comparison_years_prompt"])

    previous_reference_year = int(st.session_state.get("sectoral_reference_year", default_reference))
    year_changed = int(selected_year) != current_year
    reference_changed = int(selected_reference_year) != previous_reference_year
    region_changed = previous_region != sectoral_location
    mode_changed = previous_mode != sector_overview_mode
    st.session_state.sectoral_snapshot_year = int(selected_year)
    st.session_state.sectoral_reference_year = int(selected_reference_year)
    st.session_state.sectoral_snapshot_region = sectoral_location
    st.session_state.sector_overview_mode = sector_overview_mode
    sectoral_snapshot_year = int(selected_year)
    sectoral_reference_year = int(selected_reference_year)
    sectoral_date_range = [
        pd.to_datetime(f"{sectoral_snapshot_year}-01-01"),
        pd.to_datetime(f"{sectoral_snapshot_year}-12-31"),
    ]
    sectoral_payload["snapshot_year"] = sectoral_snapshot_year
    sectoral_payload["min_date"] = sectoral_date_range[0].strftime("%Y-%m-%d")
    sectoral_payload["max_date"] = sectoral_date_range[1].strftime("%Y-%m-%d")
    sectoral_snapshot_payload["year"] = sectoral_snapshot_year
    sectoral_snapshot_payload["reference_year"] = sectoral_reference_year
    sectoral_snapshot_payload["locations"] = [sectoral_location] if sectoral_location else None
    sectoral_snapshot_payload["sectors"] = [selected_sector_focus]
    sectoral_submit_button = st.button(T["submit_sectoral"], use_container_width=True)
    if (year_changed or reference_changed or region_changed or mode_changed) and st.session_state.sectoral_snapshot_data:
        sectoral_submit_button = True
elif dashboard_view == "comparison":
    current_year = int(st.session_state.sectoral_snapshot_year)
    default_reference = current_year - 1 if current_year - 1 in SECTOR_SNAPSHOT_YEARS else SECTOR_SNAPSHOT_YEARS[0]
    comparison_metric_label = st.radio(
        T["comparison_metric"],
        list(T["comparison_metric_options"].values()),
        horizontal=True,
    )
    comparison_metric = next(
        key for key, value in T["comparison_metric_options"].items()
        if value == comparison_metric_label
    )
    if comparison_metric == "growth":
        st.caption(T["comparison_years_prompt"])
        c_year, c_ref, c_region = st.columns(3)
        with c_year:
            selected_reference_year = st.selectbox(
                T["comparison_from_year"],
                SECTOR_SNAPSHOT_YEARS,
                index=SECTOR_SNAPSHOT_YEARS.index(default_reference),
            )
        with c_ref:
            selected_year = st.selectbox(
                T["comparison_to_year"],
                SECTOR_SNAPSHOT_YEARS,
                index=SECTOR_SNAPSHOT_YEARS.index(current_year if current_year in SECTOR_SNAPSHOT_YEARS else SECTOR_SNAPSHOT_YEARS[-1]),
            )
        with c_region:
            selected_region = st.selectbox(
                T["region_filter"],
                list(SECTOR_REGION_OPTIONS.keys()),
                help=T["region_filter_help"],
            )
    else:
        c_year, c_ref, c_region = st.columns([2, 1, 1])
        with c_year:
            selected_year = st.select_slider(
                T["sectoral_snapshot_year"],
                options=SECTOR_SNAPSHOT_YEARS,
                value=current_year if current_year in SECTOR_SNAPSHOT_YEARS else SECTOR_SNAPSHOT_YEARS[-1],
                help=T["sectoral_year_bar_help"],
            )
        with c_ref:
            selected_reference_year = st.selectbox(
                T["sectoral_reference_year"],
                SECTOR_SNAPSHOT_YEARS,
                index=SECTOR_SNAPSHOT_YEARS.index(default_reference),
            )
        with c_region:
            selected_region = st.selectbox(
                T["region_filter"],
                list(SECTOR_REGION_OPTIONS.keys()),
                help=T["region_filter_help"],
            )
    sectoral_location = SECTOR_REGION_OPTIONS[selected_region]
    st.session_state.sectoral_snapshot_year = int(selected_year)
    st.session_state.sectoral_reference_year = int(selected_reference_year)
    sectoral_snapshot_year = int(selected_year)
    sectoral_reference_year = int(selected_reference_year)
    comparison_sectors = st.multiselect(
        T["comparison_sectors"],
        SECTOR_FOCUS_OPTIONS,
        default=SECTOR_FOCUS_OPTIONS[:5],
    )
    comparison_skills = st.multiselect(
        T["comparison_skills"],
        SECTOR_SKILL_OPTIONS,
        default=[],
    )
    comparison_payload = {
        "year": int(sectoral_snapshot_year),
        "reference_year": int(sectoral_reference_year),
        "locations": [sectoral_location] if sectoral_location else None,
        "sectors": comparison_sectors or None,
        "skills": comparison_skills or None,
        "metric": comparison_metric,
    }
    st.caption(T["sectoral_year_bar_caption"].format(year=sectoral_snapshot_year))
    comparison_submit_button = st.button(T["submit_comparison"], use_container_width=True)
elif dashboard_view == "regional_sectoral":
    current_year = int(st.session_state.sectoral_snapshot_year)
    selected_year = st.select_slider(
        T["sectoral_snapshot_year"],
        options=SECTOR_SNAPSHOT_YEARS,
        value=current_year if current_year in SECTOR_SNAPSHOT_YEARS else SECTOR_SNAPSHOT_YEARS[-1],
        help=T["sectoral_year_bar_help"],
    )
    regional_sectoral_level = st.radio(
        T["regional_sectoral_level"],
        ["raw", "nuts1", "nuts2", "nuts3"],
        horizontal=True,
    )
    visual_options = T["regional_sectoral_visual_options"]
    visual_label = st.radio(
        T["regional_sectoral_visual"],
        list(visual_options.values()),
        horizontal=True,
    )
    regional_sectoral_visual = next(key for key, value in visual_options.items() if value == visual_label)
    regional_sectoral_top_k = st.number_input(
        T["regional_sectoral_top_k"],
        min_value=1,
        max_value=25,
        value=10,
        step=1,
    )
    st.session_state.sectoral_snapshot_year = int(selected_year)
    sectoral_snapshot_year = int(selected_year)
    regional_sectoral_payload = {
        "year": int(sectoral_snapshot_year),
        "locations": None,
        "top_k": int(regional_sectoral_top_k),
    }
    st.caption(T["sectoral_year_bar_caption"].format(year=sectoral_snapshot_year))
    regional_sectoral_submit_button = st.button(T["submit_regional_sectoral"], use_container_width=True)

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
            st.session_state.sectoral_snapshot_data = None
            st.session_state.sectoral_data = None
            st.session_state.sector_skills_comparison_data = None
            st.session_state.regional_sectoral_data = None
            st.session_state.temporal_projection_data = None
        else:
            error_msg = data.get("_error", T['server_error']) if isinstance(data, dict) else T['server_error']
            st.error(error_msg)

if temporal_submit_button:
    with st.spinner(f"🚀 {T['loading']}"):
        temporal_response = get_temporal_projection_data(
            st.session_state.api_base_url,
            temporal_payload,
            st.session_state.backend_timeout
        )
        if temporal_response and "_error" not in temporal_response:
            st.session_state.temporal_projection_data = temporal_response
            st.session_state.all_data = None
            st.session_state.sectoral_snapshot_data = None
            st.session_state.sectoral_data = None
            st.session_state.sector_skills_comparison_data = None
            st.session_state.regional_sectoral_data = None
        else:
            error_msg = temporal_response.get("_error", T['server_error']) if isinstance(temporal_response, dict) else T['server_error']
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
            st.session_state.all_data = None
            st.session_state.sectoral_data = None
            st.session_state.sector_skills_comparison_data = None
            st.session_state.regional_sectoral_data = None
            st.session_state.temporal_projection_data = None
        else:
            error_msg = sectoral_response.get("_error", T['server_error']) if isinstance(sectoral_response, dict) else T['server_error']
            st.error(error_msg)

if comparison_submit_button:
    with st.spinner(f"🚀 {T['loading']}"):
        comparison_response = get_sector_skills_comparison_data(
            st.session_state.api_base_url,
            comparison_payload,
            st.session_state.backend_timeout
        )
        if comparison_response and "_error" not in comparison_response:
            st.session_state.sector_skills_comparison_data = comparison_response
            st.session_state.sectoral_snapshot_data = None
            st.session_state.all_data = None
            st.session_state.sectoral_data = None
            st.session_state.regional_sectoral_data = None
            st.session_state.temporal_projection_data = None
        else:
            error_msg = comparison_response.get("_error", T['server_error']) if isinstance(comparison_response, dict) else T['server_error']
            st.error(error_msg)

if regional_sectoral_submit_button:
    with st.spinner(f"🚀 {T['loading']}"):
        regional_sectoral_response = get_regional_sectoral_data(
            st.session_state.api_base_url,
            regional_sectoral_payload,
            st.session_state.backend_timeout
        )
        if regional_sectoral_response and "_error" not in regional_sectoral_response:
            st.session_state.regional_sectoral_data = regional_sectoral_response
            st.session_state.sector_skills_comparison_data = None
            st.session_state.sectoral_snapshot_data = None
            st.session_state.all_data = None
            st.session_state.sectoral_data = None
            st.session_state.temporal_projection_data = None
        else:
            error_msg = regional_sectoral_response.get("_error", T['server_error']) if isinstance(regional_sectoral_response, dict) else T['server_error']
            st.error(error_msg)

# --- LOGICA DI RENDERING ---
# Mostriamo i risultati se almeno una analisi è presente nello stato della sessione
if st.session_state.all_data or st.session_state.sectoral_data or st.session_state.sectoral_snapshot_data or st.session_state.sector_skills_comparison_data or st.session_state.regional_sectoral_data or st.session_state.temporal_projection_data:
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
    sector_skills_comparison_response = st.session_state.sector_skills_comparison_data or {}
    regional_sectoral_response = st.session_state.regional_sectoral_data or {}
    temporal_projection_response = st.session_state.temporal_projection_data or {}
    ins = all_data["insights"]
    summary = all_data["dimension_summary"]

    if dashboard_view in {"sector", "comparison", "regional_sectoral", "temporal"}:
        tab4 = st.container()
    else:
        tab1, tab2, tab3, tab4 = st.tabs(T['tabs'])

    if dashboard_view == "skill":
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
                    st.plotly_chart(fig, width="stretch", key="skill_ranking_chart")
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
                            st.plotly_chart(fig_trend, width="stretch", key="skill_trend_chart")

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
                    st.plotly_chart(fig_map, width="stretch", key="geo_map_chart")
                with c_stat:
                    st.plotly_chart(px.pie(df_geo, values='job_count', names='location', hole=0.4),
                                    width="stretch",
                                    key="geo_pie_chart")
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
                    st.plotly_chart(fig_reg, width="stretch", key=f"regional_skills_{target_code}")

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

        if dashboard_view == "regional_sectoral":
            h_main, h_info = st.columns([8, 1])
            with h_main:
                st.header(T["regional_sectoral_header"], help=T["regional_sectoral_help"])
            with h_info:
                dev_info(
                    "Regional Sector Distribution",
                    REGIONAL_SECTORAL_ENDPOINT,
                    {
                        "status": "completed",
                        "year": 2024,
                        "data_source": "postgres",
                        "window": {
                            "label": "2024 snapshot",
                            "min_date": "2024-01-01",
                            "max_date": "2024-12-31"
                        },
                        "regional_sectoral": {
                            "raw": [
                                {
                                    "code": "IT",
                                    "total_jobs": 120,
                                    "top_sectors": [
                                        {
                                            "sector": "Manufacturing",
                                            "sector_code": "Manufacturing",
                                            "count": 34,
                                            "share_in_region": 28.33,
                                            "specialization": 1.42
                                        }
                                    ]
                                }
                            ],
                            "nuts1": [],
                            "nuts2": [],
                            "nuts3": []
                        }
                    },
                    [
                        "status",
                        "year",
                        "data_source",
                        "window.label",
                        "regional_sectoral.raw[]",
                        "regional_sectoral.nuts1[]",
                        "regional_sectoral.nuts2[]",
                        "regional_sectoral.nuts3[]",
                        "area.code",
                        "area.total_jobs",
                        "area.top_sectors[].sector",
                        "area.top_sectors[].sector_code",
                        "area.top_sectors[].count",
                        "area.top_sectors[].share_in_region",
                        "area.top_sectors[].specialization"
                    ],
                    regional_sectoral_payload
                )

            render_refresh_status_notice(regional_sectoral_response)
            regional_payload = regional_sectoral_response.get("regional_sectoral", {})
            regions_for_level = regional_payload.get(regional_sectoral_level, [])
            if regions_for_level:
                iso_mapping = {"IT": "ITA", "FR": "FRA", "DE": "DEU", "ES": "ESP", "GB": "GBR", "EL": "GRC", "SE": "SWE"}
                all_sector_options = sorted({
                    sector.get("sector")
                    for area in regions_for_level
                    for sector in area.get("top_sectors", [])
                    if sector.get("sector")
                })
                region_first_tab, sector_first_tab = st.tabs([
                    T["regional_sectoral_tabs"]["region_first"],
                    T["regional_sectoral_tabs"]["sector_first"],
                ])

                with region_first_tab:
                    selected_region_filter = st.selectbox(
                        T["regional_sectoral_country_filter"],
                        list(REGIONAL_SECTORAL_REGION_OPTIONS.keys()),
                        help=T["regional_sectoral_region_help"],
                        key=f"regional_sectoral_region_filter_{regional_sectoral_level}",
                    )
                    selected_location = REGIONAL_SECTORAL_REGION_OPTIONS[selected_region_filter]
                    selected_regions = [
                        area for area in regions_for_level
                        if (
                            not selected_location
                            or str(area.get("code", "")).upper() == selected_location
                            or str(area.get("code", "")).upper().startswith(selected_location)
                        )
                    ]
                    summary_rows = []
                    for area in selected_regions:
                        top_sectors = area.get("top_sectors", [])
                        leading = top_sectors[0] if top_sectors else {}
                        summary_rows.append({
                            "code": area.get("code"),
                            "total_jobs": area.get("total_jobs", 0),
                            "top_sector": leading.get("sector", "-"),
                            "top_sector_count": leading.get("count", 0),
                            "top_sector_share": leading.get("share_in_region", 0),
                            "top_sector_specialization": leading.get("specialization", 0),
                        })

                    df_region_summary = pd.DataFrame(
                        summary_rows,
                        columns=[
                            "code",
                            "total_jobs",
                            "top_sector",
                            "top_sector_count",
                            "top_sector_share",
                            "top_sector_specialization",
                        ],
                    )
                    if df_region_summary.empty:
                        st.info(T["no_data"])

                    can_map = (
                        regional_sectoral_level == "raw"
                        and not df_region_summary.empty
                        and df_region_summary["code"].astype(str).isin(iso_mapping.keys()).any()
                    )
                    visual_mode = regional_sectoral_visual
                    if visual_mode == "auto":
                        visual_mode = "map" if can_map else "treemap"
                    if visual_mode == "map" and not can_map:
                        st.info(T["regional_no_level"].format(strategy=T["regional_sectoral_visual_options"]["map"]))
                        visual_mode = "treemap"

                    st.subheader(T["regional_sectoral_overview"])
                    if visual_mode == "map":
                        df_map = df_region_summary.copy()
                        df_map["iso_alpha_3"] = df_map["code"].map(iso_mapping)
                        df_map = df_map.dropna(subset=["iso_alpha_3"])
                        fig_regional_map = px.choropleth(
                            df_map,
                            locations="iso_alpha_3",
                            color="top_sector_specialization",
                            hover_name="code",
                            hover_data={
                                "total_jobs": True,
                                "top_sector": True,
                                "top_sector_share": True,
                                "top_sector_specialization": True,
                                "iso_alpha_3": False,
                            },
                            color_continuous_scale="RdYlGn",
                            projection="natural earth",
                            title=T["regional_sectoral_overview"],
                        )
                        st.plotly_chart(fig_regional_map, width="stretch", key="regional_sectoral_map")
                    else:
                        fig_regional_tree = px.treemap(
                            df_region_summary,
                            path=["code", "top_sector"],
                            values="total_jobs",
                            color="top_sector_specialization",
                            color_continuous_scale="RdYlGn",
                            hover_data=["top_sector_count", "top_sector_share", "top_sector_specialization"],
                            title=T["regional_sectoral_overview"],
                        )
                        st.plotly_chart(
                            fig_regional_tree,
                            width="stretch",
                            key=f"regional_sectoral_treemap_{regional_sectoral_level}",
                        )

                    st.subheader(T["regional_sectoral_table"])
                    st.dataframe(
                        df_region_summary,
                        use_container_width=True,
                        column_config={
                            "total_jobs": st.column_config.NumberColumn(T["jobs_analyzed"], help=STAT_HELP["jobs_analyzed"]),
                            "top_sector_count": st.column_config.NumberColumn(T["sector_count"], help=STAT_HELP["regional_sector_count"]),
                            "top_sector_share": st.column_config.NumberColumn(T["share_in_region"], help=STAT_HELP["share_in_region"]),
                            "top_sector_specialization": st.column_config.NumberColumn(T["specialization_label"], help=STAT_HELP["regional_sector_specialization"]),
                        }
                    )

                    area_codes = [item.get("code") for item in selected_regions]
                    if area_codes:
                        selected_area = st.selectbox(T["regional_sectoral_area"], area_codes)
                        target_area = next(item for item in selected_regions if item.get("code") == selected_area)
                        sector_rows = target_area.get("top_sectors", [])
                        if sector_rows:
                            df_region_sectors = pd.DataFrame(sector_rows)
                            fig_region_sector = px.bar(
                                df_region_sectors,
                                x="count",
                                y="sector",
                                orientation="h",
                                color="specialization",
                                color_continuous_scale="RdYlGn",
                                labels={
                                    "sector": T["agg_level"],
                                    "count": T["sector_count"],
                                    "specialization": T["specialization_label"],
                                },
                                title=f"{T['regional_sectoral_chart']}: {selected_area}",
                            )
                            fig_region_sector.update_layout(yaxis={"categoryorder": "total ascending"}, height=420)
                            st.plotly_chart(
                                fig_region_sector,
                                width="stretch",
                                key=f"regional_sectoral_{regional_sectoral_level}_{selected_area}",
                            )
                            st.dataframe(
                                df_region_sectors,
                                use_container_width=True,
                                column_config={
                                    "count": st.column_config.NumberColumn(T["sector_count"], help=STAT_HELP["regional_sector_count"]),
                                    "share_in_region": st.column_config.NumberColumn(T["share_in_region"], help=STAT_HELP["share_in_region"]),
                                    "specialization": st.column_config.NumberColumn(T["specialization_label"], help=STAT_HELP["regional_sector_specialization"]),
                                }
                            )

                with sector_first_tab:
                    if all_sector_options:
                        st.subheader(T["sector_footprint_header"], help=T["sector_footprint_help"])
                        c_sector, c_metric = st.columns([2, 1])
                        with c_sector:
                            selected_footprint_sector = st.selectbox(
                                T["sector_footprint_sector"],
                                all_sector_options,
                                key=f"sector_footprint_sector_{regional_sectoral_level}",
                            )
                        with c_metric:
                            footprint_metric_options = T["sector_footprint_metric_options"]
                            selected_metric_label = st.radio(
                                T["sector_footprint_metric"],
                                list(footprint_metric_options.values()),
                                horizontal=True,
                            )
                            selected_footprint_metric = next(
                                key for key, value in footprint_metric_options.items()
                                if value == selected_metric_label
                            )

                        footprint_rows = []
                        for area in regions_for_level:
                            match = next(
                                (
                                    sector for sector in area.get("top_sectors", [])
                                    if sector.get("sector") == selected_footprint_sector
                                ),
                                None,
                            )
                            if not match:
                                continue
                            footprint_rows.append({
                                "code": area.get("code"),
                                "total_jobs": area.get("total_jobs", 0),
                                "sector": match.get("sector"),
                                "sector_code": match.get("sector_code"),
                                "count": match.get("count", 0),
                                "share_in_region": match.get("share_in_region", 0),
                                "specialization": match.get("specialization", 0),
                            })

                        if footprint_rows:
                            df_footprint = pd.DataFrame(footprint_rows)
                            footprint_can_map = (
                                regional_sectoral_level == "raw"
                                and df_footprint["code"].astype(str).isin(iso_mapping.keys()).any()
                            )
                            footprint_visual = regional_sectoral_visual
                            if footprint_visual == "auto":
                                footprint_visual = "map" if footprint_can_map else "treemap"
                            if footprint_visual == "map" and not footprint_can_map:
                                footprint_visual = "treemap"

                            if footprint_visual == "map":
                                df_footprint_map = df_footprint.copy()
                                df_footprint_map["iso_alpha_3"] = df_footprint_map["code"].map(iso_mapping)
                                df_footprint_map = df_footprint_map.dropna(subset=["iso_alpha_3"])
                                fig_footprint = px.choropleth(
                                    df_footprint_map,
                                    locations="iso_alpha_3",
                                    color=selected_footprint_metric,
                                    hover_name="code",
                                    hover_data={
                                        "total_jobs": True,
                                        "sector": True,
                                        "count": True,
                                        "share_in_region": True,
                                        "specialization": True,
                                        "iso_alpha_3": False,
                                    },
                                    color_continuous_scale="RdYlGn",
                                    projection="natural earth",
                                    title=f"{T['sector_footprint_header']}: {selected_footprint_sector}",
                                )
                                st.plotly_chart(
                                    fig_footprint,
                                    width="stretch",
                                    key=f"sector_footprint_map_{regional_sectoral_level}_{selected_footprint_sector}",
                                )
                            else:
                                fig_footprint = px.treemap(
                                    df_footprint,
                                    path=["code", "sector"],
                                    values="count",
                                    color=selected_footprint_metric,
                                    color_continuous_scale="RdYlGn",
                                    hover_data=["total_jobs", "share_in_region", "specialization"],
                                    title=f"{T['sector_footprint_header']}: {selected_footprint_sector}",
                                )
                                st.plotly_chart(
                                    fig_footprint,
                                    width="stretch",
                                    key=f"sector_footprint_treemap_{regional_sectoral_level}_{selected_footprint_sector}",
                                )

                            st.caption(T["sector_footprint_note"])
                            st.dataframe(
                                df_footprint.sort_values(selected_footprint_metric, ascending=False),
                                use_container_width=True,
                                column_config={
                                    "count": st.column_config.NumberColumn(T["sector_count"], help=STAT_HELP["regional_sector_count"]),
                                    "share_in_region": st.column_config.NumberColumn(T["share_in_region"], help=STAT_HELP["share_in_region"]),
                                    "specialization": st.column_config.NumberColumn(T["specialization_label"], help=STAT_HELP["regional_sector_specialization"]),
                                }
                            )
            elif regional_sectoral_response.get("message"):
                st.info(regional_sectoral_response["message"])
            else:
                st.info(T["no_data"])
            st.stop()

        if dashboard_view == "temporal":
            h_main, h_info = st.columns([8, 1])
            with h_main:
                st.header(T["temporal_header"], help=T["temporal_help"])
            with h_info:
                dev_info(
                    "Temporal analysis",
                    TEMPORAL_PROJECTIONS_ENDPOINT,
                    {
                        "status": "completed",
                        "total_jobs": 120,
                        "insights": {
                            "granularity": "quarterly",
                            "forecast_method": "last_delta_baseline",
                            "periods": [
                                {
                                    "period": "2024-Q1",
                                    "job_count": 30,
                                    "growth_vs_previous": None,
                                }
                            ],
                            "skills": [
                                {
                                    "name": "Python",
                                    "growth_rate": 20.0,
                                    "series": [{"period": "2024-Q1", "count": 8}],
                                    "forecast": [{"period": "2025-Q1", "projected_count": 14.0}],
                                }
                            ],
                        },
                    },
                    [
                        "total_jobs",
                        "insights.granularity",
                        "insights.periods[].period",
                        "insights.periods[].job_count",
                        "insights.periods[].growth_vs_previous",
                        "insights.skills[].name",
                        "insights.skills[].growth_rate",
                        "insights.skills[].series[].count",
                        "insights.skills[].forecast[].projected_count",
                    ],
                    temporal_payload,
                )

            temporal_insights = temporal_projection_response.get("insights", {})
            periods = temporal_insights.get("periods", [])
            skills = temporal_insights.get("skills", [])
            if periods:
                df_periods = pd.DataFrame(periods)
                metric_with_info(
                    T["jobs_analyzed"],
                    temporal_projection_response.get("total_jobs", 0),
                    STAT_HELP["jobs_analyzed"],
                )
                fig_periods = px.line(
                    df_periods,
                    x="period",
                    y="job_count",
                    markers=True,
                    title=T["period_job_volume"],
                )
                st.plotly_chart(fig_periods, width="stretch", key="temporal_period_job_volume")

            if skills:
                series_rows = []
                forecast_rows = []
                for skill in skills:
                    for row in skill.get("series", []):
                        series_rows.append({
                            "skill": skill.get("name"),
                            "period": row.get("period"),
                            "count": row.get("count"),
                            "growth_vs_previous": row.get("growth_vs_previous"),
                        })
                    for row in skill.get("forecast", []):
                        forecast_rows.append({
                            "skill": skill.get("name"),
                            "period": row.get("period"),
                            "projected_count": row.get("projected_count"),
                            "method": row.get("method"),
                        })

                df_series = pd.DataFrame(series_rows)
                if not df_series.empty:
                    fig_skills = px.line(
                        df_series,
                        x="period",
                        y="count",
                        color="skill",
                        markers=True,
                        title=T["skill_time_series"],
                    )
                    st.plotly_chart(fig_skills, width="stretch", key="temporal_skill_time_series")
                    st.dataframe(
                        df_series,
                        width="stretch",
                        column_config={
                            "count": st.column_config.NumberColumn("count (i)", help=STAT_HELP["skill_frequency"]),
                            "growth_vs_previous": st.column_config.TextColumn("growth (i)", help=STAT_HELP["skill_growth"]),
                        },
                    )
                    period_totals = {row.get("period"): row.get("job_count", 0) for row in periods}
                    evidence_skill = next(
                        (
                            skill for skill in skills
                            if len(skill.get("series", [])) >= 2
                        ),
                        None,
                    )
                    if evidence_skill:
                        evidence_series = evidence_skill.get("series", [])
                        previous_row = evidence_series[-2]
                        current_row = evidence_series[-1]
                        current_period = current_row.get("period")
                        previous_period = previous_row.get("period")
                        statistical_payload = {
                            "comparison_type": "temporal",
                            "group_a_label": f"{evidence_skill.get('name')} in {current_period}",
                            "group_a_count": int(current_row.get("count", 0)),
                            "group_a_total": int(period_totals.get(current_period, 0)),
                            "group_b_label": f"{evidence_skill.get('name')} in {previous_period}",
                            "group_b_count": int(previous_row.get("count", 0)),
                            "group_b_total": int(period_totals.get(previous_period, 0)),
                            "alpha": 0.05,
                        }
                        if statistical_payload["group_a_total"] and statistical_payload["group_b_total"]:
                            render_statistical_evidence(statistical_payload)

                df_forecast = pd.DataFrame(forecast_rows)
                if not df_forecast.empty:
                    st.subheader(T["baseline_forecast"], help=STAT_HELP["temporal_forecast"])
                    st.dataframe(df_forecast, width="stretch")
            else:
                st.info(T["no_data"])
            st.stop()

        if dashboard_view == "comparison":
            h_main, h_info = st.columns([8, 1])
            with h_main:
                st.header(T["comparison_header"], help=T["comparison_help"])
            with h_info:
                dev_info(
                    "Sector skills comparison",
                    SECTOR_SKILLS_COMPARISON_ENDPOINT,
                    {
                        "status": "completed",
                        "year": 2024,
                        "reference_year": 2023,
                        "data_source": "postgres",
                        "metric": "share",
                        "window": {
                            "label": "2024 snapshot",
                            "min_date": "2024-01-01",
                            "max_date": "2024-12-31"
                        },
                        "sectors": ["ICT", "Education"],
                        "skills": ["Python", "SQL"],
                        "matrix": [
                            {
                                "sector": "ICT",
                                "sector_label": "ICT",
                                "skill_id": "skill-python",
                                "label": "Python",
                                "count": 188,
                                "share": 0.149,
                                "rank": 1,
                                "rank_score": 1.0,
                                "growth": 0.24,
                                "growth_value": 0.24,
                                "value": 0.149,
                                "display_value": "0.149",
                                "is_green": False,
                                "is_digital": True
                            }
                        ],
                        "message": None
                    },
                    [
                        "status",
                        "year",
                        "reference_year",
                        "data_source",
                        "metric",
                        "window.label",
                        "window.min_date",
                        "window.max_date",
                        "sectors[]",
                        "skills[]",
                        "matrix[].sector",
                        "matrix[].sector_label",
                        "matrix[].skill_id",
                        "matrix[].label",
                        "matrix[].count",
                        "matrix[].share",
                        "matrix[].rank",
                        "matrix[].rank_score",
                        "matrix[].growth",
                        "matrix[].growth_value",
                        "matrix[].value",
                        "matrix[].display_value",
                        "matrix[].is_green",
                        "matrix[].is_digital",
                        "message"
                    ],
                    comparison_payload
                )

            comparison_rows = sector_skills_comparison_response.get("matrix", [])
            render_refresh_status_notice(sector_skills_comparison_response)
            if comparison_rows:
                z, text, hover = build_heatmap_tables(comparison_rows)
                colorscale = "Viridis" if sector_skills_comparison_response.get("metric") != "growth" else "RdYlGn"
                fig_heatmap = go.Figure(data=go.Heatmap(
                    z=z.values,
                    x=list(z.columns),
                    y=list(z.index),
                    text=text.values,
                    customdata=hover.values,
                    texttemplate="%{text}",
                    colorscale=colorscale,
                    colorbar={"title": sector_skills_comparison_response.get("metric", "share")},
                    hovertemplate=(
                        "Sector: %{y}<br>"
                        "Skill: %{x}<br>"
                        "Skill ID: %{customdata}<br>"
                        "Value: %{z}<br>"
                        "Display: %{text}<extra></extra>"
                    ),
                ))
                fig_heatmap.update_layout(
                    xaxis_title=T["skill_label"],
                    yaxis_title=T["agg_level"],
                    height=max(420, 80 + len(z.index) * 45),
                )
                st.plotly_chart(fig_heatmap, width="stretch", key="sector_skills_comparison_heatmap")
                st.dataframe(
                    pd.DataFrame(comparison_rows),
                    use_container_width=True,
                    column_config={
                        "count": st.column_config.NumberColumn("count", help=STAT_HELP["observed_skill_count"]),
                        "share": st.column_config.NumberColumn("share", help=STAT_HELP["observed_skill_frequency"]),
                        "rank": st.column_config.NumberColumn("rank", help=STAT_HELP["sector_mentions"]),
                        "growth_value": st.column_config.NumberColumn("growth", help=STAT_HELP["skill_growth"]),
                    }
                )
                df_comparison = pd.DataFrame(comparison_rows)
                if {"sector_label", "label", "count", "share"}.issubset(df_comparison.columns):
                    sectors_for_test = [s for s in df_comparison["sector_label"].dropna().unique().tolist()]
                    skills_for_test = [s for s in df_comparison["label"].dropna().unique().tolist()]
                    if len(sectors_for_test) >= 2 and skills_for_test:
                        selected_skill_for_test = skills_for_test[0]
                        row_a = df_comparison[
                            (df_comparison["sector_label"] == sectors_for_test[0])
                            & (df_comparison["label"] == selected_skill_for_test)
                        ]
                        row_b = df_comparison[
                            (df_comparison["sector_label"] == sectors_for_test[1])
                            & (df_comparison["label"] == selected_skill_for_test)
                        ]
                        if not row_a.empty and not row_b.empty:
                            row_a = row_a.iloc[0]
                            row_b = row_b.iloc[0]
                            share_a = float(row_a.get("share") or 0)
                            share_b = float(row_b.get("share") or 0)
                            total_a = int(round(float(row_a.get("count", 0)) / share_a)) if share_a > 0 else 0
                            total_b = int(round(float(row_b.get("count", 0)) / share_b)) if share_b > 0 else 0
                            if total_a and total_b:
                                render_statistical_evidence(
                                    {
                                        "comparison_type": "sector_skill",
                                        "group_a_label": f"{selected_skill_for_test} in {sectors_for_test[0]}",
                                        "group_a_count": int(row_a.get("count", 0)),
                                        "group_a_total": total_a,
                                        "group_b_label": f"{selected_skill_for_test} in {sectors_for_test[1]}",
                                        "group_b_count": int(row_b.get("count", 0)),
                                        "group_b_total": total_b,
                                        "alpha": 0.05,
                                    }
                                )
            elif sector_skills_comparison_response.get("message"):
                st.info(sector_skills_comparison_response["message"])
            else:
                st.info(T["no_data"])
            st.stop()

        active_sectoral = (
            sectoral_response.get("items", [])
            or ins.get("sectoral", [])
            or ((ins.get("sectoral_views", {}).get("nace", {}) or {}).get("items", []))
        )
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
        snapshot_target = None
        render_refresh_status_notice(sectoral_snapshot_response)
        if snapshot_sectors:
            h_main, h_info = st.columns([8, 1])
            with h_main:
                st.header(T["sectoral_snapshot_header"], help=T["sectoral_snapshot_help"])
            with h_info:
                dev_info(
                    "Sectoral snapshot",
                    SECTORAL_SNAPSHOT_ENDPOINT,
                    {
                        "status": "completed",
                        "year": 2024,
                        "reference_year": 2023,
                        "data_source": "postgres",
                        "window": {
                            "label": "2024 snapshot",
                            "min_date": "2024-01-01",
                            "max_date": "2024-12-31"
                        },
                        "total_jobs": 1280,
                        "sector_filter": [],
                        "sectors": [
                            {
                                "sector": "Information and communication",
                                "sector_label": "Information and communication",
                                "job_count": 420,
                                "job_share": 0.3281,
                                "total_skill_mentions": 1260,
                                "unique_skills": 38,
                                "evolution": {
                                    "reference_year": 2023,
                                    "job_count_current": 420,
                                    "job_count_reference": 360,
                                    "job_delta": 60,
                                    "job_growth_percentage": 0.1667,
                                    "job_growth_value": 0.1667,
                                    "new_skill_count": 4,
                                    "disappeared_skill_count": 2,
                                    "growing_skill_count": 12,
                                    "declining_skill_count": 7,
                                    "skill_churn": 0.1579,
                                    "top_new_skills": [
                                        {"skill_id": "skill-ai", "label": "artificial intelligence", "count": 26, "reference_count": 0, "delta": 26}
                                    ],
                                    "top_disappeared_skills": [
                                        {"skill_id": "skill-flash", "label": "Adobe Flash", "count": 0, "reference_count": 8, "delta": -8}
                                    ],
                                    "top_growing_skills": [
                                        {"skill_id": "skill-python", "label": "Python", "count": 188, "reference_count": 152, "delta": 36}
                                    ],
                                    "top_declining_skills": [
                                        {"skill_id": "skill-legacy", "label": "legacy systems", "count": 12, "reference_count": 30, "delta": -18}
                                    ]
                                },
                                "top_skills": [
                                    {
                                        "skill_id": "skill-python",
                                        "label": "Python",
                                        "count": 188,
                                        "frequency": 0.1492,
                                        "share_in_sector": 0.1492,
                                        "rank": 1,
                                        "growth_vs_reference_year": 0.24,
                                        "growth_value": 0.24,
                                        "sector_breadth": 4,
                                        "is_green": False,
                                        "is_digital": True
                                    }
                                ],
                                "all_skills": [
                                    {
                                        "skill_id": "skill-python",
                                        "label": "Python",
                                        "count": 188,
                                        "frequency": 0.1492,
                                        "share_in_sector": 0.1492,
                                        "rank": 1,
                                        "growth_vs_reference_year": 0.24,
                                        "growth_value": 0.24,
                                        "sector_breadth": 4,
                                        "is_green": False,
                                        "is_digital": True
                                    },
                                    {
                                        "skill_id": "skill-sustainability",
                                        "label": "sustainability",
                                        "count": 16,
                                        "frequency": 0.0127,
                                        "share_in_sector": 0.0127,
                                        "rank": 14,
                                        "growth_vs_reference_year": "new_entry",
                                        "growth_value": 1.0,
                                        "sector_breadth": 3,
                                        "is_green": True,
                                        "is_digital": False
                                    }
                                ],
                                "top_job_titles": [
                                    {"name": "Software Engineer", "count": 86}
                                ]
                            }
                        ],
                        "message": None
                    },
                    [
                        "status",
                        "year",
                        "reference_year",
                        "data_source",
                        "window.label",
                        "window.min_date",
                        "window.max_date",
                        "total_jobs",
                        "sector_filter[]",
                        "sectors[].sector",
                        "sectors[].sector_label",
                        "sectors[].job_count",
                        "sectors[].job_share",
                        "sectors[].total_skill_mentions",
                        "sectors[].unique_skills",
                        "sectors[].evolution.reference_year",
                        "sectors[].evolution.job_count_current",
                        "sectors[].evolution.job_count_reference",
                        "sectors[].evolution.job_delta",
                        "sectors[].evolution.job_growth_percentage",
                        "sectors[].evolution.new_skill_count",
                        "sectors[].evolution.disappeared_skill_count",
                        "sectors[].evolution.growing_skill_count",
                        "sectors[].evolution.declining_skill_count",
                        "sectors[].evolution.skill_churn",
                        "sectors[].evolution.top_new_skills[]",
                        "sectors[].evolution.top_disappeared_skills[]",
                        "sectors[].evolution.top_growing_skills[]",
                        "sectors[].evolution.top_declining_skills[]",
                        "sectors[].top_skills[].skill_id",
                        "sectors[].top_skills[].label",
                        "sectors[].top_skills[].count",
                        "sectors[].top_skills[].frequency",
                        "sectors[].top_skills[].share_in_sector",
                        "sectors[].top_skills[].rank",
                        "sectors[].top_skills[].growth_vs_reference_year",
                        "sectors[].top_skills[].growth_value",
                        "sectors[].top_skills[].sector_breadth",
                        "sectors[].top_skills[].is_green",
                        "sectors[].top_skills[].is_digital",
                        "sectors[].all_skills[].skill_id",
                        "sectors[].all_skills[].label",
                        "sectors[].all_skills[].count",
                        "sectors[].all_skills[].frequency",
                        "sectors[].all_skills[].share_in_sector",
                        "sectors[].all_skills[].rank",
                        "sectors[].all_skills[].growth_vs_reference_year",
                        "sectors[].all_skills[].growth_value",
                        "sectors[].all_skills[].sector_breadth",
                        "sectors[].all_skills[].is_green",
                        "sectors[].all_skills[].is_digital",
                        "sectors[].top_job_titles[].name",
                        "sectors[].top_job_titles[].count",
                        "message"
                    ],
                    sectoral_snapshot_payload
                )

            if dashboard_view != "sector":
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
            preferred_sector = st.session_state.get("sector_focus_choice", SECTOR_FOCUS_OPTIONS[0])
            option_labels = list(snapshot_options.keys())
            preferred_option = next(
                (
                    label for label, item in snapshot_options.items()
                    if item.get("sector_label") == preferred_sector or item.get("sector") == preferred_sector
                ),
                option_labels[0],
            )
            snapshot_target = snapshot_options[preferred_option]
            st.caption(f"{T['sectoral_snapshot_detail']}: {preferred_option}")

        if dashboard_view != "sector":
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
                    st.plotly_chart(fig_sec, width="stretch", key="sector_distribution_snapshot")
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
                    st.plotly_chart(fig_sec, width="stretch", key="sector_distribution_live")
                else:
                    st.write(T['no_data'])

            with c2:
                st.subheader(T['top_titles'] if not snapshot_target else T["sectoral_top_titles"], help=STAT_HELP["title_count"])
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
                jt = snapshot_target.get("top_job_titles", []) if snapshot_target else ins.get("job_titles", [])
                if jt:
                    st.plotly_chart(px.bar(pd.DataFrame(jt), x='count', y='name', orientation='h',
                                           title=T['jt_title'], color_discrete_sequence=['#3498db']),
                                    width="stretch",
                                    key=f"sector_titles_{snapshot_target.get('sector') if snapshot_target else 'all'}")
                else:
                    st.write(T['no_data'])

            with c3:
                sector_skill_title = T["sectoral_top_skills"] if snapshot_target else T['top_emp']
                sector_skill_help = STAT_HELP["observed_skill_count"] if snapshot_target else STAT_HELP["employer_count"]
                st.subheader(sector_skill_title, help=sector_skill_help)
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
                if snapshot_target:
                    top_skills_preview = (snapshot_target.get("top_skills") or [])[:10]
                    if top_skills_preview:
                        df_skills_preview = pd.DataFrame(top_skills_preview)
                        label_col = "label" if "label" in df_skills_preview.columns else "skill_id"
                        fig_skills_preview = px.bar(
                            df_skills_preview,
                            x="count",
                            y=label_col,
                            orientation="h",
                            labels={label_col: T["skill_label"], "count": T["total_mentions"]},
                        )
                        fig_skills_preview.update_layout(yaxis={'categoryorder': 'total ascending'})
                        st.plotly_chart(
                            fig_skills_preview,
                            width="stretch",
                            key=f"sector_skill_preview_{sectoral_snapshot_year}_{sectoral_location or 'global'}_{snapshot_target.get('sector')}"
                        )
                    else:
                        st.write(T["no_data"])
                else:
                    emp = ins.get("employers", [])
                    if emp:
                        st.plotly_chart(px.pie(pd.DataFrame(emp), values='count', names='name',
                                               title=T['active_emp'], hole=0.3),
                                        width="stretch",
                                        key="sector_employers")
                    else:
                        st.write(T['no_data'])

        if snapshot_sectors:
            st.markdown("---")
            focus_main, focus_info = st.columns([8, 1])
            with focus_main:
                st.subheader(f"{T['sectoral_snapshot_detail']}: {snapshot_target.get('sector_label', snapshot_target.get('sector'))}")
            with focus_info:
                dev_info(
                    "Selected sector focus",
                    SECTORAL_SNAPSHOT_ENDPOINT,
                    {
                        "status": "completed",
                        "year": 2024,
                        "reference_year": 2023,
                        "data_source": "postgres",
                        "window": {
                            "label": "2024 snapshot",
                            "min_date": "2024-01-01",
                            "max_date": "2024-12-31"
                        },
                        "total_jobs": 1280,
                        "sector_filter": [],
                        "sectors": [
                            {
                                "sector": "Information and communication",
                                "sector_label": "Information and communication",
                                "job_count": 420,
                                "job_share": 0.3281,
                                "total_skill_mentions": 1260,
                                "unique_skills": 38,
                                "evolution": {
                                    "reference_year": 2023,
                                    "job_count_current": 420,
                                    "job_count_reference": 360,
                                    "job_delta": 60,
                                    "job_growth_percentage": 0.1667,
                                    "job_growth_value": 0.1667,
                                    "new_skill_count": 4,
                                    "disappeared_skill_count": 2,
                                    "growing_skill_count": 12,
                                    "declining_skill_count": 7,
                                    "skill_churn": 0.1579,
                                    "top_new_skills": [
                                        {"skill_id": "skill-ai", "label": "artificial intelligence", "count": 26, "reference_count": 0, "delta": 26}
                                    ],
                                    "top_disappeared_skills": [
                                        {"skill_id": "skill-flash", "label": "Adobe Flash", "count": 0, "reference_count": 8, "delta": -8}
                                    ],
                                    "top_growing_skills": [
                                        {"skill_id": "skill-python", "label": "Python", "count": 188, "reference_count": 152, "delta": 36}
                                    ],
                                    "top_declining_skills": [
                                        {"skill_id": "skill-legacy", "label": "legacy systems", "count": 12, "reference_count": 30, "delta": -18}
                                    ]
                                },
                                "top_skills": [
                                    {
                                        "skill_id": "skill-python",
                                        "label": "Python",
                                        "count": 188,
                                        "frequency": 0.1492,
                                        "share_in_sector": 0.1492,
                                        "rank": 1,
                                        "growth_vs_reference_year": 0.24,
                                        "growth_value": 0.24,
                                        "sector_breadth": 4,
                                        "is_green": False,
                                        "is_digital": True
                                    }
                                ],
                                "all_skills": [
                                    {
                                        "skill_id": "skill-python",
                                        "label": "Python",
                                        "count": 188,
                                        "frequency": 0.1492,
                                        "share_in_sector": 0.1492,
                                        "rank": 1,
                                        "growth_vs_reference_year": 0.24,
                                        "growth_value": 0.24,
                                        "sector_breadth": 4,
                                        "is_green": False,
                                        "is_digital": True
                                    },
                                    {
                                        "skill_id": "skill-sustainability",
                                        "label": "sustainability",
                                        "count": 16,
                                        "frequency": 0.0127,
                                        "share_in_sector": 0.0127,
                                        "rank": 14,
                                        "growth_vs_reference_year": "new_entry",
                                        "growth_value": 1.0,
                                        "sector_breadth": 3,
                                        "is_green": True,
                                        "is_digital": False
                                    }
                                ],
                                "top_job_titles": [
                                    {"name": "Software Engineer", "count": 86},
                                    {"name": "Data Analyst", "count": 54}
                                ]
                            }
                        ],
                        "message": None
                    },
                    [
                        "request.year",
                        "request.reference_year",
                        "request.locations[]",
                        "sectors[] filtered client-side by selected sector label",
                        "selected sector.sector",
                        "selected sector.sector_label",
                        "selected sector.job_count",
                        "selected sector.job_share",
                        "selected sector.total_skill_mentions",
                        "selected sector.unique_skills",
                        "selected sector.evolution.reference_year",
                        "selected sector.evolution.job_count_current",
                        "selected sector.evolution.job_count_reference",
                        "selected sector.evolution.job_delta",
                        "selected sector.evolution.job_growth_percentage",
                        "selected sector.evolution.new_skill_count",
                        "selected sector.evolution.disappeared_skill_count",
                        "selected sector.evolution.growing_skill_count",
                        "selected sector.evolution.declining_skill_count",
                        "selected sector.evolution.skill_churn",
                        "selected sector.evolution.top_new_skills[]",
                        "selected sector.evolution.top_disappeared_skills[]",
                        "selected sector.evolution.top_growing_skills[]",
                        "selected sector.evolution.top_declining_skills[]",
                        "selected sector.top_skills[].skill_id",
                        "selected sector.top_skills[].label",
                        "selected sector.top_skills[].count",
                        "selected sector.top_skills[].frequency",
                        "selected sector.top_skills[].share_in_sector",
                        "selected sector.top_skills[].rank",
                        "selected sector.top_skills[].growth_vs_reference_year",
                        "selected sector.top_skills[].growth_value",
                        "selected sector.top_skills[].sector_breadth",
                        "selected sector.top_skills[].is_green",
                        "selected sector.top_skills[].is_digital",
                        "selected sector.all_skills[].skill_id",
                        "selected sector.all_skills[].label",
                        "selected sector.all_skills[].count",
                        "selected sector.all_skills[].frequency",
                        "selected sector.all_skills[].share_in_sector",
                        "selected sector.all_skills[].rank",
                        "selected sector.all_skills[].growth_vs_reference_year",
                        "selected sector.all_skills[].growth_value",
                        "selected sector.all_skills[].sector_breadth",
                        "selected sector.all_skills[].is_green",
                        "selected sector.all_skills[].is_digital",
                        "selected sector.top_job_titles[].name",
                        "selected sector.top_job_titles[].count"
                    ],
                    sectoral_snapshot_payload
                )
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                metric_with_info(T["jobs_analyzed"], snapshot_target.get("job_count", 0), STAT_HELP["jobs_analyzed"])
            with k2:
                metric_with_info(T["sectoral_job_share"], snapshot_target.get("job_share", 0), STAT_HELP["sectoral_job_share"])
            with k3:
                metric_with_info(T["total_mentions"], snapshot_target.get("total_skill_mentions", 0), STAT_HELP["total_skill_mentions"])
            with k4:
                metric_with_info(T["unique_items"], snapshot_target.get("unique_skills", 0), STAT_HELP["unique_skills"])

            evolution = snapshot_target.get("evolution") or {}
            if evolution and st.session_state.get("sector_overview_mode", "snapshot") == "evolution":
                st.subheader(T["sector_evolution"], help=T["sector_evolution_help"])
                e1, e2, e3, e4, e5 = st.columns(5)
                with e1:
                    metric_with_info(
                        T["job_delta"],
                        evolution.get("job_delta", 0),
                        STAT_HELP["sector_job_delta"],
                    )
                with e2:
                    metric_with_info(
                        T["job_growth"],
                        format_growth_percentage(evolution.get("job_growth_percentage")),
                        STAT_HELP["sector_job_growth"],
                    )
                with e3:
                    metric_with_info(
                        T["new_skills"],
                        evolution.get("new_skill_count", 0),
                        STAT_HELP["sector_new_skills"],
                    )
                with e4:
                    metric_with_info(
                        T["disappeared_skills"],
                        evolution.get("disappeared_skill_count", 0),
                        STAT_HELP["sector_disappeared_skills"],
                    )
                with e5:
                    metric_with_info(
                        T["skill_churn"],
                        format_growth_percentage(evolution.get("skill_churn")),
                        STAT_HELP["sector_skill_churn"],
                    )

                evo_a, evo_b = st.columns(2)
                with evo_a:
                    render_evolution_skill_table(
                        T["top_new_skills"],
                        evolution.get("top_new_skills", []),
                        STAT_HELP["sector_new_skills"],
                        f"top_new_skills_{sectoral_snapshot_year}_{sectoral_location or 'global'}_{snapshot_target.get('sector')}",
                        T["no_new_skills"],
                    )
                    render_evolution_skill_table(
                        T["top_growing_skills"],
                        evolution.get("top_growing_skills", []),
                        STAT_HELP["sector_growing_skills"],
                        f"top_growing_skills_{sectoral_snapshot_year}_{sectoral_location or 'global'}_{snapshot_target.get('sector')}",
                        T["no_growing_skills"],
                    )
                with evo_b:
                    render_evolution_skill_table(
                        T["top_disappeared_skills"],
                        evolution.get("top_disappeared_skills", []),
                        STAT_HELP["sector_disappeared_skills"],
                        f"top_disappeared_skills_{sectoral_snapshot_year}_{sectoral_location or 'global'}_{snapshot_target.get('sector')}",
                        T["no_disappeared_skills"],
                    )
                    render_evolution_skill_table(
                        T["top_declining_skills"],
                        evolution.get("top_declining_skills", []),
                        STAT_HELP["sector_declining_skills"],
                        f"top_declining_skills_{sectoral_snapshot_year}_{sectoral_location or 'global'}_{snapshot_target.get('sector')}",
                        T["no_declining_skills"],
                    )

            if st.session_state.get("sector_overview_mode", "snapshot") == "evolution":
                if not evolution:
                    st.info(T["no_data"])
                st.stop()

            portfolio_rows = build_skill_portfolio_rows(snapshot_sectors, snapshot_target)
            st.subheader(T["skill_portfolio"], help=T["skill_portfolio_help"])
            if portfolio_rows:
                df_portfolio = pd.DataFrame(portfolio_rows)
                fig_portfolio = px.scatter(
                    df_portfolio,
                    x="sector_breadth",
                    y="importance",
                    size="count",
                    color="category",
                    hover_name="label",
                    hover_data={
                        "skill_id": True,
                        "count": True,
                        "importance": ":.3f",
                        "sector_breadth": True,
                        "category": True,
                    },
                    labels={
                        "sector_breadth": "sector breadth",
                        "importance": "importance in sector",
                        "count": "count",
                        "category": "type",
                    },
                )
                fig_portfolio.update_layout(height=420)
                st.plotly_chart(
                    fig_portfolio,
                    width="stretch",
                    key=f"skill_portfolio_{sectoral_snapshot_year}_{sectoral_location or 'global'}_{snapshot_target.get('sector')}"
                )
            else:
                st.info(T["no_data"])

            snap_skill_col, snap_title_col = st.columns(2)

            with snap_skill_col:
                st.subheader(T["sectoral_top_skills"], help=STAT_HELP["observed_skill_count"])
                top_skills = (snapshot_target.get("top_skills") or [])[:10]
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
                    st.plotly_chart(
                        fig_top_skills,
                        width="stretch",
                        key=f"sector_top_skills_{sectoral_snapshot_year}_{sectoral_location or 'global'}_{snapshot_target.get('sector')}"
                    )
                else:
                    st.write(T["no_data"])

                all_skills = snapshot_target.get("all_skills") or snapshot_target.get("top_skills", [])
                if all_skills:
                    with st.expander(T["sectoral_all_skills"], expanded=False):
                        df_all_skills = pd.DataFrame(all_skills)
                        label_col = "label" if "label" in df_all_skills.columns else "skill_id"
                        search_term = st.text_input(T["skill_search"], "", key=f"skill_search_{snapshot_target['sector']}")
                        if search_term:
                            mask = df_all_skills[label_col].astype(str).str.contains(search_term, case=False, na=False)
                            df_all_skills = df_all_skills[mask]
                        display_cols = [
                            c for c in [
                                "skill_id",
                                "label",
                                "count",
                                "share_in_sector",
                                "rank",
                                "growth_vs_reference_year",
                                "sector_breadth",
                                "is_green",
                                "is_digital",
                            ]
                            if c in df_all_skills.columns
                        ]
                        st.dataframe(
                            df_all_skills[display_cols],
                            use_container_width=True,
                            column_config={
                                "count": st.column_config.NumberColumn(
                                    "count (i)",
                                    help=STAT_HELP["observed_skill_count"]
                                ),
                                "share_in_sector": st.column_config.NumberColumn(
                                    "share in sector (i)",
                                    help=STAT_HELP["observed_skill_frequency"]
                                ),
                                "rank": st.column_config.NumberColumn(
                                    "rank (i)",
                                    help=STAT_HELP["skill_rank"]
                                ),
                                "growth_vs_reference_year": st.column_config.TextColumn(
                                    "growth between years (i)",
                                    help=STAT_HELP["skill_reference_growth"]
                                ),
                                "sector_breadth": st.column_config.NumberColumn(
                                    "sector breadth (i)",
                                    help=STAT_HELP["sector_breadth"]
                                ),
                            }
                        )

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
                    st.plotly_chart(
                        fig_top_titles,
                        width="stretch",
                        key=f"sector_top_titles_{sectoral_snapshot_year}_{sectoral_location or 'global'}_{snapshot_target.get('sector')}"
                    )
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
                    st.plotly_chart(fig_obs, width="stretch", key=f"observed_skills_{selected_sector}")

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
        elif sectoral_snapshot_response.get("status") == "not_available":
            st.info(sectoral_snapshot_response.get("message", T["no_data"]))
        elif not snapshot_sectors:
            st.info(T['no_sectoral'])

else:
    # Mostriamo il messaggio di benvenuto solo se non ci sono dati caricati
    st.info(T['welcome'])
