from __future__ import annotations

import unittest

from be001.support import REPO_ROOT, frozen, profile, provenance, scheduling_text, task, worktree
from ai_dev_flow_dashboard.core.models import DependencySpec, Diagnostic
from ai_dev_flow_dashboard.core.parallel import ParallelEngine
from ai_dev_flow_dashboard.core.relationships import RelationshipEngine
from ai_dev_flow_dashboard.core.scheduling import SchedulingParser


class ParallelEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = ParallelEngine()
        self.relationships = RelationshipEngine()

    def assess(
        self,
        left,
        right,
        left_profile,
        right_profile,
        *,
        edges=(),
        worktrees=True,
        diagnostics=(),
    ):
        evidence = (
            {left.task_id: worktree(left.task_id), right.task_id: worktree(right.task_id)}
            if worktrees
            else {}
        )
        return self.engine.assess(
            (left, right),
            {left.task_id: left_profile, right.task_id: right_profile},
            edges,
            evidence,
            diagnostics,
        )[0]

    def test_clean_disjoint_pair_is_candidate_and_never_authority(self):
        left = task("LEFT", write_scope=("file:src/a.py",))
        right = task("RIGHT", write_scope=("file:src/b.py",))
        item = self.assess(
            left,
            right,
            profile(scopes=("file:src/a.py",)),
            profile(scopes=("file:src/b.py",)),
        )
        self.assertEqual("candidate", item.result)
        self.assertEqual(("ALL_CHECKS_PASSED",), item.reason_codes)
        self.assertTrue(item.requires_user_confirmation)

    def test_parallel_intent_tri_value_pair_matrix_is_fail_closed(self):
        for left_intent in ("serial", "unknown", "consider"):
            for right_intent in ("serial", "unknown", "consider"):
                with self.subTest(left=left_intent, right=right_intent):
                    left = task("LEFT", parallel_intent=left_intent, write_scope=("file:src/a.py",))
                    right = task("RIGHT", parallel_intent=right_intent, write_scope=("file:src/b.py",))
                    item = self.assess(
                        left,
                        right,
                        profile(
                            scopes=("file:src/a.py",),
                            values={"parallel_intent": left_intent},
                        ),
                        profile(
                            scopes=("file:src/b.py",),
                            values={"parallel_intent": right_intent},
                        ),
                    )
                    expected = (
                        "must_serial"
                        if "serial" in {left_intent, right_intent}
                        else "unknown"
                        if "unknown" in {left_intent, right_intent}
                        else "candidate"
                    )
                    self.assertEqual(expected, item.result)
                    self.assertEqual(
                        expected == "candidate",
                        "ALL_CHECKS_PASSED" in item.reason_codes,
                    )

    def test_segment_prefix_is_not_string_prefix(self):
        left = task("LEFT", write_scope=("dir:src/a",))
        right = task("RIGHT", write_scope=("dir:src/ab",))
        item = self.assess(
            left,
            right,
            profile(scopes=("dir:src/a",)),
            profile(scopes=("dir:src/ab",)),
        )
        self.assertEqual("candidate", item.result)

    def test_scope_module_dependency_and_conflict_matrix(self):
        left = task("LEFT")
        right = task("RIGHT")
        cases = []
        cases.append(
            (
                "scope",
                profile(scopes=("dir:src",)),
                profile(scopes=("file:src/b.py",)),
                (),
                "WRITE_SCOPE_OVERLAP",
            )
        )
        cases.append(
            (
                "lock",
                profile(scopes=("file:a",), locks=("shared",)),
                profile(scopes=("file:b",), locks=("shared",)),
                (),
                "MODULE_LOCK_OVERLAP",
            )
        )
        dependency = DependencySpec("RIGHT", "lifecycle", "Ready", provenance("depends_on", "RIGHT"))
        dependency_profiles = {
            "LEFT": profile(scopes=("file:a",), dependencies=(dependency,)),
            "RIGHT": profile(scopes=("file:b",)),
        }
        dependency_edges, _ = self.relationships.build((left, right), dependency_profiles)
        cases.append(
            (
                "dependency",
                dependency_profiles["LEFT"],
                dependency_profiles["RIGHT"],
                dependency_edges,
                "DEPENDENCY_PATH_PRESENT",
            )
        )
        conflict_profiles = {
            "LEFT": profile(scopes=("file:a",), values={"conflicts_with": ("RIGHT",)}),
            "RIGHT": profile(scopes=("file:b",)),
        }
        conflict_edges, _ = self.relationships.build((left, right), conflict_profiles)
        cases.append(
            (
                "conflict",
                conflict_profiles["LEFT"],
                conflict_profiles["RIGHT"],
                conflict_edges,
                "EXPLICIT_CONFLICT",
            )
        )
        for name, left_profile, right_profile, edges, reason in cases:
            with self.subTest(name=name):
                case_left = task("LEFT", module_locks=("shared",)) if name == "lock" else left
                case_right = task("RIGHT", module_locks=("shared",)) if name == "lock" else right
                item = self.assess(case_left, case_right, left_profile, right_profile, edges=edges)
                self.assertEqual("must_serial", item.result)
                self.assertIn(reason, item.hard_conflicts)

    def test_projection_only_overlap_does_not_become_hard_conflict(self):
        left = task("LEFT", write_scope=("file:docs/TASK_BOARD.md",))
        right = task("RIGHT", write_scope=("file:docs/TASK_BOARD.md",))
        item = self.assess(
            left,
            right,
            profile(scopes=("file:docs/TASK_BOARD.md",)),
            profile(scopes=("file:docs/TASK_BOARD.md",)),
        )
        self.assertEqual("candidate", item.result)
        self.assertEqual(("PROJECTION_ONLY_CONFLICT",), item.projection_conflicts)
        self.assertIn("ALL_CHECKS_PASSED", item.reason_codes)

    def test_architecture_and_high_ua_are_serial(self):
        architecture = self.assess(
            task("LEFT", risk_flags=("architecture",)),
            task("RIGHT"),
            profile(scopes=("file:a",), values={"risk_flags": ("architecture",)}),
            profile(scopes=("file:b",)),
        )
        self.assertEqual("must_serial", architecture.result)
        self.assertIn("HIGH_RISK_SERIAL", architecture.hard_conflicts)
        high_ua = self.assess(
            task("LEFT", ua_level="UA6"),
            task("RIGHT"),
            profile(scopes=("file:a",)),
            profile(scopes=("file:b",)),
        )
        self.assertEqual("must_serial", high_ua.result)
        self.assertIn("UA_LEVEL_SERIAL", high_ua.hard_conflicts)

    def test_missing_legacy_or_dirty_worktree_evidence_is_unknown(self):
        left = task("LEFT")
        right = task("RIGHT")
        legacy = self.assess(
            left,
            right,
            profile(state="legacy_inferred"),
            profile(scopes=("file:b",)),
        )
        self.assertEqual("unknown", legacy.result)
        dirty = self.engine.assess(
            (left, right),
            {
                "LEFT": profile(scopes=("file:a",)),
                "RIGHT": profile(scopes=("file:b",)),
            },
            (),
            {
                "LEFT": worktree("LEFT", dirty_state="dirty", dirty_paths=("a",)),
                "RIGHT": worktree("RIGHT"),
            },
        )[0]
        self.assertEqual("unknown", dirty.result)
        self.assertIn("DIRTY_OWNERSHIP_UNKNOWN", dirty.reason_codes)

    def test_uniquely_owned_dirty_worktree_can_remain_a_candidate(self):
        left = task("LEFT", write_scope=("file:a",))
        right = task("RIGHT", write_scope=("file:b",))
        item = self.engine.assess(
            (left, right),
            {
                "LEFT": profile(scopes=("file:a",)),
                "RIGHT": profile(scopes=("file:b",)),
            },
            (),
            {
                "LEFT": worktree(
                    "LEFT",
                    dirty_state="dirty",
                    dirty_paths=("a",),
                    dirty_ownership="owned_by_task",
                ),
                "RIGHT": worktree("RIGHT"),
            },
        )[0]
        self.assertEqual("candidate", item.result)
        self.assertIn("ALL_CHECKS_PASSED", item.reason_codes)

    def test_unowned_or_inconsistent_dirty_evidence_fails_closed(self):
        for dirty_state, ownership in (
            ("dirty", "unowned"),
            ("dirty", "unknown"),
            ("clean", "owned_by_task"),
        ):
            with self.subTest(dirty_state=dirty_state, ownership=ownership):
                item = self.engine.assess(
                    (task("LEFT"), task("RIGHT")),
                    {
                        "LEFT": profile(scopes=("file:a",)),
                        "RIGHT": profile(scopes=("file:b",)),
                    },
                    (),
                    {
                        "LEFT": worktree(
                            "LEFT",
                            dirty_state=dirty_state,
                            dirty_paths=("a",) if dirty_state == "dirty" else (),
                            dirty_ownership=ownership,
                        ),
                        "RIGHT": worktree("RIGHT"),
                    },
                )[0]
                self.assertEqual("unknown", item.result)
                self.assertIn("DIRTY_OWNERSHIP_UNKNOWN", item.reason_codes)

    def test_invalid_parallel_input_field_is_unknown_not_candidate(self):
        left = task("LEFT")
        right = task("RIGHT")
        invalid_scope = profile(
            scopes=(),
            values={"write_scope": None},
        )
        item = self.assess(
            left,
            right,
            invalid_scope,
            profile(scopes=("file:b",)),
        )
        self.assertEqual("unknown", item.result)
        self.assertNotIn("ALL_CHECKS_PASSED", item.reason_codes)

    def test_real_parser_unsupported_schema_cannot_be_parallel_candidate(self):
        invalid = SchedulingParser(REPO_ROOT).parse(
            frozen(
                scheduling_text(
                    scheduling_schema="ai-dev-flow/scheduling/v2",
                    depends_on="none",
                    parent="none",
                )
            ),
            "LEFT",
            {"LEFT", "RIGHT"},
        )
        self.assertEqual("invalid", invalid.state)
        item = self.assess(
            task("LEFT"),
            task("RIGHT"),
            invalid,
            profile(scopes=("file:src/b.py",)),
        )
        self.assertEqual("unknown", item.result)
        self.assertNotIn("ALL_CHECKS_PASSED", item.reason_codes)

    def test_task_core_diagnostic_blocks_parallel_candidate(self):
        diagnostic = Diagnostic(
            "d" * 64,
            "V_STATE_GUARD",
            "violation",
            "invalid state",
            ("LEFT",),
            (provenance("lifecycle", "Ready"),),
        )
        item = self.assess(
            task("LEFT", diagnostic_ids=(diagnostic.diagnostic_id,)),
            task("RIGHT"),
            profile(scopes=("file:src/a.py",)),
            profile(scopes=("file:src/b.py",)),
            diagnostics=(diagnostic,),
        )
        self.assertEqual("unknown", item.result)
        self.assertNotIn("ALL_CHECKS_PASSED", item.reason_codes)

    def test_unknown_task_diagnostic_id_fails_parallel_closed(self):
        item = self.assess(
            task("LEFT", diagnostic_ids=("e" * 64,)),
            task("RIGHT"),
            profile(scopes=("file:src/a.py",)),
            profile(scopes=("file:src/b.py",)),
        )
        self.assertEqual("unknown", item.result)

    def test_core_enum_diagnostics_block_parallel_candidate(self):
        for field in ("task_type", "task_class"):
            with self.subTest(field=field):
                diagnostic = Diagnostic(
                    ("a" if field == "task_type" else "b") * 64,
                    "E_UNKNOWN_VALUE",
                    "error",
                    f"invalid {field}",
                    ("LEFT",),
                    (provenance(field, "invalid"),),
                )
                item = self.assess(
                    task("LEFT", diagnostic_ids=(diagnostic.diagnostic_id,)),
                    task("RIGHT"),
                    profile(scopes=("file:src/a.py",)),
                    profile(scopes=("file:src/b.py",)),
                    diagnostics=(diagnostic,),
                )
                self.assertEqual("unknown", item.result)
                self.assertNotIn("ALL_CHECKS_PASSED", item.reason_codes)

    def test_replaces_cycle_diagnostic_does_not_overblock_parallel(self):
        diagnostic = Diagnostic(
            "c" * 64,
            "REPLACES_CYCLE",
            "error",
            "replacement graph cycle",
            ("LEFT",),
            (provenance("replaces", "RIGHT"),),
        )
        item = self.assess(
            task("LEFT", diagnostic_ids=(diagnostic.diagnostic_id,)),
            task("RIGHT"),
            profile(scopes=("file:src/a.py",)),
            profile(scopes=("file:src/b.py",)),
            diagnostics=(diagnostic,),
        )
        self.assertEqual("candidate", item.result)
        self.assertIn("ALL_CHECKS_PASSED", item.reason_codes)

    def test_shared_worktree_is_serial(self):
        left = task("LEFT")
        right = task("RIGHT")
        item = self.engine.assess(
            (left, right),
            {
                "LEFT": profile(scopes=("file:a",)),
                "RIGHT": profile(scopes=("file:b",)),
            },
            (),
            {
                "LEFT": worktree("LEFT", root="D:/wt/shared"),
                "RIGHT": worktree("RIGHT", root="D:/wt/shared"),
            },
        )[0]
        self.assertEqual("must_serial", item.result)
        self.assertIn("WORKTREE_SHARED", item.hard_conflicts)

    def test_large_pair_set_is_bounded_and_reports_truncation(self):
        tasks = tuple(task(f"TASK-{index:03d}") for index in range(100))
        profiles = {
            item.task_id: profile(scopes=(f"file:src/{item.task_id}.py",))
            for item in tasks
        }
        assessments, diagnostics = self.engine.assess_with_diagnostics(
            tasks,
            profiles,
            (),
            {},
        )
        self.assertEqual(256, len(assessments))
        self.assertEqual(
            ["PARALLEL_ASSESSMENT_TRUNCATED"],
            [item.code for item in diagnostics],
        )
        self.assertTrue(all(item.result == "unknown" for item in assessments))

    def _consumer_fixture(
        self,
        *,
        omit_axis: str | None = None,
        left_contract_scope: bool = False,
        owner_diagnostic: Diagnostic | None = None,
    ):
        owner = task(
            "OWNER",
            lifecycle="Accepted",
            review_status="Passed",
            ua_status="Passed",
            commit_status="Committed",
            risk_flags=("public_api",),
            write_scope=("dir:dashboard/contracts",),
            diagnostic_ids=(
                (owner_diagnostic.diagnostic_id,)
                if owner_diagnostic is not None
                else ()
            ),
        )
        left = task(
            "LEFT",
            task_class="D",
            risk_flags=("public_api", "shared_component"),
            write_scope=(("file:dashboard/contracts/change.json",) if left_contract_scope else ("file:backend/a.py",)),
        )
        right = task(
            "RIGHT",
            risk_flags=("public_api",),
            write_scope=("file:frontend/b.ts",),
        )
        required = (
            ("commit_status", "Committed"),
            ("lifecycle", "Accepted"),
            ("review_status", "Passed"),
            ("ua_status", "Passed"),
        )
        dependencies = tuple(
            DependencySpec("OWNER", axis, expected, provenance("depends_on", axis))
            for axis, expected in required
            if axis != omit_axis
        )
        profiles = {
            "OWNER": profile(scopes=("dir:dashboard/contracts",), values={"risk_flags": ("public_api",)}),
            "LEFT": profile(
                scopes=(
                    ("file:dashboard/contracts/change.json",)
                    if left_contract_scope
                    else ("file:backend/a.py",)
                ),
                dependencies=dependencies,
                values={"risk_flags": ("public_api", "shared_component")},
            ),
            "RIGHT": profile(
                scopes=("file:frontend/b.ts",),
                dependencies=dependencies,
                values={"risk_flags": ("public_api",)},
            ),
        }
        edges, _ = self.relationships.build((owner, left, right), profiles)
        evidence = {
            "OWNER": worktree("OWNER"),
            "LEFT": worktree("LEFT"),
            "RIGHT": worktree("RIGHT"),
        }
        diagnostics = (owner_diagnostic,) if owner_diagnostic is not None else ()
        assessments = self.engine.assess(
            (owner, left, right),
            profiles,
            edges,
            evidence,
            diagnostics,
        )
        pair = next(item for item in assessments if (item.left_task_id, item.right_task_id) == ("LEFT", "RIGHT"))
        return pair

    def test_accepted_contract_consumer_exception_is_narrow_and_fail_closed(self):
        complete = self._consumer_fixture()
        self.assertEqual("candidate", complete.result)
        missing_axis = self._consumer_fixture(omit_axis="ua_status")
        self.assertEqual("unknown", missing_axis.result)
        contract_writer = self._consumer_fixture(left_contract_scope=True)
        self.assertEqual("must_serial", contract_writer.result)
        self.assertIn("SHARED_HIGH_RISK_SURFACE", contract_writer.hard_conflicts)

    def test_accepted_contract_owner_diagnostic_blocks_exception(self):
        diagnostic = Diagnostic(
            "d" * 64,
            "E_LEGACY_CONFLICT",
            "error",
            "conflicting commit status",
            ("OWNER",),
            (provenance("commit_status", "Committed"),),
        )
        pair = self._consumer_fixture(owner_diagnostic=diagnostic)
        self.assertEqual("unknown", pair.result)
        self.assertNotIn("ALL_CHECKS_PASSED", pair.reason_codes)


if __name__ == "__main__":
    unittest.main()
