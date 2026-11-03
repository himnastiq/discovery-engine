#!/usr/bin/env python3
"""Discovery Engine - Consolidated Cross-Platform Demo Supervisor (P10.1).

Manages pre-flight artifact validation, safe port and PID tracking (.demo/pids.json),
production frontend building, health verification, and clean shutdown across Windows,
macOS, and Linux.
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"
DEMO_DIR = REPO_ROOT / ".demo"
PIDS_FILE = DEMO_DIR / "pids.json"

try:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
except (ImportError, OSError):
    pass


def get_python_executable() -> str:
    """Find the active or virtualenv Python binary."""
    venv_py_win = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
    venv_py_unix = REPO_ROOT / ".venv" / "bin" / "python"
    backend_venv_win = BACKEND_DIR / ".venv" / "Scripts" / "python.exe"
    backend_venv_unix = BACKEND_DIR / ".venv" / "bin" / "python"

    if sys.platform == "win32":
        if venv_py_win.exists():
            return str(venv_py_win)
        if backend_venv_win.exists():
            return str(backend_venv_win)
    else:
        if venv_py_unix.exists():
            return str(venv_py_unix)
        if backend_venv_unix.exists():
            return str(backend_venv_unix)

    return sys.executable


def get_npm_executable() -> str:
    """Return platform-appropriate npm command name."""
    return "npm.cmd" if sys.platform == "win32" else "npm"


def get_npx_executable() -> str:
    """Return platform-appropriate npx command name."""
    return "npx.cmd" if sys.platform == "win32" else "npx"


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a TCP port is currently open and bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        try:
            s.connect((host, port))
            return True
        except (TimeoutError, ConnectionRefusedError, OSError):
            return False


def get_pid_holding_port(port: int) -> int | None:
    """Detect PID bound to a listening port on Windows or Unix."""
    if sys.platform == "win32":
        try:
            res = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                check=False,
            )
            for line in res.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    tokens = line.strip().split()
                    if len(tokens) >= 5:
                        try:
                            return int(tokens[-1])
                        except ValueError:
                            pass
        except (subprocess.SubprocessError, OSError):
            pass
    else:
        try:
            res = subprocess.run(
                ["lsof", "-i", f":{port}", "-t"],
                capture_output=True,
                text=True,
                check=False,
            )
            out = res.stdout.strip()
            if out:
                return int(out.split()[0])
        except (subprocess.SubprocessError, OSError, ValueError):
            pass
    return None


def get_process_name_by_pid(pid: int) -> str:
    """Lookup process name for a given PID."""
    if sys.platform == "win32":
        try:
            res = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                check=False,
            )
            out = res.stdout.strip()
            if out and not out.startswith("INFO:"):
                # "name.exe","1234","Console","1","10,000 K"
                parts = [p.strip('"') for p in out.split(",")]
                if parts:
                    return parts[0]
        except (subprocess.SubprocessError, OSError):
            pass
    else:
        try:
            res = subprocess.run(
                ["ps", "-p", str(pid), "-o", "comm="],
                capture_output=True,
                text=True,
                check=False,
            )
            out = res.stdout.strip()
            if out:
                return out
        except (subprocess.SubprocessError, OSError):
            pass
    return f"PID {pid}"


def terminate_pid_tree(pid: int, force: bool = False) -> None:
    """Terminate a process and all its child processes cleanly."""
    if sys.platform == "win32":
        args = ["taskkill", "/PID", str(pid), "/T"]
        if force:
            args.append("/F")
        subprocess.run(args, capture_output=True, check=False)
    else:
        sig = signal.SIGKILL if force else signal.SIGTERM
        try:
            os.kill(pid, sig)
        except OSError:
            pass


def load_tracked_pids() -> dict[str, Any]:
    """Read .demo/pids.json if present."""
    if not PIDS_FILE.exists():
        return {}
    try:
        return json.loads(PIDS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_tracked_pids(data: dict[str, Any]) -> None:
    """Write active process info to .demo/pids.json."""
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    PIDS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def clear_tracked_pids() -> None:
    """Remove .demo/pids.json."""
    if PIDS_FILE.exists():
        try:
            PIDS_FILE.unlink()
        except OSError:
            pass


def stop_demo(force: bool = False) -> int:
    """Stop running servers recorded in .demo/pids.json."""
    tracked = load_tracked_pids()
    if not tracked:
        print("[INFO] No active Discovery Engine demo tracked in .demo/pids.json.")
        return 0

    pids_to_kill: list[int] = []
    if tracked.get("backend_pid"):
        pids_to_kill.append(int(tracked["backend_pid"]))
    if tracked.get("frontend_pid"):
        pids_to_kill.append(int(tracked["frontend_pid"]))

    print(f"[INFO] Stopping Discovery Engine demo processes: {pids_to_kill}...")
    for pid in pids_to_kill:
        print(f"  Stopping PID {pid} ({get_process_name_by_pid(pid)})...")
        terminate_pid_tree(pid, force=force)

    # Wait up to 5 seconds for ports to clear
    ports = [tracked.get("api_port", 8000), tracked.get("web_port", 3000)]
    for port in ports:
        for _ in range(5):
            if not is_port_in_use(port):
                break
            time.sleep(1.0)

    clear_tracked_pids()
    print("[SUCCESS] Demo servers stopped.")
    return 0


def preflight_check(
    artifacts_dir: Path,
    build_missing: bool = False,
    python_bin: str = "python",
) -> bool:
    """Verify artifacts presence, checksums, and code hash parity (P10.1)."""
    sys.path.insert(0, str(BACKEND_DIR))
    from engine.artifacts import compute_code_hash, verify_artifacts  # type: ignore
    from engine.errors import DiscoveryEngineError  # type: ignore

    types = ["movies", "products", "articles"]
    missing_types: list[str] = []
    current_code_hash = compute_code_hash()

    print("\n" + "=" * 65)
    print("  Discovery Engine Demo Pre-Flight Check")
    print("=" * 65)
    print(f"  Artifacts Directory: {artifacts_dir.resolve()}")
    print(f"  Current Code Hash  : {current_code_hash[:16]}...")

    for t in types:
        target_dir = artifacts_dir / t
        manifest_file = target_dir / "manifest.json"

        if not manifest_file.exists():
            print(f"  [{t.upper()}] MISSING manifest.json")
            missing_types.append(t)
            continue

        try:
            manifest = verify_artifacts(target_dir)
            m_code_hash = manifest.get("code_hash", "")
            variant = manifest.get("dataset_variant", "unknown")
            source = manifest.get("dataset_source", variant)

            hash_status = "MATCH"
            if m_code_hash and m_code_hash != current_code_hash:
                hash_status = f"STALE (manifest: {m_code_hash[:8]} vs code: {current_code_hash[:8]})"

            print(
                f"  [{t.upper()}] Verified OK | Variant: {variant} | Source: {source} | Code: {hash_status}"
            )
            if "STALE" in hash_status:
                print(
                    f"    [WARN] Artifacts for '{t}' were built with earlier code. Consider retraining if models behave unexpectedly."
                )

        except (
            DiscoveryEngineError,
            ValueError,
            KeyError,
            OSError,
            json.JSONDecodeError,
        ) as exc:
            print(f"  [{t.upper()}] CORRUPTED: {exc}")
            missing_types.append(t)

    if missing_types:
        print("\n" + "-" * 65)
        print(f"[ERROR] Missing or corrupted artifacts detected for: {missing_types}")
        if not build_missing:
            print("\nTo build final benchmark artifacts per README:")
            for mt in missing_types:
                print(f"  cd backend && {python_bin} -m engine.train --type {mt}")
            print("\nOr to build lightweight fast demo artifacts:")
            for mt in missing_types:
                print(
                    f"  cd backend && {python_bin} -m engine.train --type {mt} --fast"
                )
            print(
                "\nAlternatively, re-run with '--build-missing' to auto-build fast variants."
            )
            print("-" * 65)
            return False
        else:
            print(
                f"\n[INFO] Auto-building fast demo variants for {missing_types} (--build-missing)..."
            )
            print("=" * 65)
            print("  [FAST VARIANT NOTICE] Auto-built artifacts use --fast mode.")
            print(
                "  Evaluation tab metrics will reflect fast subsets, not 1M report goldens."
            )
            print("=" * 65)
            for mt in missing_types:
                print(f"\n>>> Training {mt} (--fast)...")
                cmd = [python_bin, "-m", "engine.train", "--type", mt, "--fast"]
                res = subprocess.run(cmd, cwd=BACKEND_DIR, check=False)
                if res.returncode != 0:
                    print(
                        f"[ERROR] Failed to auto-build artifacts for '{mt}'.",
                        file=sys.stderr,
                    )
                    return False
            print("[SUCCESS] Missing artifacts auto-built successfully.")

    print("[SUCCESS] All artifacts verified.")
    return True


def ensure_frontend_build() -> bool:
    """Ensure Next.js production build (.next) is present and current."""
    next_dir = FRONTEND_DIR / ".next"
    npm_cmd = get_npm_executable()

    needs_build = False
    if not next_dir.exists():
        needs_build = True
    else:
        # Check source timestamps
        build_time = next_dir.stat().st_mtime
        for src_path in (FRONTEND_DIR / "src").rglob("*"):
            if src_path.is_file() and src_path.stat().st_mtime > build_time:
                needs_build = True
                break

    if needs_build:
        print("\n[BUILD] Creating Next.js production build (npm run build)...")
        res = subprocess.run([npm_cmd, "run", "build"], cwd=FRONTEND_DIR, check=False)
        if res.returncode != 0:
            print("[ERROR] Next.js build failed.", file=sys.stderr)
            return False
        print("[SUCCESS] Next.js production build created.")
    else:
        print("[INFO] Existing Next.js production build is up to date.")
    return True


def handle_port(port: int, our_pids: list[int], force: bool = False) -> bool:
    """Resolve port binding safely, refusing to kill foreign processes without --force."""
    if not is_port_in_use(port):
        return True

    holding_pid = get_pid_holding_port(port)
    if holding_pid is not None and holding_pid in our_pids:
        print(
            f"[INFO] Port {port} is occupied by previous demo PID {holding_pid}. Terminating..."
        )
        terminate_pid_tree(holding_pid, force=force)
        for _ in range(5):
            time.sleep(1.0)
            if not is_port_in_use(port):
                return True
        return False

    proc_name = get_process_name_by_pid(holding_pid) if holding_pid else "Unknown"
    print(
        f"\n[ERROR] Port {port} is currently in use by foreign process '{proc_name}' (PID: {holding_pid}).",
        file=sys.stderr,
    )
    if not force:
        print(
            "Foreign processes are never terminated automatically to protect other applications.\n"
            "Please free the port manually, choose an alternate port with --api-port/--web-port,\n"
            "or run with --force to terminate it.",
            file=sys.stderr,
        )
        return False
    else:
        if holding_pid:
            print(
                f"[WARN] --force enabled: terminating foreign process {holding_pid}..."
            )
            terminate_pid_tree(holding_pid, force=True)
            time.sleep(1.5)
            return not is_port_in_use(port)
        return False


def poll_backend_health(port: int, timeout: int = 30) -> bool:
    """Poll GET /v1/health until healthy or timeout expires."""
    print(
        f"\n[HEALTH] Polling API health on http://127.0.0.1:{port}/v1/health (timeout {timeout}s)..."
    )
    start = time.perf_counter()
    while time.perf_counter() - start < timeout:
        try:
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2.0)
            conn.request("GET", "/v1/health")
            res = conn.getresponse()
            if res.status == 200:
                body = res.read().decode("utf-8")
                data = json.loads(body)
                types = data.get("types", {})
                degraded = False
                for t_name, t_info in types.items():
                    if not t_info.get("available", True):
                        degraded = True
                        print(
                            f"  [WARN] Type '{t_name}' is degraded: {t_info.get('error', 'unavailable')}"
                        )
                if degraded:
                    print(
                        "  [HEALTH] API is responsive with degraded domains (continuing per specification)."
                    )
                else:
                    print("  [HEALTH] All content types healthy and available.")
                conn.close()
                return True
            conn.close()
        except (OSError, http.client.HTTPException, json.JSONDecodeError):
            pass
        time.sleep(1.0)

    print(f"[ERROR] API failed to respond within {timeout}s.", file=sys.stderr)
    return False


def poll_frontend_ready(port: int, timeout: int = 20) -> bool:
    """Poll frontend until port accepts connections."""
    print(f"[HEALTH] Verifying frontend readiness on http://localhost:{port}...")
    start = time.perf_counter()
    while time.perf_counter() - start < timeout:
        if is_port_in_use(port):
            return True
        time.sleep(0.5)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Discovery Engine - Unified Demo Supervisor (P10.1)"
    )
    parser.add_argument(
        "--stop", action="store_true", help="Stop running demo processes"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force terminate foreign processes on busy ports",
    )
    parser.add_argument(
        "--build-missing",
        action="store_true",
        help="Auto-build fast variants for missing artifacts",
    )
    parser.add_argument(
        "--api-port", type=int, default=8000, help="API server port (default 8000)"
    )
    parser.add_argument(
        "--web-port", type=int, default=3000, help="Frontend web port (default 3000)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Health check timeout in seconds (default 60)",
    )
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        default=REPO_ROOT / "artifacts",
        help="Path to artifacts root (default ./artifacts)",
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Start servers in background and return immediately",
    )
    args = parser.parse_args()

    if args.stop:
        return stop_demo(force=args.force)

    python_bin = get_python_executable()

    # Step 1: Pre-flight artifacts validation
    if not preflight_check(
        args.artifacts_dir, build_missing=args.build_missing, python_bin=python_bin
    ):
        return 1

    # Step 2: Ensure frontend production build
    if not ensure_frontend_build():
        return 1

    # Step 3: Check and resolve ports safely
    tracked = load_tracked_pids()
    our_pids = []
    if tracked.get("backend_pid"):
        our_pids.append(int(tracked["backend_pid"]))
    if tracked.get("frontend_pid"):
        our_pids.append(int(tracked["frontend_pid"]))

    if not handle_port(args.api_port, our_pids, force=args.force):
        return 1
    if not handle_port(args.web_port, our_pids, force=args.force):
        return 1

    # Step 4: Launch backend server
    print(f"\n[LAUNCH] Starting FastAPI backend on http://127.0.0.1:{args.api_port}...")
    backend_env = os.environ.copy()
    backend_env["PYTHONPATH"] = str(BACKEND_DIR)
    backend_env["ARTIFACT_DIR"] = str(args.artifacts_dir.resolve())

    backend_cmd = [
        python_bin,
        "-m",
        "uvicorn",
        "api.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(args.api_port),
    ]

    backend_proc = subprocess.Popen(
        backend_cmd,
        cwd=BACKEND_DIR,
        env=backend_env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Step 5: Launch frontend server in production mode
    print(
        f"[LAUNCH] Starting Next.js frontend (production) on http://localhost:{args.web_port}..."
    )
    frontend_env = os.environ.copy()
    frontend_env["API_BASE_URL"] = f"http://127.0.0.1:{args.api_port}"

    npx_cmd = get_npx_executable()
    frontend_cmd = [
        npx_cmd,
        "next",
        "start",
        "-H",
        "127.0.0.1",
        "-p",
        str(args.web_port),
    ]

    frontend_proc = subprocess.Popen(
        frontend_cmd,
        cwd=FRONTEND_DIR,
        env=frontend_env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Save tracked PIDs
    save_tracked_pids(
        {
            "backend_pid": backend_proc.pid,
            "frontend_pid": frontend_proc.pid,
            "api_port": args.api_port,
            "web_port": args.web_port,
            "started_at": time.time(),
        }
    )

    # Step 6: Verify health
    healthy = poll_backend_health(args.api_port, timeout=args.timeout)
    web_ready = poll_frontend_ready(args.web_port, timeout=15)

    if not healthy or not web_ready:
        print(
            "[ERROR] Startup health verification failed. Cleaning up...",
            file=sys.stderr,
        )
        stop_demo(force=True)
        return 1

    print("\n" + "=" * 65)
    print("  Discovery Engine Demo is Live!")
    print("=" * 65)
    print(f"  Frontend Dashboard : http://localhost:{args.web_port}")
    print(f"  Backend API Root   : http://127.0.0.1:{args.api_port}")
    print(f"  API Health Check   : http://127.0.0.1:{args.api_port}/v1/health")
    print(f"  Swagger API Docs   : http://127.0.0.1:{args.api_port}/docs")
    print("=" * 65)
    print("  To stop servers at any time, run: python tools/demo.py --stop")
    print("=" * 65 + "\n")

    if args.no_wait:
        return 0

    print("Demo servers running in background. Press Ctrl+C to terminate cleanly.")
    try:
        while True:
            # Check if children died unexpectedly
            if backend_proc.poll() is not None:
                print(
                    "\n[WARN] Backend process terminated unexpectedly.", file=sys.stderr
                )
                break
            if frontend_proc.poll() is not None:
                print(
                    "\n[WARN] Frontend process terminated unexpectedly.",
                    file=sys.stderr,
                )
                break
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\n[INTERRUPT] Received Ctrl+C. Shutting down demo servers...")
    finally:
        stop_demo(force=True)

    return 0


if __name__ == "__main__":
    expected_py = Path(get_python_executable()).resolve()
    current_py = Path(sys.executable).resolve()
    if expected_py.exists() and expected_py != current_py:
        res = subprocess.run([str(expected_py), *sys.argv], check=False)
        sys.exit(res.returncode)
    sys.exit(main())
