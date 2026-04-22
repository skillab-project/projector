#!/usr/bin/env python3
import argparse
import html
import json
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from quality_gates import load_check_policies, load_gates


DASHBOARD_CSS = """
:root {
  color-scheme: light;
  --bg: #f5f7fa;
  --panel: #ffffff;
  --ink: #1f2328;
  --muted: #667085;
  --line: #d7dde5;
  --green: #237a4b;
  --red: #b42318;
  --amber: #a15c00;
  --blue: #255c99;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: var(--bg);
  color: var(--ink);
  line-height: 1.45;
}
a { color: var(--blue); text-decoration-thickness: 1px; text-underline-offset: 2px; }
header {
  padding: 32px clamp(18px, 4vw, 56px) 24px;
  border-bottom: 1px solid var(--line);
  background: #eef3f8;
}
main {
  padding: 24px clamp(18px, 4vw, 56px) 48px;
  display: grid;
  gap: 24px;
}
h1, h2 { margin: 0; letter-spacing: 0; }
h1 { font-size: clamp(28px, 5vw, 44px); }
h2 { font-size: 20px; margin-bottom: 12px; }
.meta { color: var(--muted); margin-top: 8px; }
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}
.card, section {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
}
.card { padding: 16px; }
.card strong {
  display: block;
  font-size: 28px;
  margin-bottom: 4px;
}
.card span { color: var(--muted); }
section { padding: 18px; overflow: auto; }
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
  min-width: 700px;
}
th, td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--line);
  text-align: left;
  vertical-align: top;
}
th { color: var(--muted); background: #fbfcfd; }
code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
}
.pill {
  display: inline-block;
  min-width: 76px;
  text-align: center;
  padding: 3px 8px;
  border-radius: 999px;
  color: white;
  font-size: 12px;
  font-weight: 700;
}
.pass { background: var(--green); }
.fail { background: var(--red); }
.below { background: var(--amber); }
.info { background: var(--blue); }
.missing { background: var(--muted); }
.links {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.links a {
  display: inline-block;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: #fff;
  padding: 7px 12px;
  color: var(--ink);
  text-decoration: none;
}
""".strip()


@dataclass
class TestSummary:
    label: str
    path: str
    exists: bool
    tests: int = 0
    failures: int = 0
    errors: int = 0
    skipped: int = 0
    time: float = 0.0

    @property
    def passed(self):
        return max(self.tests - self.failures - self.errors - self.skipped, 0)

    @property
    def status(self):
        if not self.exists:
            return "missing"
        if self.failures or self.errors:
            return "fail"
        return "pass"


def e(value):
    return html.escape(str(value))


def pct(value):
    return f"{value * 100:.1f}%"


def pill(status):
    labels = {
        "pass": "PASS",
        "fail": "FAIL",
        "below": "BELOW",
        "info": "INFO",
        "missing": "MISSING",
    }
    return f'<span class="pill {status}">{labels.get(status, status.upper())}</span>'


def get_build_context():
    change_id = os.environ.get("CHANGE_ID", "")
    marker_source = " ".join(
        os.environ.get(name, "")
        for name in ("JOB_NAME", "BUILD_URL", "BRANCH_NAME")
    ).lower()

    if change_id:
        if "merge" in marker_source:
            mode = "PR merge"
        elif "head" in marker_source:
            mode = "PR head"
        else:
            mode = "PR"
        scope = f"PR #{change_id}"
        source = os.environ.get("CHANGE_BRANCH") or os.environ.get("BRANCH_NAME") or "unknown"
        target = os.environ.get("CHANGE_TARGET") or "unknown"
    else:
        mode = "Branch"
        scope = os.environ.get("BRANCH_NAME") or "unknown"
        source = scope
        target = ""

    return {
        "mode": mode,
        "scope": scope,
        "source": source,
        "target": target,
        "sha": os.environ.get("GIT_COMMIT", ""),
        "build_url": os.environ.get("BUILD_URL", ""),
    }


def parse_junit(path, label):
    file_path = Path(path)
    if not file_path.exists():
        return TestSummary(label=label, path=path, exists=False)

    root = ET.parse(file_path).getroot()
    suites = [root] if root.tag == "testsuite" else root.findall("testsuite")
    summary = TestSummary(label=label, path=path, exists=True)
    for suite in suites:
        summary.tests += int(suite.attrib.get("tests", 0))
        summary.failures += int(suite.attrib.get("failures", 0))
        summary.errors += int(suite.attrib.get("errors", 0))
        summary.skipped += int(suite.attrib.get("skipped", 0))
        summary.time += float(suite.attrib.get("time", 0.0))
    return summary


def parse_coverage(path):
    file_path = Path(path)
    if not file_path.exists():
        return {"exists": False}

    root = ET.parse(file_path).getroot()
    classes = []
    for class_node in root.findall(".//class"):
        filename = class_node.attrib.get("filename", "")
        line_rate = float(class_node.attrib.get("line-rate", 0.0))
        branch_rate = float(class_node.attrib.get("branch-rate", 0.0))
        classes.append({"filename": filename, "line_rate": line_rate, "branch_rate": branch_rate})

    lines_valid = int(root.attrib.get("lines-valid", 0))
    lines_covered = int(root.attrib.get("lines-covered", 0))
    branches_valid = int(root.attrib.get("branches-valid", 0))
    branches_covered = int(root.attrib.get("branches-covered", 0))
    total_valid = lines_valid + branches_valid
    total_covered = lines_covered + branches_covered
    total_rate = (total_covered / total_valid) if total_valid else 0.0

    return {
        "exists": True,
        "total_rate": total_rate,
        "line_rate": float(root.attrib.get("line-rate", 0.0)),
        "branch_rate": float(root.attrib.get("branch-rate", 0.0)),
        "lines_valid": lines_valid,
        "lines_covered": lines_covered,
        "branches_valid": branches_valid,
        "branches_covered": branches_covered,
        "worst_files": sorted(classes, key=lambda item: item["line_rate"])[:5],
    }


def parse_mutation(path):
    file_path = Path(path)
    if not file_path.exists():
        return {"exists": False}

    data = json.loads(file_path.read_text(encoding="utf-8"))
    killed = int(data.get("killed", 0))
    survived = int(data.get("survived", 0))
    effective = killed + survived
    score = (killed / effective) if effective else 0.0
    return {"exists": True, "score": score, **data}


def render_cards(tests, coverage, mutation, coverage_gate, mutation_advisory):
    total_tests = sum(item.tests for item in tests if item.exists)
    total_failed = sum(item.failures + item.errors for item in tests if item.exists)
    total_skipped = sum(item.skipped for item in tests if item.exists)
    total_passed = sum(item.passed for item in tests if item.exists)
    coverage_value = coverage.get("total_rate", 0.0) if coverage.get("exists") else None
    mutation_value = mutation.get("score", 0.0) if mutation.get("exists") else None

    return f"""
    <div class="cards">
      <div class="card"><strong>{total_passed}/{total_tests}</strong><span>tests passed</span></div>
      <div class="card"><strong>{total_failed}</strong><span>test failures/errors</span></div>
      <div class="card"><strong>{total_skipped}</strong><span>tests skipped</span></div>
      <div class="card"><strong>{pct(coverage_value) if coverage_value is not None else "missing"}</strong><span>coverage, gate {coverage_gate:.0f}%</span></div>
      <div class="card"><strong>{pct(mutation_value) if mutation_value is not None else "missing"}</strong><span>mutation, advisory {mutation_advisory:.0f}%</span></div>
      <div class="card"><strong>{mutation.get("survived", "missing")}</strong><span>survived mutants</span></div>
    </div>
    """


def render_build_context(context):
    rows = [
        ("Build mode", context["mode"]),
        ("Scope", context["scope"]),
        ("Source branch", context["source"]),
    ]
    if context["target"]:
        rows.append(("Target branch", context["target"]))
    if context["sha"]:
        rows.append(("Commit", context["sha"][:12]))
    if context["build_url"]:
        rows.append(("Jenkins build", f'<a href="{e(context["build_url"])}">Open build</a>'))

    body = "\n".join(
        f"<tr><td>{e(label)}</td><td>{value if value.startswith('<a ') else e(value)}</td></tr>"
        for label, value in rows
    )
    return f"""
    <section>
      <h2>Build Context</h2>
      <table>
        <tbody>{body}</tbody>
      </table>
    </section>
    """


def render_test_table(tests):
    rows = []
    for item in tests:
        rows.append(
            f"""
            <tr>
              <td>{e(item.label)}</td>
              <td>{pill(item.status)}</td>
              <td>{item.tests if item.exists else "missing"}</td>
              <td>{item.passed if item.exists else "missing"}</td>
              <td>{item.failures if item.exists else "missing"}</td>
              <td>{item.errors if item.exists else "missing"}</td>
              <td>{item.skipped if item.exists else "missing"}</td>
              <td><code>{e(item.path)}</code></td>
            </tr>
            """
        )
    return f"""
    <section>
      <h2>Tests</h2>
      <table>
        <thead><tr><th>Suite</th><th>Status</th><th>Total</th><th>Passed</th><th>Failures</th><th>Errors</th><th>Skipped</th><th>Source</th></tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </section>
    """


def render_gate_table(tests, coverage, mutation, coverage_gate, mutation_advisory, check_policies):
    test_outcome = "fail" if any(item.status == "fail" for item in tests) else "pass"
    if any(item.status == "missing" for item in tests):
        test_outcome = "missing" if test_outcome == "pass" else test_outcome

    if coverage.get("exists"):
        coverage_outcome = "pass" if coverage["total_rate"] * 100 >= coverage_gate else "fail"
        coverage_note = (
            f'{check_policies["coverage"]["rule"]}: '
            f'{pct(coverage["total_rate"])} >= {coverage_gate:.0f}%'
        )
    else:
        coverage_outcome = "missing"
        coverage_note = f'{check_policies["coverage"]["rule"]}: coverage.xml not found'

    if mutation.get("exists"):
        mutation_outcome = "pass" if mutation["score"] * 100 >= mutation_advisory else "below"
        mutation_note = f'{pct(mutation["score"])} advisory threshold {mutation_advisory:.0f}%'
    else:
        mutation_outcome = "missing"
        mutation_note = "mutmut stats not found"

    rows = [
        ("tests", test_outcome, test_outcome, check_policies["tests"]["rule"]),
        ("coverage", coverage_outcome, coverage_outcome, coverage_note),
        ("mutation", "pass" if mutation.get("exists") else "missing", mutation_outcome, mutation_note),
        ("lint", "pass", "info", check_policies["lint"]["rule"]),
    ]
    body = "\n".join(
        (
            f"<tr><td>{e(check_policies[key]['label'])}</td><td>{pill(jenkins_result)}</td>"
            f"<td>{e(check_policies[key]['jenkins_result'])}</td><td>{e(check_policies[key]['mode'])}</td>"
            f"<td>{pill(quality_outcome)}</td><td>{e(note)}</td></tr>"
        )
        for key, jenkins_result, quality_outcome, note in rows
    )
    return f"""
    <section>
      <h2>Quality Gates</h2>
      <table>
        <thead><tr><th>Check</th><th>Jenkins Result</th><th>Jenkins Meaning</th><th>Quality Mode</th><th>Quality Outcome</th><th>Rule</th></tr></thead>
        <tbody>{body}</tbody>
      </table>
    </section>
    """


def render_coverage(coverage, coverage_gate):
    if not coverage.get("exists"):
        return "<section><h2>Coverage</h2><p>coverage.xml missing.</p></section>"
    rows = []
    for item in coverage["worst_files"]:
        rows.append(
            f"""
            <tr>
              <td>{e(item["filename"])}</td>
              <td>{pct(item["line_rate"])}</td>
              <td>{pct(item["branch_rate"])}</td>
            </tr>
            """
        )
    return f"""
    <section>
      <h2>Coverage</h2>
      <table>
        <thead><tr><th>Metric</th><th>Value</th><th>Gate</th></tr></thead>
        <tbody>
          <tr><td>Total coverage</td><td>{pct(coverage["total_rate"])}</td><td>{coverage_gate:.0f}%</td></tr>
          <tr><td>Line coverage</td><td>{pct(coverage["line_rate"])}</td><td>advisory</td></tr>
          <tr><td>Branch coverage</td><td>{pct(coverage["branch_rate"])}</td><td>advisory</td></tr>
          <tr><td>Lines</td><td>{coverage["lines_covered"]}/{coverage["lines_valid"]}</td><td></td></tr>
          <tr><td>Branches</td><td>{coverage["branches_covered"]}/{coverage["branches_valid"]}</td><td></td></tr>
        </tbody>
      </table>
      <h2>Lowest Coverage Files</h2>
      <table>
        <thead><tr><th>File</th><th>Line</th><th>Branch</th></tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </section>
    """


def render_mutation(mutation, mutation_advisory):
    if not mutation.get("exists"):
        return "<section><h2>Mutation</h2><p>mutants/mutmut-cicd-stats.json missing.</p></section>"
    rows = [
        ("Score", pct(mutation["score"])),
        ("Advisory threshold", f"{mutation_advisory:.0f}%"),
        ("Killed", mutation.get("killed", 0)),
        ("Survived", mutation.get("survived", 0)),
        ("No tests", mutation.get("no_tests", 0)),
        ("Skipped", mutation.get("skipped", 0)),
        ("Timeout", mutation.get("timeout", 0)),
        ("Suspicious", mutation.get("suspicious", 0)),
    ]
    body = "\n".join(f"<tr><td>{e(name)}</td><td>{e(value)}</td></tr>" for name, value in rows)
    return f"""
    <section>
      <h2>Mutation</h2>
      <table>
        <thead><tr><th>Metric</th><th>Value</th></tr></thead>
        <tbody>{body}</tbody>
      </table>
    </section>
    """


def render_links():
    links = [
        ("Test report", "../test-report/index.html"),
        ("Coverage report", "../coverage-report/index.html"),
        ("Mutation report", "../mutation-report/index.html"),
        ("Mutation survived", "../mutation-report/status-survived.html"),
        ("Pylint report", "../pylint-report.txt"),
        ("Flake8 report", "../flake8-report.json"),
    ]
    items = "\n".join(f'<a href="{href}">{e(label)}</a>' for label, href in links)
    return f"""
    <section>
      <h2>Detailed Reports</h2>
      <div class="links">{items}</div>
    </section>
    """


def render_dashboard(tests, coverage, mutation, coverage_gate, mutation_advisory, build_context, check_policies):
    body = f"""
    {render_cards(tests, coverage, mutation, coverage_gate, mutation_advisory)}
    {render_build_context(build_context)}
    {render_gate_table(tests, coverage, mutation, coverage_gate, mutation_advisory, check_policies)}
    {render_test_table(tests)}
    {render_coverage(coverage, coverage_gate)}
    {render_mutation(mutation, mutation_advisory)}
    {render_links()}
    """
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CI Quality Dashboard</title>
  <link rel="stylesheet" href="report.css">
</head>
<body>
  <header>
    <h1>CI Quality Dashboard</h1>
    <div class="meta">Read-only overview generated from Jenkins artifacts. Quality gates are enforced by Jenkins commands.</div>
  </header>
  <main>{body}</main>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description="Generate a read-only CI quality dashboard.")
    parser.add_argument("--output-dir", default="quality-dashboard")
    parser.add_argument("--config", default="pyproject.toml")
    parser.add_argument("--coverage-gate", type=float)
    parser.add_argument("--mutation-advisory", type=float)
    args = parser.parse_args()

    gates = load_gates(args.config)
    check_policies = load_check_policies(args.config)
    coverage_gate = args.coverage_gate if args.coverage_gate is not None else gates["coverage"]
    mutation_advisory = (
        args.mutation_advisory if args.mutation_advisory is not None else gates["mutation_advisory"]
    )

    tests = [
        parse_junit("test-results.xml", "Unit tests"),
        parse_junit("integration-test-results.xml", "Integration tests"),
    ]
    coverage = parse_coverage("coverage.xml")
    mutation = parse_mutation("mutants/mutmut-cicd-stats.json")
    build_context = get_build_context()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "report.css").write_text(DASHBOARD_CSS + "\n", encoding="utf-8")
    (output_dir / "index.html").write_text(
        render_dashboard(tests, coverage, mutation, coverage_gate, mutation_advisory, build_context, check_policies),
        encoding="utf-8",
    )
    print(output_dir / "index.html")


if __name__ == "__main__":
    main()
