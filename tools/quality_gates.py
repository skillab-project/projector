#!/usr/bin/env python3
import argparse
import tomllib
from pathlib import Path


DEFAULTS = {
    "coverage": 78.0,
    "mutation_advisory": 55.0,
}


def load_gates(path):
    config_path = Path(path)
    if not config_path.exists():
        return DEFAULTS.copy()

    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    configured = data.get("tool", {}).get("quality_gates", {})
    gates = DEFAULTS.copy()
    for key in gates:
        if key in configured:
            gates[key] = float(configured[key])
    return gates


def main():
    parser = argparse.ArgumentParser(description="Read quality gate thresholds from pyproject.toml.")
    parser.add_argument("name", choices=sorted(DEFAULTS))
    parser.add_argument("--config", default="pyproject.toml")
    args = parser.parse_args()

    value = load_gates(args.config)[args.name]
    print(f"{value:g}")


if __name__ == "__main__":
    main()
