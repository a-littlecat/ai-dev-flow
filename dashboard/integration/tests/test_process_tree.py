from __future__ import annotations

import subprocess
import unittest
from unittest import mock

from dashboard.integration.process_tree import (
    process_group_options,
    terminate_process_tree,
    track_process_tree,
)


class ProcessTreeTests(unittest.TestCase):
    def test_windows_taskkill_discards_native_encoded_output(self):
        process = mock.Mock()
        process.pid = 12345
        process.poll.return_value = None
        with (
            mock.patch("dashboard.integration.process_tree.os.name", "nt"),
            mock.patch(
                "dashboard.integration.process_tree.subprocess.run"
            ) as run,
        ):
            terminate_process_tree(process)
        run.assert_called_once_with(
            ["taskkill", "/PID", "12345", "/T", "/F"],
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def test_windows_job_is_terminated_even_after_root_exit(self):
        process = mock.Mock()
        process.pid = 12345
        process.poll.return_value = 0
        setattr(process, "_dashboard_job_handle", 678)
        with (
            mock.patch("dashboard.integration.process_tree.os.name", "nt"),
            mock.patch(
                "dashboard.integration.process_tree._terminate_windows_job",
                return_value=True,
            ) as terminate_job,
            mock.patch(
                "dashboard.integration.process_tree.subprocess.run"
            ) as run,
        ):
            terminate_process_tree(process)
        terminate_job.assert_called_once_with(678)
        run.assert_not_called()
        self.assertIsNone(getattr(process, "_dashboard_job_handle"))

    def test_windows_tracking_retains_job_handle_on_process(self):
        process = mock.Mock()
        process.pid = 12345
        calls = []
        with (
            mock.patch("dashboard.integration.process_tree.os.name", "nt"),
            mock.patch(
                "dashboard.integration.process_tree._create_windows_job",
                side_effect=lambda value: calls.append(("job", value)) or 678,
            ) as create_job,
            mock.patch(
                "dashboard.integration.process_tree._resume_windows_process",
                side_effect=lambda pid: calls.append(("resume", pid)),
            ) as resume,
        ):
            self.assertIs(process, track_process_tree(process))
        create_job.assert_called_once_with(process)
        resume.assert_called_once_with(12345)
        self.assertEqual([("job", process), ("resume", 12345)], calls)
        self.assertEqual(678, getattr(process, "_dashboard_job_handle"))

    def test_windows_process_starts_suspended_before_job_assignment(self):
        with (
            mock.patch("dashboard.integration.process_tree.os.name", "nt"),
            mock.patch.object(
                subprocess,
                "CREATE_NEW_PROCESS_GROUP",
                0x200,
                create=True,
            ),
            mock.patch.object(
                subprocess,
                "CREATE_SUSPENDED",
                0x4,
                create=True,
            ),
        ):
            options = process_group_options()
        self.assertEqual(0x204, options["creationflags"])


if __name__ == "__main__":
    unittest.main()
