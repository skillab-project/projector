#!/usr/bin/env python3
import argparse
import html
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path


REPORT_CSS = """
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
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
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
  min-width: 720px;
}
th, td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--line);
  text-align: left;
  vertical-align: top;
}
th { color: var(--muted); background: #fbfcfd; }
pre {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  background: #fbfcfd;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px;
  margin: 8px 0 0;
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
.skip { background: var(--amber); }
.missing { background: var(--muted); }
""".strip()


@dataclass
class Case:
    suite: str
    classname: str
    name: str
    time: float
    status: str = "passed"
    message: str = ""
    detail: str = ""


@dataclass
class Suite:
    label: str
    path: str
    exists: bool
    tests: int = 0
    failures: int = 0
    errors: int = 0
    skipped: int = 0
    time: float = 0.0
    cases: list[Case] = field(default_factory=list)

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


def pill(status):
    labels = {"pass": "PASS", "fail": "FAIL", "skip": "SKIPPED", "missing": "MISSING"}
    return f'<span class="pill {status}">{labels.get(status, status.upper())}</span>'


def parse_junit(path, label):
    file_path = Path(path)
    if not file_path.exists():
        return Suite(label=label, path=path, exists=False)

    root = ET.parse(file_path).getroot()
    suite_nodes = [root] if root.tag == "testsuite" else root.findall("testsuite")
    suite = Suite(label=label, path=path, exists=True)
    for suite_node in suite_nodes:
        suite_name = suite_node.attrib.get("name", label)
        suite.tests += int(suite_node.attrib.get("tests", 0))
        suite.failures += int(suite_node.attrib.get("failures", 0))
        suite.errors += int(suite_node.attrib.get("errors", 0))
        suite.skipped += int(suite_node.attrib.get("skipped", 0))
        suite.time += float(suite_node.attrib.get("time", 0.0))

        for case_node in suite_node.findall("testcase"):
            case = Case(
                suite=suite_name,
                classname=case_node.attrib.get("classname", ""),
                name=case_node.attrib.get("name", ""),
                time=float(case_node.attrib.get("time", 0.0)),
            )
            failure = case_node.find("failure")
            error = case_node.find("error")
            skipped = case_node.find("skipped")
            if failure is not None:
                case.status = "failed"
                case.message = failure.attrib.get("message", "")
                case.detail = failure.text or ""
            elif error is not None:
                case.status = "error"
                case.message = error.attrib.get("message", "")
                case.detail = error.text or ""
            elif skipped is not None:
                case.status = "skipped"
                case.message = skipped.attrib.get("message", "")
                case.detail = skipped.text or ""
            suite.cases.append(case)
    return suite


def render_cards(suites):
    total = sum(suite.tests for suite in suites if suite.exists)
    passed = sum(suite.passed for suite in suites if suite.exists)
    failures = sum(suite.failures for suite in suites if suite.exists)
    errors = sum(suite.errors for suite in suites if suite.exists)
    skipped = sum(suite.skipped for suite in suites if suite.exists)
    missing = sum(1 for suite in suites if not suite.exists)
    return f"""
    <div class="cards">
      <div class="card"><strong>{passed}/{total}</strong><span>tests passed</span></div>
      <div class="card"><strong>{failures}</strong><span>failures</span></div>
      <div class="card"><strong>{errors}</strong><span>errors</span></div>
      <div class="card"><strong>{skipped}</strong><span>skipped</span></div>
      <div class="card"><strong>{missing}</strong><span>missing reports</span></div>
    </div>
    """


def render_suite_table(suites):
    rows = []
    for suite in suites:
        rows.append(
            f"""
            <tr>
              <td>{e(suite.label)}</td>
              <td>{pill(suite.status)}</td>
              <td>{suite.tests if suite.exists else "missing"}</td>
              <td>{suite.passed if suite.exists else "missing"}</td>
              <td>{suite.failures if suite.exists else "missing"}</td>
              <td>{suite.errors if suite.exists else "missing"}</td>
              <td>{suite.skipped if suite.exists else "missing"}</td>
              <td>{suite.time:.2f}s</td>
              <td><code>{e(suite.path)}</code></td>
            </tr>
            """
        )
    return f"""
    <section>
      <h2>Suites</h2>
      <table>
        <thead><tr><th>Suite</th><th>Status</th><th>Total</th><th>Passed</th><th>Failures</th><th>Errors</th><th>Skipped</th><th>Time</th><th>Source</th></tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </section>
    """


def render_problem_cases(suites):
    cases = [case for suite in suites for case in suite.cases if case.status in {"failed", "error"}]
    if not cases:
        return "<section><h2>Failures And Errors</h2><p>No failed or errored tests.</p></section>"
    rows = []
    for case in cases:
        rows.append(
            f"""
            <tr>
              <td>{pill("fail")}</td>
              <td>{e(case.classname)}::{e(case.name)}</td>
              <td>{e(case.message)}<pre>{e(case.detail)}</pre></td>
            </tr>
            """
        )
    return f"""
    <section>
      <h2>Failures And Errors</h2>
      <table>
        <thead><tr><th>Status</th><th>Test</th><th>Message</th></tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </section>
    """


def render_skipped_cases(suites):
    cases = [case for suite in suites for case in suite.cases if case.status == "skipped"]
    if not cases:
        return "<section><h2>Skipped Tests</h2><p>No skipped tests.</p></section>"
    rows = []
    for case in cases:
        rows.append(
            f"""
            <tr>
              <td>{pill("skip")}</td>
              <td>{e(case.classname)}::{e(case.name)}</td>
              <td>{e(case.message)}</td>
            </tr>
            """
        )
    return f"""
    <section>
      <h2>Skipped Tests</h2>
      <table>
        <thead><tr><th>Status</th><th>Test</th><th>Reason</th></tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </section>
    """


def render_report(suites):
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Test Report</title>
  <link rel="stylesheet" href="report.css">
</head>
<body>
  <header>
    <h1>Test Report</h1>
    <div class="meta">Generated from pytest JUnit output. XML files remain machine-readable artifacts; this page is for humans.</div>
  </header>
  <main>
    {render_cards(suites)}
    {render_suite_table(suites)}
    {render_problem_cases(suites)}
    {render_skipped_cases(suites)}
  </main>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description="Generate a human-readable HTML report from pytest JUnit XML files.")
    parser.add_argument("--output-dir", default="test-report")
    args = parser.parse_args()

    suites = [
        parse_junit("test-results.xml", "Unit tests"),
        parse_junit("integration-test-results.xml", "Integration tests"),
    ]
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "report.css").write_text(REPORT_CSS + "\n", encoding="utf-8")
    (output_dir / "index.html").write_text(render_report(suites), encoding="utf-8")
    print(output_dir / "index.html")


if __name__ == "__main__":
    main()
