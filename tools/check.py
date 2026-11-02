#!/usr/bin/env python3
"""Discovery Engine - Cross-platform quality checks runner (FIX-43).

Runs linting, formatting check, type checking, and test suite across platforms
without requiring GNU Make or Unix shell utilities:
  1. ruff check .
  2. ruff format --check .
  3. mypy engine/ api/
  4. pytest tests/ -v --tb=short
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"


def run_step(name: str, cmd: list[str], cwd: Path) -> None:
    """Execute a single check step and exit on failure."""
    cmd_str = " ".join(cmd)
    print("\n========================================================")
    print(f"RUNNING: {name}")
    print(f"COMMAND: {cmd_str}")
    print(f"CWD:     {cwd}")
    print("========================================================")

    res = subprocess.run(cmd, check=False, cwd=cwd)
    if res.returncode != 0:
        print(
            f"\n[FAILURE] {name} failed with exit code {res.returncode}.",
            file=sys.stderr,
        )
        sys.exit(res.returncode)
    print(f"[PASSED]  {name}")


def get_python_executable() -> str:
    """Find the active or virtualenv Python binary."""
    venv_py_win = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
    venv_py_unix = REPO_ROOT / ".venv" / "bin" / "python"
    if sys.platform == "win32" and venv_py_win.exists():
        return str(venv_py_win)
    if venv_py_unix.exists():
        return str(venv_py_unix)
    return sys.executable


def main() -> None:
    py = get_python_executable()

    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"

    steps = [
        ("Ruff Linter", [py, "-m", "ruff", "check", "."], BACKEND_DIR),
        (
            "Ruff Format Check",
            [py, "-m", "ruff", "format", "--check", "."],
            BACKEND_DIR,
        ),
        ("Mypy Type Checker", [py, "-m", "mypy", "engine/", "api/"], BACKEND_DIR),
        (
            "Conformance Audit Document Check",
            [py, str(REPO_ROOT / "tools" / "check_conformance.py"), "--check"],
            REPO_ROOT,
        ),
        (
            "Tracked Files Git Hygiene Check",
            [py, str(REPO_ROOT / "tools" / "check_tracked_files.py")],
            REPO_ROOT,
        ),
        (
            "Pytest Test Suite",
            [
                py,
                "-m",
                "pytest",
                "tests/",
                "-v",
                "--tb=short",
                "-m",
                "not real_data and not llm_live",
            ],
            BACKEND_DIR,
        ),
    ]

    if (FRONTEND_DIR / "node_modules").exists():
        steps.extend(
            [
                ("Frontend Linter (eslint)", [npm_cmd, "run", "lint"], FRONTEND_DIR),
                (
                    "Frontend Type Checker (tsc)",
                    [npm_cmd, "run", "type-check"],
                    FRONTEND_DIR,
                ),
                ("Frontend Vitest Suite", [npm_cmd, "run", "test"], FRONTEND_DIR),
                (
                    "Frontend Secret Leakage Check",
                    [npm_cmd, "run", "check-secrets"],
                    FRONTEND_DIR,
                ),
            ]
        )

    print("========================================================")
    print("Discovery Engine Quality Assurance Checks")
    print(f"Python interpreter: {py}")
    print(f"Repository root:    {REPO_ROOT}")
    print("========================================================")

    for name, cmd, cwd in steps:
        run_step(name, cmd, cwd)

    print("\n========================================================")
    print("[SUCCESS] All checks passed successfully.")
    print("========================================================")


if __name__ == "__main__":
    main()
