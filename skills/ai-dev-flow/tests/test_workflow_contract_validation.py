import importlib.util
import json
import pathlib
import hashlib
import shutil
import sys
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "skills" / "ai-dev-flow" / "tests" / "fixtures"
MODULE = ROOT / "skills" / "ai-dev-flow" / "scripts" / "workflow_contract.py"


def load_module():
    spec = importlib.util.spec_from_file_location("workflow_contract", MODULE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class WorkflowContractValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api = load_module()
        cls.manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))

    def test_validator_oracles(self):
        for item in self.manifest["fixtures"]:
            if item["phase"] != "validator_004" or not pathlib.Path(item["input"]).suffix == ".md":
                continue
            with self.subTest(item=item["id"]):
                source = FIXTURES / item["input"]
                contract = self.api.reader.inspect_task(source, validate_filename=False)
                diagnostics = self.api._validate(contract, require_commit=False, source_file=source)
                report = type("Oracle", (), {"diagnostics": diagnostics})()
                self.assertCountEqual([d.code for d in report.diagnostics], item["expected_diagnostics"])

    def test_valid_single_and_project(self):
        source = FIXTURES / "projects" / "valid-project" / "docs" / "tasks" / "PROJECT-001.md"
        with tempfile.TemporaryDirectory() as td:
            target = pathlib.Path(td) / "PROJECT-001-copy.md"
            shutil.copyfile(source, target)
            single = self.api.WorkflowContract.inspect(target)
        self.assertEqual(single.summary.exit_code, 0)
        with tempfile.TemporaryDirectory() as td:
            project_root = pathlib.Path(td)
            task_dir = project_root / "docs" / "tasks"
            task_dir.mkdir(parents=True)
            shutil.copyfile(source, task_dir / "PROJECT-001.md")
            project = self.api.WorkflowContract.inspect(project_root)
        self.assertEqual(len(project.contracts), 1)
        self.assertEqual(len(project.projections), 1)
        self.assertIn("W_BOARD_MISSING", [d.code for d in project.diagnostics])

    def test_git_transition_and_unavailable_warning(self):
        self.assertIsNone(self.api._transition_code("Draft", "Ready", True))
        self.assertEqual(self.api._transition_code("Ready", "Draft", True), "V_ILLEGAL_TRANSITION")
        self.assertEqual(self.api._transition_code(None, "Review", False), "W_TRANSITION_UNVERIFIABLE")
        with tempfile.TemporaryDirectory() as td:
            target = pathlib.Path(td) / "TASK-UNAVAILABLE.md"
            text = (FIXTURES / "valid" / "task-a-document.md").read_text(encoding="utf-8").replace("FIX-VALID-A", "TASK-UNAVAILABLE")
            target.write_text(text, encoding="utf-8")
            with mock.patch.object(self.api.subprocess, "run", side_effect=FileNotFoundError("git unavailable")):
                report = self.api.WorkflowContract.inspect(target)
        self.assertIn("W_TRANSITION_UNVERIFIABLE", [d.code for d in report.diagnostics])
        self.assertEqual(report.summary.exit_code, 0)

    def test_git_unavailable_is_detected_once_for_a_project(self):
        source = FIXTURES / "valid" / "task-a-document.md"
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            task_dir = root / "docs" / "tasks"
            task_dir.mkdir(parents=True)
            for index in range(6):
                task_id = f"TASK-BATCH-{index:03d}"
                (task_dir / f"{task_id}.md").write_text(
                    source.read_text(encoding="utf-8").replace("FIX-VALID-A", task_id),
                    encoding="utf-8",
                )
            with mock.patch.object(
                self.api.subprocess,
                "run",
                side_effect=FileNotFoundError("git unavailable"),
            ) as git_run:
                report = self.api.WorkflowContract.inspect(root)
        self.assertEqual(1, git_run.call_count)
        self.assertEqual(
            6,
            sum(item.code == "W_TRANSITION_UNVERIFIABLE" for item in report.diagnostics),
        )

    def test_git_transition_timeout_and_invalid_utf8_fail_closed(self):
        source = FIXTURES / "valid" / "task-a-document.md"
        for failure in (
            __import__("subprocess").TimeoutExpired(["git"], 5),
            UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte"),
        ):
            with self.subTest(failure=type(failure).__name__):
                with tempfile.TemporaryDirectory() as td:
                    target = pathlib.Path(td) / "TASK-GIT-BOUNDARY.md"
                    target.write_text(
                        source.read_text(encoding="utf-8").replace(
                            "FIX-VALID-A",
                            "TASK-GIT-BOUNDARY",
                        ),
                        encoding="utf-8",
                    )
                    with mock.patch.object(
                        self.api.subprocess,
                        "run",
                        side_effect=failure,
                    ):
                        report = self.api.WorkflowContract.inspect(target)
                self.assertIn(
                    "W_TRANSITION_UNVERIFIABLE",
                    [item.code for item in report.diagnostics],
                )
                self.assertEqual(0, report.summary.exit_code)

    def test_git_transition_subprocesses_are_bounded_and_strict_utf8(self):
        completed = mock.Mock(stdout="")
        with mock.patch.object(
            self.api.subprocess,
            "run",
            return_value=completed,
        ) as run:
            self.api._run_git_text(pathlib.Path("D:/repo"), ["status"])
        kwargs = run.call_args.kwargs
        self.assertEqual(self.api.GIT_TRANSITION_TIMEOUT_SECONDS, kwargs["timeout"])
        self.assertEqual("utf-8", kwargs["encoding"])
        self.assertEqual("strict", kwargs["errors"])

        binary = mock.Mock(stdout=b"query missing\n")
        with mock.patch.object(
            self.api.subprocess,
            "run",
            return_value=binary,
        ) as run:
            self.assertEqual(
                {"query": None},
                self.api._cat_file_batch(pathlib.Path("D:/repo"), ("query",)),
            )
        self.assertEqual(
            self.api.GIT_TRANSITION_TIMEOUT_SECONDS,
            run.call_args.kwargs["timeout"],
        )

    def test_frozen_reader_cache_reuses_unchanged_text_and_invalidates_changed_text(self):
        source = (FIXTURES / "valid" / "task-a-document.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            task_dir = root / "docs" / "tasks"
            task_dir.mkdir(parents=True)
            paths = tuple(task_dir / f"TASK-CACHE-{index:03d}.md" for index in range(2))
            frozen = {}
            for index, path in enumerate(paths):
                text = source.replace("FIX-VALID-A", f"TASK-CACHE-{index:03d}")
                path.write_text(text, encoding="utf-8")
                frozen[path.absolute()] = text
            self.api._cached_reader_inspect.cache_clear()
            original = self.api.reader.inspect_text
            with mock.patch.object(
                self.api.reader,
                "inspect_text",
                wraps=original,
            ) as inspect_text, mock.patch.object(
                self.api.subprocess,
                "run",
                side_effect=FileNotFoundError("git unavailable"),
            ):
                first = self.api.WorkflowContract.inspect(
                    root,
                    frozen_task_texts=frozen,
                )
                first_calls = inspect_text.call_count
                second = self.api.WorkflowContract.inspect(
                    root,
                    frozen_task_texts=frozen,
                )
                self.assertEqual(first_calls, inspect_text.call_count)
                changed = dict(frozen)
                changed[paths[0].absolute()] = changed[paths[0].absolute()].replace(
                    "`Review`",
                    "`In Progress`",
                )
                third = self.api.WorkflowContract.inspect(
                    root,
                    frozen_task_texts=changed,
                )
            self.api._cached_reader_inspect.cache_clear()
        self.assertEqual(2, first_calls)
        self.assertEqual(first.contracts, second.contracts)
        self.assertEqual(first_calls + 1, inspect_text.call_count)
        self.assertNotEqual(first.contracts, third.contracts)

    def test_chinese_path_read_only_and_board_not_evaluated(self):
        source = FIXTURES / "valid" / "task-a-document.md"
        before = (hashlib.sha256(source.read_bytes()).hexdigest(), source.stat().st_mtime_ns)
        with tempfile.TemporaryDirectory() as td:
            target = pathlib.Path(td) / "中文目录" / "TASK-ZH.md"
            target.parent.mkdir()
            target.write_text(source.read_text(encoding="utf-8").replace("FIX-VALID-A", "TASK-ZH"), encoding="utf-8")
            report = self.api.WorkflowContract.inspect(target)
            self.assertEqual(report.summary.exit_code, 0)
        self.assertEqual(before, (hashlib.sha256(source.read_bytes()).hexdigest(), source.stat().st_mtime_ns))
        board_project = self.api.WorkflowContract.inspect(FIXTURES / "projects" / "board-drift")
        self.assertEqual(len(board_project.projections), 1)
        self.assertTrue(any(d.code in {"V_BOARD_DRIFT", "W_BOARD_ORPHAN"} for d in board_project.diagnostics))

    def canonical(self, *, lifecycle="Review", task_type="code", task_class="C", extra="", outcome=True):
        outcome_text = "" if not outcome else """\n## Outcome\n\n- Base / Diff：base=base123;diff=base123..head456\n- 隔离位置：branch/test\n- 回滚方式：revert commit\n- 修改文件：file.py\n- 验证证据：tests pass\n- Review findings：none\n"""
        return f"""# TASK-CHECK：validator\n\n## Workflow Contract\n\n- `schema_version`: `adf/v0.7.0`\n- `task_id`: `TASK-CHECK`\n- `task_type`: `{task_type}`\n- `task_class`: `{task_class}`\n- `lifecycle`: `{lifecycle}`\n- `review_status`: `Passed`\n- `ua_level`: `UA3`\n- `ua_status`: `Pending`\n- `commit_status`: `Committed`\n{extra}\n## 目标与边界\n\n- 目标：check\n- 非目标：none\n- 允许修改：file.py\n- 禁止修改：other.py\n\n## 完成标准与验证\n\n- 完成标准：passes\n- 验证命令或检查：python test\n{outcome_text}"""

    def codes_for_text(self, text):
        contract = self.api.reader.inspect_text(text, pathlib.Path("TASK-CHECK.md"))
        return [item.code for item in self.api._validate(contract, require_commit=True)]

    def v010_completion(self, requirement="Not Required", review_status="Not Run"):
        return self.canonical(lifecycle="Accepted").replace(
            "- `schema_version`: `adf/v0.7.0`",
            "- `schema_version`: `adf/v0.10.0`",
        ).replace(
            "- `review_status`: `Passed`",
            f"- `review_requirement`: `{requirement}`\n- `review_status`: `{review_status}`",
        ).replace(
            "- `ua_level`: `UA3`\n- `ua_status`: `Pending`",
            "- `ua_level`: `UA0`\n- `ua_status`: `Not Required`\n- `acceptance_authority`: `User Confirmed`",
        )

    def test_v010_review_requirement_completion_guards(self):
        allowed = self.codes_for_text(self.v010_completion())
        self.assertNotIn("V_REVIEW_GUARD", allowed)

        required = self.codes_for_text(self.v010_completion("Required", "Not Run"))
        self.assertIn("V_REVIEW_GUARD", required)

        for state in ("In Review", "Needs Fix", "Blocked"):
            with self.subTest(state=state):
                codes = self.codes_for_text(self.v010_completion("Not Required", state))
                self.assertIn("V_REVIEW_GUARD", codes)

        passed = self.codes_for_text(self.v010_completion("Required", "Passed"))
        self.assertNotIn("V_REVIEW_GUARD", passed)

    def test_v010_policy_required_inputs_reject_not_required(self):
        controlled = self.v010_completion().replace(
            "- `task_class`: `C`",
            "- `task_class`: `D`",
        )
        self.assertIn(
            "V_REVIEW_REQUIREMENT_GUARD",
            self.codes_for_text(controlled),
        )

        high_ua = self.v010_completion().replace(
            "- `ua_level`: `UA0`",
            "- `ua_level`: `UA5`",
        )
        self.assertIn(
            "V_REVIEW_REQUIREMENT_GUARD",
            self.codes_for_text(high_ua),
        )

        with tempfile.TemporaryDirectory() as td:
            source = pathlib.Path(td) / "TASK-CHECK.md"
            source.write_text(
                self.v010_completion()
                + "\n## Scheduling\n\n"
                + "- `risk_flags`: `shared_component`\n",
                encoding="utf-8",
            )
            contract = self.api.reader.inspect_task(source)
            codes = [
                item.code
                for item in self.api._validate(
                    contract,
                    require_commit=True,
                    source_file=source,
                )
            ]
        self.assertIn("V_REVIEW_REQUIREMENT_GUARD", codes)

    def test_complete_core_state_ua_delivery_and_overlay_guards(self):
        self.assertNotIn("V_STATE_GUARD", self.codes_for_text(self.canonical()))
        self.assertIn("V_STATE_GUARD", self.codes_for_text(self.canonical(outcome=False)))
        needs_fix = self.canonical(lifecycle="Needs Fix").replace("- Review findings：none", "- Review findings：none")
        self.assertIn("V_STATE_GUARD", self.codes_for_text(needs_fix))
        ua = self.canonical().replace("- `ua_status`: `Pending`", "- `ua_status`: `Passed`\n- `ua_evidence`: `#ua`\n- `acceptance_authority`: `User Confirmed`")
        self.assertIn("V_UA_GUARD", self.codes_for_text(ua))
        merged = self.canonical(lifecycle="Accepted", extra="- `merge_status`: `Merged`\n- `merge_authority`: `User Authorized`\n").replace("- `ua_status`: `Pending`", "- `ua_status`: `Passed`\n- `ua_evidence`: `#ua`\n- `acceptance_authority`: `User Confirmed`").replace("- 验证证据：tests pass", "- 验证证据：tests pass\n- UA 动作与结果：用户确认")
        self.assertIn("V_STATE_GUARD", self.codes_for_text(merged))
        overlay = self.canonical(lifecycle="In Progress", extra="- `overlays`: `real_env_signal`\n").replace("base=base123;diff=base123..head456", "base=base123")
        self.assertIn("V_STATE_GUARD", self.codes_for_text(overlay))

    def test_strict_single_value_grammar_and_ua_reverse_guards(self):
        empty_base = self.canonical(lifecycle="In Progress").replace("base=base123;diff=base123..head456", "base=")
        self.assertIn("V_STATE_GUARD", self.codes_for_text(empty_base))
        conflicting = self.canonical().replace("- Base / Diff：base=base123;diff=base123..head456", "- Base / Diff：base=base123;diff=base123..head456\n- Base / Diff：base=other;diff=other..head")
        self.assertIn("E_PARSE", self.codes_for_text(conflicting))
        pending_authority = self.canonical(extra="- `acceptance_authority`: `User Confirmed`\n")
        self.assertIn("V_UA_GUARD", self.codes_for_text(pending_authority))
        failed_authority = self.canonical(extra="- `acceptance_authority`: `Designated Acceptor Confirmed`\n").replace("- `ua_status`: `Pending`", "- `ua_status`: `Failed`\n- `ua_evidence`: `evidence-id`").replace("- Review findings：none", "- Review findings：none\n- UA 动作与结果：failed")
        self.assertIn("V_UA_GUARD", self.codes_for_text(failed_authority))
        non_ua0 = self.canonical().replace("- `ua_status`: `Pending`", "- `ua_status`: `Not Required`")
        self.assertIn("V_UA_GUARD", self.codes_for_text(non_ua0))

    def test_public_semantics_do_not_change_near_manifest(self):
        source = FIXTURES / "valid" / "task-a-document.md"
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            target = root / "task-a-document.md"
            shutil.copyfile(source, target)
            before = self.api.WorkflowContract.inspect(target)
            (root / "manifest.json").write_text(json.dumps({"fixtures": [{"input": target.name}]}), encoding="utf-8")
            after = self.api.WorkflowContract.inspect(target)
        self.assertEqual([(d.code, d.severity) for d in before.diagnostics], [(d.code, d.severity) for d in after.diagnostics])
        self.assertIn("E_TASK_ID_CONFLICT", [d.code for d in after.diagnostics])

    def test_real_git_history_legal_dirty_and_illegal(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            task = root / "docs" / "tasks" / "TASK-HIST.md"
            task.parent.mkdir(parents=True)
            subprocess_commands = [
                ["git", "init"], ["git", "config", "user.email", "test@example.invalid"], ["git", "config", "user.name", "Test"]
            ]
            for command in subprocess_commands:
                __import__("subprocess").run(command, cwd=root, check=True, capture_output=True)
            draft = self.canonical(lifecycle="Draft", task_type="document", task_class="A", outcome=False).replace("TASK-CHECK", "TASK-HIST")
            task.write_text(draft, encoding="utf-8")
            __import__("subprocess").run(["git", "add", "docs/tasks/TASK-HIST.md"], cwd=root, check=True)
            __import__("subprocess").run(["git", "commit", "-m", "draft"], cwd=root, check=True, capture_output=True)
            ready = self.canonical(lifecycle="Ready", task_type="document", task_class="A", outcome=False).replace("TASK-CHECK", "TASK-HIST")
            task.write_text(ready, encoding="utf-8")
            __import__("subprocess").run(["git", "commit", "-am", "ready"], cwd=root, check=True, capture_output=True)
            legal = self.api.WorkflowContract.inspect(task)
            self.assertNotIn("V_ILLEGAL_TRANSITION", [d.code for d in legal.diagnostics])
            task.write_text(draft, encoding="utf-8")
            dirty = self.api.WorkflowContract.inspect(task)
            self.assertIn("W_TRANSITION_UNVERIFIABLE", [d.code for d in dirty.diagnostics])
            __import__("subprocess").run(["git", "commit", "-am", "illegal"], cwd=root, check=True, capture_output=True)
            illegal = self.api.WorkflowContract.inspect(task)
            self.assertIn("V_ILLEGAL_TRANSITION", [d.code for d in illegal.diagnostics])

    def test_v010_review_cannot_regress_to_not_run_after_review_started(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            task = root / "docs" / "tasks" / "TASK-REVIEW-HIST.md"
            task.parent.mkdir(parents=True)
            for command in (
                ["git", "init"],
                ["git", "config", "user.email", "test@example.invalid"],
                ["git", "config", "user.name", "Test"],
            ):
                __import__("subprocess").run(
                    command,
                    cwd=root,
                    check=True,
                    capture_output=True,
                )
            started = self.v010_completion("Not Required", "In Review").replace(
                "TASK-CHECK",
                "TASK-REVIEW-HIST",
            ).replace("`Accepted`", "`Review`")
            task.write_text(started, encoding="utf-8")
            __import__("subprocess").run(
                ["git", "add", "docs/tasks/TASK-REVIEW-HIST.md"],
                cwd=root,
                check=True,
            )
            __import__("subprocess").run(
                ["git", "commit", "-m", "review started"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            regressed = self.v010_completion("Not Required", "Not Run").replace(
                "TASK-CHECK",
                "TASK-REVIEW-HIST",
            )
            task.write_text(regressed, encoding="utf-8")
            __import__("subprocess").run(
                ["git", "commit", "-am", "hide review"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            report = self.api.WorkflowContract.inspect(task)
            task.write_text(
                regressed.replace("- 验证证据：tests pass", "- 验证证据：tests pass again"),
                encoding="utf-8",
            )
            __import__("subprocess").run(
                ["git", "commit", "-am", "ordinary edit"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            three_step = self.api.WorkflowContract.inspect(task)
        self.assertIn(
            "V_REVIEW_REGRESSION",
            [item.code for item in report.diagnostics],
        )
        self.assertIn(
            "V_REVIEW_REGRESSION",
            [item.code for item in three_step.diagnostics],
        )

    def test_v010_review_history_rename_is_blocked_after_review_started(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            old_task = root / "docs" / "tasks" / "TASK-REVIEW-OLD.md"
            new_task = root / "docs" / "tasks" / "TASK-REVIEW-RENAMED.md"
            old_task.parent.mkdir(parents=True)
            for command in (
                ["git", "init"],
                ["git", "config", "user.email", "test@example.invalid"],
                ["git", "config", "user.name", "Test"],
            ):
                __import__("subprocess").run(
                    command, cwd=root, check=True, capture_output=True
                )
            started = self.v010_completion("Not Required", "In Review").replace(
                "TASK-CHECK", "TASK-REVIEW-OLD"
            ).replace("`Accepted`", "`Review`")
            old_task.write_text(started, encoding="utf-8")
            __import__("subprocess").run(
                ["git", "add", "."], cwd=root, check=True, capture_output=True
            )
            __import__("subprocess").run(
                ["git", "commit", "-m", "review started"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            hidden = started.replace("`Review`", "`Accepted`").replace(
                "`In Review`", "`Not Run`"
            )
            old_task.write_text(hidden, encoding="utf-8")
            __import__("subprocess").run(
                ["git", "commit", "-am", "hide review"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            __import__("subprocess").run(
                ["git", "mv", old_task.relative_to(root), new_task.relative_to(root)],
                cwd=root,
                check=True,
                capture_output=True,
            )
            hidden = hidden.replace("TASK-REVIEW-OLD", "TASK-REVIEW-RENAMED")
            new_task.write_text(hidden, encoding="utf-8")
            __import__("subprocess").run(
                ["git", "commit", "-am", "rename task"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            new_task.write_text(
                hidden.replace("- 验证证据：tests pass", "- 验证证据：tests pass again"),
                encoding="utf-8",
            )
            __import__("subprocess").run(
                ["git", "commit", "-am", "ordinary edit"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            report = self.api.WorkflowContract.inspect(new_task)
        self.assertIn(
            "V_REVIEW_HISTORY_AMBIGUOUS",
            [item.code for item in report.diagnostics],
        )

    def test_v010_review_history_copy_from_unchanged_source_is_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            old_task = root / "docs" / "tasks" / "TASK-COPY-OLD.md"
            new_task = root / "docs" / "tasks" / "TASK-COPY-NEW.md"
            old_task.parent.mkdir(parents=True)
            for command in (
                ["git", "init"],
                ["git", "config", "user.email", "test@example.invalid"],
                ["git", "config", "user.name", "Test"],
            ):
                __import__("subprocess").run(
                    command, cwd=root, check=True, capture_output=True
                )
            started = self.v010_completion("Not Required", "In Review").replace(
                "TASK-CHECK", "TASK-COPY-OLD"
            ).replace("`Accepted`", "`Review`")
            old_task.write_text(started, encoding="utf-8")
            __import__("subprocess").run(
                ["git", "add", "."], cwd=root, check=True, capture_output=True
            )
            __import__("subprocess").run(
                ["git", "commit", "-m", "review started"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            hidden = started.replace("`Review`", "`Accepted`").replace(
                "`In Review`", "`Not Run`"
            )
            old_task.write_text(hidden, encoding="utf-8")
            __import__("subprocess").run(
                ["git", "commit", "-am", "hide review"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            new_task.write_text(old_task.read_text(encoding="utf-8"), encoding="utf-8")
            __import__("subprocess").run(
                ["git", "add", "."], cwd=root, check=True, capture_output=True
            )
            __import__("subprocess").run(
                ["git", "commit", "-m", "copy unchanged task"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            copied = hidden.replace("TASK-COPY-OLD", "TASK-COPY-NEW").replace(
                "- 验证证据：tests pass", "- 验证证据：ordinary edit"
            )
            new_task.write_text(copied, encoding="utf-8")
            __import__("subprocess").run(
                ["git", "commit", "-am", "ordinary copied task edit"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            report = self.api.WorkflowContract.inspect(new_task)
        self.assertIn(
            "V_REVIEW_HISTORY_AMBIGUOUS",
            [item.code for item in report.diagnostics],
        )

    def test_v010_unrelated_sibling_rename_does_not_block_target(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            task_dir = root / "docs" / "tasks"
            target = task_dir / "TASK-TARGET.md"
            sibling = task_dir / "TASK-SIBLING.md"
            renamed = task_dir / "TASK-SIBLING-RENAMED.md"
            task_dir.mkdir(parents=True)
            for command in (
                ["git", "init"],
                ["git", "config", "user.email", "test@example.invalid"],
                ["git", "config", "user.name", "Test"],
            ):
                __import__("subprocess").run(
                    command, cwd=root, check=True, capture_output=True
                )
            target.write_text(
                self.v010_completion("Not Required", "Not Run").replace(
                    "TASK-CHECK", "TASK-TARGET"
                ),
                encoding="utf-8",
            )
            sibling.write_text("# unrelated sibling\n", encoding="utf-8")
            __import__("subprocess").run(
                ["git", "add", "."], cwd=root, check=True, capture_output=True
            )
            __import__("subprocess").run(
                ["git", "commit", "-m", "initial tasks"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            __import__("subprocess").run(
                ["git", "mv", sibling.relative_to(root), renamed.relative_to(root)],
                cwd=root,
                check=True,
                capture_output=True,
            )
            __import__("subprocess").run(
                ["git", "commit", "-m", "rename unrelated sibling"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            report = self.api.WorkflowContract.inspect(target)
        self.assertNotIn(
            "V_REVIEW_HISTORY_AMBIGUOUS",
            [item.code for item in report.diagnostics],
        )


if __name__ == "__main__":
    unittest.main()
