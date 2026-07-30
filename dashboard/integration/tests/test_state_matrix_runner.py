from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from unittest import mock

from dashboard.integration.state_matrix import StateMatrixError, run_state_matrix


class StateMatrixRunnerTests(unittest.TestCase):
    def test_timeout_terminates_and_reaps_the_playwright_process_tree(self):
        child = mock.Mock()
        child.pid = 12345
        child.poll.return_value = None
        child.communicate.side_effect = (
            subprocess.TimeoutExpired("playwright", 180),
            ("partial stdout", "partial stderr"),
        )
        temporary = mock.MagicMock()
        temporary.__enter__.return_value = "matrix-temp"
        with (
            mock.patch(
                "dashboard.integration.state_matrix.shutil.which",
                return_value="node.exe",
            ),
            mock.patch("pathlib.Path.is_file", return_value=True),
            mock.patch(
                "dashboard.integration.state_matrix.tempfile.TemporaryDirectory",
                return_value=temporary,
            ),
            mock.patch(
                "dashboard.integration.state_matrix.create_matrix_project",
                return_value=Path("matrix-project"),
            ),
            mock.patch("dashboard.integration.state_matrix.apply_scenario"),
            mock.patch(
                "dashboard.integration.state_matrix.subprocess.Popen",
                return_value=child,
            ),
            mock.patch(
                "dashboard.integration.state_matrix.track_process_tree",
                side_effect=lambda process: process,
            ),
            mock.patch(
                "dashboard.integration.state_matrix._terminate_process_tree"
            ) as terminate,
        ):
            with self.assertRaisesRegex(StateMatrixError, "timed out"):
                run_state_matrix()
        terminate.assert_called_once_with(child)
        self.assertEqual(2, child.communicate.call_count)

    def test_interruption_also_terminates_and_reaps_the_process_tree(self):
        child = mock.Mock()
        child.pid = 12345
        child.poll.return_value = None
        child.communicate.side_effect = (KeyboardInterrupt(), ("", ""))
        temporary = mock.MagicMock()
        temporary.__enter__.return_value = "matrix-temp"
        with (
            mock.patch(
                "dashboard.integration.state_matrix.shutil.which",
                return_value="node.exe",
            ),
            mock.patch("pathlib.Path.is_file", return_value=True),
            mock.patch(
                "dashboard.integration.state_matrix.tempfile.TemporaryDirectory",
                return_value=temporary,
            ),
            mock.patch(
                "dashboard.integration.state_matrix.create_matrix_project",
                return_value=Path("matrix-project"),
            ),
            mock.patch("dashboard.integration.state_matrix.apply_scenario"),
            mock.patch(
                "dashboard.integration.state_matrix.subprocess.Popen",
                return_value=child,
            ),
            mock.patch(
                "dashboard.integration.state_matrix.track_process_tree",
                side_effect=lambda process: process,
            ),
            mock.patch(
                "dashboard.integration.state_matrix._terminate_process_tree"
            ) as terminate,
        ):
            with self.assertRaises(KeyboardInterrupt):
                run_state_matrix()
        terminate.assert_called_once_with(child)
        self.assertEqual(2, child.communicate.call_count)


if __name__ == "__main__":
    unittest.main()
