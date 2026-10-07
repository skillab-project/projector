# Configuration and Docker Compose

This is the canonical reference for SKILLAB Projector runtime configuration.
The quick-start and database guides link here instead of maintaining separate
copies of environment-variable defaults.

## Compose Files

The repository has two standalone Compose files. Always select the intended
file explicitly; `docker-compose.dev.yml` is not an automatic Compose override.

| File | Purpose | Services | Host ports |
| --- | --- | --- | --- |
| `docker-compose.dev.yml` | local development and demo | database, API, dashboard, snapshot scheduler | DB `5433`, API `8000`, dashboard `8501` |
| `docker-compose.yml` | deployment-oriented API stack | database and API; snapshot scheduler is present but commented out | DB `8014`, API `8013` |

Start the local application stack:

```bash
docker compose -f docker-compose.dev.yml up -d \
  projector-db projector-api projector-dashboard
```

Start only the local database:

```bash
docker compose -f docker-compose.dev.yml up -d projector-db
```

Start the database and recurring snapshot scheduler:

```bash
docker compose -f docker-compose.dev.yml up -d \
  projector-db projector-snapshot-refresh
```

The deployment-oriented file requires image naming variables and currently
does not enable the dashboard or snapshot scheduler:

```bash
docker compose -f docker-compose.yml up -d projector-db projector-api
```

## Configuration Files and Precedence

Compose uses two different environment mechanisms:

- Compose interpolation reads shell variables and the root `.env` file. It
  resolves expressions such as `${SNAPSHOT_PAGE_SIZE:-500}` before containers
  are created.
- `env_file` passes variables into a container. The development services use
  `dev.env`; the deployment API uses `.env`.
- A service-level `environment` entry takes precedence over the same variable
  supplied by `env_file`.
- `app/core/config.py` also loads the root `.env` when the Python application is
  run directly outside Docker.

`dev.env` is ignored by Git and excluded from Docker build contexts. Do not
commit Tracker credentials. Treat `.env` the same way when it contains secrets.

Example local `dev.env`:

```env
TRACKER_API=https://your-tracker-url
TRACKER_USERNAME=your_username
TRACKER_PASSWORD=your_password
CI=false
DATABASE_URL=postgresql://skillab:skillab@projector-db:5432/skillab_projector
```

When running Python directly on the host, use the published database port
instead:

```env
DATABASE_URL=postgresql://skillab:skillab@localhost:5433/skillab_projector
```

## Services

### `projector-db`

PostgreSQL 16 stores the sector snapshots.

| Setting | Development | Deployment-oriented |
| --- | --- | --- |
| Container port | `5432` | `5432` |
| Host port | `5433` | `8014` |
| Database | `skillab_projector` | `skillab_projector` |
| User | `skillab` | `skillab` |
| Persistent volume | `projector-db-data` | `projector-db-data` |
| Initialization | `migrations/` mounted read-only | `migrations/` mounted read-only |
| Health check | `pg_isready` | `pg_isready` |

Migration scripts run only when PostgreSQL initializes an empty data volume.
Removing the volume with `down -v` destroys the local database and causes the
migrations and demo seed data to run again on the next start.

### `projector-api`

The FastAPI service is built from `Dockerfile.app` and starts
`uvicorn app.main:app` on container port `8000`.

| Setting | Development | Deployment-oriented |
| --- | --- | --- |
| Host port | `8000` | `8013` |
| Environment file | `dev.env` | `.env` |
| Database hostname | `projector-db` | `projector-db` |
| Cache volume | `projector-api-cache` | `projector-api-cache` |
| Log volume | `projector-api-logs` | `projector-api-logs` |
| Dependency | healthy `projector-db` | healthy `projector-db` |
| Health endpoint | `/projector/health` | `/projector/health` |

### `projector-dashboard`

The Streamlit dashboard exists only in `docker-compose.dev.yml`. It waits for a
healthy API and connects to it through the internal Compose network.

| Setting | Value |
| --- | --- |
| Host/container port | `8501` / `8501` |
| API URL | `http://projector-api:8000/projector` |
| Environment file | `dev.env` |
| Entrypoint | `app/example_dashboard/demo_dashboard.py` |

### `projector-snapshot-refresh`

The long-running scheduler is built from `Dockerfile.snapshot`. It is enabled
in `docker-compose.dev.yml` and commented out in `docker-compose.yml`.

It depends on a healthy database, stores resumable fetch data in
`projector-snapshot-cache`, writes logs to `projector-snapshot-logs`, and uses
`restart: always`.

## Application Variables

| Variable | Required | Default | Used by | Meaning |
| --- | --- | --- | --- | --- |
| `TRACKER_API` | yes for live Tracker data | none | API, scheduler | Tracker base URL |
| `TRACKER_USERNAME` | yes for live Tracker data | none | API, scheduler | Tracker login username |
| `TRACKER_PASSWORD` | yes for live Tracker data | none | API, scheduler | Tracker login password |
| `DATABASE_URL` | yes for snapshot features | none | API, scheduler, scripts | PostgreSQL connection URL |
| `TRACKER_CACHE_TTL_DAYS` | no | `30` | API, scheduler | Completed Tracker-cache lifetime in days; `0` disables expiry |
| `SKILLAB_USE_LOCAL_SECTOR_FILES` | no | `false` | API, scheduler | Accepts `1`, `true`, `yes`, or `on`; enables local sector support files |
| `PROJECTOR_API_BASE_URL` | no | `http://127.0.0.1:8000/projector` | dashboard | API base URL; Compose overrides it with the internal service URL |
| `CI` | no | unset | tests/tooling | Marks CI execution where checked |

## Snapshot Scheduler Variables

These variables configure `projector-snapshot-refresh`. Empty start/end years
mean the current year.

| Variable | Default | Meaning |
| --- | --- | --- |
| `SNAPSHOT_INTERVAL_MONTHS` | `3` | Minimum age of the latest completed snapshot before refresh |
| `SNAPSHOT_CHECK_INTERVAL_DAYS` | `1` | Time between due-date checks |
| `SNAPSHOT_START_YEAR` | current year | First year included in a refresh |
| `SNAPSHOT_END_YEAR` | current year | Last year included in a refresh |
| `SNAPSHOT_REGIONS` | auto-detected | Comma-separated location codes |
| `SNAPSHOT_SKIP_GLOBAL` | `false` | Skip the global snapshot when true |
| `SNAPSHOT_RUN_IMMEDIATELY` | `true` | Check and run a due refresh on scheduler startup |
| `SNAPSHOT_PAGE_SIZE` | `500` | Jobs requested per Tracker page |
| `SNAPSHOT_PAGE_CONCURRENCY` | `4` | Tracker pages fetched concurrently |
| `SNAPSHOT_MAX_RETRIES` | `5` | Retries for each Tracker page |
| `SNAPSHOT_SCHEDULER_LOG_FILE` | `logs/sector_snapshot_scheduler.log` | Log path inside the container |
| `SNAPSHOT_DEBUG` | `false` | Enable verbose scheduler console logging |

Boolean scheduler variables accept `1`, `true`, `yes`, and `on` as true
values. Other values are treated as false.

Example override:

```bash
SNAPSHOT_START_YEAR=2024 \
SNAPSHOT_END_YEAR=2024 \
SNAPSHOT_PAGE_CONCURRENCY=8 \
docker compose -f docker-compose.dev.yml up -d \
  projector-db projector-snapshot-refresh
```

## Deployment Image Variables

`docker-compose.yml` constructs the API image name from these Compose-time
variables. They must be available in the shell or root `.env` before Compose
parses the file.

| Variable | Meaning | Example |
| --- | --- | --- |
| `APP_NAME` | Container and image name | `skillab-projector-api` |
| `DOCKER_REG` | Registry hostname, including any intended separator | `harbor.example.org` |
| `DOCKER_REPO` | Registry repository path | `/skillab-all/` |
| `DOCKER_TAG` | Image tag | `latest` |

The resulting reference is
`${DOCKER_REG}${DOCKER_REPO}${APP_NAME}:${DOCKER_TAG}`.

## Operations and Diagnostics

Render and validate the resolved local Compose configuration:

```bash
docker compose -f docker-compose.dev.yml config
```

Inspect status and health:

```bash
docker compose -f docker-compose.dev.yml ps
```

Follow API or scheduler logs:

```bash
docker compose -f docker-compose.dev.yml logs -f projector-api
docker compose -f docker-compose.dev.yml logs -f projector-snapshot-refresh
```

Stop the local stack without deleting data:

```bash
docker compose -f docker-compose.dev.yml down
```

Reset the local database and all named Compose volumes:

```bash
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml up -d projector-db
```

`down -v` is destructive for local database, cache, and log volumes.
