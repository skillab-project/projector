# Architecture and Operational Notes

## Runtime stack
- FastAPI for the HTTP API
- `httpx.AsyncClient` for upstream communication
- async execution model
- file-based JSON cache for job batches

## External dependency
The Projector depends on the SKILLAB Tracker for raw data and metadata enrichment.

Internally it uses:
- `POST /login`
- `POST /jobs`
- `POST /skills`
- `POST /occupations`

This means Projector latency and failure modes are partly determined by Tracker availability and response times.

## High-level internal flow
1. Receive request from the client
2. Build filter payload
3. Authenticate against Tracker if no token is cached in memory
4. Fetch matching jobs page by page
5. Reuse cached results when the same filter payload was seen before
6. Extract occupation identifiers and resolve them to sector labels
7. Extract skill URIs and resolve them to readable labels
8. Apply heuristic green/digital tagging
9. Aggregate rankings, sectors, employers, titles, geo breakdown, and trends
10. Return the final JSON payload

## Caching behavior
The engine hashes the filter payload using MD5 and stores the raw result in:
```text
cache_data/search_<hash>.json
```

### What this means
- same payload => same cache key
- repeated analyses on identical filters can become much faster
- no cache expiration currently exists

### Operational implication
If Tracker data changes, repeated requests with the same filter may still return cached historical results until the cache is removed manually.

## Stop behavior
The API exposes `POST /projector/stop`.

Internally this sets a boolean stop flag in the engine.
Long-running methods periodically check that flag and stop safely.

### Important implication
This is not a process kill.
It is a cooperative interruption.

The client should therefore interpret the endpoint as:
> stop as soon as it is safe to stop

## Trend strategy
The code supports two trend modes conceptually:
- trend calculation from already downloaded in-memory data,
- trend calculation via two independent sub-period fetches.

The public endpoints currently use these to compare period A and period B inside a selected date range.

## Regional strategy
The engine provides two levels of geography:

### 1. Raw geography
Directly based on the `location_code` value present in source jobs.

### 2. NUTS-like geography
Constructed by string slicing, optionally with synthetic distribution when `demo=true`.

This lets the system demonstrate regional analysis even when only national location codes are available.

## Known implementation caveats
These should remain visible in documentation until fixed.

### Response-model mismatch
The declared schema and actual payload are not perfectly aligned.

### Empty payload inconsistency
The no-data response path may omit fields that are present in the declared full schema.

### Missing stop helper in one trend branch
A stop-related helper referenced in trend logic is not defined in the current codebase.

### Market-health semantics
The current market-health implementation distinguishes only between `expanding` and `shrinking`, with no dedicated `stable` state.

### Sector-counting logic deserves review
The current implementation contains a nested loop around sector counting that may inflate counts.

### Heuristic twin-transition tagging
Green and digital classification is currently heuristic and label-based, not full canonical ESCO taxonomy mapping.

## Recommended production hardening
To move from prototype-quality behavior to production-quality behavior, priority actions should be:
1. align code payloads and Pydantic schemas
2. define a standard error envelope
3. validate inputs explicitly
4. fix stop and empty-response edge cases
5. introduce versioning such as `/api/v1/...`
6. document status codes and error semantics
7. define cache invalidation strategy
