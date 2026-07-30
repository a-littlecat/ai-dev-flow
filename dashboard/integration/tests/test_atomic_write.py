from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dashboard.integration.atomic_write import atomic_replace_bytes


class AtomicWriteTests(unittest.TestCase):
    def test_transient_windows_lease_is_retried_without_weakening_the_deadline(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "value.txt"
            target.write_bytes(b"before")
            real_replace = __import__("os").replace
            calls = 0

            def replace(source, destination):
                nonlocal calls
                calls += 1
                if calls < 3:
                    raise PermissionError(5, "leased")
                real_replace(source, destination)

            with patch(
                "dashboard.integration.atomic_write.os.replace",
                side_effect=replace,
            ), patch(
                "dashboard.integration.atomic_write.time.perf_counter_ns",
                return_value=123456,
            ), patch("dashboard.integration.atomic_write.time.sleep"):
                completed_at = atomic_replace_bytes(target, b"after")
            self.assertEqual(3, calls)
            self.assertEqual(123456, completed_at)
            self.assertEqual(b"after", target.read_bytes())

    def test_persistent_lease_fails_closed_at_the_bounded_deadline(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "value.txt"
            target.write_bytes(b"before")
            with patch(
                "dashboard.integration.atomic_write.os.replace",
                side_effect=PermissionError(5, "leased"),
            ), patch(
                "dashboard.integration.atomic_write.time.monotonic",
                side_effect=(0.0, 0.1, 1.0),
            ), patch("dashboard.integration.atomic_write.time.sleep"):
                with self.assertRaises(PermissionError):
                    atomic_replace_bytes(
                        target,
                        b"after",
                        timeout_seconds=0.5,
                    )
            self.assertEqual(b"before", target.read_bytes())


if __name__ == "__main__":
    unittest.main()
