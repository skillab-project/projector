SKILLAB PROJECTOR: Development Backlog & Planning
1. Project Overview
SKILLAB Projector is a microservice designed to decompose knowledge and insights from the Skills Analyzer and Forecaster. Its goal is to provide fine-grained, actionable information across three core dimensions: Geography, Time, and Sectors.

2. EPIC 1: Data Integration & Multi-Dimensional Filtering
Objective: Connect to the Tracker API to ingest raw job market data and apply cross-dimensional filters.
User Story 1.1: API Connectivity & Authentication
As a Projector microservice,
I want to authenticate and connect to the /api/jobs endpoint,
So that I can retrieve job posting data securely.
User Story 1.2: Geographical Filtering
As a User,
I want to filter skill projections by location_code (NUTS/ISO),
So that I can analyze specific regional labor markets.
User Story 1.3: Temporal Filtering
As a User,
I want to define time intervals using min_upload_date and max_upload_date,
So that I can compare skill demand across different periods.
User Story 1.4: Sectorial Filtering
As a User,
I want to filter data by occupation_ids (ESCO) or keywords,
So that I can isolate and analyze specific industrial sectors.

3. EPIC 2: Skill Decomposition & Analysis (Core Logic)
Objective: Transform raw text and metadata into atomic insights and statistical projections.
User Story 2.1: Atomic Skill Decomposition
As a Microservice,
I want to extract and map skills from job descriptions to the ESCO standard,
So that I can provide high-granularity information.
User Story 2.2: Trend Projection
As an Analyst,
I want to calculate the percentage change of skill requirements between two timeframes,
So that I can identify "Emerging Skills."
User Story 2.3: Geographical Gap Analysis
As a Policymaker,
I want to compare skill density between two different regions,
So that I can identify territorial skill gaps.
User Story 2.4: Cross-Sectoral Correlation
As an HR Manager,
I want to identify transversal skills common to multiple sectors (e.g., Digital Skills in the Green sector),
So that I can optimize reskilling strategies.

4. EPIC 3: API Delivery & Explainable AI (XAI)
Objective: Expose processed insights through interpretable and integrable API endpoints.
User Story 3.1: Projection API Endpoint
As a Developer of the Intelligent Agent,
I want to invoke a Projector endpoint that returns aggregated JSON projections,
So that I don't have to process individual raw job records.
User Story 3.2: Explainability & Insights
As an End User,
I want the Projector to provide the "why" behind a projection (e.g., "This skill is critical because it appears in 40% of sector X postings"),
So that I can trust the data for decision-making.
User Story 3.3: Integration with Organizational Recommender
As a Microservice,
I want to push processed data to the Recommender module,
So that it can suggest upskilling paths based on real-time market trends.

5. Sprint 1 Implementation Plan (Sample)
Task ID
Task Description
Priority
Story Points
TSK-01
Setup Microservice boilerplate (FastAPI + Docker)
High
3
TSK-02
Develop Python client for /api/jobs with pagination
High
5
TSK-03
Implement Multi-Dimensional Parser (Time, Space, Sector)
High
8
TSK-04
Create Unit Tests for API integration and mapping
Medium
3


6. Definition of Done (DoD)
Code passes all integration tests with the Skillab Tracker API.
Extracted data is correctly mapped to ESCO URIs.
Microservice handles high-volume data requests asynchronously.
OpenAPI (Swagger) documentation is fully updated.

