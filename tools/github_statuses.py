#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import urllib.error
import urllib.request

from quality_dashboard import parse_coverage, parse_junit, parse_mutation
from quality_gates import load_check_policies, load_gates


MAX_DESCRIPTION = 140


def run_git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()


def infer_repo():
    remote = run_git("config", "--get", "remote.origin.url")
    match = re.search(r"github\.com[:/](?P<repo>[^/]+/[^/.]+)(?:\.git)?$", remote)
    if not match:
        raise ValueError(f"Cannot infer GitHub repository from remote URL: {remote}")
    return match.group("repo")


def infer_sha():
    return os.environ.get("GIT_COMMIT") or run_git("rev-parse", "HEAD")


def infer_pr_number():
    change_id = os.environ.get("CHANGE_ID")
    if change_id:
        return change_id

    change_url = os.environ.get("CHANGE_URL", "")
    match = re.search(r"/pull/(\d+)(?:$|[/?#])", change_url)
    if match:
        return match.group(1)

    return None


def artifact_url(path):
    build_url = os.environ.get("JENKINS_ARTIFACT_BASE_URL") or os.environ.get("BUILD_URL", "")
    build_url = build_url.rstrip("/")
    if not build_url:
        return None
    return f"{build_url}/artifact/{path}"


def build_mode():
    if not os.environ.get("CHANGE_ID"):
        return "Branch"

    marker_source = " ".join(
        os.environ.get(name, "")
        for name in ("JOB_NAME", "BUILD_URL", "BRANCH_NAME")
    ).lower()
    if "merge" in marker_source:
        return "PR merge"
    if "head" in marker_source:
        return "PR head"
    return "PR"


def describe(message):
    return f"{build_mode()}: {message}"


def clamp_description(value):
    value = " ".join(str(value).split())
    return value[:MAX_DESCRIPTION]


def skipped_after_early_failure(reason="earlier pipeline failure"):
    return describe(f"Skipped after {reason}")


def coverage_gate_failed(gates):
    coverage = parse_coverage("coverage.xml")
    if not coverage.get("exists"):
        return False
    return coverage["total_rate"] * 100 < gates["coverage"]


def post_status(repo, sha, token, context, state, description, target_url=None):
    payload = {
        "state": state,
        "context": context,
        "description": clamp_description(description),
    }
    if target_url:
        payload["target_url"] = target_url

    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/statuses/{sha}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "projector-jenkins-quality-statuses",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        response.read()


def post_pr_comment(repo, issue_number, token, body):
    payload = {"body": body}
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "projector-jenkins-quality-statuses",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        response.read()


def explain_comment_http_error(exc):
    if exc.code in (401, 403):
        return "token cannot write PR comments; grant Issues: write or use the GitHub App token"
    if exc.code == 404:
        return "PR comment endpoint not found; check repo, PR number, and token repository access"
    return "GitHub rejected the PR comment request"


def tests_status(gates):
    suites = [
        parse_junit("test-results.xml", "Unit tests"),
        parse_junit("integration-test-results.xml", "Integration tests"),
    ]
    existing = [suite for suite in suites if suite.exists]
    if existing:
        total = sum(suite.tests for suite in existing)
        failed = sum(suite.failures + suite.errors for suite in existing)
        skipped = sum(suite.skipped for suite in existing)
        passed = sum(suite.passed for suite in existing)
        if failed:
            missing = [suite.label for suite in suites if not suite.exists]
            suffix = f"; skipped: {', '.join(missing)}" if missing else ""
            return (
                "failure",
                describe(f"Tests: {passed}/{total} passed, {failed} failed/errors, {skipped} skipped{suffix}"),
                artifact_url("test-report/index.html"),
            )

    if any(not suite.exists for suite in suites):
        if suites[0].exists and not suites[1].exists:
            reason = "coverage gate failure" if coverage_gate_failed(gates) else "earlier pipeline failure"
            return ("error", skipped_after_early_failure(reason), artifact_url("test-report/index.html"))
        missing = ", ".join(suite.label for suite in suites if not suite.exists)
        return ("error", describe(f"Missing JUnit report: {missing}"), artifact_url("test-report/index.html"))

    total = sum(suite.tests for suite in suites)
    failed = sum(suite.failures + suite.errors for suite in suites)
    skipped = sum(suite.skipped for suite in suites)
    passed = sum(suite.passed for suite in suites)
    state = "failure" if failed else "success"
    return (
        state,
        describe(f"Tests: {passed}/{total} passed, {failed} failed/errors, {skipped} skipped"),
        artifact_url("test-report/index.html"),
    )


def coverage_status(gates):
    coverage = parse_coverage("coverage.xml")
    if not coverage.get("exists"):
        return ("error", describe("Missing coverage.xml"), artifact_url("quality-dashboard/index.html"))

    value = coverage["total_rate"] * 100
    gate = gates["coverage"]
    state = "success" if value >= gate else "failure"
    description = describe(f"Coverage: {value:.1f}% / gate {gate:g}%; branch {coverage['branch_rate'] * 100:.1f}%")
    return (state, description, artifact_url("coverage-report/index.html") or artifact_url("quality-dashboard/index.html"))


def mutation_status(gates):
    mutation = parse_mutation("mutants/mutmut-cicd-stats.json")
    if not mutation.get("exists"):
        if coverage_gate_failed(gates):
            return ("error", skipped_after_early_failure("coverage gate failure"), artifact_url("quality-dashboard/index.html"))
        return ("error", describe("Missing mutation stats"), artifact_url("quality-dashboard/index.html"))

    value = mutation["score"] * 100
    advisory = gates["mutation_advisory"]
    relation = "meets" if value >= advisory else "below"
    description = describe(
        f"Mutation: {value:.1f}% {relation} advisory {advisory:g}%; "
        f"killed {mutation.get('killed', 0)}, survived {mutation.get('survived', 0)}"
    )
    return ("success", description, artifact_url("mutation-report/index.html") or artifact_url("quality-dashboard/index.html"))


def code_quality_status(check_policies, gates):
    has_pylint = os.path.exists("pylint-report.txt")
    has_flake8 = os.path.exists("flake8-report.json")
    if not has_pylint and not has_flake8:
        if coverage_gate_failed(gates):
            return ("error", skipped_after_early_failure("coverage gate failure"), artifact_url("quality-dashboard/index.html"))
        return ("error", describe("Missing lint reports"), artifact_url("quality-dashboard/index.html"))
    return ("success", describe(check_policies["lint"]["rule"]), artifact_url("quality-dashboard/index.html"))


def strip_build_mode(description):
    prefix = f"{build_mode()}: "
    if description.startswith(prefix):
        return description[len(prefix):]
    return description


def ci_status(statuses):
    tests_state = statuses["Tests"][0]
    coverage_state = statuses["Coverage Gate"][0]
    tests_description = strip_build_mode(statuses["Tests"][1])
    coverage_description = strip_build_mode(statuses["Coverage Gate"][1])

    if tests_state != "success":
        return (tests_state, describe(tests_description), artifact_url("quality-dashboard/index.html"))
    if coverage_state != "success":
        return (coverage_state, describe(coverage_description), artifact_url("quality-dashboard/index.html"))
    return ("success", describe("Tests and coverage passed"), artifact_url("quality-dashboard/index.html"))


def markdown_link(label, url):
    if not url:
        return label
    return f"[{label}]({url})"


def render_pr_comment(statuses):
    state_icons = {
        "success": "PASS",
        "failure": "FAIL",
        "error": "ERROR",
        "pending": "PENDING",
    }
    build_url = os.environ.get("BUILD_URL", "").rstrip("/")
    sha = infer_sha()
    short_sha = sha[:7] if sha else "unknown"
    lines = [
        "## Automated Jenkins CI result",
        "",
        "_This comment was generated automatically by Jenkins._",
        "",
        f"- Build: {build_mode()}",
        f"- Commit: `{short_sha}`",
    ]
    if build_url:
        lines.append(f"- Jenkins build: {markdown_link(build_url, build_url)}")

    lines.extend(["", "| Check | Result | Summary | Report |", "| --- | --- | --- | --- |"])
    for label, (state, description, target_url) in statuses.items():
        summary = strip_build_mode(description)
        result = "SKIPPED" if summary.startswith("Skipped after ") else state_icons.get(state, state.upper())
        lines.append(
            f"| {label} | {result} | {summary} | "
            f"{markdown_link('open', target_url) if target_url else '-'} |"
        )

    dashboard_url = artifact_url("quality-dashboard/index.html")
    if dashboard_url:
        lines.extend(["", f"Quality dashboard: {markdown_link('open dashboard', dashboard_url)}"])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Publish compact Jenkins quality statuses to a GitHub commit.")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"), help="GitHub repo in owner/name form.")
    parser.add_argument("--sha", default=os.environ.get("GIT_COMMIT"), help="Commit SHA to update.")
    parser.add_argument("--config", default="pyproject.toml")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN not set; skipping GitHub commit statuses.")
        return

    repo = args.repo or infer_repo()
    sha = args.sha or infer_sha()
    gates = load_gates(args.config)
    check_policies = load_check_policies(args.config)

    statuses = {
        "Tests": tests_status(gates),
        "Coverage Gate": coverage_status(gates),
        "Mutation Advisory": mutation_status(gates),
        "Lint Reports": code_quality_status(check_policies, gates),
    }

    state, description, target_url = ci_status(statuses)
    try:
        post_status(repo, sha, token, "Jenkins / CI", state, description, target_url)
        print(f"Published Jenkins / CI: {state} - {description}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"Failed to publish Jenkins / CI: HTTP {exc.code} {body}")
    except Exception as exc:
        print(f"Failed to publish Jenkins / CI: {exc}")

    issue_number = infer_pr_number()
    if issue_number:
        try:
            post_pr_comment(repo, issue_number, token, render_pr_comment(statuses))
            print(f"Published Jenkins CI comment on PR #{issue_number}.")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            print(f"Failed to publish Jenkins CI comment: HTTP {exc.code} {explain_comment_http_error(exc)}")
            print(body)
        except Exception as exc:
            print(f"Failed to publish Jenkins CI comment: {exc}")
    else:
        print("No PR number found; skipping Jenkins CI PR comment.")


if __name__ == "__main__":
    main()
