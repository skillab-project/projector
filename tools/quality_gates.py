#!/usr/bin/env python3
import argparse
import copy
import tomllib
from pathlib import Path


DEFAULT_GATES = {
    "coverage": 78.0,
    "mutation_advisory": 55.0,
}

DEFAULT_CHECK_POLICIES = {
    "tests": {
        "label": "Pytest",
        "mode": "Enforced",
        "jenkins_result": "SUCCESS when pytest exits with code 0",
        "rule": "Controlled by pytest exit code in Jenkins",
    },
    "coverage": {
        "label": "Coverage",
        "mode": "Enforced",
        "jenkins_result": "SUCCESS when coverage gate passes",
        "rule": "Total coverage must meet the configured coverage gate",
    },
    "mutation": {
        "label": "Mutation",
        "mode": "Advisory",
        "jenkins_result": "SUCCESS when mutation analysis and reports are generated",
        "rule": "",
    },
    "lint": {
        "label": "Lint",
        "mode": "Report only",
        "jenkins_result": "SUCCESS when lint reports are generated",
        "rule": "Reports are archived; no blocking gate configured",
    },
}


def load_tool_config(path):
    config_path = Path(path)
    if not config_path.exists():
        return {}
    return tomllib.loads(config_path.read_text(encoding="utf-8")).get("tool", {})


def load_gates(path):
    configured = load_tool_config(path).get("quality_gates", {})
    gates = DEFAULT_GATES.copy()
    for key in gates:
        if key in configured:
            gates[key] = float(configured[key])
    return gates


def load_check_policies(path):
    configured = load_tool_config(path).get("quality_checks", {})
    policies = copy.deepcopy(DEFAULT_CHECK_POLICIES)
    for key, values in configured.items():
        if key not in policies or not isinstance(values, dict):
            continue
        for field in ("label", "mode", "jenkins_result", "rule"):
            if field in values:
                policies[key][field] = str(values[field])
    return policies


def main():
    parser = argparse.ArgumentParser(description="Read quality gate thresholds from pyproject.toml.")
    parser.add_argument("name", choices=sorted(DEFAULT_GATES))
    parser.add_argument("--config", default="pyproject.toml")
    args = parser.parse_args()

    value = load_gates(args.config)[args.name]
    print(f"{value:g}")


if __name__ == "__main__":
    main()
