import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. Configurazione Pagina
st.set_page_config(page_title="SKILLAB Projector Intelligence", layout="wide")

if 'lang' not in st.session_state:
    st.session_state.lang = 'IT'


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
        # Tab 4 Rinominata
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
        'top_sectors': "Distribuzione Settoriale (Intelligence)",  # NEW
        'sector_title': "Domanda per Macro-Settore",  # NEW
        'welcome': "Configura i filtri a sinistra e clicca su 'Lancia Proiezione' per interrogare il Projector.",
        'intelligence_label': "Dettaglio Intelligence (Phase 1)"  # NEW
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
        'top_sectors': "Sectoral Distribution (Intelligence)",  # NEW
        'sector_title': "Demand by Macro-Sector",  # NEW
        'welcome': "Configure the filters on the left and click 'Launch Projection' to query the Projector.",
        'intelligence_label': "Intelligence Detail (Phase 1)"  # NEW
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


@st.cache_data(ttl=600)
def get_trends_data(p):
    res = requests.post(f"{API_BASE_URL}/emerging-skills", data=p)
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

payload = {
    "keywords": [keywords] if keywords else None,
    "locations": [location] if location else None,
    "min_date": date_range[0].strftime("%Y-%m-%d"),
    "max_date": date_range[1].strftime("%Y-%m-%d")
}

tab1, tab2, tab3, tab4 = st.tabs(T['tabs'])

if submit_button:
    # --- TAB 1: RANKING SKILLS (INTELLIGENCE AGGIUNTA) ---
    with tab1:
        st.header(T['top_skills'])
        data = get_analysis_data(payload)
        if data and "insights" in data:
            ranking = data["insights"].get("ranking", [])
            if ranking:
                df_ranking = pd.DataFrame(ranking).head(15)

                # Aggiunta tag Twin Transition (Phase 1)
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
                    st.metric(T['jobs_analyzed'], data["dimension_summary"]["jobs_analyzed"])
                    st.subheader(T['intelligence_label'])
                    # Visualizziamo i nuovi campi Phase 1 nella tabella
                    st.dataframe(df_ranking[['name', 'frequency', 'primary_sector', 'Twin']], use_container_width=True)

    # --- TAB 2: TRENDS (INTELLIGENCE AGGIUNTA) ---
    with tab2:
        st.header(T['trends_header'])
        trend_data = get_trends_data(payload)
        if trend_data and "insights" in trend_data:
            ins = trend_data["insights"]

            if "market_health" in ins:
                mh = ins["market_health"]
                st.info(
                    f"{T['market_status']}: **{mh['status'].upper()}** | {T['volume_var']}: **{mh['volume_growth_percentage']}%**")

            trends_list = ins.get("trends", [])
            if trends_list:
                df_trends = pd.DataFrame.from_records(trends_list)
                if 'growth' in df_trends.columns:
                    new_entries = df_trends[df_trends['growth'] == 'new_entry']
                    df_numeric = df_trends[df_trends['growth'] != 'new_entry'].copy()
                    df_numeric['growth'] = pd.to_numeric(df_numeric['growth'], errors='coerce')
                    df_numeric = df_numeric.dropna(subset=['growth'])

                    if not df_numeric.empty:
                        df_plot = pd.concat([df_numeric.head(10), df_numeric.tail(10)])
                        # Aggiunta primary_sector nel grafico dei trend
                        fig_trend = px.bar(df_plot, x='growth', y='name', orientation='h',
                                           color='trend_type',
                                           hover_data=["primary_sector"],  # Phase 1 info
                                           color_discrete_map={'emerging': '#2ecc71', 'declining': '#e74c3c'},
                                           title=T['delta_title'])
                        st.plotly_chart(fig_trend, use_container_width=True)

                    if not new_entries.empty:
                        st.subheader(T['new_entries'])
                        st.success(", ".join(new_entries['name'].astype(str).tolist()))

    # --- TAB 3: GEOGRAFIA (INVARIATA) ---
    with tab3:
        st.header(T['geo_header'])
        data = get_analysis_data(payload)
        if data and "dimension_summary" in data:
            geo = data["dimension_summary"].get("geo_breakdown", [])
            if geo:
                df_geo = pd.DataFrame(geo)
                iso_mapping = {"IT": "ITA", "FR": "FRA", "DE": "DEU", "ES": "ESP", "EL": "GRC"}  # ... mapping ...
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

    # --- TAB 4: SETTORI, JOBS & EMPLOYERS (LAYOUT ESTESO) ---
    with tab4:
        st.header(T['jobs_emp_header'])
        data = get_analysis_data(payload)
        if data and "insights" in data:
            # Layout a 3 colonne per includere il nuovo grafico dei settori
            c1, c2, c3 = st.columns(3)

            with c1:
                st.subheader(T['top_sectors'])  # NUOVO GRAFICO PHASE 1
                sec = data["insights"].get("sectors", [])
                if sec:
                    df_sec = pd.DataFrame(sec)
                    st.plotly_chart(px.pie(df_sec, values='count', names='name',
                                           title=T['sector_title'], hole=0.4,
                                           color_discrete_sequence=px.colors.qualitative.Pastel))
                else:
                    st.write(T['no_data'])

            with c2:
                st.subheader(T['top_titles'])
                jt = data["insights"].get("job_titles", [])
                if jt:
                    st.plotly_chart(px.bar(pd.DataFrame(jt), x='count', y='name', orientation='h',
                                           title=T['jt_title'], color_discrete_sequence=['#3498db']))
                else:
                    st.write(T['no_data'])

            with c3:
                st.subheader(T['top_emp'])
                emp = data["insights"].get("employers", [])
                if emp:
                    st.plotly_chart(px.pie(pd.DataFrame(emp), values='count', names='name',
                                           title=T['active_emp'], hole=0.3))
                else:
                    st.write(T['no_data'])

else:
    st.info(T['welcome'])