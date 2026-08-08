from __future__ import annotations

import hashlib
import json
import os
import py_compile
import shutil
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

from dashboard.integration.tests import support


REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_SKILL = REPO_ROOT / "skills" / "ai-dev-flow"
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _create_external_project(root: Path, task_id: str) -> Path:
    task_dir = root / "docs" / "tasks"
    task_dir.mkdir(parents=True)
    task = support.TASK.replace("STACK-001", task_id).replace(
        "codex/stack-001",
        f"codex/{task_id.casefold()}",
    )
    board = support.BOARD.replace("STACK-001", task_id)
    (task_dir / f"{task_id}.md").write_text(
        task.format(lifecycle="Ready"),
        encoding="utf-8",
        newline="\n",
    )
    (root / "docs" / "TASK_BOARD.md").write_text(
        board.format(lifecycle="Ready"),
        encoding="utf-8",
        newline="\n",
    )
    (root / ".gitattributes").write_text("* -text\n", encoding="utf-8", newline="\n")
    support._git(root, "init", "-b", "main")
    support._git(root, "add", ".")
    support._git(root, "commit", "-m", "external dashboard fixture")
    return root


def _tree_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }


def _wait_for_states(runtime_root: Path, count: int) -> list[dict[str, object]]:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        paths = sorted(runtime_root.glob("*/*/state.json"))
        if len(paths) == count:
            return [json.loads(path.read_text(encoding="utf-8")) for path in paths]
        time.sleep(0.05)
    raise AssertionError(f"expected {count} runtime states below {runtime_root}")


def _snapshot(port: int, *, timeout: float = 30) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    url = f"http://127.0.0.1:{port}/api/v1/snapshot"
    while time.monotonic() < deadline:
        try:
            with _OPENER.open(url, timeout=2) as response:
                if response.status == 200:
                    return json.load(response)
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(0.1)
    raise AssertionError(f"snapshot did not become ready: {url}")


def _body(port: int, path: str) -> bytes:
    with _OPENER.open(f"http://127.0.0.1:{port}{path}", timeout=5) as response:
        if response.status != 200:
            raise AssertionError(f"unexpected HTTP status {response.status}: {path}")
        return response.read()


def _json_body(port: int, path: str) -> dict[str, object]:
    return json.loads(_body(port, path))


def _wait_for_revision(port: int, previous: str) -> dict[str, object]:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        snapshot = _snapshot(port, timeout=2)
        if snapshot["revision"] != previous:
            return snapshot
        time.sleep(0.1)
    raise AssertionError(f"snapshot revision did not advance on port {port}")


def _stop(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.send_signal(signal.CTRL_BREAK_EVENT)
    process.wait(timeout=15)


@unittest.skipUnless(os.name == "nt", "portable runtime uses the Windows read lease")
class PortableRuntimeIntegrationTests(unittest.TestCase):
    def test_same_project_second_instance_is_rejected_and_first_remains_available(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            installed_skill = root / "installed" / "ai-dev-flow"
            shutil.copytree(
                SOURCE_SKILL,
                installed_skill,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            project = _create_external_project(root / "project", "SINGLETON-001")
            runtime_root = root / "runtime"
            command = [
                sys.executable,
                "-X",
                "utf8",
                str(installed_skill / "scripts" / "dashboard.py"),
                "--project-root",
                str(project),
                "--port",
                "0",
                "--runtime-root",
                str(runtime_root),
                "--no-open",
            ]
            options = {
                "cwd": root,
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
                "text": True,
                "encoding": "utf-8",
                "creationflags": subprocess.CREATE_NEW_PROCESS_GROUP,
            }
            first = subprocess.Popen(command, **options)
            try:
                state = _wait_for_states(runtime_root, 1)[0]
                port = int(state["port"])
                second = subprocess.run(
                    command,
                    cwd=root,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=20,
                )
                self.assertEqual(2, second.returncode)
                self.assertIn("already running", second.stderr)
                self.assertIn(f"http://127.0.0.1:{port}/", second.stderr)
                explicit_command = list(command)
                explicit_command[explicit_command.index("--port") + 1] = str(port)
                explicit_second = subprocess.run(
                    explicit_command,
                    cwd=root,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=20,
                )
                self.assertEqual(2, explicit_second.returncode)
                self.assertIn("already running", explicit_second.stderr)
                self.assertIn(
                    f"http://127.0.0.1:{port}/",
                    explicit_second.stderr,
                )
                self.assertNotIn("address already in use", explicit_second.stderr.casefold())
                self.assertEqual(
                    ["SINGLETON-001"],
                    [item["task_id"] for item in _snapshot(port)["tasks"]],
                )
                console = _json_body(port, "/api/v1/console")
                self.assertEqual("adf/project-console/v1", console["schema_version"])
                self.assertEqual(
                    "SINGLETON-001",
                    console["human_attention"][0]["task_id"],
                )
                self.assertEqual(1, len(list(runtime_root.glob("*/*/state.json"))))
            finally:
                _stop(first)
                if first.stdout:
                    first.stdout.close()
                if first.stderr:
                    first.stderr.close()

    def test_unregistered_bundle_file_fails_startup(self):
        for kind, relative in (
            ("static", "dashboard/static/assets/unregistered.js"),
            (
                "unchecked-bytecode",
                "dashboard/backend/src/ai_dev_flow_dashboard/"
                f"__pycache__/portable.{sys.implementation.cache_tag}.pyc",
            ),
        ):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                installed_skill = root / "installed" / "ai-dev-flow"
                shutil.copytree(
                    SOURCE_SKILL,
                    installed_skill,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
                )
                project = _create_external_project(root / "project", "STARTUP-001")
                unexpected = installed_skill / relative
                unexpected.parent.mkdir(parents=True, exist_ok=True)
                if kind == "static":
                    unexpected.write_bytes(b"export {};\n")
                else:
                    portable_source = (
                        installed_skill
                        / "dashboard"
                        / "backend"
                        / "src"
                        / "ai_dev_flow_dashboard"
                        / "portable.py"
                    )
                    original = portable_source.read_bytes()
                    try:
                        portable_source.write_text(
                            "raise RuntimeError('unregistered bytecode loaded')\n",
                            encoding="utf-8",
                            newline="\n",
                        )
                        py_compile.compile(
                            str(portable_source),
                            cfile=str(unexpected),
                            doraise=True,
                            invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH,
                        )
                    finally:
                        portable_source.write_bytes(original)
                result = subprocess.run(
                    [
                        sys.executable,
                        "-X",
                        "utf8",
                        str(installed_skill / "scripts" / "dashboard.py"),
                        "--project-root",
                        str(project),
                        "--runtime-root",
                        str(root / "runtime"),
                        "--no-open",
                    ],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=20,
                )
                self.assertEqual(2, result.returncode)
                self.assertIn("file set differs from its manifest", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertNotIn("unregistered bytecode loaded", result.stderr)
                self.assertEqual([], list((root / "runtime").glob("*/*/state.json")))

    def test_two_external_projects_are_isolated_and_clean_up_independently(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            installed_skill = root / "installed" / "ai-dev-flow"
            shutil.copytree(
                SOURCE_SKILL,
                installed_skill,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            project_a = _create_external_project(root / "project-a", "ALPHA-001")
            project_b = _create_external_project(root / "project-b", "BETA-001")
            runtime_root = root / "runtime"
            skill_before = _tree_hashes(installed_skill)
            project_a_before = _tree_hashes(project_a)
            project_b_before = _tree_hashes(project_b)
            command = [
                sys.executable,
                "-X",
                "utf8",
                str(installed_skill / "scripts" / "dashboard.py"),
            ]
            child_env = os.environ.copy()
            child_env.pop("PYTHONHOME", None)
            child_env.pop("PYTHONPATH", None)
            git_executable = shutil.which("git")
            self.assertIsNotNone(git_executable)
            git_only_path = str(Path(git_executable).resolve().parent)
            child_env["PATH"] = git_only_path
            self.assertIsNone(shutil.which("node", path=git_only_path))
            options = {
                "cwd": root,
                "env": child_env,
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
                "text": True,
                "encoding": "utf-8",
                "creationflags": subprocess.CREATE_NEW_PROCESS_GROUP,
            }
            process_a = subprocess.Popen(
                [
                    *command,
                    "--project-root",
                    str(project_a),
                    "--port",
                    "0",
                    "--runtime-root",
                    str(runtime_root),
                    "--no-open",
                ],
                **options,
            )
            process_b = subprocess.Popen(
                [
                    *command,
                    "--project-root",
                    str(project_b),
                    "--port",
                    "0",
                    "--runtime-root",
                    str(runtime_root),
                    "--no-open",
                ],
                **options,
            )
            try:
                states = _wait_for_states(runtime_root, 2)
                by_project = {str(item["project_root"]): item for item in states}
                state_a = by_project[str(project_a.resolve())]
                state_b = by_project[str(project_b.resolve())]
                port_a = int(state_a["port"])
                port_b = int(state_b["port"])
                self.assertNotEqual(port_a, port_b)
                self.assertNotEqual(state_a["instance_id"], state_b["instance_id"])
                self.assertNotEqual(state_a["project_key"], state_b["project_key"])

                snapshot_a = _snapshot(port_a)
                snapshot_b = _snapshot(port_b)
                self.assertEqual(
                    ["ALPHA-001"],
                    [item["task_id"] for item in snapshot_a["tasks"]],
                )
                self.assertEqual(
                    ["BETA-001"],
                    [item["task_id"] for item in snapshot_b["tasks"]],
                )
                self.assertEqual(project_a_before, _tree_hashes(project_a))
                self.assertEqual(project_b_before, _tree_hashes(project_b))
                self.assertEqual(skill_before, _tree_hashes(installed_skill))

                static_file = next(
                    (installed_skill / "dashboard" / "static" / "assets").glob("*.js")
                )
                static_url = (
                    "/assets/"
                    + static_file.relative_to(
                        installed_skill / "dashboard" / "static" / "assets"
                    ).as_posix()
                )
                static_response = _body(port_a, static_url)
                static_original = static_file.read_bytes()
                backend_file = (
                    installed_skill
                    / "dashboard"
                    / "backend"
                    / "src"
                    / "ai_dev_flow_dashboard"
                    / "portable.py"
                )
                backend_original = backend_file.read_bytes()
                extra_static = static_file.parent / "unregistered-runtime.js"
                extra_backend = backend_file.parent / "unregistered_runtime.py"
                extra_bytecode = (
                    backend_file.parent
                    / "__pycache__"
                    / "portable.cpython-311.pyc"
                )
                extra_bytecode.parent.mkdir(parents=True, exist_ok=True)
                extra_bytecode.write_bytes(b"unregistered bytecode")
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    current_states = _wait_for_states(runtime_root, 2)
                    if all(item["restart_required"] is True for item in current_states):
                        break
                    time.sleep(0.1)
                else:
                    self.fail(
                        "running instances did not detect unregistered bytecode"
                    )
                self.assertEqual(static_response, _body(port_a, static_url))
                self.assertEqual(snapshot_a["revision"], _snapshot(port_a)["revision"])
                self.assertEqual(snapshot_b["revision"], _snapshot(port_b)["revision"])

                static_file.write_bytes(static_original + b"\n// changed after startup\n")
                backend_file.write_bytes(backend_original + b"\n# changed after startup\n")
                extra_static.write_text("export {};\n", encoding="utf-8", newline="\n")
                extra_backend.write_text("# new file\n", encoding="utf-8", newline="\n")
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    current_states = _wait_for_states(runtime_root, 2)
                    if all(item["restart_required"] is True for item in current_states):
                        break
                    time.sleep(0.1)
                else:
                    self.fail("running instances did not detect the Skill update")
                self.assertEqual(static_response, _body(port_a, static_url))
                with self.assertRaises(urllib.error.HTTPError) as missing_asset:
                    _body(port_a, "/assets/unregistered-runtime.js")
                self.assertEqual(404, missing_asset.exception.code)
                self.assertEqual(snapshot_a["revision"], _snapshot(port_a)["revision"])
                self.assertEqual(snapshot_b["revision"], _snapshot(port_b)["revision"])
                static_file.write_bytes(static_original)
                backend_file.write_bytes(backend_original)
                extra_static.unlink()
                extra_backend.unlink()
                extra_bytecode.unlink()
                extra_bytecode.parent.rmdir()

                client = socket.create_connection(("127.0.0.1", port_a), timeout=3)
                client.settimeout(10)
                client.sendall(
                    (
                        "GET /api/v1/events HTTP/1.1\r\n"
                        f"Host: 127.0.0.1:{port_a}\r\n"
                        f"Last-Event-ID: {snapshot_a['revision']}\r\n"
                        "\r\n"
                    ).encode("ascii")
                )
                task_a = project_a / "docs" / "tasks" / "ALPHA-001.md"
                board_a = project_a / "docs" / "TASK_BOARD.md"
                support.atomic_replace_bytes(
                    task_a,
                    support.TASK.replace("STACK-001", "ALPHA-001")
                    .replace("codex/stack-001", "codex/alpha-001")
                    .format(lifecycle="In Progress")
                    .encode("utf-8"),
                )
                support.atomic_replace_bytes(
                    board_a,
                    support.BOARD.replace("STACK-001", "ALPHA-001")
                    .format(lifecycle="In Progress")
                    .encode("utf-8"),
                )
                event_bytes = b""
                while b"event: snapshot" not in event_bytes:
                    event_bytes += client.recv(65536)
                client.close()
                changed_a = _snapshot(port_a)
                self.assertNotEqual(snapshot_a["revision"], changed_a["revision"])
                self.assertEqual(snapshot_b["revision"], _snapshot(port_b)["revision"])
                self.assertEqual("In Progress", changed_a["tasks"][0]["lifecycle"])
                project_a_after_user_edit = _tree_hashes(project_a)
                status_a = subprocess.run(
                    ["git", "-C", str(project_a), "status", "--porcelain=v1"],
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                ).stdout
                self.assertIn("docs/TASK_BOARD.md", status_a)
                self.assertIn("docs/tasks/ALPHA-001.md", status_a)
                head_before = changed_a["project"]["head"]
                support._git(project_a, "add", "docs/TASK_BOARD.md", "docs/tasks/ALPHA-001.md")
                support._git(project_a, "commit", "-m", "advance alpha")
                committed_a = _wait_for_revision(port_a, changed_a["revision"])
                self.assertNotEqual(head_before, committed_a["project"]["head"])
                support._git(project_a, "switch", "-c", "codex/portable-alpha")
                branched_a = _wait_for_revision(port_a, committed_a["revision"])
                self.assertEqual("codex/portable-alpha", branched_a["project"]["branch"])
                linked = root / "linked-alpha"
                support._git(
                    project_a,
                    "worktree",
                    "add",
                    str(linked),
                    "-b",
                    "codex/linked-alpha",
                )
                linked_a = _wait_for_revision(port_a, branched_a["revision"])
                self.assertEqual(2, len(linked_a["project"]["worktrees"]))
                self.assertEqual(snapshot_b["revision"], _snapshot(port_b)["revision"])
                project_a_after_user_edit = _tree_hashes(project_a)

                _stop(process_a)
                self.assertEqual(0, process_a.returncode)
                self.assertEqual(["BETA-001"], [
                    item["task_id"] for item in _snapshot(port_b)["tasks"]
                ])
                self.assertEqual(1, len(list(runtime_root.glob("*/*/state.json"))))
                self.assertEqual(project_a_after_user_edit, _tree_hashes(project_a))

                _stop(process_b)
                self.assertEqual(0, process_b.returncode)
                self.assertEqual([], list(runtime_root.glob("*/*/state.json")))
                self.assertEqual(project_b_before, _tree_hashes(project_b))
                self.assertEqual(skill_before, _tree_hashes(installed_skill))
                for port in (port_a, port_b):
                    with self.assertRaises(OSError):
                        socket.create_connection(("127.0.0.1", port), timeout=0.2)
            finally:
                for process in (process_a, process_b):
                    if process.poll() is None:
                        process.terminate()
                        process.wait(timeout=10)
                    if process.stdout:
                        process.stdout.close()
                    if process.stderr:
                        process.stderr.close()
