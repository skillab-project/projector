# Contributing

This repository keeps the application source, tests, CI configuration, and quality tooling together. The runtime product for users should be distributed as a release artifact, package, or Docker image; development tooling stays versioned in the source repository so every build can be reproduced.

## Branch And Release Flow

Use short-lived feature branches and open pull requests into `main`.

```text
feature/* -> pull request -> quality checks -> main -> runtime artifact
```

`main` is the stable source channel. It may contain test, CI, and quality tooling because those files define how the project is validated. Users who only need to run the API should consume a released artifact or Docker image rather than a stripped-down branch.

Do not mix unrelated infrastructure work into feature pull requests. CI, dashboard, gate, and reporting changes should use their own pull request.

## Local Development

Install runtime dependencies:

```bash
pip install -r requirements.txt
```

Install development dependencies when running the quality tooling locally:

```bash
pip install -r requirements-dev.txt
```

Start the API from the repository root:

```bash
uvicorn main:app --reload
```

Start the dashboard:

```bash
streamlit run demo_dashboard.py
```

Keep secrets in `.env` files only. `.env` files are ignored and must not be committed.

## Test Suites

The maintained test entrypoint on `main` is:

```bash
pytest test.py
```

Jenkins separates the suite into:

- unit/non-integration tests: `pytest test.py -m "not integration"`
- integration tests: `pytest test.py -m "integration"`

Integration tests require the application or external service endpoints to be reachable. The `integration` marker is registered in `pytest.ini`.

## Quality Gates

Quality thresholds and check policies live in `pyproject.toml`.

- `[tool.quality_gates]` contains numeric thresholds.
- `[tool.quality_checks]` describes labels, quality mode, Jenkins meaning, and human-readable rules.

Current enforced gates:

- tests must pass;
- total coverage must meet the configured coverage gate.

Current advisory/report-only checks:

- mutation score is advisory;
- lint reports are report-only.

The dashboard intentionally separates two concepts:

- `Jenkins Result`: whether the CI stage completed according to its Jenkins contract;
- `Quality Outcome`: how the generated metric should be interpreted.

For example, mutation testing can have `Jenkins Result = PASS` and `Quality Outcome = BELOW` because the mutation score is advisory while the stage successfully generated reports.

## Jenkins Pipeline

The Jenkins pipeline is defined in `Jenkinsfile` and runs inside the CI Docker image built from `Dockerfile.ci`.

Main stages:

- `Build CI Image`: builds the isolated Python CI environment.
- `Prepare Workspace`: removes generated reports and caches.
- `Run Tests`: runs non-integration tests with coverage and the enforced coverage gate.
- `Integration Tests`: runs tests marked `integration`.
- `Code Quality`: generates lint reports without blocking the pipeline.
- `Mutation Testing`: runs mutmut and generates mutation reports; mutation is advisory.

The pipeline publishes JUnit results, archives generated reports, generates the quality dashboard, and publishes compact GitHub commit statuses.

## GitHub Checks

Jenkins publishes custom GitHub commit statuses:

- `Jenkins / Tests`
- `Jenkins / Coverage Gate`
- `Jenkins / Mutation Advisory`
- `Jenkins / Code Quality`

These statuses are readable summaries with direct `Details` links to the relevant report.

The Jenkins native status, such as `continuous-integration/jenkins/pr-head` or `continuous-integration/jenkins/pr-merge`, represents the full pipeline result. If Jenkins is configured with pull request strategy `Both the current pull request revision and the pull request merged with the current target branch revision`, the `pr-merge` build is the strongest pre-merge signal. It only exists when the pull request can be cleanly merged with the target branch.

Recommended required checks for pull requests:

- the Jenkins native `pr-merge` check when available;
- CodeQL, if enabled as a repository rule.

The custom Jenkins statuses can remain informational because the native Jenkins status already reflects the enforced stages. They are useful for diagnosis and links.

## Dashboards And Reports

Generated reports are archived by Jenkins and ignored by Git.

Main generated artifacts:

- `quality-dashboard/index.html`: single overview for tests, coverage, mutation, quality gates, and Jenkins context.
- `test-report/index.html`: readable test report parsed from JUnit XML.
- `coverage-report/index.html`: coverage HTML report.
- `mutation-report/index.html`: mutation testing report.
- `mutation-report/status-survived.html`: survived mutants.
- `pylint-report.txt` and `flake8-report.json`: lint outputs.

The generated directories and XML files must not be committed.

## Mutation Testing

Mutmut configuration lives in `[tool.mutmut]` in `pyproject.toml`.

On `main`, mutation testing targets the current root-layout modules:

- `main.py`
- `schemas.py`

Mutation testing is advisory, so a score below the advisory target should be treated as improvement work, not as a broken pipeline.

When the package layout branch is merged, update the mutmut and coverage configuration to the package paths used by that branch.

## Where Things Live

```text
Jenkinsfile                     CI pipeline
Dockerfile.ci                   CI image
pytest.ini                      pytest markers and pytest defaults
pyproject.toml                  coverage, mutmut, quality gates, quality check policies
requirements-dev.txt            development and CI dependencies
tools/quality_gates.py          reads gate thresholds and check policies
tools/quality_dashboard.py      generates the quality dashboard
tools/test_report.py            generates the readable test report
tools/mutation_report.py        generates mutation HTML reports
tools/github_statuses.py        publishes GitHub commit statuses
```

## Before Opening A Pull Request

Make sure the pull request is focused on one topic. Avoid mixing feature code with CI or quality infrastructure unless the feature requires the infrastructure change.

At minimum, run the relevant tests locally when practical. The authoritative result is the Jenkins pipeline attached to the pull request.
