# Overview

## Index
- [Projector definition](#projector-definition)
- [Problem it solves](#problem-it-solves)
- [Typical users](#typical-users)
- [Exposed endpoints](#exposed-endpoints)
- [Analyze skills endpoint overview](#analyze-skills-endpoint-overview)
- [Emerging skills endpoint overview](#emerging-skills-endpoint-overview)
- [Stop endpoint overview](#stop-endpoint-overview)
- [Conceptual distinction](#conceptual-distinction)

---

## Projector definition

The **SKILLAB Projector** is a FastAPI microservice that sits on top of the SKILLAB Tracker and transforms raw job-posting records into **labor-market intelligence**.

Instead of returning individual vacancies only, it returns a structured summary of a filtered market slice, including:
- top requested skills,
- sector distribution,
- top employers,
- top job titles,
- trend signals over time,
- geographic decomposition,
- specialization indicators by area.

---

## Problem it solves

The Tracker is useful for retrieving vacancy records. The Projector is useful when you need to answer questions such as:
- Which skills are most requested in a selected market?
- Which skills are rising or declining over time?
- Which employers dominate the current hiring volume?
- Which territories appear specialized in a competence?
- How should a dashboard summarize a large batch of job postings?

---

## Typical users

### Developers
Need a stable API that returns aggregated intelligence rather than thousands of raw records.

### Dashboard authors
Need ready-to-visualize data structures for rankings, trends, and maps.

### Analysts and project stakeholders
Need interpretable indicators without reading the code.

---

## Exposed endpoints

The public API currently exposes three endpoints:
- `POST /projector/analyze-skills`
- `POST /projector/emerging-skills`
- `POST /projector/stop`

---

## Analyze skills endpoint overview

### Section index
- [What it returns](#analyze-skills-what-it-returns)

This is the main endpoint and should be considered the default entry point for consumers.

## Analyze skills what it returns
It returns:
- summary context for the analyzed batch,
- paginated top-skill ranking,
- sectors,
- employers,
- job titles,
- trend analysis computed on the selected period,
- raw and NUTS-like regional projections.

---

## Emerging skills endpoint overview

### Section index
- [What it answers](#emerging-skills-what-it-answers)

This is a lighter endpoint specialized in trend analysis.

## Emerging skills what it answers
It compares two sub-periods inside the requested time window and answers one core question:

> what is increasing, decreasing, or newly appearing?

---

## Stop endpoint overview

### Section index
- [Behavior](#stop-endpoint-behavior)

This endpoint sends a cooperative stop signal to the engine.

## Stop endpoint behavior
It does not kill a process instantly.  
It asks the engine to stop safely at the next checkpoint.

---

## Conceptual distinction

The Projector is not a pure CRUD API.  
It is an **analytics API**.

That means the documentation must explain two things clearly:

1. **how to call the endpoints**, and  
2. **what the returned indicators actually mean**.

Swagger covers the first point well.  
This `/docs` package exists mainly to cover the second one.
## Conceptual distinction: ISCO vs NACE

- ISCO is occupation-group centric.
- NACE is economic-activity centric.
- The system supports both to allow complementary sector analysis views.

In NACE mode:
- `Observed` is direct from job evidence mapped through crosswalk.
- `Derived Canonical` and `Aggregated Official Matrix` are ESCO-derived views aggregated by NACE (not native NACE ontologies).
