from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from be002 import support  # noqa: F401
from ai_dev_flow_dashboard.git_snapshot import (
    GitCommandError,
    GitParseError,
    GitSnapshotCollector,
    SafeGitRunner,
    parse_status_z,
    parse_worktree_list_z,
)
from ai_dev_flow_dashboard.git_snapshot.parser import parse_rev_parse


class GitParserTests(unittest.TestCase):
    def test_rev_parse_requires_four_strict_utf8_lines(self):
        root = Path.cwd().resolve()
        data = (
            f"{root}\n{root / '.git'}\n{root / '.git'}\n{'a' * 40}\n"
        ).encode("utf-8")
        parsed = parse_rev_parse(data)
        self.assertEqual(root, parsed[0])
        self.assertEqual("a" * 40, parsed[3])
        with self.assertRaises(GitParseError):
            parse_rev_parse(data + b"extra\n")
        with self.assertRaises(GitParseError):
            parse_rev_parse(b"\xff")

    def test_worktree_porcelain_supports_space_unicode_detached_locked_prunable(self):
        root = Path.cwd().resolve()
        first = root / "linked space 中文"
        second = root / "detached"
        data = (
            f"worktree {first}\0HEAD {'a' * 40}\0branch refs/heads/codex/test\0\0"
            f"worktree {second}\0HEAD {'b' * 40}\0detached\0locked reason\0prunable reason\0\0"
        ).encode("utf-8")
        parsed = parse_worktree_list_z(data)
        self.assertEqual(2, len(parsed))
        self.assertEqual("refs/heads/codex/test", parsed[0].branch)
        self.assertTrue(parsed[1].detached)
        self.assertTrue(parsed[1].locked)
        self.assertTrue(parsed[1].prunable)

    def test_worktree_porcelain_rejects_duplicate_or_ambiguous_records(self):
        root = Path.cwd().resolve()
        duplicate = (
            f"worktree {root}\0HEAD {'a' * 40}\0branch refs/heads/a\0"
            "branch refs/heads/b\0\0"
        ).encode()
        with self.assertRaises(GitParseError):
            parse_worktree_list_z(duplicate)
        ambiguous = (
            f"worktree {root}\0HEAD {'a' * 40}\0branch refs/heads/a\0detached\0\0"
        ).encode()
        with self.assertRaises(GitParseError):
            parse_worktree_list_z(ambiguous)

    def test_status_collects_regular_untracked_rename_copy_and_submodule_paths(self):
        payload = (
            " M src/a.py\0"
            "?? 新目录/file name.txt\0"
            "R  src/new.py\0src/old.py\0"
            "C  src/copy.py\0src/source.py\0"
            " M modules/submodule\0"
        ).encode("utf-8")
        paths = parse_status_z(payload)
        self.assertEqual(
            {
                "src/a.py",
                "新目录/file name.txt",
                "src/new.py",
                "src/old.py",
                "src/copy.py",
                "src/source.py",
                "modules/submodule",
            },
            set(paths),
        )

    def test_status_rejects_decode_truncation_and_unsafe_paths(self):
        for payload in (
            b"\xff\0",
            b" M path",
            b"R  new\0",
            b" M ../escape\0",
            b" M C:/absolute\0",
            b" M bad\\path\0",
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(GitParseError):
                    parse_status_z(payload)


class SafeGitRunnerTests(unittest.TestCase):
    def test_runner_uses_parameter_array_no_shell_and_frozen_timeout(self):
        calls = []

        def executor(args, **kwargs):
            calls.append((args, kwargs))
            return subprocess.CompletedProcess(args, 0, b"git version 2.50.1\n", b"")

        runner = SafeGitRunner(executor=executor)
        runner.git_version()
        self.assertEqual(["git", "--version"], calls[0][0])
        self.assertIs(False, calls[0][1]["shell"])
        self.assertEqual(5.0, calls[0][1]["timeout"])
        self.assertEqual(subprocess.DEVNULL, calls[0][1]["stdin"])
        self.assertEqual("0", calls[0][1]["env"]["GIT_OPTIONAL_LOCKS"])

    def test_runner_rejects_every_non_allowlisted_command(self):
        runner = SafeGitRunner()
        with self.assertRaises(GitCommandError) as caught:
            runner._run(("git", "-C", str(Path.cwd()), "checkout", "main"))
        self.assertEqual("GIT_COMMAND_REJECTED", caught.exception.code)

    def test_timeout_is_a_stable_diagnostic_code(self):
        def executor(args, **kwargs):
            raise subprocess.TimeoutExpired(args, kwargs["timeout"])

        runner = SafeGitRunner(executor=executor)
        with self.assertRaises(GitCommandError) as caught:
            runner.git_version()
        self.assertEqual("GIT_COMMAND_TIMEOUT", caught.exception.code)


class RealGitCollectionTests(unittest.TestCase):
    def _git(self, root: Path, *args: str):
        return subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )

    def test_real_linked_worktree_git_file_unicode_dirty_and_read_only_collection(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "repo space 中文"
            linked = Path(directory) / "linked space 中文"
            base.mkdir()
            self._git(base, "init")
            self._git(base, "config", "user.name", "Dashboard Test")
            self._git(base, "config", "user.email", "dashboard@example.invalid")
            (base / "tracked.txt").write_text("base\n", encoding="utf-8")
            self._git(base, "add", "tracked.txt")
            self._git(base, "commit", "-m", "base")
            self._git(base, "worktree", "add", "-b", "codex/linked", str(linked))
            self.assertTrue((linked / ".git").is_file())
            (linked / "未跟踪 file.txt").write_text("dirty\n", encoding="utf-8")
            before = self._git(
                linked,
                "status",
                "--porcelain=v1",
                "-z",
                "--untracked-files=all",
                "--ignore-submodules=none",
            ).stdout
            collection = GitSnapshotCollector(linked).collect()
            after = self._git(
                linked,
                "status",
                "--porcelain=v1",
                "-z",
                "--untracked-files=all",
                "--ignore-submodules=none",
            ).stdout
            self.assertEqual(before, after)
            self.assertEqual("ok", collection.state)
            self.assertEqual("codex/linked", collection.branch)
            current = next(item for item in collection.worktrees if Path(item.root) == linked.resolve())
            self.assertEqual("dirty", current.dirty_state)
            self.assertEqual("unknown", current.dirty_ownership)
            self.assertIn("未跟踪 file.txt", current.dirty_paths)
            self.assertIsNotNone(collection.git_dir)
            self.assertIsNotNone(collection.common_dir)


if __name__ == "__main__":
    unittest.main()
