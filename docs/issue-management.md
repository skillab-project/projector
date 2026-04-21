# Issue Management

This document defines how SKILLAB Projector issues should be classified and moved through the GitHub Project.

## Core Principle

Use GitHub labels to describe what an issue is about.
Use the GitHub Project status to describe where the issue is in the workflow.

Do not use native GitHub Issue Types for this repository. Keep the native issue type empty and use exactly one `type:*` label instead.

## Type Labels

Every issue must have exactly one `type:*` label.

| Label | Use when |
| --- | --- |
| `type: epic` | The issue is an operational container for related issues or sub-issues. It closes when the linked work is complete. |
| `type: feature` | The issue describes a new capability or implementable behavior. |
| `type: bug` | The issue describes incorrect behavior against a clear expectation or specification. |
| `type: docs` | The issue is about user, API, technical, or demo documentation. |
| `type: refactor` | The issue changes internal code structure without changing functional or analytical meaning. |
| `type: chore` | The issue is maintenance, tooling, setup, Docker, CI/CD, or operational work. |
| `type: question` | The issue is a focused clarification question before it can be classified further. |
| `type: research` | The issue is open investigation where the right approach is not known yet. |
| `type: conceptual-design` | The issue defines a new analytical or conceptual model before implementation. |
| `type: conceptual-redesign` | The issue reworks an existing or planned model because the current design is misleading or inappropriate. |

## Area Labels

Use `area:*` labels to identify the project surface touched by the issue. An issue may have more than one area.

Current areas:

- `area: sectoral`
- `area: regional`
- `area: temporal`
- `area: statistical`
- `area: cross-dimension`
- `area: architecture`
- `area: api`
- `area: docs`
- `area: dashboard`
- `area: demo`
- `area: devops`
- `area: data-ingestion`
- `area: testing`

## Scope Labels

Use `scope:*` labels to describe the kind of work or reasoning required. An issue may have more than one scope.

Current scopes:

- `scope: analytical-model`: analytical definitions, interpretation rules, normalization choices, or conceptual data model.
- `scope: data-mapping`: mapping between data sources, classifications, or taxonomies such as ESCO, ISCO, or NACE.
- `scope: metrics`: metrics, scoring, ranking, or analytical calculations.
- `scope: api-response`: response shape, API contract, or returned data structure.
- `scope: validation`: sanity checks, data quality, statistical validation, or conceptual validation.
- `scope: performance`: performance, scalability, or runtime efficiency.

## Project Status

Project status belongs in the GitHub Project, not in labels.

Recommended statuses:

| Status | Meaning |
| --- | --- |
| `Backlog` | The issue is valid but not being actively shaped or implemented. |
| `In Design` | The model, solution, acceptance criteria, or tradeoffs are being defined. |
| `Decision Review` | A decision has been proposed or documented and needs validation. |
| `Ready` | The issue is clear enough to be implemented. |
| `In Progress` | Someone is actively working on it. |
| `Review` | A PR, verification step, or review is in progress. |
| `Done` | The issue is completed and can be closed. |

## Workflow Rules

Implementation issues usually follow:

```text
Backlog -> Ready -> In Progress -> Review -> Done
```

Conceptual, research, and decision issues usually follow:

```text
Backlog -> In Design -> Decision Review -> Done
```

If a conceptual issue produces implementation work:

```text
conceptual issue
  -> decision documented
  -> implementation sub-issues created
  -> conceptual issue closed
  -> sub-issues continue through the implementation workflow
```

It is valid for implementation sub-issues to remain open after their parent conceptual issue is closed. In that case, the parent represents a resolved decision, not the completion of all downstream work.

## Parent And Sub-Issue Rules

- `type: conceptual-design`, `type: conceptual-redesign`, `type: research`, and `type: question` issues close when the decision is made and documented.
- `type: epic` issues close when their linked implementation work is complete.
- `type: feature` issues should stay reasonably small. If they produce multiple independent work items, consider creating sub-issues or promoting the parent to `type: epic`.

## Examples

### Sector Definition

Issue: `Understand what Sector is`

Suggested classification:

- `type: conceptual-design`
- `area: sectoral`
- `scope: analytical-model`
- `scope: data-mapping`

Suggested project status:

- `In Design` while the model is being discussed.
- `Decision Review` when a decision has been documented and needs validation.
- `Done` once the decision is accepted and implementation sub-issues exist.

### Sectoral Intelligence And Time

Issue: `Sectoral Intelligence depends on Time`

Suggested classification:

- `type: conceptual-redesign`
- `area: sectoral`
- `area: temporal`
- `scope: analytical-model`

Suggested project status:

- `In Design` while the corrected model is being shaped.
- `Decision Review` when the proposed model is written down.
- `Done` when the decision is accepted and implementation sub-issues have been created.

### Regional x Sectoral Output

Issue: `Regional x Sectoral: most represented sectors by region`

Suggested classification:

- `type: feature`
- `area: cross-dimension`
- `area: regional`
- `area: sectoral`
- `scope: analytical-model`
- `scope: metrics`
- `scope: api-response`

Suggested project status:

- `Ready` only after the output shape, metrics, and acceptance criteria are clear.
