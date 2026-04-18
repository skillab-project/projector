Perfetto, ti faccio una **tabella chiara, completa e “da documentazione ufficiale”** 👇
(con ruolo, relazioni e uso nel codice)

---

# 📂 SKILLAB Projector – File ESCO & Data Sources

| File                                  | Tipo            | Contenuto                  | Relazione principale                                | Come lo usi                         | Esempio                      |
| ------------------------------------- | --------------- | -------------------------- | --------------------------------------------------- | ----------------------------------- | ---------------------------- |
| **`occupations_en.csv`**              | ESCO CSV        | Occupation + metadati      | `occupation → isco_group`, `occupation → nace_code` | Definisce il **sector**             | `Software Developer → 2512`  |
| **`ISCOGroups_en.csv`**               | ESCO CSV        | Label gruppi ISCO          | `isco_group → label`                                | Traduce i sector in label leggibili | `2512 → Software developers` |
| **`occupationSkillRelations_en.csv`** | ESCO CSV        | Relazione occupation-skill | `occupation → skill`                                | Costruisce il **canonical**         | `Software Dev → programming` |
| **`skillsHierarchy_en.csv`**          | ESCO CSV        | Gerarchia skill            | `skill → skill_group`                               | Aggregazione semantica              | `python → programming`       |
| **`Skills_Occupations Matrix.xlsx`**  | ESCO ufficiale  | Matrice pesata             | `occupation_group → skill_group → weight`           | Analisi avanzata/policy             | `C251 → programming = 0.8`   |
| **Job API**                           | SKILLAB Tracker | Job reali                  | `job → occupation`, `job → skill`                   | Costruisce **observed**             | job con python, sql          |

---

# 🔗 Relazioni tra i file

## 🔵 Core mapping

```text
job
 → occupation (Tracker)
 → occupations_en.csv
     → isco_group
     → nace_code
```

---

## 🔵 Skill mapping

```text
job → skills (observed)

occupationSkillRelations_en.csv
 → occupation → skills (canonical)
```

---

## 🔵 Skill grouping

```text
skillsHierarchy_en.csv
 → skill → skill_group
```

---

## 🔵 Sector labeling

```text
occupations_en.csv → isco_group
ISCOGroups_en.csv → label
```

---

## 🔵 Matrice avanzata

```text
Matrix Excel
 → occupation_group → skill_group → weight
```

---

# 📊 Schema completo (visivo)

```text id="c8t5wv"
JOB (Tracker)
 ├── occupation_id
 │     └── occupations_en.csv
 │            ├── isco_group → ISCOGroups_en.csv → sector label
 │            └── nace_code (non usato ora)
 │
 ├── skills (observed)
 │     └── skillsHierarchy_en.csv → skill groups
 │
 └── canonical (via occupationSkillRelations_en.csv)
       └── skillsHierarchy_en.csv → skill groups

+ (opzionale)
Matrix Excel → weighted skill groups
```

---

# 🧠 Ruolo di ogni file (in una riga)

| File                              | Ruolo                       |
| --------------------------------- | --------------------------- |
| `occupations_en.csv`              | definisce i sector          |
| `ISCOGroups_en.csv`               | rende leggibili i sector    |
| `occupationSkillRelations_en.csv` | definisce il canonical      |
| `skillsHierarchy_en.csv`          | permette aggregazione       |
| Matrix Excel                      | aggiunge pesi (avanzato)    |
| Job API                           | porta la realtà del mercato |

---

# 🔥 Differenza concettuale chiave

| Tipo        | File                     | Significato        |
| ----------- | ------------------------ | ------------------ |
| Observed    | Job API                  | domanda reale      |
| Canonical   | occupationSkillRelations | modello ESCO       |
| Aggregation | skillsHierarchy          | semplificazione    |
| Sector      | occupations + ISCOGroups | dimensione analisi |
| Advanced    | Matrix                   | pesi realistici    |

---

# 📌 Esempio end-to-end

## Input

```json
job:
{
  "occupation": "Software Developer",
  "skills": ["python", "sql"]
}
```

---

## Mapping

```text
occupations_en.csv:
Software Developer → 2512

ISCOGroups_en.csv:
2512 → Software developers
```

---

## Canonical

```text
occupationSkillRelations:
Software Developer → programming, testing
```

---

## Skill Groups

```text
skillsHierarchy:
python → programming
sql → data management
```

---

## Output finale

```text
Sector: Software developers

Observed:
python, sql

Canonical:
programming, testing

Skill Groups:
programming, data management
```

---

# 🎯 TL;DR

> Il sistema combina più file ESCO per trasformare job reali in analisi strutturate tramite mapping occupation → sector, skill → group e canonical knowledge.

---

Se vuoi, prossimo step ti faccio:

👉 una versione **super sintetica da README (10 righe)**
👉 oppure un diagramma tipo architettura per slide/paper
## Additional source: ESCO-NACE crosswalk

- File type: crosswalk workbook
- Content: `occupation (ESCO URI) -> one or more NACE codes/titles`
- Main use: NACE label resolution and NACE sector aggregation

Relational flow:

```text
occupation (ESCO)
 -> ESCO-NACE crosswalk
    -> nace_code
    -> nace_title
```

Note:
- `occupations_en.csv` may still expose a single `nace_code`.
- The crosswalk is now the preferred source for NACE-facing semantics and labels.
