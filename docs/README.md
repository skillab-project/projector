# SKILLAB Projector Documentation

## Index
- [Purpose of this documentation](#purpose-of-this-documentation)
- [Suggested reading order](#suggested-reading-order)
- [Why this structure](#why-this-structure)
- [Recommended repository layout](#recommended-repository-layout)
- [Publishing recommendation](#publishing-recommendation)

---

## Purpose of this documentation

This folder contains the recommended documentation structure for the **SKILLAB Projector** API.

It is designed for three audiences:
- developers integrating the API,
- dashboard or frontend authors,
- stakeholders who need to understand what the service does without reading the source code.

---

## Suggested reading order

### Section index
- [Overview document](./overview.md)
- [API reference document](./api-reference.md)
- [Data model document](./data-model.md)
- [Architecture document](./architecture.md)
- [Examples document](./examples.md)

1. **[overview.md](./overview.md)** — what the service is, what problem it solves, and when to use it  
2. **[api-reference.md](./api-reference.md)** — endpoint-by-endpoint reference  
3. **[data-model.md](./data-model.md)** — meaning of fields and metrics returned by the API  
4. **[architecture.md](./architecture.md)** — internal flow, Tracker dependency, caching, stop behavior, and caveats  
5. **[examples.md](./examples.md)** — ready-to-use request/response examples and integration patterns  

---

## Why this structure

FastAPI Swagger is excellent for trying endpoints, but it does not explain the business meaning of concepts such as:
- market health,
- specialization / location quotient,
- raw geography vs NUTS-like geography,
- emerging vs declining skills,
- demo mode.

For that reason, the recommended production setup is:
- **Swagger/OpenAPI** for interactive technical exploration  
- this **/docs** folder for stable, versioned written documentation  

---

## Recommended repository layout

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