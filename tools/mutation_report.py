#!/usr/bin/env python3
import argparse
import html
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


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


def render_report(mutants):
    totals = Counter(m["status"] for m in mutants)
    killed = totals["killed"]
    survived = totals["survived"]
    effective_total = killed + survived
    score = pct(killed, survived)

    by_file = defaultdict(Counter)
    by_function = defaultdict(Counter)
    for mutant in mutants:
        by_file[mutant["file"]][mutant["status"]] += 1
        function_key = f'{mutant["file"]}::{mutant["class"]}.{mutant["function"]}'
        by_function[function_key][mutant["status"]] += 1

    file_rows = []
    for source_file, counts in sorted(by_file.items()):
        file_score = pct(counts["killed"], counts["survived"])
        file_rows.append(
            f"""
            <tr>
              <td>{html.escape(source_file)}</td>
              <td>{sum(counts.values())}</td>
              <td>{counts['killed']}</td>
              <td>{counts['survived']}</td>
              <td>{counts['no_tests']}</td>
              <td><span class="score">{file_score}%</span></td>
            </tr>
            """
        )

    cluster_rows = []
    clusters = sorted(
        by_function.items(),
        key=lambda item: (item[1]["survived"], item[1]["no_tests"], sum(item[1].values())),
        reverse=True,
    )
    for function_key, counts in clusters[:40]:
        cluster_score = pct(counts["killed"], counts["survived"])
        cluster_rows.append(
            f"""
            <tr>
              <td>{html.escape(function_key)}</td>
              <td>{sum(counts.values())}</td>
              <td>{counts['killed']}</td>
              <td>{counts['survived']}</td>
              <td>{counts['no_tests']}</td>
              <td><span class="score">{cluster_score}%</span></td>
            </tr>
            """
        )

    mutant_rows = []
    interesting = [m for m in mutants if m["status"] in {"survived", "no_tests", "pending"}]
    for mutant in sorted(interesting, key=lambda m: (m["status"], m["file"], m["function"], m["number"])):
        command = f"mutmut show {mutant['name']}"
        mutant_rows.append(
            f"""
            <tr data-status="{html.escape(mutant['status'])}">
              <td><span class="pill {html.escape(mutant['status'])}">{html.escape(mutant['status'])}</span></td>
              <td>{html.escape(mutant['file'])}</td>
              <td>{html.escape(mutant['class'])}.{html.escape(mutant['function'])}</td>
              <td><code>{html.escape(mutant['name'])}</code></td>
              <td><code>{html.escape(command)}</code></td>
            </tr>
            """
        )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mutation Test Report</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f7f4;
      --ink: #1f2328;
      --muted: #667085;
      --line: #d9ded6;
      --panel: #ffffff;
      --green: #2f7d4f;
      --red: #b42318;
      --amber: #a15c00;
      --blue: #315d95;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--ink);
      line-height: 1.45;
    }}
    header {{
      padding: 32px clamp(18px, 4vw, 56px) 22px;
      border-bottom: 1px solid var(--line);
      background: #eef2ec;
    }}
    main {{
      padding: 24px clamp(18px, 4vw, 56px) 48px;
      display: grid;
      gap: 24px;
    }}
    h1, h2 {{
      margin: 0;
      letter-spacing: 0;
    }}
    h1 {{ font-size: clamp(28px, 5vw, 48px); }}
    h2 {{ font-size: 20px; margin-bottom: 12px; }}
    .meta {{ color: var(--muted); margin-top: 8px; }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }}
    .card strong {{
      display: block;
      font-size: 28px;
      margin-bottom: 4px;
    }}
    .card span {{ color: var(--muted); }}
    section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
      overflow: auto;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
      min-width: 780px;
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
    }}
    th {{
      color: var(--muted);
      font-weight: 650;
      background: #fbfbf8;
      position: sticky;
      top: 0;
    }}
    code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
      overflow-wrap: anywhere;
    }}
    .score {{ font-weight: 700; color: var(--blue); }}
    .pill {{
      display: inline-block;
      min-width: 74px;
      text-align: center;
      padding: 3px 8px;
      border-radius: 999px;
      color: white;
      font-size: 12px;
      font-weight: 700;
    }}
    .survived {{ background: var(--red); }}
    .no_tests {{ background: var(--amber); }}
    .pending {{ background: var(--muted); }}
    .killed {{ background: var(--green); }}
    .toolbar {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 12px;
    }}
    input, select {{
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 9px 10px;
      font: inherit;
      background: white;
    }}
    input {{ flex: 1 1 260px; }}
  </style>
</head>
<body>
  <header>
    <h1>Mutation Test Report</h1>
    <div class="meta">Generated from <code>mutants/*.meta</code>. Mutation score excludes no-test and pending mutants.</div>
  </header>
  <main>
    <div class="cards">
      <div class="card"><strong>{score}%</strong><span>mutation score</span></div>
      <div class="card"><strong>{effective_total}</strong><span>effective mutants</span></div>
      <div class="card"><strong>{killed}</strong><span>killed</span></div>
      <div class="card"><strong>{survived}</strong><span>survived</span></div>
      <div class="card"><strong>{totals['no_tests']}</strong><span>no tests</span></div>
    </div>

    <section>
      <h2>Files</h2>
      <table>
        <thead><tr><th>File</th><th>Total</th><th>Killed</th><th>Survived</th><th>No Tests</th><th>Score</th></tr></thead>
        <tbody>{''.join(file_rows)}</tbody>
      </table>
    </section>

    <section>
      <h2>Largest Survivor Clusters</h2>
      <table>
        <thead><tr><th>Function</th><th>Total</th><th>Killed</th><th>Survived</th><th>No Tests</th><th>Score</th></tr></thead>
        <tbody>{''.join(cluster_rows)}</tbody>
      </table>
    </section>

    <section>
      <h2>Actionable Mutants</h2>
      <div class="toolbar">
        <input id="query" placeholder="Filter by file, function, mutant name, command">
        <select id="status">
          <option value="">All statuses</option>
          <option value="survived">Survived</option>
          <option value="no_tests">No tests</option>
          <option value="pending">Pending</option>
        </select>
      </div>
      <table id="mutants">
        <thead><tr><th>Status</th><th>File</th><th>Function</th><th>Mutant</th><th>Inspect</th></tr></thead>
        <tbody>{''.join(mutant_rows)}</tbody>
      </table>
    </section>
  </main>
  <script>
    const query = document.getElementById('query');
    const status = document.getElementById('status');
    const rows = [...document.querySelectorAll('#mutants tbody tr')];
    function update() {{
      const q = query.value.toLowerCase();
      const s = status.value;
      for (const row of rows) {{
        const matchesText = row.textContent.toLowerCase().includes(q);
        const matchesStatus = !s || row.dataset.status === s;
        row.style.display = matchesText && matchesStatus ? '' : 'none';
      }}
    }}
    query.addEventListener('input', update);
    status.addEventListener('change', update);
  </script>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description="Generate a static HTML report from mutmut metadata.")
    parser.add_argument("--mutants-dir", default="mutants", help="Directory created by mutmut.")
    parser.add_argument("--output", default="mutation-report/index.html", help="Output HTML path.")
    args = parser.parse_args()

    mutants_dir = Path(args.mutants_dir)
    output = Path(args.output)
    mutants = load_mutants(mutants_dir)
    if not mutants:
        raise SystemExit(f"No mutmut metadata found under {mutants_dir}. Run mutmut first.")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_report(mutants), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
