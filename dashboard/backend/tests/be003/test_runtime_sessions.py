from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from be001.support import REPO_ROOT
from ai_dev_flow_dashboard.cli import main as cli_main
from ai_dev_flow_dashboard.core.schema_validator import validate_contract
from ai_dev_flow_dashboard.runtime import RuntimeSessionError, RuntimeSessionStore


class Clock:
    def __init__(self):
        self.value = dt.datetime(2026, 8, 8, 12, 0, tzinfo=dt.timezone.utc)

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += dt.timedelta(seconds=seconds)


class RuntimeSessionStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.project = self.root / "project"
        (self.project / "docs" / "tasks").mkdir(parents=True)
        self.runtime = self.root / "runtime"
        self.clock = Clock()
        self.store = RuntimeSessionStore(
            self.project, runtime_root=self.runtime, now=self.clock
        )

    def tearDown(self):
        self.temporary.cleanup()

    def test_start_update_wait_end_are_atomic_and_ended_is_idempotent(self):
        with mock.patch(
            "ai_dev_flow_dashboard.runtime.session.os.replace",
            wraps=os.replace,
        ) as replace:
            started = self.store.start(
                session_id="codex-test",
                task_id="TEST-001",
                harness_id="codex",
                phase="implementing",
                next_step="实现 runtime store",
                worktree=str(self.project),
            )
            self.clock.advance(10)
            updated = self.store.update(
                "codex-test", phase="validating", next_step="运行测试"
            )
            waited = self.store.wait("codex-test", "等待用户确认")
            ended = self.store.end("codex-test", "completed")
            repeated = self.store.end("codex-test", "ignored")
        self.assertEqual(4, replace.call_count)
        self.assertEqual("implementing", started["phase"])
        validate_contract(
            started,
            schema_path=REPO_ROOT / "dashboard" / "contracts" / "runtime-session-v1.schema.json",
        )
        self.assertEqual("validating", updated["phase"])
        self.assertEqual("waiting_user", waited["phase"])
        self.assertEqual("done", ended["phase"])
        self.assertEqual(ended, repeated)
        self.assertFalse(list(self.store.sessions_dir.glob("*.tmp")))
        self.assertEqual("ended", self.store.list()[0]["freshness"])

    def test_stale_invalid_json_time_and_cross_project_binding(self):
        self.store.start(
            session_id="stale-one",
            task_id="TEST-001",
            harness_id="codex",
            phase="implementing",
            next_step="work",
            stale_after_seconds=5,
        )
        self.clock.advance(6)
        self.store.sessions_dir.joinpath("bad.json").write_text("{", encoding="utf-8")
        invalid_time = json.loads(
            self.store.sessions_dir.joinpath("stale-one.json").read_text(encoding="utf-8")
        )
        invalid_time["session_id"] = "bad-time"
        invalid_time["updated_at"] = "2020-01-01T00:00:00Z"
        self.store.sessions_dir.joinpath("bad-time.json").write_text(
            json.dumps(invalid_time), encoding="utf-8"
        )
        other = self.root / "other"
        (other / "docs" / "tasks").mkdir(parents=True)
        other_store = RuntimeSessionStore(other, runtime_root=self.runtime, now=self.clock)
        other_store._prepare_directories()
        other_store.sessions_dir.joinpath("forged.json").write_bytes(
            self.store.sessions_dir.joinpath("stale-one.json").read_bytes()
        )
        states = {item["session_id"]: item["freshness"] for item in self.store.list()}
        self.assertEqual("stale", states["stale-one"])
        self.assertEqual("invalid", states["bad"])
        self.assertEqual("invalid", states["bad-time"])
        self.assertEqual("invalid", other_store.list()[0]["freshness"])

        mismatched = json.loads(
            self.store.sessions_dir.joinpath("stale-one.json").read_text(encoding="utf-8")
        )
        mismatched["session_id"] = "different-id"
        self.store.sessions_dir.joinpath("wrong-name.json").write_text(
            json.dumps(mismatched), encoding="utf-8"
        )
        wrong = next(item for item in self.store.list() if item["session_id"] == "wrong-name")
        self.assertEqual("invalid", wrong["freshness"])

    def test_path_traversal_project_local_root_and_session_symlink_fail_closed(self):
        with self.assertRaises(RuntimeSessionError):
            RuntimeSessionStore(self.project, runtime_root=self.project / "runtime")
        with self.assertRaises(RuntimeSessionError):
            self.store.start(
                session_id="../escape",
                task_id="TEST-001",
                harness_id="codex",
                phase="planning",
                next_step="none",
            )
        self.store._prepare_directories()
        outside = self.root / "outside.json"
        outside.write_text("{}", encoding="utf-8")
        link = self.store.sessions_dir / "evil.json"
        try:
            link.symlink_to(outside)
        except OSError:
            self.skipTest("symlink creation is unavailable")
        self.assertEqual("invalid", self.store.list()[0]["freshness"])

    def test_start_conflict_update_missing_and_replace_boundary(self):
        arguments = dict(
            session_id="same",
            task_id="TEST-001",
            harness_id="codex",
            phase="planning",
            next_step="plan",
        )
        self.store.start(**arguments)
        with self.assertRaises(RuntimeSessionError):
            self.store.start(**arguments)
        self.assertEqual("planning", self.store.start(**arguments, replace=True)["phase"])
        with self.assertRaises(RuntimeSessionError):
            self.store.update("missing", phase="validating")

    def test_future_timestamps_beyond_clock_skew_are_invalid(self):
        for field in ("started_at", "updated_at", "ended_at"):
            with self.subTest(field=field):
                session_id = f"future-{field}"
                self.store.start(
                    session_id=session_id,
                    task_id="TEST-001",
                    harness_id="codex",
                    phase="implementing",
                    next_step="work",
                )
                path = self.store.sessions_dir / f"{session_id}.json"
                payload = json.loads(path.read_text(encoding="utf-8"))
                payload[field] = "2026-08-08T12:05:01Z"
                path.write_text(json.dumps(payload), encoding="utf-8")
                item = next(item for item in self.store.list() if item["session_id"] == session_id)
                self.assertEqual("invalid", item["freshness"])

    def test_concurrent_start_without_replace_has_one_winner(self):
        original_replace = os.replace
        entered = threading.Event()
        release = threading.Event()
        outcomes = []

        def delayed_replace(source, target):
            entered.set()
            release.wait(timeout=2)
            return original_replace(source, target)

        def run_start(label):
            try:
                self.store.start(
                    session_id="race",
                    task_id=f"TEST-{label}",
                    harness_id="codex",
                    phase="implementing",
                    next_step="work",
                )
                outcomes.append("success")
            except RuntimeSessionError:
                outcomes.append("conflict")

        with mock.patch(
            "ai_dev_flow_dashboard.runtime.session.os.replace",
            side_effect=delayed_replace,
        ):
            first = threading.Thread(target=run_start, args=("A",))
            second = threading.Thread(target=run_start, args=("B",))
            first.start()
            self.assertTrue(entered.wait(timeout=2))
            second.start()
            second.join(timeout=2)
            release.set()
            first.join(timeout=2)
        self.assertCountEqual(["success", "conflict"], outcomes)
        self.assertEqual(1, len(self.store.list()))

    def test_first_runtime_directory_creation_is_safe_across_processes(self):
        script = (
            "import pathlib,sys;"
            "from ai_dev_flow_dashboard.runtime import RuntimeSessionStore;"
            "store=RuntimeSessionStore(pathlib.Path(sys.argv[1]),runtime_root=pathlib.Path(sys.argv[2]));"
            "store.start(session_id=sys.argv[3],task_id='TEST-001',harness_id='codex',phase='implementing',next_step='work')"
        )
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(REPO_ROOT / "dashboard" / "backend" / "src")
        processes = [
            subprocess.Popen(
                [sys.executable, "-B", "-X", "utf8", "-c", script, str(self.project), str(self.runtime), session_id],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                env=environment,
            )
            for session_id in ("first-a", "first-b")
        ]
        results = [process.communicate(timeout=20) for process in processes]
        self.assertEqual([0, 0], [process.returncode for process in processes], results)
        self.assertEqual(["first-a", "first-b"], sorted(item["session_id"] for item in self.store.list()))

    def test_abandoned_process_lock_is_released_by_the_operating_system(self):
        script = (
            "import pathlib,time;"
            "from ai_dev_flow_dashboard.runtime import RuntimeSessionStore;"
            f"store=RuntimeSessionStore(pathlib.Path({str(self.project)!r}),runtime_root=pathlib.Path({str(self.runtime)!r}));"
            "ctx=store._mutation_lock('abandoned');ctx.__enter__();"
            "print('locked',flush=True);time.sleep(30)"
        )
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(REPO_ROOT / "dashboard" / "backend" / "src")
        process = subprocess.Popen(
            [sys.executable, "-B", "-X", "utf8", "-c", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            env=environment,
        )
        try:
            self.assertEqual("locked", process.stdout.readline().strip())
        finally:
            process.terminate()
            process.wait(timeout=10)
            if process.stdout:
                process.stdout.close()
            if process.stderr:
                process.stderr.close()
        result = self.store.start(
            session_id="abandoned",
            task_id="TEST-001",
            harness_id="codex",
            phase="implementing",
            next_step="retry",
        )
        self.assertEqual("abandoned", result["session_id"])

    def test_project_directory_link_is_rejected_before_external_write(self):
        self.runtime.mkdir()
        outside = self.root / "outside-directory"
        outside.mkdir()
        try:
            self.store.project_dir.symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("directory symlink creation is unavailable")
        with self.assertRaises(RuntimeSessionError):
            self.store.start(
                session_id="escape",
                task_id="TEST-001",
                harness_id="codex",
                phase="planning",
                next_step="none",
            )
        self.assertEqual([], list(outside.iterdir()))

    @unittest.skipUnless(os.name == "nt", "Windows junction behavior")
    def test_project_directory_junction_is_rejected_before_external_write(self):
        self.runtime.mkdir()
        outside = self.root / "outside-junction-target"
        outside.mkdir()
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(self.store.project_dir), str(outside)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            self.skipTest("junction creation is unavailable")
        with mock.patch.object(type(self.store.project_dir), "is_junction", new=None, create=True):
            with self.assertRaises(RuntimeSessionError):
                self.store.start(
                    session_id="junction-escape",
                    task_id="TEST-001",
                    harness_id="codex",
                    phase="planning",
                    next_step="none",
                )
        self.assertEqual([], list(outside.iterdir()))


class RuntimeCliTests(unittest.TestCase):
    def test_session_cli_round_trip_and_json_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            runtime = root / "runtime"
            (project / "docs" / "tasks").mkdir(parents=True)
            common = ["--project-root", str(project), "--runtime-root", str(runtime), "--format", "json"]
            with mock.patch("builtins.print") as output:
                code = cli_main(
                    [
                        "session",
                        "start",
                        *common,
                        "--session",
                        "cli-one",
                        "--task",
                        "TEST-001",
                        "--harness",
                        "generic",
                        "--phase",
                        "implementing",
                        "--next-step",
                        "run",
                    ]
                )
            self.assertEqual(0, code)
            self.assertEqual("cli-one", json.loads(output.call_args.args[0])["session_id"])
            self.assertEqual(2, cli_main(["session", "update", *common, "--session", "missing", "--phase", "done"]))

    def test_status_cli_uses_console_builder(self):
        with tempfile.TemporaryDirectory() as runtime:
            with mock.patch("builtins.print") as output:
                code = cli_main(
                    [
                        "status",
                        "--project-root",
                        str(REPO_ROOT),
                        "--runtime-root",
                        runtime,
                        "--skill-root",
                        str(REPO_ROOT / "skills" / "ai-dev-flow"),
                        "--format",
                        "json",
                    ]
                )
            self.assertEqual(0, code)
            self.assertEqual("adf/project-console/v1", json.loads(output.call_args.args[0])["schema_version"])


if __name__ == "__main__":
    unittest.main()
