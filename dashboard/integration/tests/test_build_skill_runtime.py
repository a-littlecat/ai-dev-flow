from __future__ import annotations

import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dashboard.integration import build_skill_runtime as bundle


REPO_ROOT = Path(__file__).resolve().parents[3]


def _copy_inputs(target: Path) -> None:
    shutil.copytree(
        REPO_ROOT / "dashboard" / "backend" / "src",
        target / "dashboard" / "backend" / "src",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    contracts = target / "dashboard" / "contracts"
    contracts.mkdir(parents=True)
    for source in sorted((REPO_ROOT / "dashboard" / "contracts").glob("*.schema.json")):
        shutil.copyfile(source, contracts / source.name)
    frontend = target / "dashboard" / "frontend"
    frontend.mkdir(parents=True)
    for name in (
        "index.html",
        "package.json",
        "package-lock.json",
        "tsconfig.json",
        "vite.config.ts",
    ):
        shutil.copyfile(REPO_ROOT / "dashboard" / "frontend" / name, frontend / name)
    shutil.copytree(REPO_ROOT / "dashboard" / "frontend" / "src", frontend / "src")
    shutil.copytree(REPO_ROOT / "dashboard" / "frontend" / "dist", frontend / "dist")
    integration = target / "dashboard" / "integration"
    integration.mkdir(parents=True)
    shutil.copyfile(
        REPO_ROOT / "dashboard" / "integration" / "runtime.gitattributes",
        integration / "runtime.gitattributes",
    )
    skill = target / "skills" / "ai-dev-flow"
    skill.mkdir(parents=True)
    shutil.copyfile(REPO_ROOT / "skills" / "ai-dev-flow" / "VERSION", skill / "VERSION")


def _bundle_paths(root: Path) -> dict[str, object]:
    frontend = root / "dashboard" / "frontend"
    skill = root / "skills" / "ai-dev-flow"
    return {
        "REPO_ROOT": root,
        "SKILL_ROOT": skill,
        "TARGET_ROOT": skill / "dashboard",
        "BACKEND_SOURCE": root / "dashboard" / "backend" / "src" / "ai_dev_flow_dashboard",
        "CONTRACT_SOURCE": root / "dashboard" / "contracts" / "dashboard-contracts-v1.schema.json",
        "FRONTEND_ROOT": frontend,
        "FRONTEND_DIST": frontend / "dist",
        "ATTRIBUTES_SOURCE": root / "dashboard" / "integration" / "runtime.gitattributes",
        "_assert_frontend_codegen_current": lambda: None,
        "_build_frontend": lambda: None,
    }


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class SkillRuntimeBuildTests(unittest.TestCase):
    def test_installed_layout_supports_session_status_and_status_watch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            installed_skill = root / "installed" / "ai-dev-flow"
            shutil.copytree(
                REPO_ROOT / "skills" / "ai-dev-flow",
                installed_skill,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            project = root / "project"
            task_dir = project / "docs" / "tasks"
            task_dir.mkdir(parents=True)
            shutil.copyfile(
                REPO_ROOT / "docs" / "tasks" / "ADF-V010-RUNTIME-CONSOLE-BE.md",
                task_dir / "ADF-V010-RUNTIME-CONSOLE-BE.md",
            )
            subprocess.run(
                ["git", "-C", str(project), "init", "-b", "main"],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "-C", str(project), "add", "."],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(project),
                    "-c",
                    "user.name=Runtime Test",
                    "-c",
                    "user.email=runtime@example.invalid",
                    "commit",
                    "-m",
                    "runtime fixture",
                ],
                check=True,
                capture_output=True,
            )
            runtime_root = root / "runtime"
            wrapper = installed_skill / "scripts" / "adf.py"
            common = [
                "--project-root",
                str(project),
                "--runtime-root",
                str(runtime_root),
                "--format",
                "json",
            ]
            started = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-X",
                    "utf8",
                    str(wrapper),
                    "session",
                    "start",
                    *common,
                    "--session",
                    "installed-layout",
                    "--task",
                    "ADF-V010-RUNTIME-CONSOLE-BE",
                    "--harness",
                    "integration",
                    "--phase",
                    "validating",
                    "--next-step",
                    "verify installed layout",
                ],
                cwd=root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=30,
            )
            self.assertEqual(0, started.returncode, started.stderr)
            self.assertEqual("installed-layout", json.loads(started.stdout)["session_id"])
            status_command = [
                sys.executable,
                "-u",
                "-B",
                "-X",
                "utf8",
                str(wrapper),
                "status",
                *common,
                "--skill-root",
                str(installed_skill),
            ]
            status = subprocess.run(
                status_command,
                cwd=root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=30,
            )
            self.assertEqual(0, status.returncode, status.stderr)
            self.assertEqual("adf/project-console/v1", json.loads(status.stdout)["schema_version"])
            watch = subprocess.Popen(
                [*status_command, "--watch", "--interval", "0.05"],
                cwd=root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
            )
            try:
                first_line = watch.stdout.readline() if watch.stdout else ""
                self.assertEqual(
                    "adf/project-console/v1",
                    json.loads(first_line)["schema_version"],
                )
            finally:
                watch.terminate()
                watch.wait(timeout=10)
                if watch.stdout:
                    watch.stdout.close()
                if watch.stderr:
                    watch.stderr.close()

    def test_build_and_check_fail_before_bundle_work_when_codegen_is_stale(self):
        failure = subprocess.CalledProcessError(1, ["npm", "run", "codegen:check"])
        for action in (
            bundle.build,
            bundle.verify,
        ):
            with self.subTest(action=action), patch.object(
                bundle,
                "_assert_frontend_codegen_current",
                side_effect=failure,
            ):
                with self.assertRaises(subprocess.CalledProcessError):
                    action()

    def test_codegen_gate_invokes_the_read_only_frontend_check(self):
        with patch.object(bundle.subprocess, "run") as run:
            bundle._assert_frontend_codegen_current()
        run.assert_called_once_with(
            [
                "npm.cmd" if bundle.sys.platform == "win32" else "npm",
                "run",
                "codegen:check",
            ],
            cwd=bundle.FRONTEND_ROOT,
            check=True,
        )

    def test_build_always_rebuilds_frontend_and_skip_flag_is_rejected(self):
        with patch.object(bundle.subprocess, "run") as run:
            bundle._build_frontend()
        run.assert_called_once_with(
            [
                "npm.cmd" if bundle.sys.platform == "win32" else "npm",
                "run",
                "build",
                "--",
                "--sourcemap",
                "false",
            ],
            cwd=bundle.FRONTEND_ROOT,
            check=True,
        )
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                bundle._parser().parse_args(["--skip-frontend-build"])

    def test_failed_frontend_rebuild_cannot_legalize_stale_dist(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _copy_inputs(root)
            paths = _bundle_paths(root)
            with patch.multiple(bundle, **paths):
                self.assertTrue(bundle.build()["ok"])
                stale_asset = paths["FRONTEND_DIST"] / "assets" / "stale.js"
                stale_asset.write_text("new Function('return true')();\n", encoding="utf-8")
                failure = subprocess.CalledProcessError(1, ["npm", "run", "build"])
                with patch.object(bundle, "_build_frontend", side_effect=failure):
                    with self.assertRaises(subprocess.CalledProcessError):
                        bundle.build()
                with self.assertRaisesRegex(
                    bundle.BundleError,
                    "runtime manifest does not match canonical sources",
                ):
                    bundle.verify()

    def test_source_change_during_frontend_build_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _copy_inputs(root)
            paths = _bundle_paths(root)
            source = paths["FRONTEND_ROOT"] / "src" / "api" / "schema.ts"

            def mutate_source() -> None:
                source.write_text(
                    source.read_text(encoding="utf-8") + "\n",
                    encoding="utf-8",
                )

            with patch.multiple(bundle, **paths), patch.object(
                bundle,
                "_build_frontend",
                side_effect=mutate_source,
            ):
                with self.assertRaisesRegex(
                    bundle.BundleError,
                    "canonical sources changed during the frontend build",
                ):
                    bundle.build()

    def test_check_rejects_cache_pollution_and_build_removes_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _copy_inputs(root)
            paths = _bundle_paths(root)
            with patch.multiple(bundle, **paths):
                self.assertTrue(bundle.build()["ok"])
                rogue = (
                    paths["TARGET_ROOT"]
                    / "backend"
                    / "src"
                    / "ai_dev_flow_dashboard"
                    / "__pycache__"
                    / "portable.cpython-311.pyc"
                )
                rogue.parent.mkdir(parents=True)
                rogue.write_bytes(b"unregistered bytecode")
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    self.assertEqual(2, bundle.main(["--check"]))
                self.assertIn("runtime file set drifted", stderr.getvalue())
                with self.assertRaisesRegex(bundle.BundleError, "runtime file set drifted"):
                    bundle.verify()
                self.assertTrue(bundle.build()["ok"])
                self.assertFalse(rogue.exists())
                self.assertTrue(bundle.verify()["ok"])

    def test_bundle_is_identical_in_true_and_false_autocrlf_fresh_checkouts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            _copy_inputs(source)
            with patch.multiple(bundle, **_bundle_paths(source)):
                self.assertTrue(bundle.build()["ok"])
                self.assertTrue(bundle.verify()["ok"])
            subprocess.run(["git", "-C", str(source), "init"], check=True, capture_output=True)
            subprocess.run(
                ["git", "-C", str(source), "config", "user.email", "bundle@example.invalid"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(source), "config", "user.name", "Bundle"],
                check=True,
            )
            subprocess.run(["git", "-C", str(source), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(source), "commit", "-m", "bundle fixture"],
                check=True,
                capture_output=True,
            )

            results: dict[str, dict[str, bytes]] = {}
            for setting in ("true", "false"):
                checkout = root / f"checkout-{setting}"
                subprocess.run(
                    [
                        "git",
                        "-c",
                        f"core.autocrlf={setting}",
                        "clone",
                        "--no-local",
                        str(source),
                        str(checkout),
                    ],
                    check=True,
                    capture_output=True,
                )
                with patch.multiple(bundle, **_bundle_paths(checkout)):
                    self.assertTrue(bundle.verify()["ok"])
                    self.assertTrue(bundle.build()["ok"])
                    self.assertTrue(bundle.verify()["ok"])
                results[setting] = _tree_bytes(
                    checkout / "skills" / "ai-dev-flow" / "dashboard"
                )
                status = subprocess.check_output(
                    ["git", "-C", str(checkout), "status", "--porcelain=v1"],
                    text=True,
                )
                self.assertEqual("", status)

                self.assertEqual(44, len(results["true"]))
            self.assertEqual(results["true"], results["false"])


if __name__ == "__main__":
    unittest.main()
