import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. Configurazione Pagina
st.set_page_config(page_title="SKILLAB Projector Intelligence", layout="wide")

# Inizializzazione Session State
if 'lang' not in st.session_state:
    st.session_state.lang = 'IT'

if 'all_data' not in st.session_state:
    st.session_state.all_data = None


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
        'submit': "Lancia Proiezione 🚀",
        'stop': "STOP ANALISI ⛔",
        'stop_toast': "Segnale di stop inviato!",
        'server_error': "Server non raggiungibile.",
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
        'intelligence_label': "Dettaglio Intelligence (Phase 1)"
    },
    'EN': {
        'title': "🚀 SKILLAB Projector: Intelligence Dashboard",
        'subtitle': "Predictive analysis and real-time monitoring of Job Postings.",
        'filters_header': "Search Filters",
        'keywords': "Keywords",
        'location': "Location Code (e.g. ITC4C)",
        'date_range': "Time Range",
        'submit': "Launch Projection 🚀",
        'stop': "STOP ANALYSIS ⛔",
        'stop_toast': "Stop signal sent!",
        'server_error': "Server unreachable.",
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
        'intelligence_label': "Intelligence Detail (Phase 1)"
    }
}

T = translations[st.session_state.lang]

st.title(T['title'])
st.markdown(T['subtitle'])

API_BASE_URL = "http://127.0.0.1:8000/projector"


@st.cache_data(ttl=600)
def get_analysis_data(p):
    res = requests.post(f"{API_BASE_URL}/analyze-skills", data=p)
    return res.json() if res.status_code == 200 else None


with st.sidebar:
    st.selectbox("Language / Lingua", ["Italiano", "English"],
                 index=0 if st.session_state.lang == 'IT' else 1,
                 on_change=change_lang, key="lang_choice")
    st.markdown("---")

    with st.form("my_filters"):
        st.header(T['filters_header'])
        keywords = st.text_input(T['keywords'], "software")
        location = st.text_input(T['location'], "")
        date_range = st.date_input(T['date_range'], [pd.to_datetime("2024-01-01"), pd.to_datetime("2024-12-31")])
        submit_button = st.form_submit_button(T['submit'])

    st.markdown("---")
    if st.button(T['stop'], type="primary", use_container_width=True):
        try:
            requests.post(f"{API_BASE_URL}/stop")
            st.toast(T['stop_toast'])
        except:
            st.error(T['server_error'])

    st.markdown("---")
    st.subheader("🛠️ Demo Settings")
    demo_mode = st.checkbox("Enable NUTS Demo Data", value=False,
                            help="Attiva l'iniezione di codici NUTS fittizi per testare la gerarchia del Task 3.5")

# Costruzione Payload
payload = {
    "keywords": [keywords] if keywords else None,
    "locations": [location] if location else None,
    "min_date": date_range[0].strftime("%Y-%m-%d"),
    "max_date": date_range[1].strftime("%Y-%m-%d"),
    "demo": demo_mode
}

# --- LOGICA DI ACQUISIZIONE DATI ---
if submit_button:
    with st.spinner("🚀 Intelligence is loading..."):
        data = get_analysis_data(payload)
        if data:
            st.session_state.all_data = data
        else:
            st.error(T['server_error'])

# --- LOGICA DI RENDERING ---
# Mostriamo i risultati solo se all_data è presente nello stato della sessione
if st.session_state.all_data:
    all_data = st.session_state.all_data
    ins = all_data["insights"]
    summary = all_data["dimension_summary"]

    tab1, tab2, tab3, tab4 = st.tabs(T['tabs'])

    # --- TAB 1: RANKING SKILLS ---
    with tab1:
        st.header(T['top_skills'])
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
                st.metric(T['jobs_analyzed'], summary.get("jobs_analyzed", 0))
                st.subheader(T['intelligence_label'])
                st.dataframe(df_ranking[['name', 'frequency', 'primary_sector', 'Twin']], use_container_width=True)

    # --- TAB 2: TRENDS ---
    with tab2:
        st.header(T['trends_header'])
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
        st.header(T['geo_header'])
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
            st.header("🌍 Regional Intelligence & NUTS Projections (Task 3.5)")

            strategy = st.radio(
                "Seleziona granularità della proiezione:",
                ["Location Codes (Raw)", "NUTS 1 (Macro)", "NUTS 2 (Regioni)", "NUTS 3 (Province)"],
                horizontal=True,
                help="Scegli il livello di scomposizione dei dati come richiesto dal Task 3.5"
            )

            strat_map = {
                "Location Codes (Raw)": "raw",
                "NUTS 1 (Macro)": "nuts1",
                "NUTS 2 (Regioni)": "nuts2",
                "NUTS 3 (Province)": "nuts3"
            }

            selected_list = regional_dict.get(strat_map[strategy], [])

            if selected_list:
                area_codes = [item["code"] for item in selected_list]
                col_sel, col_met = st.columns([2, 1])

                with col_sel:
                    target_code = st.selectbox(
                        f"Seleziona area per analisi granulare ({strategy}):",
                        area_codes
                    )

                target = next(i for i in selected_list if i["code"] == target_code)

                with col_met:
                    st.metric("Market Share", f"{target['market_share']}%",
                              help="Incidenza dell'area sul volume totale")

                st.subheader(f"Competenze chiave in {target_code}")
                df_reg_skills = pd.DataFrame(target["top_skills"])

                fig_reg = px.bar(
                    df_reg_skills,
                    x="count",
                    y="skill",
                    orientation='h',
                    text="count",
                    color="specialization",
                    color_continuous_scale="RdYlGn",
                    labels={"skill": "Competenza", "count": "Job Post", "specialization": "Specializzazione (LQ)"},
                    title=f"Profilo della forza lavoro: {target_code}"
                )
                fig_reg.update_layout(yaxis={'categoryorder': 'total ascending'}, height=400)
                st.plotly_chart(fig_reg, use_container_width=True)

                st.info(f"💡 **Insight Task 3.5**: L'area **{target_code}** mostra una domanda focalizzata. Le barre più verdi indicano competenze con alta specializzazione regionale.")
            else:
                st.warning(f"Dati non disponibili per il livello {strategy}.")
        else:
            st.info("Esegui una proiezione per visualizzare l'analisi regionale.")

    # --- TAB 4: SETTORI, JOBS & EMPLOYERS ---
    with tab4:
        st.header(T['jobs_emp_header'])
        c1, c2, c3 = st.columns(3)

        with c1:
            st.subheader(T['top_sectors'])
            sec = ins.get("sectors", [])
            if sec:
                df_sec = pd.DataFrame(sec)
                st.plotly_chart(px.pie(df_sec, values='count', names='name',
                                       title=T['sector_title'], hole=0.4,
                                       color_discrete_sequence=px.colors.qualitative.Pastel))
            else:
                st.write(T['no_data'])

        with c2:
            st.subheader(T['top_titles'])
            jt = ins.get("job_titles", [])
            if jt:
                st.plotly_chart(px.bar(pd.DataFrame(jt), x='count', y='name', orientation='h',
                                       title=T['jt_title'], color_discrete_sequence=['#3498db']))
            else:
                st.write(T['no_data'])

        with c3:
            st.subheader(T['top_emp'])
            emp = ins.get("employers", [])
            if emp:
                st.plotly_chart(px.pie(pd.DataFrame(emp), values='count', names='name',
                                       title=T['active_emp'], hole=0.3))
            else:
                st.write(T['no_data'])

else:
    # Mostriamo il messaggio di benvenuto solo se non ci sono dati caricati
    st.info(T['welcome'])