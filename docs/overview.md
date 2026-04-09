# Overview

## What the SKILLAB Projector is
The **SKILLAB Projector** is a FastAPI microservice that sits on top of the SKILLAB Tracker and transforms raw job-posting records into **labor-market intelligence**.

Instead of returning individual vacancies only, it returns a structured summary of a filtered market slice, including:
- top requested skills,
- sector distribution,
- top employers,
- top job titles,
- trend signals over time,
- geographic decomposition,
- specialization indicators by area.

## What problem it solves
The Tracker is useful for retrieving vacancy records. The Projector is useful when you need to answer questions such as:
- Which skills are most requested in a selected market?
- Which skills are rising or declining over time?
- Which employers dominate the current hiring volume?
- Which territories appear specialized in a competence?
- How should a dashboard summarize a large batch of job postings?

## Typical users
### Developers
Need a stable API that returns aggregated intelligence rather than thousands of raw records.

### Dashboard authors
Need ready-to-visualize data structures for rankings, trends, and maps.

### Analysts and project stakeholders
Need interpretable indicators without reading the code.

## What the service currently exposes
The public API currently exposes three endpoints:
- `POST /projector/analyze-skills`
- `POST /projector/emerging-skills`
- `POST /projector/stop`

## What `analyze-skills` gives you
This is the main endpoint and should be considered the default entry point for consumers.

It returns:
- summary context for the analyzed batch,
- paginated top-skill ranking,
- sectors,
- employers,
- job titles,
- trend analysis computed on the selected period,
- raw and NUTS-like regional projections.

## What `emerging-skills` gives you
This is a lighter endpoint specialized in trend analysis.

It compares two sub-periods inside the requested time window and answers one core question:
> what is increasing, decreasing, or newly appearing?

## What `stop` gives you
This endpoint sends a cooperative stop signal to the engine.
It does not kill a process instantly. It asks the engine to stop safely at the next checkpoint.

## Important conceptual distinction
The Projector is not a pure CRUD API.
It is an **analytics API**.

That means the documentation must explain two things clearly:
1. **how to call the endpoints**, and
2. **what the returned indicators actually mean**.

Swagger covers the first point well.
This `/docs` package exists mainly to cover the second one.
