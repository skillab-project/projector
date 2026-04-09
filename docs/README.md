# SKILLAB Projector Documentation

This folder contains the recommended documentation structure for the **SKILLAB Projector** API.

It is designed for three audiences:
- developers integrating the API,
- dashboard or frontend authors,
- stakeholders who need to understand what the service does without reading the source code.

## Suggested reading order
1. **overview.md** — what the service is, what problem it solves, and when to use it
2. **api-reference.md** — endpoint-by-endpoint reference
3. **data-model.md** — meaning of fields and metrics returned by the API
4. **architecture.md** — internal flow, Tracker dependency, caching, stop behavior, and caveats
5. **examples.md** — ready-to-use request/response examples and integration patterns

## Why this structure
FastAPI Swagger is excellent for trying endpoints, but it does not explain the business meaning of concepts such as:
- market health,
- specialization / location quotient,
- raw geography vs NUTS-like geography,
- emerging vs declining skills,
- demo mode.

For that reason, the recommended production setup is:
- **Swagger/OpenAPI** for interactive technical exploration,
- this **/docs** folder for stable, versioned written documentation.

## Recommended repo layout
```text
repo-root/
├── main.py
├── schemas.py
├── README.md
└── docs/
    ├── README.md
    ├── overview.md
    ├── api-reference.md
    ├── data-model.md
    ├── architecture.md
    └── examples.md
```

## Publishing recommendation
For the current maturity of the project, the best choice is to keep this documentation **inside the repository** under `/docs`.

That gives you:
- versioning together with the code,
- simple maintenance,
- clear navigation for collaborators,
- easy promotion later to GitHub Pages or ReadTheDocs if needed.
