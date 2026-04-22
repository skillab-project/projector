#!/usr/bin/env python3
import argparse
import html
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


REPORT_CSS = """
:root {
  color-scheme: light;
  --bg: #f6f7f9;
  --ink: #1f2328;
  --muted: #667085;
  --line: #d7dde5;
  --panel: #ffffff;
  --green: #237a4b;
  --red: #b42318;
  --amber: #a15c00;
  --blue: #255c99;
  --violet: #6654a8;
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
  padding: 32px clamp(18px, 4vw, 56px) 22px;
  border-bottom: 1px solid var(--line);
  background: #edf2f7;
}
main {
  padding: 24px clamp(18px, 4vw, 56px) 48px;
  display: grid;
  gap: 24px;
}
h1, h2, h3 {
  margin: 0;
  letter-spacing: 0;
}
h1 { font-size: clamp(28px, 5vw, 44px); }
h2 { font-size: 20px; margin-bottom: 12px; }
h3 { font-size: 16px; margin-bottom: 10px; }
.meta { color: var(--muted); margin-top: 8px; }
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
}
.card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 16px;
}
.card strong {
  display: block;
  font-size: 28px;
  margin-bottom: 4px;
}
.card span { color: var(--muted); }
section {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 18px;
  overflow: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
  min-width: 760px;
}
th, td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--line);
  text-align: left;
  vertical-align: top;
}
th {
  color: var(--muted);
  font-weight: 650;
  background: #fbfcfd;
}
code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  overflow-wrap: anywhere;
}
.score { font-weight: 700; color: var(--blue); }
.pill {
  display: inline-block;
  min-width: 74px;
  text-align: center;
  padding: 3px 8px;
  border-radius: 999px;
  color: white;
  font-size: 12px;
  font-weight: 700;
}
.survived { background: var(--red); }
.no_tests { background: var(--amber); }
.pending { background: var(--muted); }
.killed { background: var(--green); }
.nav {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
}
.nav a {
  display: inline-block;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--panel);
  padding: 7px 12px;
  color: var(--ink);
  text-decoration: none;
}
.nav a.current {
  border-color: var(--blue);
  color: white;
  background: var(--blue);
}
.note {
  border-left: 4px solid var(--violet);
  padding: 10px 12px;
  background: #f4f2fb;
  color: #35304f;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}
.compact { min-width: 0; }
""".strip()


def mutant_status(exit_code):
    if exit_code is None:
        return "pending"
    if exit_code == 0:
        return "survived"
    if exit_code == 33:
        return "no_tests"
    return "killed"


def parse_mutant_name(name):
    match = re.search(r"\.x.(?P<class>[^.]+).(?P<func>.*?)__mutmut_(?P<num>\d+)$", name)
    if not match:
        return "", "", ""
    return match.group("class"), match.group("func"), match.group("num")


def load_mutants(mutants_dir):
    mutants = []
    for meta_path in sorted(mutants_dir.glob("**/*.meta")):
        source_file = meta_path.relative_to(mutants_dir).as_posix()[:-5]
        with meta_path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        for name, exit_code in data.get("exit_code_by_key", {}).items():
            class_name, function_name, mutant_number = parse_mutant_name(name)
            status = mutant_status(exit_code)
            mutants.append(
                {
                    "name": name,
                    "file": source_file,
                    "class": class_name,
                    "function": function_name,
                    "number": mutant_number,
                    "status": status,
                }
            )
    return mutants


def pct(killed, survived):
    total = killed + survived
    if total == 0:
        return "0.0"
    return f"{(killed / total) * 100:.1f}"


def slug(value):
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-")


def e(value):
    return html.escape(str(value))


def page(title, current, body, depth=0):
    prefix = "../" * depth
    nav = [
        ("Overview", f"{prefix}index.html", "overview"),
        ("Survived", f"{prefix}status-survived.html", "survived"),
        ("No tests", f"{prefix}status-no_tests.html", "no_tests"),
        ("Pending", f"{prefix}status-pending.html", "pending"),
    ]
    nav_links = "\n".join(
        f'<a class="{"current" if key == current else ""}" href="{href}">{label}</a>'
        for label, href, key in nav
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{e(title)}</title>
  <link rel="stylesheet" href="{prefix}report.css">
</head>
<body>
  <header>
    <h1>{e(title)}</h1>
    <div class="meta">Generated from <code>mutants/*.meta</code>. Mutation score excludes no-test and pending mutants.</div>
    <nav class="nav">{nav_links}</nav>
  </header>
  <main>{body}</main>
</body>
</html>
"""


def aggregate(mutants):
    totals = Counter(m["status"] for m in mutants)
    by_file = defaultdict(Counter)
    by_function = defaultdict(Counter)
    by_file_function = defaultdict(lambda: defaultdict(Counter))
    for mutant in mutants:
        by_file[mutant["file"]][mutant["status"]] += 1
        function_name = f'{mutant["class"]}.{mutant["function"]}'
        function_key = f'{mutant["file"]}::{function_name}'
        by_function[function_key][mutant["status"]] += 1
        by_file_function[mutant["file"]][function_name][mutant["status"]] += 1
    return totals, by_file, by_function, by_file_function


def status_pill(status):
    return f'<span class="pill {e(status)}">{e(status)}</span>'


def cards(totals):
    killed = totals["killed"]
    survived = totals["survived"]
    effective_total = killed + survived
    score = pct(killed, survived)
    return f"""
    <div class="cards">
      <div class="card"><strong>{score}%</strong><span>mutation score</span></div>
      <div class="card"><strong>{effective_total}</strong><span>effective mutants</span></div>
      <div class="card"><strong>{killed}</strong><span>killed</span></div>
      <div class="card"><strong>{survived}</strong><span>survived</span></div>
      <div class="card"><strong>{totals['no_tests']}</strong><span>no tests</span></div>
      <div class="card"><strong>{totals['pending']}</strong><span>pending</span></div>
    </div>
    """


def file_summary_rows(by_file):
    rows = []
    for source_file, counts in sorted(by_file.items()):
        file_score = pct(counts["killed"], counts["survived"])
        detail = f"files/{slug(source_file)}.html"
        rows.append(
            f"""
            <tr>
              <td><a href="{e(detail)}">{e(source_file)}</a></td>
              <td>{sum(counts.values())}</td>
              <td>{counts['killed']}</td>
              <td>{counts['survived']}</td>
              <td>{counts['no_tests']}</td>
              <td>{counts['pending']}</td>
              <td><span class="score">{file_score}%</span></td>
            </tr>
            """
        )
    return "".join(rows)


def cluster_rows(by_function, limit=40):
    rows = []
    clusters = sorted(
        by_function.items(),
        key=lambda item: (item[1]["survived"], item[1]["no_tests"], sum(item[1].values())),
        reverse=True,
    )
    for function_key, counts in clusters[:limit]:
        cluster_score = pct(counts["killed"], counts["survived"])
        source_file = function_key.split("::", 1)[0]
        detail = f"files/{slug(source_file)}.html"
        rows.append(
            f"""
            <tr>
              <td><a href="{e(detail)}">{e(function_key)}</a></td>
              <td>{sum(counts.values())}</td>
              <td>{counts['killed']}</td>
              <td>{counts['survived']}</td>
              <td>{counts['no_tests']}</td>
              <td><span class="score">{cluster_score}%</span></td>
            </tr>
            """
        )
    return "".join(rows)


def mutant_rows(mutants, link_prefix="files/"):
    rows = []
    for mutant in sorted(mutants, key=lambda m: (m["status"], m["file"], m["function"], m["number"])):
        command = f"mutmut show {mutant['name']}"
        detail = f"{link_prefix}{slug(mutant['file'])}.html"
        rows.append(
            f"""
            <tr>
              <td>{status_pill(mutant['status'])}</td>
              <td><a href="{e(detail)}">{e(mutant['file'])}</a></td>
              <td>{e(mutant['class'])}.{e(mutant['function'])}</td>
              <td><code>{e(mutant['name'])}</code></td>
              <td><code>{e(command)}</code></td>
            </tr>
            """
        )
    return "".join(rows)


def render_index(mutants):
    totals, by_file, by_function, _ = aggregate(mutants)
    actionable = [m for m in mutants if m["status"] in {"survived", "no_tests", "pending"}]
    body = f"""
    {cards(totals)}
    <section class="note compact">
      <strong>Overview first.</strong>
      This page contains the quality snapshot, file health, largest survivor clusters, and all actionable mutants.
      Use file links only when you need deeper detail for a specific source file.
    </section>
    <section>
      <h2>Files</h2>
      <table>
        <thead><tr><th>File</th><th>Total</th><th>Killed</th><th>Survived</th><th>No Tests</th><th>Pending</th><th>Score</th></tr></thead>
        <tbody>{file_summary_rows(by_file)}</tbody>
      </table>
    </section>
    <section>
      <h2>Largest Survivor Clusters</h2>
      <table>
        <thead><tr><th>Function</th><th>Total</th><th>Killed</th><th>Survived</th><th>No Tests</th><th>Score</th></tr></thead>
        <tbody>{cluster_rows(by_function)}</tbody>
      </table>
    </section>
    <section>
      <h2>Actionable Mutants</h2>
      <table>
        <thead><tr><th>Status</th><th>File</th><th>Function</th><th>Mutant</th><th>Inspect</th></tr></thead>
        <tbody>{mutant_rows(actionable)}</tbody>
      </table>
    </section>
    """
    return page("Mutation Test Report", "overview", body)


def render_status_page(mutants, status):
    filtered = [m for m in mutants if m["status"] == status]
    body = f"""
    <section>
      <h2>{e(status)} mutants</h2>
      <table>
        <thead><tr><th>Status</th><th>File</th><th>Function</th><th>Mutant</th><th>Inspect</th></tr></thead>
        <tbody>{mutant_rows(filtered)}</tbody>
      </table>
    </section>
    """
    return page(f"Mutation Report: {status}", status, body)


def render_file_page(source_file, file_mutants, function_counts):
    counts = Counter(m["status"] for m in file_mutants)
    score = pct(counts["killed"], counts["survived"])
    function_rows = []
    for function_name, fn_counts in sorted(
        function_counts.items(),
        key=lambda item: (item[1]["survived"], item[1]["no_tests"], sum(item[1].values())),
        reverse=True,
    ):
        function_rows.append(
            f"""
            <tr>
              <td>{e(function_name)}</td>
              <td>{sum(fn_counts.values())}</td>
              <td>{fn_counts['killed']}</td>
              <td>{fn_counts['survived']}</td>
              <td>{fn_counts['no_tests']}</td>
              <td><span class="score">{pct(fn_counts['killed'], fn_counts['survived'])}%</span></td>
            </tr>
            """
        )
    body = f"""
    <div class="cards">
      <div class="card"><strong>{score}%</strong><span>file mutation score</span></div>
      <div class="card"><strong>{sum(counts.values())}</strong><span>total mutants</span></div>
      <div class="card"><strong>{counts['killed']}</strong><span>killed</span></div>
      <div class="card"><strong>{counts['survived']}</strong><span>survived</span></div>
      <div class="card"><strong>{counts['no_tests']}</strong><span>no tests</span></div>
    </div>
    <section>
      <h2>Function Summary</h2>
      <table>
        <thead><tr><th>Function</th><th>Total</th><th>Killed</th><th>Survived</th><th>No Tests</th><th>Score</th></tr></thead>
        <tbody>{''.join(function_rows)}</tbody>
      </table>
    </section>
    <section>
      <h2>All Mutants In This File</h2>
      <table>
        <thead><tr><th>Status</th><th>File</th><th>Function</th><th>Mutant</th><th>Inspect</th></tr></thead>
        <tbody>{mutant_rows(file_mutants, link_prefix="")}</tbody>
      </table>
    </section>
    """
    return page(f"Mutation Detail: {source_file}", "overview", body, depth=1)


def write_report(mutants, output):
    output.parent.mkdir(parents=True, exist_ok=True)
    report_dir = output.parent
    files_dir = report_dir / "files"
    files_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "report.css").write_text(REPORT_CSS + "\n", encoding="utf-8")
    output.write_text(render_index(mutants), encoding="utf-8")

    for status in ("survived", "no_tests", "pending"):
        (report_dir / f"status-{status}.html").write_text(render_status_page(mutants, status), encoding="utf-8")

    _, _, _, by_file_function = aggregate(mutants)
    by_file_mutants = defaultdict(list)
    for mutant in mutants:
        by_file_mutants[mutant["file"]].append(mutant)

    for source_file, file_mutants in by_file_mutants.items():
        detail_path = files_dir / f"{slug(source_file)}.html"
        detail_path.write_text(
            render_file_page(source_file, file_mutants, by_file_function[source_file]),
            encoding="utf-8",
        )


def main():
    parser = argparse.ArgumentParser(description="Generate a Jenkins-friendly HTML report from mutmut metadata.")
    parser.add_argument("--mutants-dir", default="mutants", help="Directory created by mutmut.")
    parser.add_argument("--output", default="mutation-report/index.html", help="Output HTML path.")
    args = parser.parse_args()

    mutants_dir = Path(args.mutants_dir)
    output = Path(args.output)
    mutants = load_mutants(mutants_dir)
    if not mutants:
        raise SystemExit(f"No mutmut metadata found under {mutants_dir}. Run mutmut first.")

    write_report(mutants, output)
    print(output)


if __name__ == "__main__":
    main()
