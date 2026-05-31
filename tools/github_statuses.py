#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import urllib.error
import urllib.request

from quality_dashboard import parse_coverage, parse_junit, parse_mutation, pct
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
        reason = "coverage gate failure" if coverage_gate_failed(gates) else "earlier pipeline failure"
        return ("error", skipped_after_early_failure(reason), artifact_url("quality-dashboard/index.html"))

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
        reason = "coverage gate failure" if coverage_gate_failed(gates) else "earlier pipeline failure"
        return ("error", skipped_after_early_failure(reason), artifact_url("quality-dashboard/index.html"))
    return ("success", describe(check_policies["lint"]["rule"]), artifact_url("quality-dashboard/index.html"))


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

    statuses = [
        ("Jenkins / Tests", *tests_status(gates)),
        ("Jenkins / Coverage Gate", *coverage_status(gates)),
        ("Jenkins / Mutation Advisory", *mutation_status(gates)),
        ("Jenkins / Code Quality", *code_quality_status(check_policies, gates)),
    ]

    for context, state, description, target_url in statuses:
        try:
            post_status(repo, sha, token, context, state, description, target_url)
            print(f"Published {context}: {state} - {description}")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            print(f"Failed to publish {context}: HTTP {exc.code} {body}")
        except Exception as exc:
            print(f"Failed to publish {context}: {exc}")


if __name__ == "__main__":
    main()
