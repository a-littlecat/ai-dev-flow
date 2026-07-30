from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from dashboard.integration.artifact_guard import (
    baseline_digest,
    baseline_paths,
    canonical_working_hashes,
    digest_from_hashes,
    verify,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST = REPO_ROOT / "dashboard" / "integration" / "accepted-artifacts.json"


class AcceptedArtifactGuardTests(unittest.TestCase):
    def test_repository_accepted_artifacts_match_frozen_baseline(self):
        report = verify(REPO_ROOT, MANIFEST)
        self.assertFalse(report["ok"], report)
        self.assertFalse(report["accepted_ok"], report)
        self.assertTrue(report["baseline_preserved"], report)
        self.assertTrue(report["candidate_consistent"], report)
        self.assertEqual(104, report["file_count"])
        self.assertEqual(100, report["expected_file_count"])
        self.assertEqual(16, len(report["candidate_paths"]))
        self.assertEqual([], report["candidate_mismatches"])

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

    def test_v2_candidate_overlay_is_exact_and_drift_is_reported(self):
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
            baseline_root, _ = baseline_digest(root, base, paths)
            target.write_text("candidate\n", encoding="utf-8")
            added = root / "accepted" / "new.txt"
            added.write_text("new\n", encoding="utf-8")
            candidate_files, missing = canonical_working_hashes(
                root,
                ("accepted/value.txt", "accepted/new.txt"),
            )
            self.assertEqual([], missing)
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema_version": "ai-dev-flow/dashboard-artifact-manifest/v2",
                        "base_commit": base,
                        "algorithm": "sha256",
                        "roots": ["accepted"],
                        "baseline_file_count": 1,
                        "baseline_root_digest": baseline_root,
                        "file_count": 1,
                        "root_digest": baseline_root,
                        "candidate": {
                            "task_id": "TEST-001",
                            "status": "review_candidate",
                            "hash_algorithm": "git-blob",
                            "file_count": 2,
                            "root_digest": digest_from_hashes(candidate_files),
                            "files": candidate_files,
                        },
                    }
                ),
                encoding="utf-8",
            )
            report = verify(root, manifest)
            self.assertFalse(report["ok"], report)
            self.assertFalse(report["accepted_ok"], report)
            self.assertTrue(report["baseline_preserved"], report)
            self.assertTrue(report["candidate_consistent"], report)
            self.assertEqual([], report["candidate_index_mismatches"])

            target.write_text("index-only\n", encoding="utf-8")
            subprocess.run(
                ["git", "-C", str(root), "add", "accepted/value.txt"],
                check=True,
            )
            target.write_text("candidate\n", encoding="utf-8")
            report = verify(root, manifest)
            self.assertFalse(report["candidate_consistent"], report)
            self.assertEqual(
                ["accepted/value.txt"],
                report["candidate_index_mismatches"],
            )

            subprocess.run(["git", "-C", str(root), "add", "accepted"], check=True)
            report = verify(root, manifest)
            self.assertTrue(report["candidate_consistent"], report)
            self.assertEqual([], report["candidate_index_mismatches"])

            base_blob = subprocess.check_output(
                ["git", "-C", str(root), "rev-parse", f"{base}:accepted/value.txt"],
                text=True,
            ).strip()
            conflict_blob = subprocess.check_output(
                ["git", "-C", str(root), "hash-object", "-w", "--stdin"],
                input="conflict\n",
                text=True,
            ).strip()
            subprocess.run(
                ["git", "-C", str(root), "update-index", "--force-remove", "accepted/value.txt"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(root), "update-index", "--index-info"],
                input=(
                    f"100644 {base_blob} 1\taccepted/value.txt\n"
                    f"100644 {candidate_files['accepted/value.txt']} 2\taccepted/value.txt\n"
                    f"100644 {conflict_blob} 3\taccepted/value.txt\n"
                ),
                text=True,
                check=True,
            )
            report = verify(root, manifest)
            self.assertFalse(report["candidate_consistent"], report)
            self.assertEqual(
                ["accepted/value.txt"],
                report["candidate_index_mismatches"],
            )

            subprocess.run(["git", "-C", str(root), "add", "accepted"], check=True)
            added.write_text("drift\n", encoding="utf-8")
            report = verify(root, manifest)
            self.assertFalse(report["ok"])
            self.assertFalse(report["candidate_consistent"])
            self.assertEqual(["accepted/new.txt"], report["candidate_mismatches"])

    def test_v2_candidate_hash_is_stable_across_autocrlf_fresh_checkouts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            subprocess.run(["git", "-C", str(source), "init"], check=True, capture_output=True)
            subprocess.run(
                ["git", "-C", str(source), "config", "user.email", "guard@example.invalid"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(source), "config", "user.name", "Guard"],
                check=True,
            )
            accepted = source / "accepted"
            accepted.mkdir()
            (accepted / "value.txt").write_bytes(b"baseline\n")
            subprocess.run(["git", "-C", str(source), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(source), "commit", "-m", "baseline"],
                check=True,
                capture_output=True,
            )
            base = subprocess.check_output(
                ["git", "-C", str(source), "rev-parse", "HEAD"],
                text=True,
            ).strip()
            paths = baseline_paths(source, base, ("accepted",))
            baseline_root, _ = baseline_digest(source, base, paths)
            (accepted / "value.txt").write_bytes(b"candidate\nline\n")
            candidate_files, _ = canonical_working_hashes(
                source,
                ("accepted/value.txt",),
            )
            manifest_payload = {
                "schema_version": "ai-dev-flow/dashboard-artifact-manifest/v2",
                "base_commit": base,
                "algorithm": "sha256",
                "roots": ["accepted"],
                "baseline_file_count": 1,
                "baseline_root_digest": baseline_root,
                "file_count": 1,
                "root_digest": baseline_root,
                "candidate": {
                    "task_id": "TEST-001",
                    "status": "review_candidate",
                    "hash_algorithm": "git-blob",
                    "file_count": 1,
                    "root_digest": digest_from_hashes(candidate_files),
                    "files": candidate_files,
                },
            }
            subprocess.run(["git", "-C", str(source), "add", "accepted/value.txt"], check=True)
            subprocess.run(
                ["git", "-C", str(source), "commit", "-m", "candidate"],
                check=True,
                capture_output=True,
            )
            for setting in ("true", "false"):
                checkout = root / f"checkout-{setting}"
                subprocess.run(
                    ["git", "clone", "--no-local", str(source), str(checkout)],
                    check=True,
                    capture_output=True,
                )
                subprocess.run(
                    ["git", "-C", str(checkout), "config", "core.autocrlf", setting],
                    check=True,
                )
                subprocess.run(
                    ["git", "-C", str(checkout), "reset", "--hard", "HEAD"],
                    check=True,
                    capture_output=True,
                )
                manifest = checkout / "manifest.json"
                manifest.write_text(json.dumps(manifest_payload), encoding="utf-8")
                report = verify(checkout, manifest)
                self.assertTrue(report["candidate_consistent"], report)

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
