from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.request
from unittest import mock
from pathlib import Path

from dashboard.integration.launcher import (
    LauncherError,
    _LOOPBACK_OPENER,
    _ready,
    _stop,
    _validate_port,
    _wait_until_ready,
    build_commands,
    run,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


class LauncherContractTests(unittest.TestCase):
    def test_direct_script_entrypoints_bootstrap_repo_imports_in_isolated_python(self):
        scripts = (
            "launcher.py",
            "benchmark.py",
            "state_fixture.py",
            "state_matrix.py",
        )
        with tempfile.TemporaryDirectory() as directory:
            for name in scripts:
                path = REPO_ROOT / "dashboard" / "integration" / name
                command = (
                    "import runpy;"
                    f"runpy.run_path({str(path)!r}, run_name='isolated_import')"
                )
                env = os.environ.copy()
                env.pop("PYTHONHOME", None)
                env.pop("PYTHONPATH", None)
                result = subprocess.run(
                    [sys.executable, "-P", "-B", "-X", "utf8", "-c", command],
                    cwd=directory,
                    env=env,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=30,
                )
                self.assertEqual(
                    0,
                    result.returncode,
                    f"{name}: stdout={result.stdout!r} stderr={result.stderr!r}",
                )

    def test_commands_are_shell_free_loopback_only_and_point_at_integration_config(self):
        backend_src = REPO_ROOT / "dashboard" / "backend" / "src"
        frontend_root = REPO_ROOT / "dashboard" / "frontend"
        backend, frontend, env = build_commands(
            REPO_ROOT,
            backend_src,
            frontend_root,
            Path("node"),
            18765,
            15173,
        )
        self.assertIn("--host", backend)
        self.assertEqual("127.0.0.1", backend[backend.index("--host") + 1])
        self.assertEqual("18765", backend[backend.index("--port") + 1])
        self.assertEqual("node", frontend[0])
        self.assertTrue(frontend[-1].endswith("vite.config.mjs"))
        self.assertEqual("18765", env["DASHBOARD_BACKEND_PORT"])
        self.assertEqual("15173", env["DASHBOARD_FRONTEND_PORT"])
        self.assertTrue(env["PYTHONPATH"].split(os.pathsep)[0].endswith("dashboard\\backend\\src"))

    def test_proxy_normalizes_only_the_loopback_target_host(self):
        config = (REPO_ROOT / "dashboard" / "integration" / "vite.config.mjs").read_text(
            encoding="utf-8"
        )
        self.assertIn('host: "127.0.0.1"', config)
        self.assertIn('target: `http://127.0.0.1:${backendPort}`', config)
        self.assertIn("changeOrigin: true", config)
        self.assertIn("cors: false", config)
        self.assertIn('"Content-Security-Policy"', config)
        self.assertIn('"X-Content-Type-Options": "nosniff"', config)
        self.assertIn('"Referrer-Policy": "no-referrer"', config)

    def test_readiness_uses_a_proxy_disabled_loopback_opener(self):
        self.assertFalse(
            any(
                isinstance(handler, urllib.request.ProxyHandler)
                for handler in _LOOPBACK_OPENER.handlers
            )
        )
        response = mock.MagicMock()
        response.__enter__.return_value.status = 200
        with mock.patch.object(
            _LOOPBACK_OPENER,
            "open",
            return_value=response,
        ) as opened:
            self.assertTrue(_ready("http://127.0.0.1:18765/health"))
        opened.assert_called_once_with(
            "http://127.0.0.1:18765/health",
            timeout=2,
        )

    def test_startup_wait_returns_immediately_after_stop_is_requested(self):
        child = mock.Mock()
        child.poll.return_value = None
        stop_requested = mock.Mock()
        stop_requested.is_set.return_value = True
        with mock.patch("dashboard.integration.launcher._ready") as ready:
            self.assertFalse(
                _wait_until_ready(
                    (child,),
                    "http://127.0.0.1:18765/health",
                    60,
                    stop_requested,
                )
            )
        ready.assert_not_called()

    def test_stop_terminates_each_live_child_process_tree_and_reaps_roots(self):
        backend = mock.Mock()
        frontend = mock.Mock()
        backend.poll.return_value = None
        frontend.poll.return_value = None
        with mock.patch(
            "dashboard.integration.launcher.terminate_process_tree"
        ) as terminate:
            _stop((backend, frontend))
        self.assertEqual(
            [mock.call(frontend), mock.call(backend)],
            terminate.call_args_list,
        )
        frontend.wait.assert_called_once_with(timeout=5)
        backend.wait.assert_called_once_with(timeout=5)

    def test_invalid_ports_fail_closed(self):
        for value in (-1, 0, 65536):
            with self.subTest(value=value):
                with self.assertRaises(LauncherError):
                    _validate_port("test", value)

    def test_backend_is_stopped_when_frontend_process_cannot_start(self):
        args = argparse.Namespace(
            project_root=str(REPO_ROOT),
            backend_port=18765,
            frontend_port=15173,
            no_open=True,
            startup_timeout=1.0,
        )
        backend = mock.Mock()
        backend.poll.return_value = None
        backend.wait.return_value = 0
        with (
            mock.patch("dashboard.integration.launcher._assert_port_available"),
            mock.patch(
                "dashboard.integration.launcher._resolve_runtime",
                return_value=(Path("backend"), Path("frontend"), Path("node")),
            ),
            mock.patch(
                "dashboard.integration.launcher.build_commands",
                return_value=(["backend"], ["frontend"], {}),
            ),
            mock.patch(
                "dashboard.integration.launcher.subprocess.Popen",
                side_effect=(backend, OSError("frontend denied")),
            ),
            mock.patch(
                "dashboard.integration.launcher.track_process_tree",
                side_effect=lambda process: process,
            ),
            mock.patch(
                "dashboard.integration.launcher.terminate_process_tree"
            ) as terminate,
        ):
            with self.assertRaisesRegex(OSError, "frontend denied"):
                run(args)
        terminate.assert_called_once_with(backend)
        backend.wait.assert_called_once()


if __name__ == "__main__":
    unittest.main()
