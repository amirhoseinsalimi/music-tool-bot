#!/usr/bin/env python3
"""Ensure environment variables used by the bot are documented in README.md."""

import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")
COMPOSE_NAME = re.compile(r"\$\{([A-Z][A-Z0-9_]*)")


def python_environment_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if not isinstance(node.func.value, ast.Name) or node.func.value.id != "os":
            continue
        if node.func.attr not in {"getenv", "environ"} or not node.args:
            continue
        name = node.args[0]
        if isinstance(name, ast.Constant) and isinstance(name.value, str) and ENV_NAME.fullmatch(name.value):
            names.add(name.value)
    return names


def main() -> int:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    documented = set(re.findall(r"^\|\s*([A-Z][A-Z0-9_]*)\s*\|", readme, re.MULTILINE))
    required = set()

    for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\s*([A-Z][A-Z0-9_]*)\s*=", line)
        if match:
            required.add(match.group(1))

    for path in ROOT.rglob("*.py"):
        if {".venv", "venv", "tests", ".git"} & set(path.parts):
            continue
        required.update(python_environment_names(path))

    for path in ROOT.glob("docker-compose*.yaml"):
        required.update(COMPOSE_NAME.findall(path.read_text(encoding="utf-8")))
    # Compose injects this value directly; it is not sourced from the operator's .env.
    required.add("PTB_TIMEDELTA")

    missing = sorted(required - documented)
    private_links = re.findall(r"\]\((?:\.\./)+docs/[^)]*\)", readme)
    if missing:
        print("Environment variables missing from the README configuration table:")
        print("\n".join(f"  {name}" for name in missing))
    if private_links:
        print("README contains workspace-only documentation links:")
        print("\n".join(f"  {link}" for link in private_links))
    if missing or private_links:
        return 1
    print(f"README documents all {len(required)} environment variables; no private docs links found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
