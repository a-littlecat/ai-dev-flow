import hashlib
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills" / "ai-dev-flow" / "scripts" / "board_generator.py"

TASK_TEMPLATE = """# {task_id}：{title}

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `{task_id}`
- `task_type`: `test`
- `task_class`: `B`
- `lifecycle`: `{lifecycle}`
- `review_status`: `Pending`
- `ua_level`: `UA3`
- `ua_status`: `Pending`

## 目标与边界

- 目标：fixture。
- 非目标：none
- 允许修改：fixture。
- 禁止修改：none

## 完成标准与验证

- 完成标准：fixture。
- 验证命令或检查：fixture。
"""

ZONE_PLACEHOLDER = "（占位，待生成）"


def load_module():
    spec = importlib.util.spec_from_file_location("board_generator", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def build_board(manual="", zone=ZONE_PLACEHOLDER, tail="", authority=None, markers=True):
    parts = [
        "# 测试看板",
        "",
        "> 任务状态表为生成区，请勿手改；生成区标记范围外为人工维护区。",
        "",
        "## 当前执行任务",
        "",
        manual or "人工区叙述。",
        "",
    ]
    if markers:
        parts += [
            "<!-- ADF-GENERATED:BEGIN -->",
            zone,
            "<!-- ADF-GENERATED:END -->",
            "",
        ]
    if authority is not None:
        parts += ["## 当前授权边界", "", authority, ""]
    parts += ["## 下一允许动作", "", tail or "人工叙述。", ""]
    return "\n".join(parts)


class ProjectFixture:
    def __init__(self, root):
        self.root = pathlib.Path(root)
        (self.root / "docs" / "tasks").mkdir(parents=True)

    def add_task(self, task_id, title, lifecycle):
        path = self.root / "docs" / "tasks" / f"{task_id}.md"
        path.write_text(
            TASK_TEMPLATE.format(task_id=task_id, title=title, lifecycle=lifecycle),
            encoding="utf-8",
        )
        return path

    def set_board(self, text):
        path = self.root / "docs" / "TASK_BOARD.md"
        path.write_text(text, encoding="utf-8")
        return path

    def snapshot(self):
        return {
            item.relative_to(self.root).as_posix(): item.read_bytes()
            for item in sorted(self.root.rglob("*"))
            if item.is_file()
        }


class BoardGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, "-B", "-X", "utf8", str(SCRIPT), *[str(item) for item in args]],
            text=True,
            encoding="utf-8",
            capture_output=True,
        )

    def make_project(self, td, tasks=(("ALPHA-001", "样例甲", "Ready"), ("SHUT-001", "样例乙", "Closed"))):
        fixture = ProjectFixture(td)
        for task_id, title, lifecycle in tasks:
            fixture.add_task(task_id, title, lifecycle)
        return fixture

    def expected_row(self, task_id, title, lifecycle):
        return (
            f"| {task_id} | {title} | B | {lifecycle} | Pending | UA3 | Pending / None | "
            f"commit=Not Recorded;merge=Not Recorded;merge_authority=None | docs/tasks/{task_id}.md |"
        )

    def test_check_read_only_and_zero_drift_after_write(self):
        with tempfile.TemporaryDirectory() as td:
            fixture = self.make_project(td)
            fixture.set_board(build_board())
            first = self.run_cli(fixture.root, "--write")
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            before = fixture.snapshot()
            result = self.run_cli(fixture.root, "--check")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("errors=0, warnings=0", result.stdout)
            self.assertEqual(fixture.snapshot(), before, "--check 必须纯只读")

    def test_check_detects_drift_without_writing(self):
        with tempfile.TemporaryDirectory() as td:
            fixture = self.make_project(td)
            board = fixture.set_board(build_board())
            before = fixture.snapshot()
            result = self.run_cli(fixture.root, "--check")
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertIn("BOARD_DRIFT", result.stdout)
            self.assertIn("expected=", result.stdout)
            self.assertIn("actual=", result.stdout)
            self.assertIn('"source_type": "generated"', result.stdout)
            self.assertEqual(fixture.snapshot(), before)
            self.assertEqual(board.read_text(encoding="utf-8"), build_board())

    def test_check_missing_markers_is_drift(self):
        with tempfile.TemporaryDirectory() as td:
            fixture = self.make_project(td)
            board = fixture.set_board(build_board(markers=False))
            before = board.read_bytes()
            result = self.run_cli(fixture.root, "--check")
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertIn("BOARD_DRIFT", result.stdout)
            self.assertIn("标记", result.stdout)
            self.assertEqual(board.read_bytes(), before)

    def test_write_byte_stable_and_manual_byte_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            fixture = self.make_project(td)
            original = build_board(
                manual="人工区保留 `ALPHA-001`，一个字节都不能动。",
                tail="人工尾部叙述。",
            )
            board = fixture.set_board(original)
            first = self.run_cli(fixture.root, "--write")
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            written_once = board.read_bytes()
            second = self.run_cli(fixture.root, "--write")
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertIn("byte-stable", second.stdout)
            self.assertEqual(board.read_bytes(), written_once, "--write 重复执行必须零 diff")

            module = self.module
            lines = original.split("\n")
            begin, end = module._locate_generated_zone(lines)
            new_lines = board.read_text(encoding="utf-8").split("\n")
            new_begin, new_end = module._locate_generated_zone(new_lines)
            self.assertEqual(new_lines[:new_begin + 1], lines[:begin + 1], "生成区前人工区必须 byte-preserve")
            self.assertEqual(new_lines[new_end:], lines[end:], "生成区后人工区必须 byte-preserve")
            zone_lines = new_lines[new_begin + 1:new_end]
            self.assertEqual(
                zone_lines,
                [
                    "| 任务 | 名称 | 等级 | 状态 | Review | UA | 验收 | 交付 | 任务文件 |",
                    "|" + "---|" * 9,
                    self.expected_row("ALPHA-001", "样例甲", "Ready"),
                    self.expected_row("SHUT-001", "样例乙", "Closed"),
                ],
            )
            check = self.run_cli(fixture.root, "--check")
            self.assertEqual(check.returncode, 0, check.stdout)
            self.assertNotIn("BOARD_DRIFT", check.stdout)

    def test_write_refuses_without_markers(self):
        with tempfile.TemporaryDirectory() as td:
            fixture = self.make_project(td)
            board = fixture.set_board(build_board(markers=False))
            before = board.read_bytes()
            result = self.run_cli(fixture.root, "--write")
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertIn("BOARD_DRIFT", result.stdout)
            self.assertEqual(board.read_bytes(), before)

    def test_manual_ref_diagnostics(self):
        with tempfile.TemporaryDirectory() as td:
            fixture = self.make_project(td)
            fixture.set_board(build_board(
                manual=(
                    "人工区提及 `SHUT-001`（已关闭）、`ALPHA-001`（进行中）与 `GHOST-009`（不存在），"
                    "另有链接 [旧任务](tasks/NOPE-002.md)。"
                ),
            ))
            write = self.run_cli(fixture.root, "--write")
            self.assertEqual(write.returncode, 0, write.stdout + write.stderr)
            result = self.run_cli(fixture.root, "--check", "--format", "json")
            self.assertEqual(result.returncode, 0, result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["summary"]["errors"], 0)
            by_code = {}
            for item in payload["diagnostics"]:
                by_code.setdefault(item["code"], []).append(item)
            stale = by_code.get("BOARD_MANUAL_STALE_REF", [])
            self.assertEqual(len(stale), 1)
            self.assertIn("SHUT-001", stale[0]["message"])
            self.assertNotIn("ALPHA-001", stale[0]["message"])
            unknown = by_code.get("BOARD_MANUAL_UNKNOWN_REF", [])
            self.assertEqual(len(unknown), 2)
            messages = " ".join(item["message"] for item in unknown)
            self.assertIn("GHOST-009", messages)
            self.assertIn("tasks/NOPE-002.md", messages)
            for item in stale + unknown:
                self.assertEqual(item["severity"], "warning")
                self.assertEqual(item["path"], "docs/TASK_BOARD.md")
                self.assertGreater(item["line"], 0)
                provenance = item["provenance"]
                self.assertEqual(len(provenance), 1)
                self.assertEqual(provenance[0]["field"], "manual_ref")
                self.assertEqual(provenance[0]["source_type"], "manual")
                self.assertEqual(provenance[0]["heading"], "当前执行任务")
                self.assertTrue(provenance[0]["raw_value"])

    def test_generated_zone_rows_do_not_trigger_manual_ref(self):
        with tempfile.TemporaryDirectory() as td:
            fixture = self.make_project(td)
            fixture.set_board(build_board())
            self.assertEqual(self.run_cli(fixture.root, "--write").returncode, 0)
            result = self.run_cli(fixture.root, "--check", "--format", "json")
            payload = json.loads(result.stdout)
            self.assertEqual(payload["diagnostics"], [], "生成区内的 Closed 任务行不得触发人工区引用诊断")

    def test_migrate_split_number_reconcile_and_idempotent(self):
        authority = "第一段授权原文。\n\n- 列表项一\n- 列表项二\n\n第三段授权原文。"
        blocks = ["第一段授权原文。", "- 列表项一\n- 列表项二", "第三段授权原文。"]
        with tempfile.TemporaryDirectory() as td:
            fixture = self.make_project(td)
            board = fixture.set_board(build_board(authority=authority))
            result = self.run_cli(fixture.root, "--migrate-authority-log", "--date", "20260810")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("AUTH-20260810-001", result.stdout)

            log = (fixture.root / "docs" / "AUTHORITY_LOG.md").read_text(encoding="utf-8")
            for offset, block in enumerate(blocks):
                entry_id = f"AUTH-20260810-{offset + 1:03d}"
                sha = hashlib.sha256(block.encode("utf-8")).hexdigest()
                self.assertIn(f"## {entry_id}", log)
                self.assertIn(f"- sha256: {sha}", log)
                self.assertIn(block, log, "原文必须逐字保留")
            entries, error = self.module._parse_authority_log(log)
            self.assertIsNone(error)
            self.assertEqual([item[2] for item in entries], blocks)

            board_text = board.read_text(encoding="utf-8")
            self.assertIn("## 当前授权边界\n\n## 下一允许动作", board_text)
            self.assertNotIn("第一段授权原文", board_text)
            self.assertIn("# 测试看板", board_text)

            before = fixture.snapshot()
            again = self.run_cli(fixture.root, "--migrate-authority-log", "--date", "20260811")
            self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
            self.assertIn("无迁移动作", again.stdout)
            self.assertEqual(fixture.snapshot(), before, "重复迁移必须幂等零 diff")

    def test_migrate_skips_already_archived_and_continues_sequence(self):
        with tempfile.TemporaryDirectory() as td:
            fixture = self.make_project(td)
            board = fixture.set_board(build_board(authority="旧段落甲。"))
            self.assertEqual(
                self.run_cli(fixture.root, "--migrate-authority-log", "--date", "20260810").returncode,
                0,
            )
            board.write_text(
                build_board(authority="旧段落甲。\n\n新段落乙。"),
                encoding="utf-8",
            )
            result = self.run_cli(fixture.root, "--migrate-authority-log", "--date", "20260811")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("跳过已归档 1 条", result.stdout)
            log = (fixture.root / "docs" / "AUTHORITY_LOG.md").read_text(encoding="utf-8")
            self.assertEqual(log.count("旧段落甲。"), 1, "已归档条目不得重复搬移")
            self.assertIn("## AUTH-20260811-001", log)
            self.assertIn("新段落乙。", log)
            self.assertIn("## 当前授权边界\n\n## 下一允许动作", board.read_text(encoding="utf-8"))

    def test_migrate_tampered_log_reports_mismatch_without_writes(self):
        with tempfile.TemporaryDirectory() as td:
            fixture = self.make_project(td)
            board = fixture.set_board(build_board(authority="原始段落。"))
            self.assertEqual(
                self.run_cli(fixture.root, "--migrate-authority-log", "--date", "20260810").returncode,
                0,
            )
            log_path = fixture.root / "docs" / "AUTHORITY_LOG.md"
            tampered = log_path.read_text(encoding="utf-8").replace("原始段落。", "篡改段落。")
            log_path.write_text(tampered, encoding="utf-8")
            board.write_text(build_board(authority="新段落。"), encoding="utf-8")
            before = fixture.snapshot()
            result = self.run_cli(fixture.root, "--migrate-authority-log", "--date", "20260811")
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertIn("ARCHIVE_MIGRATION_MISMATCH", result.stdout)
            self.assertIn("SHA256", result.stdout)
            self.assertEqual(fixture.snapshot(), before, "对账失败不得写任何文件")

    def test_migrate_atomic_failure_leaves_no_partial_state(self):
        module = self.module
        with tempfile.TemporaryDirectory() as td:
            fixture = self.make_project(td)
            board = fixture.set_board(build_board(authority="待归档段落。"))
            before = fixture.snapshot()
            with mock.patch.object(os, "replace", side_effect=OSError("boom")):
                with self.assertRaises(OSError):
                    module.migrate_authority_log(fixture.root.resolve(), "20260810")
            self.assertEqual(fixture.snapshot(), before, "替换失败时原文件必须保持原状")
            leftovers = [item for item in (fixture.root / "docs").iterdir() if item.suffix == ".tmp"]
            self.assertEqual(leftovers, [], "失败后不得残留临时文件")
            self.assertEqual(board.read_text(encoding="utf-8"), build_board(authority="待归档段落。"))

    def test_migrate_second_replace_failure_converges_on_rerun(self):
        module = self.module
        with tempfile.TemporaryDirectory() as td:
            fixture = self.make_project(td)
            fixture.set_board(build_board(authority="段落一。"))
            calls = []
            real_replace = os.replace

            def flaky_replace(src, dst):
                calls.append(dst)
                if len(calls) == 2:
                    raise OSError("boom on board")
                return real_replace(src, dst)

            with mock.patch.object(os, "replace", side_effect=flaky_replace):
                with self.assertRaises(OSError):
                    module.migrate_authority_log(fixture.root.resolve(), "20260810")
            board = fixture.root / "docs" / "TASK_BOARD.md"
            self.assertIn("段落一。", board.read_text(encoding="utf-8"), "看板替换失败必须保持原状")
            log_path = fixture.root / "docs" / "AUTHORITY_LOG.md"
            self.assertIn("段落一。", log_path.read_text(encoding="utf-8"))
            diagnostics, summary = module.migrate_authority_log(fixture.root.resolve(), "20260810")
            self.assertEqual(diagnostics, [])
            self.assertEqual(summary["migrated"], 0)
            self.assertEqual(summary["skipped"], 1, "重跑必须跳过已归档条目并收敛")
            self.assertNotIn("段落一。", board.read_text(encoding="utf-8"))
            log = log_path.read_text(encoding="utf-8")
            self.assertEqual(log.count("段落一。"), 1)

    def test_cli_json_format(self):
        with tempfile.TemporaryDirectory() as td:
            fixture = self.make_project(td)
            fixture.set_board(build_board())
            result = self.run_cli(fixture.root, "--check", "--format", "json")
            self.assertEqual(result.returncode, 2, result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["summary"]["errors"], 1)
            self.assertEqual(payload["summary"]["exit_code"], 2)
            drift = [item for item in payload["diagnostics"] if item["code"] == "BOARD_DRIFT"]
            self.assertEqual(len(drift), 1)
            self.assertEqual(drift[0]["severity"], "error")
            self.assertEqual(drift[0]["path"], "docs/TASK_BOARD.md")

    def test_cli_rejects_bad_target_and_bad_date(self):
        with tempfile.TemporaryDirectory() as td:
            result = self.run_cli(td, "--check")
            self.assertEqual(result.returncode, 2)
            self.assertIn("E_PARSE", result.stdout)
            fixture = self.make_project(pathlib.Path(td) / "p")
            fixture.set_board(build_board(authority="x。"))
            bad_date = self.run_cli(fixture.root, "--migrate-authority-log", "--date", "2026-08-10")
            self.assertEqual(bad_date.returncode, 2)
            self.assertIn("E_PARSE", bad_date.stdout)

    @unittest.skipUnless(shutil.which("git"), "需要 git")
    def test_repo_check_leaves_git_status_unchanged(self):
        def status():
            return subprocess.run(
                ["git", "-C", str(ROOT), "status", "--porcelain=v1"],
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=True,
            ).stdout

        before = status()
        self.run_cli(ROOT, "--check")
        self.assertEqual(status(), before, "--check 运行前后 Git 状态必须一致")


if __name__ == "__main__":
    unittest.main()
