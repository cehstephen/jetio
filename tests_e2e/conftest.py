"""End-to-end harness: launches a scenario app as a real subprocess (real
uvicorn, real TCP port, real HTTP over the wire), complementing the
in-process ASGITransport-based unit tests in tests/.
"""

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

# SECRET_KEY is required (no hardcoded default -- see GH issue #9). This
# process doesn't import jetio itself, but run_scenario_app() below copies
# this process's environ into each launched subprocess (`env =
# dict(os.environ)`), and that subprocess DOES import jetio -- so it needs
# to be set here too, before that copy happens. setdefault(), not direct
# assignment, so a real value exported in the environment (e.g. by CI)
# still wins.
os.environ.setdefault("SECRET_KEY", "test-only-secret-not-for-real-use-4f8a2c9e")

APPS_DIR = Path(__file__).parent / "apps"
REPO_ROOT = Path(__file__).parent.parent


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_until_ready(base_url: str, timeout: float = 15.0):
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        try:
            resp = httpx.get(f"{base_url}/docs", timeout=1.0)
            if resp.status_code == 200:
                return
        except httpx.TransportError as e:
            last_error = e
        time.sleep(0.2)
    return last_error


def run_scenario_app(tmp_path, script_name: str, force_utf8_stdout: bool = True):
    """Starts apps/<script_name> as a subprocess. force_utf8_stdout=False
    deliberately does NOT set PYTHONIOENCODING, to reproduce the actual
    default-Windows-console condition the startup-banner fix targets --
    setting it unconditionally (as e.g. jetio-ratelimit's e2e harness does)
    would hide exactly the scenario that fix exists for."""
    port = _free_port()
    script = APPS_DIR / script_name
    env = dict(os.environ)
    env["JETIO_APP_PORT"] = str(port)
    # Ensures the scenario app can `import jetio` regardless of whether the
    # local checkout is pip-installed (editable installs of this repo hit a
    # Windows-specific setuptools egg-info timestamp bug, so CI/contributors
    # may well be running straight from a plain `pip install -r
    # requirements.txt` without installing jetio itself).
    existing_path = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(REPO_ROOT) + (os.pathsep + existing_path if existing_path else "")
    if force_utf8_stdout:
        env["PYTHONIOENCODING"] = "utf-8"
    else:
        env.pop("PYTHONIOENCODING", None)

    process = subprocess.Popen(
        [sys.executable, str(script)],
        cwd=str(tmp_path),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    base_url = f"http://127.0.0.1:{port}"
    error = _wait_until_ready(base_url)
    if error is not None and process.poll() is not None:
        out, _ = process.communicate(timeout=5)
        raise RuntimeError(f"scenario app exited before becoming ready (code {process.returncode}):\n{out}")
    return process, base_url


def stop_scenario_app(process) -> None:
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


@pytest.fixture
def audit_app(tmp_path):
    process, base_url = run_scenario_app(tmp_path, "audit_scenario_app.py")
    yield base_url
    stop_scenario_app(process)


@pytest.fixture
def audit_app_default_console_encoding(tmp_path):
    """Same app, launched the way a real default Windows console would run
    it -- nothing forcing PYTHONIOENCODING=utf-8. Before the startup-banner
    fix, this configuration crashed on the emoji before the server ever
    bound its port."""
    process, base_url = run_scenario_app(tmp_path, "audit_scenario_app.py", force_utf8_stdout=False)
    yield base_url
    stop_scenario_app(process)


@pytest.fixture
def blog_app(tmp_path):
    process, base_url = run_scenario_app(tmp_path, "secure_blog_scenario_app.py")
    yield base_url
    stop_scenario_app(process)
