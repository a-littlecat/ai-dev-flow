from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from be001.support import REPO_ROOT
from ai_dev_flow_dashboard.runtime_compat import (
    RuntimeCompatibilityError,
    resolve_skill_runtime,
    runtime_bundle_fingerprint,
    validate_project_schemas,
    validate_skill_runtime,
    verify_runtime_bundle,
)
from ai_dev_flow_dashboard.portable import (
    PortableRuntimeError,
    _assert_external_runtime_root,
)


SKILL_ROOT = REPO_ROOT / "skills" / "ai-dev-flow"


class RuntimeCompatibilityTests(unittest.TestCase):
    def test_explicit_then_environment_then_entry_then_project_priority(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            explicit = validate_skill_runtime(SKILL_ROOT).root
            result = resolve_skill_runtime(
                project,
                explicit=explicit,
                entry_skill_root=root / "entry",
                environ={"AI_DEV_FLOW_SKILL_ROOT": str(root / "env")},
                home=root / "home",
            )
            self.assertEqual(explicit, result.root)

    def test_all_implicit_skill_locations_follow_documented_priority(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            locations = {
                "environment": root / "environment",
                "entry": root / "entry",
                "agents": root / "home" / ".agents" / "skills" / "ai-dev-flow",
                "codex": root / "home" / ".codex" / "skills" / "ai-dev-flow",
                "project": project / "skills" / "ai-dev-flow",
            }
            for target in locations.values():
                shutil.copytree(
                    SKILL_ROOT,
                    target,
                    ignore=shutil.ignore_patterns("dashboard", "__pycache__", "*.pyc"),
                )
            cases = (
                (
                    "environment",
                    {"AI_DEV_FLOW_SKILL_ROOT": str(locations["environment"])},
                    locations["entry"],
                ),
                ("entry", {}, locations["entry"]),
                ("agents", {}, None),
            )
            for expected, environ, entry in cases:
                with self.subTest(expected=expected):
                    result = resolve_skill_runtime(
                        project,
                        entry_skill_root=entry,
                        environ=environ,
                        home=root / "home",
                    )
                    self.assertEqual(locations[expected].resolve(), result.root)
            shutil.rmtree(locations["agents"])
            self.assertEqual(
                locations["codex"].resolve(),
                resolve_skill_runtime(
                    project,
                    environ={},
                    home=root / "home",
                ).root,
            )
            shutil.rmtree(locations["codex"])
            self.assertEqual(
                locations["project"].resolve(),
                resolve_skill_runtime(
                    project,
                    environ={},
                    home=root / "home",
                ).root,
            )

    def test_skill_version_and_workflow_schema_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scripts").mkdir(parents=True)
            (root / "schemas").mkdir()
            (root / "references").mkdir()
            (root / "SKILL.md").write_text("", encoding="utf-8")
            (root / "references" / "CORE.md").write_text("", encoding="utf-8")
            for name in ("workflow_contract.py", "_workflow_contract.py", "_task_board.py"):
                (root / "scripts" / name).write_text("", encoding="utf-8")
            (root / "VERSION").write_text("1.0.0\n", encoding="utf-8")
            (root / "schemas" / "workflow-contract.schema.json").write_text(
                json.dumps({"properties": {"schema_version": {"enum": ["adf/v0.7.0", "adf/v0.10.0"]}}}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                RuntimeCompatibilityError,
                "unsupported Skill VERSION",
            ):
                validate_skill_runtime(root)
            (root / "VERSION").write_text("0.9.9\n", encoding="utf-8")
            (root / "schemas" / "workflow-contract.schema.json").write_text(
                json.dumps({"properties": {"schema_version": {"const": "adf/v9"}}}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                RuntimeCompatibilityError,
                "unsupported Workflow Contract schema",
            ):
                validate_skill_runtime(root)

    def test_runtime_exposes_current_and_compatible_workflow_schemas(self):
        runtime = validate_skill_runtime(SKILL_ROOT)
        self.assertEqual("adf/v0.10.0", runtime.workflow_schema)
        self.assertEqual(
            ("adf/v0.7.0", "adf/v0.10.0"),
            runtime.workflow_schemas,
        )

    def test_project_schema_preflight_checks_explicit_versions_and_legacy_unknowns(self):
        runtime = validate_skill_runtime(SKILL_ROOT)
        with tempfile.TemporaryDirectory() as directory:
            tasks = Path(directory) / "docs" / "tasks"
            tasks.mkdir(parents=True)
            path = tasks / "BAD-001.md"
            path.write_text(
                "\n".join(
                    (
                        "# BAD-001：bad",
                        "",
                        "## Workflow Contract",
                        "",
                        "- `schema_version`: `adf/v9`",
                        "",
                        "## Scheduling",
                        "",
                        "- `scheduling_schema`: `ai-dev-flow/scheduling/v2`",
                    )
                ),
                encoding="utf-8",
                newline="\n",
            )
            with self.assertRaisesRegex(
                RuntimeCompatibilityError,
                "Workflow Contract schema",
            ):
                validate_project_schemas(Path(directory), runtime)
            path.write_text(
                "## Workflow Contract\n\n"
                "- `schema_version`: `adf/v0.7.0`\n\n"
                "## Scheduling\n\n"
                "- `scheduling_schema`: `ai-dev-flow/scheduling/v2`\n",
                encoding="utf-8",
                newline="\n",
            )
            with self.assertRaisesRegex(
                RuntimeCompatibilityError,
                "Scheduling schema",
            ):
                validate_project_schemas(Path(directory), runtime)
            cases = {
                "workflow missing": (
                    "## Workflow Contract\n\n"
                    "- `task_id`: `BAD-001`\n\n"
                    "## Scheduling\n\n"
                    "- `scheduling_schema`: `ai-dev-flow/scheduling/v1`\n"
                ),
                "workflow malformed": (
                    "## Workflow Contract\n\n"
                    "- schema_version: adf/v0.7.0\n\n"
                    "## Scheduling\n\n"
                    "- `scheduling_schema`: `ai-dev-flow/scheduling/v1`\n"
                ),
                "workflow duplicate": (
                    "## Workflow Contract\n\n"
                    "- `schema_version`: `adf/v0.7.0`\n"
                    "- `schema_version`: `adf/v0.7.0`\n\n"
                    "## Scheduling\n\n"
                    "- `scheduling_schema`: `ai-dev-flow/scheduling/v1`\n"
                ),
                "scheduling malformed": (
                    "## Workflow Contract\n\n"
                    "- `schema_version`: `adf/v0.7.0`\n\n"
                    "## Scheduling\n\n"
                    "- scheduling_schema: ai-dev-flow/scheduling/v1\n"
                ),
                "scheduling duplicate": (
                    "## Workflow Contract\n\n"
                    "- `schema_version`: `adf/v0.7.0`\n\n"
                    "## Scheduling\n\n"
                    "- `scheduling_schema`: `ai-dev-flow/scheduling/v1`\n"
                    "- `scheduling_schema`: `ai-dev-flow/scheduling/v1`\n"
                ),
            }
            for label, contents in cases.items():
                with self.subTest(label=label):
                    path.write_text(contents, encoding="utf-8", newline="\n")
                    with self.assertRaises(RuntimeCompatibilityError):
                        validate_project_schemas(Path(directory), runtime)
            path.write_text(
                "## Workflow Contract\n\n"
                "- `schema_version`: `adf/v0.7.0`\n\n"
                "## Scheduling\n\n"
                "- `priority`: `high`\n",
                encoding="utf-8",
                newline="\n",
            )
            validate_project_schemas(Path(directory), runtime)
            path.write_text(
                "## Workflow Contract\n\n"
                "- `schema_version`: `adf/v0.10.0`\n",
                encoding="utf-8",
                newline="\n",
            )
            validate_project_schemas(Path(directory), runtime)
            path.write_text(
                "# BAD-001 legacy task\n\n## 基本信息\n\n- 状态：完成\n",
                encoding="utf-8",
                newline="\n",
            )
            validate_project_schemas(Path(directory), runtime)
            path.write_bytes(b"\xff\xfe\x00")
            with self.assertRaisesRegex(
                RuntimeCompatibilityError,
                "cannot be read",
            ):
                validate_project_schemas(Path(directory), runtime)

    def test_current_repository_historical_tasks_pass_schema_preflight(self):
        validate_project_schemas(REPO_ROOT, validate_skill_runtime(SKILL_ROOT))

    def test_generated_skill_runtime_matches_manifest(self):
        verify_runtime_bundle(SKILL_ROOT)
        for relative, payload in (
            ("dashboard/static/assets/unregistered.js", b"export {};\n"),
            (
                "dashboard/backend/src/ai_dev_flow_dashboard/"
                "__pycache__/portable.cpython-311.pyc",
                b"unregistered bytecode",
            ),
        ):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as directory:
                installed = Path(directory) / "ai-dev-flow"
                shutil.copytree(
                    SKILL_ROOT,
                    installed,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
                )
                before = runtime_bundle_fingerprint(installed)
                extra = installed / relative
                extra.parent.mkdir(parents=True, exist_ok=True)
                extra.write_bytes(payload)
                self.assertNotEqual(before, runtime_bundle_fingerprint(installed))
                with self.assertRaisesRegex(
                    RuntimeCompatibilityError,
                    "file set differs",
                ):
                    verify_runtime_bundle(installed)

    def test_runtime_state_cannot_be_written_inside_project_or_skill(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            skill = root / "skill"
            for protected in (project, skill):
                with self.subTest(protected=protected):
                    with self.assertRaises(PortableRuntimeError):
                        _assert_external_runtime_root(
                            protected / "runtime",
                            project_root=project,
                            skill_roots=(skill,),
                        )
