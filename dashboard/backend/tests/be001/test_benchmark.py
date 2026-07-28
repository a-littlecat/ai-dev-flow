from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from be001 import support  # noqa: F401  # establish backend src import path
from ai_dev_flow_dashboard.core.benchmark import (
    AXES,
    BOARD_HEADER,
    BOARD_SEPARATOR,
    dataset_digest_entries,
    generate_dataset,
    generate_edges,
)


class BenchmarkOracleTests(unittest.TestCase):
    def test_edge_generator_matches_frozen_algorithm_and_is_a_dag(self):
        first = generate_edges(50, 200)
        second = generate_edges(50, 200)
        self.assertEqual(first, second)
        self.assertEqual(200, len(first))
        self.assertTrue(all(target < source for source, target, _, _ in first))
        self.assertTrue(all((axis, expected) in AXES for _, _, axis, expected in first))

    def test_dataset_entry_uses_single_nul_and_lf_bytes(self):
        entries = dataset_digest_entries({"a.txt": b"x"})
        expected = (
            b"a.txt"
            + b"\x00"
            + hashlib.sha256(b"x").hexdigest().encode("ascii")
            + b"\x0a"
        )
        self.assertEqual(expected, entries)
        self.assertEqual(1, entries.count(bytes((0x00,))))
        self.assertEqual(1, entries.count(bytes((0x0A,))))
        self.assertNotIn(b"\\0", entries)
        self.assertNotIn(b"\\n", entries)
        self.assertNotIn(b"\\x00", entries)
        self.assertNotIn(b"\\x0a", entries)

    def test_board_header_and_separator_are_lf_only(self):
        self.assertTrue(BOARD_HEADER.endswith(b"\x0a"))
        self.assertTrue(BOARD_SEPARATOR.endswith(b"\x0a"))
        self.assertNotIn(b"\r", BOARD_HEADER + BOARD_SEPARATOR)
        self.assertEqual(
            b"|---|---|---|---|---|---|---|---|---|\x0a",
            BOARD_SEPARATOR,
        )

    def test_two_full_generations_have_identical_manifest_and_source_bytes(self):
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            first = generate_dataset(first_dir, task_count=50, edge_count=200)
            second = generate_dataset(second_dir, task_count=50, edge_count=200)
            self.assertEqual(first, second)
            first_root = Path(first_dir)
            second_root = Path(second_dir)
            first_paths = sorted(
                path.relative_to(first_root).as_posix()
                for path in first_root.rglob("*")
                if path.is_file()
            )
            second_paths = sorted(
                path.relative_to(second_root).as_posix()
                for path in second_root.rglob("*")
                if path.is_file()
            )
            self.assertEqual(first_paths, second_paths)
            for relative in first_paths:
                self.assertEqual(
                    (first_root / relative).read_bytes(),
                    (second_root / relative).read_bytes(),
                    relative,
                )
            task_files = sorted((first_root / "docs" / "tasks").glob("BENCH-*.md"))
            self.assertEqual(50, len(task_files))
            self.assertTrue(all(len(path.read_bytes()) == 2048 for path in task_files))
            manifest = json.loads((first_root / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(first["dataset_sha256"], manifest["dataset_sha256"])


if __name__ == "__main__":
    unittest.main()
