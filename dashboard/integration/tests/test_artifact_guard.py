from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from dashboard.integration.artifact_guard import (
    baseline_digest,
    baseline_paths,
    verify,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST = REPO_ROOT / "dashboard" / "integration" / "accepted-artifacts.json"


class AcceptedArtifactGuardTests(unittest.TestCase):
    def test_repository_accepted_artifacts_match_frozen_baseline(self):
        report = verify(REPO_ROOT, MANIFEST)
        self.assertTrue(report["ok"], report)
        self.assertEqual(100, report["file_count"])
        self.assertEqual(report["recorded_root_digest"], report["working_root_digest"])

    def test_changed_file_is_reported_by_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "-C", str(root), "init"], check=True, capture_output=True)
            subprocess.run(
                ["git", "-C", str(root), "config", "user.email", "guard@example.invalid"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(root), "config", "user.name", "Guard"],
                check=True,
            )
            target = root / "accepted" / "value.txt"
            target.parent.mkdir()
            target.write_text("one\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(root), "commit", "-m", "baseline"],
                check=True,
                capture_output=True,
            )
            base = subprocess.check_output(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                text=True,
            ).strip()
            paths = baseline_paths(root, base, ("accepted",))
            digest, _ = baseline_digest(root, base, paths)
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema_version": "ai-dev-flow/dashboard-artifact-manifest/v1",
                        "base_commit": base,
                        "algorithm": "sha256",
                        "roots": ["accepted"],
                        "file_count": 1,
                        "root_digest": digest,
                    }
                ),
                encoding="utf-8",
            )
            target.write_text("two\n", encoding="utf-8")
            report = verify(root, manifest)
            self.assertFalse(report["ok"])
            self.assertEqual(["accepted/value.txt"], report["changed"])

            target.write_text("one\n", encoding="utf-8")
            added = root / "accepted" / "new.txt"
            added.write_text("new\n", encoding="utf-8")
            report = verify(root, manifest)
            self.assertFalse(report["ok"])
            self.assertEqual(["accepted/new.txt"], report["added"])

    def test_baseline_digest_is_independent_of_core_autocrlf(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "-C", str(root), "init"], check=True, capture_output=True)
            subprocess.run(
                ["git", "-C", str(root), "config", "user.email", "guard@example.invalid"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(root), "config", "user.name", "Guard"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(root), "config", "core.autocrlf", "false"],
                check=True,
            )
            target = root / "accepted" / "value.txt"
            target.parent.mkdir()
            target.write_bytes(b"one\ntwo\n")
            subprocess.run(["git", "-C", str(root), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(root), "commit", "-m", "baseline"],
                check=True,
                capture_output=True,
            )
            base = subprocess.check_output(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                text=True,
            ).strip()
            paths = baseline_paths(root, base, ("accepted",))

            digests = []
            for setting in ("true", "false"):
                subprocess.run(
                    ["git", "-C", str(root), "config", "core.autocrlf", setting],
                    check=True,
                )
                digests.append(baseline_digest(root, base, paths)[0])

            self.assertEqual(digests[0], digests[1])

    def test_staged_change_is_reported_when_worktree_matches_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "-C", str(root), "init"], check=True, capture_output=True)
            subprocess.run(
                ["git", "-C", str(root), "config", "user.email", "guard@example.invalid"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(root), "config", "user.name", "Guard"],
                check=True,
            )
            target = root / "accepted" / "value.txt"
            target.parent.mkdir()
            target.write_text("baseline\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(root), "commit", "-m", "baseline"],
                check=True,
                capture_output=True,
            )
            base = subprocess.check_output(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                text=True,
            ).strip()
            paths = baseline_paths(root, base, ("accepted",))
            digest, _ = baseline_digest(root, base, paths)
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema_version": "ai-dev-flow/dashboard-artifact-manifest/v1",
                        "base_commit": base,
                        "algorithm": "sha256",
                        "roots": ["accepted"],
                        "file_count": 1,
                        "root_digest": digest,
                    }
                ),
                encoding="utf-8",
            )

            target.write_text("staged change\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", str(target)], check=True)
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(root),
                    "restore",
                    "--worktree",
                    "--source=HEAD",
                    str(target),
                ],
                check=True,
            )
            self.assertEqual("baseline\n", target.read_text(encoding="utf-8"))

            report = verify(root, manifest)
            self.assertFalse(report["ok"])
            self.assertEqual(["accepted/value.txt"], report["changed"])

    def test_index_flags_cannot_hide_worktree_mismatches(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "-C", str(root), "init"], check=True, capture_output=True)
            subprocess.run(
                ["git", "-C", str(root), "config", "user.email", "guard@example.invalid"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(root), "config", "user.name", "Guard"],
                check=True,
            )
            targets = (
                root / "accepted" / "assumed.txt",
                root / "accepted" / "skipped.txt",
            )
            targets[0].parent.mkdir()
            for target in targets:
                target.write_text("baseline\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(root), "commit", "-m", "baseline"],
                check=True,
                capture_output=True,
            )
            base = subprocess.check_output(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                text=True,
            ).strip()
            paths = baseline_paths(root, base, ("accepted",))
            digest, _ = baseline_digest(root, base, paths)
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema_version": "ai-dev-flow/dashboard-artifact-manifest/v1",
                        "base_commit": base,
                        "algorithm": "sha256",
                        "roots": ["accepted"],
                        "file_count": 2,
                        "root_digest": digest,
                    }
                ),
                encoding="utf-8",
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(root),
                    "update-index",
                    "--assume-unchanged",
                    "accepted/assumed.txt",
                ],
                check=True,
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(root),
                    "update-index",
                    "--skip-worktree",
                    "accepted/skipped.txt",
                ],
                check=True,
            )
            for target in targets:
                target.write_text("hidden change\n", encoding="utf-8")

            report = verify(root, manifest)
            self.assertFalse(report["ok"])
            self.assertEqual(
                ["accepted/assumed.txt", "accepted/skipped.txt"],
                report["changed"],
            )


if __name__ == "__main__":
    unittest.main()
