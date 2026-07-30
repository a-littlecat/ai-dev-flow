from __future__ import annotations

import http.client
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

from dashboard.integration.process_tree import (
    process_group_options,
    terminate_process_tree,
    track_process_tree,
)
from dashboard.integration.tests.support import advance_project, create_project


REPO_ROOT = Path(__file__).resolve().parents[3]
LAUNCHER = REPO_ROOT / "dashboard" / "integration" / "launcher.py"
_LOOPBACK_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def request(url: str, *, method: str = "GET", headers: dict[str, str] | None = None):
    request_value = urllib.request.Request(url, method=method, headers=headers or {})
    try:
        with _LOOPBACK_OPENER.open(request_value, timeout=10) as response:
            return response.status, dict(response.headers.items()), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers.items()), exc.read()


class RealStackTests(unittest.TestCase):
    def setUp(self):
        self.process: subprocess.Popen[bytes] | None = None
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup_stack)
        self.project = create_project(Path(self.temporary.name) / "project", REPO_ROOT)
        self.backend_port = free_port()
        self.frontend_port = free_port()
        while self.frontend_port == self.backend_port:
            self.frontend_port = free_port()
        self.process = track_process_tree(subprocess.Popen(
            [
                sys.executable,
                "-B",
                "-X",
                "utf8",
                str(LAUNCHER),
                "--project-root",
                str(self.project),
                "--backend-port",
                str(self.backend_port),
                "--frontend-port",
                str(self.frontend_port),
                "--no-open",
            ],
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **process_group_options(),
        ))
        deadline = time.monotonic() + 60
        self.base = f"http://127.0.0.1:{self.frontend_port}"
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                stdout, stderr = self.process.communicate()
                self.fail(f"launcher exited early: {stdout!r} {stderr!r}")
            try:
                status, _, _ = request(f"{self.base}/api/v1/snapshot")
                if status == 200:
                    return
            except OSError:
                pass
            time.sleep(0.2)
        self.fail("real stack did not become ready")

    def _cleanup_stack(self):
        tree_terminated = False
        if self.process is not None and self.process.poll() is None:
            if os.name == "nt" and hasattr(signal, "CTRL_BREAK_EVENT"):
                self.process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                self.process.send_signal(signal.SIGINT)
            try:
                self.process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                terminate_process_tree(self.process)
                tree_terminated = True
                self.process.wait(timeout=10)
        if self.process is not None:
            if not tree_terminated:
                terminate_process_tree(self.process)
            self.process.communicate(timeout=1)
        self.temporary.cleanup()

    def test_real_proxy_snapshot_etag_security_and_revision_update(self):
        status, headers, body = request(
            f"{self.base}/api/v1/snapshot",
            headers={"Origin": "http://127.0.0.1:49152"},
        )
        self.assertEqual(200, status, body)
        self.assertNotIn("access-control-allow-origin", {key.casefold() for key in headers})
        snapshot = json.loads(body)
        self.assertEqual("ai-dev-flow/dashboard-snapshot/v1", snapshot["schema_version"])
        self.assertEqual("fresh", snapshot["state"])
        first_revision = snapshot["revision"]
        normalized_headers = {key.casefold(): value for key, value in headers.items()}
        etag = normalized_headers["etag"]

        status, headers, _ = request(f"{self.base}/")
        self.assertEqual(200, status)
        normalized_headers = {key.casefold(): value for key, value in headers.items()}
        self.assertIn("default-src 'self'", normalized_headers["content-security-policy"])
        self.assertEqual("nosniff", normalized_headers["x-content-type-options"])
        self.assertEqual("no-referrer", normalized_headers["referrer-policy"])

        status, _, body = request(
            f"{self.base}/api/v1/snapshot",
            headers={"If-None-Match": etag},
        )
        self.assertEqual(304, status)
        self.assertEqual(b"", body)

        status, _, body = request(f"{self.base}/api/v1/snapshot", method="POST")
        self.assertEqual(405, status, body)
        self.assertEqual("METHOD_NOT_ALLOWED", json.loads(body)["error"]["code"])

        direct = http.client.HTTPConnection("127.0.0.1", self.backend_port, timeout=10)
        direct.request("GET", "/api/v1/health", headers={"Host": "evil.example"})
        response = direct.getresponse()
        direct_body = response.read()
        direct.close()
        self.assertEqual(400, response.status)
        self.assertEqual("HOST_NOT_ALLOWED", json.loads(direct_body)["error"]["code"])

        events = http.client.HTTPConnection(
            "127.0.0.1",
            self.frontend_port,
            timeout=10,
        )
        self.addCleanup(events.close)
        events.request(
            "GET",
            "/api/v1/events",
            headers={"Last-Event-ID": first_revision},
        )
        event_response = events.getresponse()
        self.assertEqual(200, event_response.status)

        advance_project(self.project)
        deadline = time.monotonic() + 10
        changed = None
        changed_etag = None
        while time.monotonic() < deadline:
            status, candidate_headers, body = request(
                f"{self.base}/api/v1/snapshot",
                headers={"If-None-Match": etag},
            )
            if status == 304:
                time.sleep(0.1)
                continue
            self.assertEqual(200, status, body)
            candidate = json.loads(body)
            candidate_task = next(
                item
                for item in candidate["tasks"]
                if item["task_id"] == "STACK-001"
            )
            if (
                candidate["revision"] != first_revision
                and candidate_task["lifecycle"] == "In Progress"
            ):
                changed = candidate
                changed_etag = {
                    key.casefold(): value
                    for key, value in candidate_headers.items()
                }["etag"]
                break
            time.sleep(0.1)
        self.assertIsNotNone(changed)
        self.assertIsNotNone(changed_etag)
        self.assertNotEqual(etag, changed_etag)
        task = next(item for item in changed["tasks"] if item["task_id"] == "STACK-001")
        self.assertEqual("In Progress", task["lifecycle"])

        event_payload = None
        while True:
            line = event_response.readline()
            if not line:
                break
            if line.startswith(b"data: "):
                event_payload = json.loads(line[6:])
                break
        self.assertIsNotNone(event_payload)
        self.assertFalse(event_payload["reset_required"])
        self.assertIn("STACK-001", event_payload["changed_task_ids"])


class RealStackCleanupTests(unittest.TestCase):
    def test_loopback_requests_ignore_environment_proxies(self):
        self.assertFalse(
            any(
                isinstance(handler, urllib.request.ProxyHandler)
                for handler in _LOOPBACK_OPENER.handlers
            )
        )

    def test_timeout_terminates_the_complete_launcher_process_tree(self):
        case = RealStackTests(methodName="test_real_proxy_snapshot_etag_security_and_revision_update")
        case.process = mock.Mock()
        case.process.poll.return_value = None
        case.process.wait.side_effect = (
            subprocess.TimeoutExpired("launcher", 15),
            0,
        )
        case.process.communicate.return_value = (b"", b"")
        case.temporary = mock.Mock()
        with (
            mock.patch("dashboard.integration.tests.test_real_stack.os.name", "nt"),
            mock.patch.object(
                sys.modules[__name__],
                "terminate_process_tree",
            ) as terminate,
        ):
            case._cleanup_stack()
        terminate.assert_called_once_with(case.process)
        case.temporary.cleanup.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
