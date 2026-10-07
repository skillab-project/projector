"""Two-region comparison view for the developer demo dashboard."""

from datetime import date, timedelta
import re

import pandas as pd
import plotly.express as px
import requests
import streamlit as st


COPY = {
    "IT": {
        "title": "Confronto tra regioni",
        "region_a": "Regione A (codice NUTS)",
        "region_b": "Regione B (codice NUTS)",
        "region_help": "Due codici diversi dello stesso livello: NUTS1 (3 caratteri), NUTS2 (4), NUTS3 (5).",
        "dates": "Periodo comune alle due regioni",
        "keyword": "Keyword annunci (opzionale)",
        "submit": "Confronta regioni",
        "loading": "Confronto in corso...",
        "invalid": "Inserisci due codici NUTS diversi, dello stesso livello, e un periodo completo e ordinato.",
        "error": "Impossibile completare il confronto. Riprova o verifica la connessione al backend.",
        "empty": "Nessun annuncio trovato per queste regioni e questi filtri.",
        "partial": "Una delle due regioni non ha annunci: le differenze vanno interpretate con cautela.",
        "jobs": "Annunci",
        "difference": "Differenza annunci (B - A)",
        "jobs_help": "Numero di annunci che corrispondono al codice NUTS e ai filtri selezionati.",
        "difference_help": "Annunci nella regione B meno annunci nella regione A, nello stesso periodo. Non e una crescita temporale.",
        "skills": "Skill", "sectors": "Settori", "job_titles": "Titoli degli annunci", "employers": "Datori di lavoro",
        "name": "Nome", "count": "Occorrenze", "share": "Quota skill (%)", "metric": "Metrica",
        "count_help": "Occorrenze della voce negli annunci della regione selezionata.",
        "share_help": "Occorrenze della skill / annunci della regione x 100.",
        "delta_help": "Valore della regione B meno valore della regione A; per le quote, punti percentuali.",
        "specialization_help": "Quota della skill nella regione / quota della skill nell'insieme delle due regioni. Oltre 1 indica maggiore concentrazione.",
        "rank_help": "Posizione nella classifica completa delle skill della regione; vuoto se assente.",
        "rank": "Posizione", "specialization": "Specializzazione", "delta": "Differenza", "pp": "Differenza (punti %)",
        "request": "Richiesta", "response": "Risposta completa", "fields": "Campi utilizzati",
        "stale": "Filtri modificati: esegui nuovamente il confronto per aggiornare i risultati.",
        "scope": "Risultati", "all": "Tutti gli annunci", "region": "Regione",
    },
    "EN": {
        "title": "Region Comparison",
        "region_a": "Region A (NUTS code)", "region_b": "Region B (NUTS code)",
        "region_help": "Two different codes at the same level: NUTS1 (3 characters), NUTS2 (4), NUTS3 (5).",
        "dates": "Shared period for both regions", "keyword": "Job keyword (optional)",
        "submit": "Compare regions", "loading": "Comparing regions...",
        "invalid": "Enter two different NUTS codes at the same level and a complete, ordered date range.",
        "error": "Could not complete the comparison. Retry or check the backend connection.",
        "empty": "No postings found for these regions and filters.",
        "partial": "One region has no postings: interpret the differences with caution.",
        "jobs": "Postings", "difference": "Posting difference (B - A)",
        "jobs_help": "Number of postings matching the NUTS code and selected filters.",
        "difference_help": "Postings in region B minus postings in region A, for the same period. This is not temporal growth.",
        "skills": "Skills", "sectors": "Sectors", "job_titles": "Job titles", "employers": "Employers",
        "name": "Name", "count": "Occurrences", "share": "Skill share (%)", "metric": "Metric",
        "count_help": "Occurrences of the item in postings for the selected region.",
        "share_help": "Skill occurrences / postings in the region x 100.",
        "delta_help": "Region B value minus region A value; shares use percentage points.",
        "specialization_help": "Regional skill share / skill share across both regions combined. Above 1 means greater concentration.",
        "rank_help": "Position in the region's full skill ranking; blank when absent.",
        "rank": "Rank", "specialization": "Specialization", "delta": "Difference", "pp": "Difference (pp)",
        "request": "Request", "response": "Complete response", "fields": "Fields used",
        "stale": "Filters changed: run the comparison again to update the results.",
        "scope": "Results", "all": "All postings", "region": "Region",
    },
}


def render_region_comparison(api_base_url, timeout, language):
    text = COPY[language]
    st.header(text["title"], help=text["region_help"])
    a, b = st.columns(2)
    region_a = a.text_input(text["region_a"], "DK03", help=text["region_help"]).strip().upper()
    region_b = b.text_input(text["region_b"], "ITF4", help=text["region_help"]).strip().upper()
    dates = st.date_input(text["dates"], (date.today() - timedelta(days=365), date.today()))
    keyword = st.text_input(text["keyword"]).strip()
    valid = (
        len(dates) == 2 and dates[0] <= dates[1]
        and region_a != region_b and len(region_a) == len(region_b)
        and all(re.fullmatch(r"[A-Z]{2}[A-Z0-9]{1,3}", code) for code in (region_a, region_b))
    )
    payload = {"region_a": region_a, "region_b": region_b}
    if len(dates) == 2:
        payload.update(min_date=dates[0].isoformat(), max_date=dates[1].isoformat())
    if keyword:
        payload["keyword"] = keyword

    if st.button(text["submit"], type="primary"):
        st.session_state.pop("region_comparison_result", None)
        if not valid:
            st.warning(text["invalid"])
        else:
            with st.spinner(text["loading"]):
                try:
                    response = requests.post(f"{api_base_url.rstrip('/')}/compare-regions", data=payload, timeout=timeout)
                    response.raise_for_status()
                    result = response.json()
                except (requests.RequestException, ValueError):
                    st.error(text["error"])
                else:
                    st.session_state.region_comparison_result = (payload.copy(), result)

    stored = st.session_state.get("region_comparison_result")
    if not stored:
        return
    request, result = stored
    if request != payload:
        st.info(text["stale"])
        return
    st.caption(f"{text['scope']}: {result['window']['min_date']} / {result['window']['max_date']} | "
               f"{result['nuts_level'].upper()} | {result.get('keyword') or text['all']}")

    def api_info(fields):
        with st.popover("API"):
            st.code("POST /projector/compare-regions", language="http")
            st.markdown(text["request"])
            st.json(request)
            st.markdown(text["response"])
            st.json(result)
            st.markdown(text["fields"])
            st.code("\n".join(fields))

    api_info(["window", "scope", "keyword", "nuts_level", "region_a.total_jobs", "region_b.total_jobs", "comparison.total_jobs_difference"])
    first, second, difference = st.columns(3)
    first.metric(f"{text['jobs']} - {region_a}", result["region_a"]["total_jobs"], help=text["jobs_help"])
    second.metric(f"{text['jobs']} - {region_b}", result["region_b"]["total_jobs"], help=text["jobs_help"])
    difference.metric(text["difference"], result["comparison"]["total_jobs_difference"], help=text["difference_help"])
    totals = [result["region_a"]["total_jobs"], result["region_b"]["total_jobs"]]
    if not any(totals):
        st.info(text["empty"])
        return
    if not all(totals):
        st.warning(text["partial"])

    sections = ("skills", "sectors", "job_titles", "employers")
    for section, tab in zip(sections, st.tabs([text[key] for key in sections])):
        with tab:
            rows = result["comparison"][section]
            fields = list(rows[0]) if rows else []
            api_info([f"comparison.{section}[].{field}" for field in fields])
            if not rows:
                st.info(text["empty"])
                continue
            metric = "count"
            if section == "skills":
                metric = st.radio(text["metric"], ["count", "share"], format_func=lambda key: text[key], horizontal=True)
            frame = pd.DataFrame(rows)
            chart = frame.melt(id_vars="name", value_vars=[f"region_a_{metric}", f"region_b_{metric}"], var_name="region", value_name="value")
            chart["region"] = chart["region"].map({f"region_a_{metric}": region_a, f"region_b_{metric}": region_b})
            fig = px.bar(chart, x="value", y="name", color="region", barmode="group", orientation="h",
                         labels={"value": text[metric], "name": text["name"], "region": text["region"]},
                         height=max(350, len(frame) * 38))
            fig.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig, width="stretch", key=f"region_comparison_{section}")
            columns = {"name": st.column_config.TextColumn(text["name"]),
                       "count_difference": st.column_config.NumberColumn(text["delta"], help=text["delta_help"]),
                       "share_difference_percentage_points": st.column_config.NumberColumn(text["pp"], help=text["delta_help"])}
            for side, code in (("a", region_a), ("b", region_b)):
                for field in ("count", "share", "rank", "specialization"):
                    columns[f"region_{side}_{field}"] = st.column_config.NumberColumn(f"{code} - {text[field]}", help=text[f"{field}_help"])
            st.dataframe(frame, column_config=columns, hide_index=True, width="stretch")
