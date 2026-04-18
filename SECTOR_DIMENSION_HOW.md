Perfetto, ti faccio una **documentazione strutturata, chiara e riusabile** (livello “/docs” industriale), con **flow esplicito** e esempi.

---

# 📊 SKILLAB Projector – Data Model & Flow

## 1. Obiettivo

Il sistema trasforma dati grezzi di job postings in **informazione strutturata multi-livello**:

* domanda reale (Observed)
* conoscenza standardizzata ESCO (Canonical)
* aggregazione semantica (Skill Groups)
* analisi per settore (Sector)

---

# 🧭 2. Entità fondamentali

## 2.1 Job

**Fonte:** SKILLAB Tracker

Rappresenta un annuncio reale di lavoro.

**Campi rilevanti:**

* `skills`: lista skill ESCO
* `occupations`: lista occupation ESCO
* `location_code`: geografia

**Esempio:**

```json
{
  "occupation": "Software Developer",
  "skills": ["python", "sql"]
}
```

---

## 2.2 Occupation

**Fonte:** ESCO + CSV locale (`occupations_en.csv`)

Rappresenta un ruolo lavorativo standard.

**Serve per:**

* collegare job → conoscenza ESCO
* derivare il sector

---

## 2.3 Sector

**Definizione attuale:**

```text
occupation → isco_group
```

**Fonte:**

* `occupations_en.csv` (`iscoGroup`)
* `ISCOGroups_en.csv` (label)

**Esempio:**

```text
C2512 → Software developers
1213 → Financial managers
```

👉 Il sector è una **aggregazione di occupation**

---

## 2.4 Skill (Observed)

**Fonte:** job postings

Rappresenta le skill realmente richieste dal mercato.

**Esempio:**

```text
python, fastapi, sql
```

---

## 2.5 Skill (Canonical)

**Fonte:** `occupationSkillRelations_en.csv`

Rappresenta le skill ufficiali ESCO associate a una occupation.

**Relazione:**

```text
occupation → skill
```

**Esempio:**

```text
Software Developer → programming, testing, debugging
```

---

## 2.6 Skill Group

**Fonte:** `skillsHierarchy_en.csv`

Rappresenta una categoria semantica di skill.

**Gerarchia:**

```text
Skill → Skill Group (Level 1 / 2 / 3)
```

**Esempio:**

```text
python → programming
sql → data management
```

---

# 🔗 3. Data Flow completo

## 3.1 Pipeline generale

```text
JOB
 ├──→ Occupation
 │     └──→ Sector
 │     └──→ Canonical Skills
 │             └──→ Skill Groups
 │
 └──→ Observed Skills
         └──→ Skill Groups
```

---

# ⚙️ 4. Costruzione dei dati

## 4.1 Step 1 — Job → Occupation

```python
occ_id = get_primary_occupation_id(job)
```

---

## 4.2 Step 2 — Occupation → Sector

```python
sector = get_sector_from_occupation(occ_id)
```

**Output:**

```text
occupation → ISCO group → label
```

---

## 4.3 Step 3 — Observed Skills

```python
for skill in job["skills"]:
    sector_skill_observed[sector][skill] += 1
```

👉 rappresenta:

> domanda reale del mercato

---

## 4.4 Step 4 — Canonical Skills

```python
canonical_skills = occ_skill_relations[occ_id]

for skill in canonical_skills:
    sector_skill_canonical[sector][skill] += 1
```

👉 rappresenta:

> struttura teorica ESCO pesata sui job

---

## 4.5 Step 5 — Skill → Skill Group

```python
group = get_skill_group(skill_id)
```

Applicato sia a:

* observed
* canonical

---

## 4.6 Step 6 — Aggregazione per Sector

Tutti i dati vengono aggregati per:

```text
sector → skill
sector → skill group
```

---

# 📊 5. Esempio completo

## Input (Job)

```json
[
  {
    "occupation": "Software Developer",
    "skills": ["python", "sql"]
  },
  {
    "occupation": "Software Developer",
    "skills": ["java"]
  }
]
```

---

## ESCO

```text
Software Developer → programming, testing
```

---

## Step-by-step

### Sector

```text
Software Developer → C2512 → Software developers
```

---

### Observed Skills

```text
python = 1
sql = 1
java = 1
```

---

### Canonical Skills

```text
programming = 2
testing = 2
```

👉 perché 2 job con stessa occupation

---

### Skill Groups

#### Observed

```text
python → programming
sql → data management
```

```text
programming = 2
data management = 1
```

---

#### Canonical

```text
programming → programming
testing → quality assurance
```

```text
programming = 2
quality assurance = 2
```

---

# 🔴 6. Differenza fondamentale

| Dimensione  | Observed                | Canonical                    |
| ----------- | ----------------------- | ---------------------------- |
| Origine     | Job                     | ESCO                         |
| Significato | domanda reale           | conoscenza teorica           |
| Peso        | frequenza skill nei job | frequenza occupation nei job |
| Rumore      | alto                    | basso                        |
| Completezza | bassa                   | alta                         |

---

# 🧠 7. Interpretazione

## Observed

> “cosa le aziende chiedono esplicitamente”

## Canonical

> “cosa ESCO dice che serve per quel lavoro”

---

# 🎯 8. Perché serve tutto questo

Il sistema combina:

```text
Observed (mercato)
+
Canonical (modello)
+
Skill Groups (astrazione)
+
Sector (aggregazione)
```

per ottenere:

* analisi robusta
* confronto tra settori
* identificazione gap

---

# 🔥 9. Insight possibili

| Caso                     | Significato     |
| ------------------------ | --------------- |
| Observed ↑ / Canonical ↓ | skill emergente |
| Observed ↓ / Canonical ↑ | skill mancante  |
| Entrambi ↑               | skill core      |
| Entrambi ↓               | skill marginale |

---

# 🧾 TL;DR

> Il sistema proietta le skill ESCO (canonical) sulla distribuzione reale dei job, aggregandole per settore e astraendole tramite skill group per supportare analisi robuste e confrontabili.

---

Se vuoi, nel prossimo step ti faccio:

👉 versione **perfettamente allineata alla Task 3.5 (con NACE + matrix)**
👉 oppure un diagramma architetturale pronto per slide/paper
# 3. Sector systems

## 3.1 ISCO mode

- Native occupation-centric flow:
  `job -> occupation -> isco_group -> ISCO label`.
- View names remain:
  - Observed
  - Canonical
  - Official Matrix

## 3.2 NACE mode

- Economic-activity flow:
  `job -> occupation -> ESCO-NACE crosswalk -> nace_code -> NACE label`.
- One ESCO occupation may map to multiple NACE sectors.
- Current implementation keeps non-weighted multi-mapping to support sector-skill relation discovery.

## 3.3 NACE view semantics

- **Observed**: skills observed in jobs mapped to a NACE sector.
- **Derived Canonical**: ESCO canonical relations aggregated by NACE via crosswalk.
- **Aggregated Official Matrix**: ESCO official matrix aggregated by NACE via crosswalk.

## 3.4 Dashboard behavior

- Sector selector switches the active system between ISCO and NACE.
- NACE level selector uses conceptual labels (`Section/Division/Group/Class`) and maps to
  `nace_section/nace_division/nace_group/nace_class`.
- Sector charts/tables/cards follow the selected system payload.
- Level switching updates all NACE sectoral views (pie, selector list, detail panels and comparison summary), not only the comparison block.
- Comparison block is descriptive only (no one-to-one ISCO↔NACE mapping claim).
