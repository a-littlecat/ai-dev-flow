from __future__ import annotations

import http.client
import json
import socket
import unittest

from be002 import support
from ai_dev_flow_dashboard.core.schema_validator import validate_contract
from ai_dev_flow_dashboard.server import create_local_server


class ServerCase(unittest.TestCase):
    def setUp(self):
        self.snapshot = support.snapshot_with_task()
        self.coordinator = support.coordinator_with_snapshot(self.snapshot)
        self.server = create_local_server(
            self.coordinator,
            port=0,
            heartbeat_seconds=0.05,
            write_timeout_seconds=0.25,
        )
        self.thread = support.run_server(self.server)
        self.port = self.server.server_port

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, method, path, *, headers=None, body=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        payload = response.read()
        result = (response.status, dict(response.getheaders()), payload)
        connection.close()
        return result

    def raw_sse(self, *, last_event_id=None, until=b"\n\n", timeout=2):
        client = socket.create_connection(("127.0.0.1", self.port), timeout=timeout)
        client.settimeout(timeout)
        lines = [
            "GET /api/v1/events HTTP/1.1",
            f"Host: 127.0.0.1:{self.port}",
        ]
        if last_event_id is not None:
            lines.append(f"Last-Event-ID: {last_event_id}")
        request = ("\r\n".join(lines) + "\r\n\r\n").encode("ascii")
        client.sendall(request)
        data = b""
        while until not in data:
            chunk = client.recv(65536)
            if not chunk:
                break
            data += chunk
        return client, data


class HttpContractTests(ServerCase):
    def test_snapshot_etag_304_and_security_headers(self):
        status, headers, body = self.request("GET", "/api/v1/snapshot")
        self.assertEqual(200, status)
        self.assertEqual(
            f'"sha256-{self.snapshot["revision"]}"',
            headers["ETag"],
        )
        self.assertEqual("private, no-cache", headers["Cache-Control"])
        self.assertEqual("nosniff", headers["X-Content-Type-Options"])
        self.assertEqual("no-referrer", headers["Referrer-Policy"])
        self.assertIn("default-src 'self'", headers["Content-Security-Policy"])
        self.assertNotIn("Access-Control-Allow-Origin", headers)
        payload = json.loads(body)
        validate_contract(payload)

        status, headers, body = self.request(
            "GET",
            "/api/v1/snapshot",
            headers={"If-None-Match": headers["ETag"]},
        )
        self.assertEqual(304, status)
        self.assertEqual(b"", body)
        self.assertEqual("0", headers["Content-Length"])

    def test_task_detail_health_and_error_statuses_use_strict_envelopes(self):
        cases = (
            ("GET", "/api/v1/tasks/TEST-001", 200),
            ("GET", "/api/v1/tasks/bad%2Fid", 400),
            ("GET", "/api/v1/tasks/MISSING-001", 404),
            ("GET", "/api/v1/unknown", 404),
            ("POST", "/api/v1/snapshot", 405),
            ("PUT", "/api/v1/tasks/TEST-001", 405),
            ("GET", "/api/v1/health", 200),
        )
        for method, path, expected in cases:
            with self.subTest(method=method, path=path):
                status, headers, body = self.request(method, path)
                self.assertEqual(expected, status)
                validate_contract(json.loads(body))
                if expected == 405:
                    self.assertEqual("GET", headers["Allow"])

    def test_host_allowlist_rejects_dns_rebinding_shape(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        connection.putrequest("GET", "/api/v1/snapshot", skip_host=True)
        connection.putheader("Host", f"attacker.example:{self.port}")
        connection.endheaders()
        response = connection.getresponse()
        payload = json.loads(response.read())
        connection.close()
        self.assertEqual(400, response.status)
        self.assertEqual("HOST_NOT_ALLOWED", payload["error"]["code"])
        validate_contract(payload)

    def test_trace_connect_and_unknown_methods_share_security_boundary(self):
        for method, path, expected in (
            ("TRACE", "/api/v1/snapshot", 405),
            ("CONNECT", "/api/v1/health", 405),
            ("BREW", "/api/v1/snapshot", 405),
            ("BREW", "/api/v1/unknown", 404),
        ):
            with self.subTest(method=method, path=path):
                status, headers, body = self.request(method, path)
                self.assertEqual(expected, status)
                payload = json.loads(body)
                validate_contract(payload)
                self.assertEqual("nosniff", headers["X-Content-Type-Options"])
                self.assertEqual("no-referrer", headers["Referrer-Policy"])
                self.assertIn("default-src 'self'", headers["Content-Security-Policy"])
                self.assertNotIn("Access-Control-Allow-Origin", headers)
                self.assertNotIn("Python", headers.get("Server", ""))
                if expected == 405:
                    self.assertEqual("GET", headers["Allow"])

        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        connection.putrequest("TRACE", "/api/v1/snapshot", skip_host=True)
        connection.putheader("Host", f"attacker.example:{self.port}")
        connection.endheaders()
        response = connection.getresponse()
        headers = dict(response.getheaders())
        payload = json.loads(response.read())
        connection.close()
        self.assertEqual(400, response.status)
        self.assertEqual("HOST_NOT_ALLOWED", payload["error"]["code"])
        self.assertEqual("nosniff", headers["X-Content-Type-Options"])
        self.assertNotIn("Python", headers.get("Server", ""))

    def test_path_traversal_and_query_routes_cannot_read_files(self):
        for path in (
            "/api/v1/tasks/../secret",
            "/../../.env",
            "/api/v1/tasks/C:%5CUsers%5Csecret",
        ):
            with self.subTest(path=path):
                status, _, body = self.request("GET", path)
                self.assertIn(status, {400, 404})
                payload = json.loads(body)
                self.assertIn(
                    payload["error"]["code"],
                    {"INVALID_TASK_ID", "ROUTE_NOT_FOUND"},
                )
                self.assertNotIn("stack", str(payload).casefold())
                self.assertNotIn("environment", str(payload).casefold())

    def test_non_loopback_bind_is_rejected_before_socket_creation(self):
        with self.assertRaises(ValueError):
            create_local_server(self.coordinator, host="0.0.0.0", port=0)


class SseContractTests(ServerCase):
    def test_initial_connection_sends_retry_full_reset_event(self):
        client, data = self.raw_sse(until=b"event: snapshot")
        try:
            while b"\n\n" not in data.split(b"\r\n\r\n", 1)[-1]:
                data += client.recv(65536)
        finally:
            client.close()
        body = data.split(b"\r\n\r\n", 1)[1]
        self.assertTrue(body.startswith(b"retry: 2000\n"))
        self.assertIn(f"id: {self.snapshot['revision']}\n".encode(), body)
        payload_line = next(line for line in body.splitlines() if line.startswith(b"data: "))
        event = json.loads(payload_line[6:])
        validate_contract(event)
        self.assertTrue(event["reset_required"])
        self.assertEqual(["TEST-001"], event["changed_task_ids"])

    def test_same_last_event_id_waits_and_emits_heartbeat_only(self):
        client, data = self.raw_sse(
            last_event_id=self.snapshot["revision"],
            until=b": keep-alive\n\n",
        )
        client.close()
        body = data.split(b"\r\n\r\n", 1)[1]
        self.assertTrue(body.startswith(b"retry: 2000\n"))
        self.assertIn(b": keep-alive\n\n", body)
        self.assertNotIn(b"event: snapshot", body)

    def test_unknown_last_event_id_sends_reset_without_changed_ids(self):
        client, data = self.raw_sse(last_event_id="f" * 64, until=b"event: snapshot")
        try:
            while b"\n\n" not in data.split(b"\r\n\r\n", 1)[-1]:
                data += client.recv(65536)
        finally:
            client.close()
        body = data.split(b"\r\n\r\n", 1)[1]
        payload_line = next(line for line in body.splitlines() if line.startswith(b"data: "))
        event = json.loads(payload_line[6:])
        self.assertTrue(event["reset_required"])
        self.assertEqual([], event["changed_task_ids"])

    def test_direct_successor_uses_precise_changed_ids_without_reset(self):
        previous = self.snapshot["revision"]
        successor = support.changed_snapshot(self.snapshot, lifecycle="In Progress")
        support.publish_successor(self.coordinator, successor, previous)
        client, data = self.raw_sse(last_event_id=previous, until=b"event: snapshot")
        try:
            while b"\n\n" not in data.split(b"\r\n\r\n", 1)[-1]:
                data += client.recv(65536)
        finally:
            client.close()
        body = data.split(b"\r\n\r\n", 1)[1]
        payload_line = next(line for line in body.splitlines() if line.startswith(b"data: "))
        event = json.loads(payload_line[6:])
        self.assertFalse(event["reset_required"])
        self.assertEqual(["TEST-001"], event["changed_task_ids"])

    def test_event_larger_than_buffer_limit_disconnects_slow_client(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.server = create_local_server(
            self.coordinator,
            port=0,
            heartbeat_seconds=0.05,
            write_timeout_seconds=0.1,
            max_event_bytes=8,
        )
        self.thread = support.run_server(self.server)
        self.port = self.server.server_port
        client = socket.create_connection(("127.0.0.1", self.port), timeout=1)
        client.settimeout(1)
        client.sendall(
            (
                "GET /api/v1/events HTTP/1.1\r\n"
                f"Host: 127.0.0.1:{self.port}\r\n\r\n"
            ).encode()
        )
        data = b""
        while True:
            chunk = client.recv(65536)
            if not chunk:
                break
            data += chunk
        client.close()
        self.assertIn(b"HTTP/1.1 200", data)
        self.assertNotIn(b"event: snapshot", data)


class UnavailableSnapshotTests(unittest.TestCase):
    def test_snapshot_and_events_are_503_while_health_remains_200(self):
        coordinator = support.SnapshotCoordinator(support.REPO_ROOT)
        server = create_local_server(coordinator, port=0)
        thread = support.run_server(server)
        port = server.server_port
        try:
            for path, expected in (
                ("/api/v1/snapshot", 503),
                ("/api/v1/events", 503),
                ("/api/v1/health", 200),
            ):
                connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
                connection.request("GET", path)
                response = connection.getresponse()
                payload = json.loads(response.read())
                connection.close()
                self.assertEqual(expected, response.status)
                validate_contract(payload)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
