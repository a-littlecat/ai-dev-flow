"""Run the abnormal-state browser matrix against one real temporary stack."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dashboard.integration.process_tree import (
    process_group_options,
    terminate_process_tree,
    track_process_tree,
)
from dashboard.integration.state_fixture import apply_scenario
from dashboard.integration.tests.support import create_matrix_project

FRONTEND_ROOT = REPO_ROOT / "dashboard" / "frontend"
PLAYWRIGHT_CLI = (
    FRONTEND_ROOT / "node_modules" / "@playwright" / "test" / "cli.js"
)
CONFIG = REPO_ROOT / "dashboard" / "integration" / "playwright.config.mjs"


class StateMatrixError(RuntimeError):
    """The real backend-to-frontend abnormal-state matrix failed."""


def run_state_matrix() -> None:
    node = shutil.which("node")
    if not node:
        raise StateMatrixError("Node.js is not available on PATH")
    if not PLAYWRIGHT_CLI.is_file():
        raise StateMatrixError(
            "frontend dependencies are missing; run npm ci in dashboard/frontend"
        )
    with tempfile.TemporaryDirectory(prefix="dashboard-state-matrix-") as directory:
        project = create_matrix_project(Path(directory) / "project", REPO_ROOT)
        apply_scenario(project, "invalid-utf8")
        env = os.environ.copy()
        env.update(
            {
                "DASHBOARD_PYTHON": sys.executable,
                "DASHBOARD_PROJECT_ROOT": str(project),
                "DASHBOARD_STATE_MATRIX": "1",
                "PYTHONUTF8": "1",
                "PYTHONDONTWRITEBYTECODE": "1",
            }
        )
        process = track_process_tree(subprocess.Popen(
            [
                node,
                str(PLAYWRIGHT_CLI),
                "test",
                "-c",
                str(CONFIG),
                "state-matrix.spec.mjs",
            ],
            cwd=FRONTEND_ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            **process_group_options(),
        ))
        stdout = ""
        stderr = ""
        timeout_error: subprocess.TimeoutExpired | None = None
        try:
            stdout, stderr = process.communicate(timeout=180)
        except subprocess.TimeoutExpired as exc:
            timeout_error = exc
        finally:
            _terminate_process_tree(process)
            final_stdout, final_stderr = process.communicate()
            stdout += final_stdout
            stderr += final_stderr
        if timeout_error is not None:
            raise StateMatrixError(
                "real state matrix timed out after 180 seconds\n"
                f"stdout:\n{stdout}\n"
                f"stderr:\n{stderr}"
            ) from timeout_error
        if process.returncode != 0:
            raise StateMatrixError(
                "real state matrix failed\n"
                f"stdout:\n{stdout}\n"
                f"stderr:\n{stderr}"
            )


def _terminate_process_tree(process: subprocess.Popen[str]) -> None:
    terminate_process_tree(process)


def main() -> int:
    run_state_matrix()
    print("real backend-to-frontend state matrix passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
