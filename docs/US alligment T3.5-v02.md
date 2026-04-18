Ecco il set aggiornato di **User Stories** per lo **Skills Projector**, allineato ai requisiti M03-M30.

---

## 📋 User Stories: Skills Projector (Task 3.5)

### 🌍 Dimension 1: Regional Intelligence
> **"As a Regional Policy Maker, I want to decompose skill demand by geographical area so that I can identify specific shortages in my local labor market compared to the national average."**
* **Acceptance Criteria:**
    * Il sistema deve filtrare i dati aggregati per `location_code` (NUTS/Regioni).
    * L'output deve mostrare il ranking delle skill più richieste per una specifica area geografica.
    * Deve essere possibile confrontare la "labor market landscape" di due regioni diverse.

### 🏭 Dimension 2: Sectoral Intelligence
> **"As an Industry Representative, I want to analyze projections tailored to my specific industrial sector so that I can understand the exact workforce necessities of my field."**
* **Acceptance Criteria:**
    * Mappatura corretta tra `occupation_id` (ESCO) e macro-settori industriali.
    * Visualizzazione della distribuzione delle skill "Twin Transition" (Green/Digital) specifica per settore.
    * Assenza di discriminazioni basate su fattori non lavorativi (genere, orientamento, etc.) come da guardrail del Task 3.5.

### 📅 Dimension 3: Temporal Projections
> **"As a Labor Market Researcher, I want to view skill shortages across different time granularities (monthly, quarterly, yearly) so that I can detect seasonal trends or long-term shifts."**
* **Acceptance Criteria:**
    * Aggregazione dei dati basata sulla `upload_date` delle offerte di lavoro.
    * Calcolo del tasso di crescita (Growth Rate) per determinare se una skill è in espansione o contrazione in un dato periodo.
    * Possibilità di proiettare i dati storici verso il breve termine (Short-term forecast).

### 📊 Dimension 4: Statistical Inferential Mechanisms
> **"As a Data Analyst, I want to apply traditional hypothesis testing to cross-sectoral data so that I can determine if a detected skill shortage is statistically significant and not just a random fluctuation."**
* **Acceptance Criteria:**
    * Implementazione di test statistici (es. Chi-Square, T-test) per il confronto tra gruppi (Regione A vs Regione B, Settore X vs Settore Y).
    * Generazione di un `p-value` per ogni confronto per validare l'ipotesi di "shortage" o "demand shift".
    * Fornitura di "inferential mechanisms" chiari da passare al WP4 per l'analisi avanzata.

---

### 🛠️ Technical Implementation Notes (Internal)
* **Input:** Dati derivati da *Skills Analyzer* e *Skills Forecaster*.
* **Process:** Decomposizione tramite aggregazione SQL/Pandas e calcoli statistici tramite `scipy.stats`.
* **Output:** JSON strutturato pronto per la visualizzazione in Dashboard, privo di narrazioni soggettive ma ricco di metriche oggettive.

---

**Siamo allineati?** Se queste storie rispecchiano la tua visione del Task 3.5, il prossimo passo è aggiornare l'endpoint `/analyze-skills` per restituire queste tre "fette" di dati (Regioni, Settori, Tempo) insieme ai risultati dei test statistici.
## Sectoral Intelligence acceptance criteria (updated)

- Support both sector systems: ISCO and NACE.
- Resolve NACE labels through ESCO-NACE crosswalk (rev. 2.1 preferred source).
- Allow dashboard switching between ISCO and NACE without semantic mismatch.
- Keep explicit distinction between:
  - native ISCO views
  - NACE derived/aggregated views (`Observed`, `Derived Canonical`, `Aggregated Official Matrix`).
