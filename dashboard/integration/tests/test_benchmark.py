from __future__ import annotations

import unittest
import subprocess
from pathlib import Path
from unittest import mock

from dashboard.integration.benchmark import (
    BenchmarkError,
    EDGE_COUNT,
    RESULT_SCHEMA,
    SAMPLE_COUNT,
    TASK_COUNT,
    _cold_sample,
    _result,
    evaluate_gates,
    environment_report,
    reference_profile_qualification,
    stable_save_result,
)


class IntegrationBenchmarkContractTests(unittest.TestCase):
    def result(self, metric: str, p95_value: float, payload_bytes: int = 1024):
        samples = [1.0] * (SAMPLE_COUNT - 2) + [p95_value, p95_value + 1]
        return _result(
            environment={"os": "test"},
            dataset_manifest={
                "task_count": TASK_COUNT,
                "edge_count": EDGE_COUNT,
                "dataset_sha256": "a" * 64,
            },
            metric=metric,
            samples_ms=samples,
            payload_bytes=payload_bytes,
            peak_rss_bytes=2048,
            started_at="2026-07-29T00:00:00.000Z",
            finished_at="2026-07-29T00:00:01.000Z",
        )

    def test_result_keeps_exactly_thirty_raw_samples_and_frozen_identity(self):
        result = self.result("cold_snapshot_ms", 1999.0)
        self.assertEqual(RESULT_SCHEMA, result["schema_version"])
        self.assertEqual(30, len(result["samples_ms"]))
        self.assertEqual(TASK_COUNT, result["dataset_manifest"]["task_count"])
        self.assertEqual(EDGE_COUNT, result["dataset_manifest"]["edge_count"])

    def test_all_frozen_gates_pass_at_or_below_the_thresholds(self):
        results = [
            self.result("cold_snapshot_ms", 2000.0),
            self.result("stable_save_to_revision_ms", 1000.0),
            self.result("api_serialize_ms", 250.0, 10 * 1024 * 1024),
        ]
        report = evaluate_gates(results)
        self.assertTrue(report["passed"], report)
        self.assertTrue(all(report["checks"].values()))

    def test_any_metric_or_payload_above_a_gate_fails_the_run(self):
        results = [
            self.result("cold_snapshot_ms", 2000.001),
            self.result("stable_save_to_revision_ms", 999.0),
            self.result("api_serialize_ms", 249.0, 10 * 1024 * 1024 + 1),
        ]
        report = evaluate_gates(results)
        self.assertFalse(report["passed"])
        self.assertFalse(report["checks"]["cold_snapshot_ms"])
        self.assertFalse(report["checks"]["payload_bytes"])

    def test_reference_profile_rejects_python_3_13(self):
        environment = {
            "os": "Windows-11-10.0.26200-SP0",
            "os_build": "10.0.26200",
            "architecture": "AMD64",
            "logical_cpu_count": 16,
            "ram_bytes": 32 * 1024**3,
            "disk_media_type": "SSD",
            "temporary_filesystem": "NTFS",
            "python_major_minor": [3, 12],
            "git": "git version 2.50.1.windows.1",
            "power_scheme": "Balanced",
            "defender": (
                "AntivirusEnabled=True;RealTimeProtectionEnabled=True"
            ),
            "machine_classification": "physical",
        }
        self.assertTrue(reference_profile_qualification(environment)["passed"])
        environment["python_major_minor"] = [3, 13]
        qualification = reference_profile_qualification(environment)
        self.assertFalse(qualification["passed"])
        self.assertFalse(qualification["checks"]["python_3_11_or_3_12"])

        environment["python_major_minor"] = [3, 12]
        environment["os_build"] = "10.0.22621"
        self.assertFalse(
            reference_profile_qualification(environment)["checks"][
                "windows_11_23h2_or_newer"
            ]
        )
        environment["os_build"] = "10.0.22631"
        environment["machine_classification"] = "virtual"
        self.assertFalse(
            reference_profile_qualification(environment)["checks"][
                "physical_machine"
            ]
        )
        environment["machine_classification"] = "unknown"
        self.assertFalse(
            reference_profile_qualification(environment)["checks"][
                "physical_machine"
            ]
        )

    def test_reference_profile_accepts_localized_balanced_scheme_by_guid(self):
        environment = {
            "os": "Windows-11-10.0.26200-SP0",
            "os_build": "10.0.26200",
            "architecture": "AMD64",
            "logical_cpu_count": 16,
            "ram_bytes": 32 * 1024**3,
            "disk_media_type": "SSD",
            "temporary_filesystem": "NTFS",
            "python_major_minor": [3, 12],
            "git": "git version 2.50.1.windows.1",
            "power_scheme": (
                "电源方案 GUID: 381b4222-f694-41f0-9685-ff5bb260df2e  (平衡)"
            ),
            "defender": (
                "AntivirusEnabled=True;RealTimeProtectionEnabled=True"
            ),
            "machine_classification": "physical",
        }
        qualification = reference_profile_qualification(environment)
        self.assertTrue(qualification["checks"]["balanced_power"])
        self.assertTrue(qualification["passed"])

    def test_environment_classifies_exact_hp_manufacturer_as_physical(self):
        powershell_values = iter(
            [
                "SSD",
                "381b4222-f694-41f0-9685-ff5bb260df2e (Balanced)",
                "AntivirusEnabled=True;RealTimeProtectionEnabled=True",
                "NTFS",
                "HP",
                "EliteBook 845",
                "False",
            ]
        )
        with (
            mock.patch(
                "dashboard.integration.benchmark._powershell_value",
                side_effect=lambda _script: next(powershell_values),
            ),
            mock.patch(
                "dashboard.integration.benchmark._run"
            ) as run_command,
            mock.patch(
                "dashboard.integration.benchmark._registry_cpu",
                return_value="CPU",
            ),
        ):
            run_command.return_value.stdout = "git version 2.50.1.windows.1"
            environment = environment_report()
        self.assertEqual("HP", environment["machine_manufacturer"])
        self.assertEqual("physical", environment["machine_classification"])

    def test_cold_child_is_killed_and_reaped_after_timeout(self):
        child = mock.Mock()
        child.communicate.side_effect = (
            subprocess.TimeoutExpired("cold-child", 30),
            ("", "timed out"),
        )
        with (
            mock.patch(
                "dashboard.integration.benchmark.subprocess.Popen",
                return_value=child,
            ),
            mock.patch(
                "dashboard.integration.benchmark.track_process_tree",
                side_effect=lambda process: process,
            ),
            mock.patch(
                "dashboard.integration.benchmark.terminate_process_tree"
            ) as terminate,
        ):
            with self.assertRaisesRegex(BenchmarkError, "timed out"):
                _cold_sample(Path("fixture"))
        terminate.assert_called_once_with(child)
        self.assertEqual(2, child.communicate.call_count)

    def test_cold_child_is_terminated_and_reaped_after_interruption(self):
        child = mock.Mock()
        child.poll.return_value = None
        child.communicate.side_effect = (KeyboardInterrupt(), ("", ""))
        with (
            mock.patch(
                "dashboard.integration.benchmark.subprocess.Popen",
                return_value=child,
            ),
            mock.patch(
                "dashboard.integration.benchmark.track_process_tree",
                side_effect=lambda process: process,
            ),
            mock.patch(
                "dashboard.integration.benchmark.terminate_process_tree"
            ) as terminate,
        ):
            with self.assertRaises(KeyboardInterrupt):
                _cold_sample(Path("fixture"))
        terminate.assert_called_once_with(child)
        self.assertEqual(2, child.communicate.call_count)

    def test_stable_save_setup_failure_closes_every_started_resource(self):
        coordinator = mock.Mock()
        coordinator.refresh.return_value.revision = "a" * 64
        watcher = mock.Mock()
        watcher.wait_until_idle.return_value = False
        server = mock.Mock()
        server.server_port = 18765
        thread = mock.Mock()
        with (
            mock.patch(
                "dashboard.integration.benchmark.SnapshotCoordinator",
                return_value=coordinator,
            ),
            mock.patch(
                "dashboard.integration.benchmark.PollingWatcher",
                return_value=watcher,
            ),
            mock.patch(
                "dashboard.integration.benchmark.create_local_server",
                return_value=server,
            ),
            mock.patch(
                "dashboard.integration.benchmark.threading.Thread",
                return_value=thread,
            ),
        ):
            with self.assertRaisesRegex(BenchmarkError, "idle"):
                stable_save_result(Path("fixture"), {}, {})
        watcher.stop.assert_called_once_with()
        server.shutdown.assert_called_once_with()
        server.server_close.assert_called_once_with()
        thread.join.assert_called_once_with(timeout=5)


if __name__ == "__main__":
    unittest.main()
