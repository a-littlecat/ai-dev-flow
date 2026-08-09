from __future__ import annotations

import unittest

from be001.support import profile, provenance, task
from ai_dev_flow_dashboard.core.actions import ActionEngine
from ai_dev_flow_dashboard.core.models import DependencySpec, Diagnostic
from ai_dev_flow_dashboard.core.relationships import RelationshipEngine
from ai_dev_flow_dashboard.core.canonical import stable_text_id


class RelationshipEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = RelationshipEngine()

    def test_dependency_condition_axes_evaluate_exactly(self):
        target = task(
            "BASE-001",
            lifecycle="Accepted",
            review_status="Passed",
            ua_status="Passed",
            acceptance_authority="User Confirmed",
            commit_status="Committed",
            merge_status="Unmerged",
            merge_authority="None",
            close_authority="None",
        )
        current = task("TEST-001")
        conditions = tuple(
            DependencySpec("BASE-001", axis, expected, provenance("depends_on", expected))
            for axis, expected in (
                ("lifecycle", "Accepted"),
                ("review_status", "Passed"),
                ("ua_status", "Passed"),
                ("acceptance_authority", "User Confirmed"),
                ("commit_status", "Committed"),
                ("merge_status", "Unmerged"),
                ("merge_authority", "None"),
                ("close_authority", "None"),
            )
        )
        profiles = {
            "BASE-001": profile(scopes=("dir:dashboard/contracts",)),
            "TEST-001": profile(dependencies=conditions),
        }
        edges, diagnostics = self.engine.build((target, current), profiles)
        self.assertEqual(8, len([edge for edge in edges if edge.type == "depends_on"]))
        self.assertTrue(all(edge.condition.evaluation == "satisfied" for edge in edges))
        self.assertEqual((), diagnostics)
        first = next(edge for edge in edges if edge.condition.axis == "lifecycle")
        self.assertEqual(
            stable_text_id("depends_on", "TEST-001", "BASE-001", "lifecycle", "Accepted"),
            first.edge_id,
        )
        self.assertEqual("dependent_to_prerequisite", first.storage_direction)
        self.assertEqual("prerequisite_to_dependent", first.display_direction)

    def test_unsatisfied_dependency_is_not_promoted(self):
        target = task("BASE-001", lifecycle="Ready")
        current = task("TEST-001")
        dependency = DependencySpec(
            "BASE-001",
            "lifecycle",
            "Accepted",
            provenance("depends_on", "BASE-001#lifecycle=Accepted"),
        )
        edges, _ = self.engine.build(
            (target, current),
            {
                "BASE-001": profile(),
                "TEST-001": profile(dependencies=(dependency,)),
            },
        )
        self.assertEqual("unsatisfied", edges[0].condition.evaluation)
        self.assertEqual("Ready", edges[0].condition.actual)

    def test_dependency_and_replace_cycles_have_stable_diagnostics(self):
        a = task("A")
        b = task("B")
        dep_a = DependencySpec("B", "lifecycle", "Ready", provenance("depends_on", "B"))
        dep_b = DependencySpec("A", "lifecycle", "Ready", provenance("depends_on", "A"))
        profiles = {
            "A": profile(dependencies=(dep_a,), values={"replaces": ("B",)}),
            "B": profile(dependencies=(dep_b,), values={"replaces": ("A",)}),
        }
        edges, diagnostics = self.engine.build((a, b), profiles)
        self.assertEqual(4, len(edges))
        self.assertEqual(
            {"DEPENDENCY_CYCLE", "REPLACES_CYCLE"},
            {item.code for item in diagnostics},
        )
        again = self.engine.build((a, b), profiles)[1]
        self.assertEqual(
            [item.diagnostic_id for item in diagnostics],
            [item.diagnostic_id for item in again],
        )

    def test_thousand_node_dependency_and_replace_cycles_are_iterative(self):
        count = 1000
        nodes = tuple(task(f"TASK-{index:04d}") for index in range(count))
        for relation, code in (
            ("depends_on", "DEPENDENCY_CYCLE"),
            ("replaces", "REPLACES_CYCLE"),
        ):
            profiles = {}
            for index, node in enumerate(nodes):
                target_id = nodes[(index + 1) % count].task_id
                if relation == "depends_on":
                    profiles[node.task_id] = profile(
                        dependencies=(
                            DependencySpec(
                                target_id,
                                "lifecycle",
                                "Ready",
                                provenance("depends_on", target_id),
                            ),
                        )
                    )
                else:
                    profiles[node.task_id] = profile(
                        values={"replaces": (target_id,)},
                    )
            with self.subTest(relation=relation):
                edges, diagnostics = self.engine.build(nodes, profiles)
                self.assertEqual(count, len(edges))
                cycle = next(item for item in diagnostics if item.code == code)
                self.assertEqual(count, len(cycle.task_ids))

    def test_conflicts_are_symmetric_and_deduplicated(self):
        a = task("A")
        b = task("B")
        profiles = {
            "A": profile(values={"conflicts_with": ("B",)}),
            "B": profile(values={"conflicts_with": ("A",)}),
        }
        edges, diagnostics = self.engine.build((a, b), profiles)
        self.assertEqual(1, len(edges))
        self.assertEqual("conflicts_with", edges[0].type)
        self.assertFalse(edges[0].directional)
        self.assertEqual(("A", "B"), (edges[0].source_task_id, edges[0].target_task_id))
        self.assertEqual((), diagnostics)


class ActionEngineTests(unittest.TestCase):
    def setUp(self):
        self.relationships = RelationshipEngine()
        self.actions = ActionEngine()

    def recommendation(self, node, diagnostics=()):
        return self.actions.recommend((node,), (), diagnostics)

    def test_action_evidence_only_contains_fields_used_by_the_decision(self):
        current = task(
            "TASK",
            provenance=(
                provenance("task_id", "TASK"),
                provenance("lifecycle", "Ready"),
                provenance("write_scope", "file:src/a.py"),
            ),
        )
        item = self.actions.recommend((current,), (), ())[0]
        self.assertEqual(("lifecycle",), tuple(value.field for value in item.evidence))

    def test_action_matrix_primary_branches(self):
        cases = (
            ({"lifecycle": "Closed"}, ("none", "not_applicable", "none", "not_required", "TERMINAL_STATE")),
            ({"lifecycle": "Needs Fix"}, ("repair", "needs_authority", "repair", "unsupported", "REPAIR_AUTHORITY_UNSUPPORTED")),
            ({"lifecycle": "Draft"}, ("plan", "needs_authority", "user_decision", "missing", "PLANNING_DECISION_REQUIRED")),
            ({"lifecycle": "Ready"}, ("execute", "needs_authority", "execution", "unsupported", "EXECUTION_AUTHORITY_UNSUPPORTED")),
            ({"lifecycle": "In Progress"}, ("continue", "needs_authority", "execution", "unsupported", "CONTINUE_AUTHORITY_UNSUPPORTED")),
            ({"lifecycle": "Review", "review_status": "Pending"}, ("review", "needs_authority", "review", "unsupported", "REVIEW_AUTHORITY_UNSUPPORTED")),
            ({"lifecycle": "Review", "review_status": "Passed", "ua_status": "Pending"}, ("user_decision", "actionable", "user_decision", "not_required", "USER_DECISION_PENDING")),
            ({"lifecycle": "Review", "review_status": "Passed", "ua_status": "Passed"}, ("user_decision", "actionable", "user_decision", "not_required", "ACCEPTANCE_RECORD_PENDING")),
            ({"lifecycle": "Accepted", "commit_status": "Uncommitted"}, ("commit", "needs_authority", "commit", "unsupported", "COMMIT_AUTHORITY_UNSUPPORTED")),
            ({"lifecycle": "Accepted", "commit_status": "Committed", "merge_status": "Unmerged", "merge_authority": "User Authorized"}, ("merge", "actionable", "merge", "present", "MERGE_AUTHORITY_PRESENT")),
            ({"lifecycle": "Accepted", "commit_status": "Committed", "merge_status": "Unmerged", "merge_authority": "Denied"}, ("merge", "blocked", "merge", "denied", "MERGE_AUTHORITY_DENIED")),
            ({"lifecycle": "Accepted", "commit_status": "Committed", "merge_status": "Unmerged", "merge_authority": "None"}, ("merge", "needs_authority", "merge", "missing", "MERGE_AUTHORITY_REQUIRED")),
        )
        for overrides, expected in cases:
            with self.subTest(overrides=overrides):
                item = self.recommendation(task("TASK", **overrides))[0]
                actual = (
                    item.action_kind,
                    item.eligibility,
                    item.required_authority,
                    item.authority_state,
                    item.reason_codes[0],
                )
                self.assertEqual(expected, actual)

    def test_v010_not_required_not_run_can_reach_user_decision(self):
        item = self.recommendation(
            task(
                "TASK",
                lifecycle="Review",
                contract_schema_version="adf/v0.10.0",
                review_requirement="Not Required",
                review_state="Not Run",
                review_status="Pending",
                ua_status="Pending",
            )
        )[0]
        self.assertEqual("user_decision", item.action_kind)
        self.assertEqual("USER_DECISION_PENDING", item.reason_codes[0])

    def test_v010_required_not_run_still_requires_review(self):
        item = self.recommendation(
            task(
                "TASK",
                lifecycle="Review",
                contract_schema_version="adf/v0.10.0",
                review_requirement="Required",
                review_state="Not Run",
                review_status="Pending",
            )
        )[0]
        self.assertEqual("review", item.action_kind)
        self.assertEqual("REVIEW_AUTHORITY_UNSUPPORTED", item.reason_codes[0])

    def test_review_regression_diagnostic_blocks_not_required_acceptance_action(self):
        diagnostic = Diagnostic(
            "f" * 64,
            "V_REVIEW_REGRESSION",
            "violation",
            "review cannot return to Not Run",
            ("TASK",),
            (provenance("review_status", "Not Run"),),
        )
        item = self.recommendation(
            task(
                "TASK",
                lifecycle="Review",
                contract_schema_version="adf/v0.10.0",
                review_requirement="Not Required",
                review_state="Not Run",
                review_status="Pending",
            ),
            (diagnostic,),
        )[0]
        self.assertEqual("none", item.action_kind)
        self.assertEqual("CONTRACT_STATE_INVALID", item.reason_codes[0])

    def test_merged_returns_independent_release_and_close_recommendations(self):
        node = task(
            "TASK",
            lifecycle="Accepted",
            commit_status="Committed",
            merge_status="Merged",
            close_authority="User Authorized",
        )
        items = self.recommendation(node)
        self.assertEqual(("release", "close"), tuple(item.action_kind for item in items))
        self.assertEqual("RELEASE_AXIS_UNSUPPORTED", items[0].reason_codes[0])
        self.assertEqual("CLOSE_AUTHORITY_PRESENT", items[1].reason_codes[0])

    def test_contract_diagnostic_forces_unknown_none(self):
        diagnostic = Diagnostic(
            "d" * 64,
            "V_STATE_GUARD",
            "violation",
            "invalid state",
            ("TASK",),
            (),
        )
        item = self.recommendation(task("TASK"), (diagnostic,))[0]
        self.assertEqual("none", item.action_kind)
        self.assertEqual("unknown", item.eligibility)
        self.assertEqual(("CONTRACT_STATE_INVALID",), item.reason_codes)
        self.assertEqual(("d" * 64,), item.related_diagnostic_ids)

    def test_structurally_invalid_scheduling_forces_unknown_action(self):
        diagnostic = Diagnostic(
            "e" * 64,
            "SCHEDULING_MISSING_FIELD",
            "error",
            "missing depends_on",
            ("TASK",),
            (provenance("depends_on", None),),
        )
        item = self.recommendation(task("TASK"), (diagnostic,))[0]
        self.assertEqual(("CONTRACT_STATE_INVALID",), item.reason_codes)
        self.assertEqual("unknown", item.eligibility)

    def test_absent_and_legacy_scheduling_never_upgrade_execution_actions(self):
        for scheduling_state in ("absent", "legacy_inferred"):
            for lifecycle in ("Ready", "In Progress"):
                with self.subTest(
                    scheduling_state=scheduling_state,
                    lifecycle=lifecycle,
                ):
                    item = self.recommendation(
                        task(
                            "TASK",
                            lifecycle=lifecycle,
                            scheduling_state=scheduling_state,
                        )
                    )[0]
                    self.assertEqual("none", item.action_kind)
                    self.assertEqual("unknown", item.eligibility)

    def test_unsupported_schema_invalidates_action_input(self):
        diagnostic = Diagnostic(
            "a" * 64,
            "SCHEDULING_SCHEMA_UNSUPPORTED",
            "error",
            "unsupported schema",
            ("TASK",),
            (provenance("scheduling_schema", "ai-dev-flow/scheduling/v2"),),
        )
        item = self.recommendation(
            task("TASK", scheduling_state="invalid"),
            (diagnostic,),
        )[0]
        self.assertEqual("none", item.action_kind)
        self.assertEqual("unknown", item.eligibility)
        self.assertEqual(("CONTRACT_STATE_INVALID",), item.reason_codes)

    def test_scheduling_field_errors_only_block_action_inputs_they_affect(self):
        non_action_fields = (
            ("branch_hint", "SCHEDULING_BRANCH_INVALID"),
            ("write_scope", "SCHEDULING_PATH_INVALID"),
            ("module_locks", "SCHEDULING_LOCK_INVALID"),
            ("risk_flags", "SCHEDULING_RISK_UNKNOWN"),
        )
        for index, (field, code) in enumerate(non_action_fields, start=1):
            with self.subTest(field=field):
                diagnostic = Diagnostic(
                    f"{index}" * 64,
                    code,
                    "error",
                    field,
                    ("TASK",),
                    (provenance(field, "invalid"),),
                )
                item = self.recommendation(task("TASK"), (diagnostic,))[0]
                self.assertEqual("execute", item.action_kind)
                self.assertEqual("needs_authority", item.eligibility)

        dependency_diagnostic = Diagnostic(
            "5" * 64,
            "DEPENDENCY_EXPECTED_INVALID",
            "error",
            "invalid dependency expected value",
            ("TASK",),
            (provenance("depends_on", "BASE#lifecycle=Finished"),),
        )
        item = self.recommendation(task("TASK"), (dependency_diagnostic,))[0]
        self.assertEqual("execute", item.action_kind)
        self.assertEqual("unknown", item.eligibility)
        self.assertEqual(("DEPENDENCY_STATE_UNKNOWN",), item.reason_codes)
        self.assertEqual(("5" * 64,), item.related_diagnostic_ids)

    def test_dependency_unknown_and_unsatisfied_are_separate(self):
        current = task("CURRENT")
        unknown_target = task("UNKNOWN", lifecycle=None)
        blocked_target = task("BLOCKED", lifecycle="Ready")
        dependencies = (
            DependencySpec("UNKNOWN", "lifecycle", "Accepted", provenance("depends_on", "u")),
            DependencySpec("BLOCKED", "lifecycle", "Accepted", provenance("depends_on", "b")),
        )
        edges, graph_diagnostics = self.relationships.build(
            (current, unknown_target, blocked_target),
            {
                "CURRENT": profile(dependencies=dependencies),
                "UNKNOWN": profile(),
                "BLOCKED": profile(),
            },
        )
        items = self.actions.recommend((current, unknown_target, blocked_target), edges, graph_diagnostics)
        current_action = next(item for item in items if item.task_id == "CURRENT")
        self.assertEqual("DEPENDENCY_STATE_UNKNOWN", current_action.reason_codes[0])
        self.assertEqual(("UNKNOWN",), current_action.blocking_task_ids)

    def test_target_contract_errors_make_dependency_unknown_and_prevent_action_upgrade(self):
        cases = (
            (
                "target state guard",
                "V_STATE_GUARD",
                "violation",
                (provenance("lifecycle", "Accepted"),),
            ),
            (
                "axis conflict",
                "E_LEGACY_CONFLICT",
                "error",
                (provenance("lifecycle", "Accepted / Ready"),),
            ),
            (
                "missing provenance",
                "E_UNKNOWN_VALUE",
                "error",
                (),
            ),
        )
        for index, (name, code, severity, diagnostic_provenance) in enumerate(cases, start=1):
            with self.subTest(name=name):
                diagnostic_id = f"{index}" * 64
                diagnostic = Diagnostic(
                    diagnostic_id,
                    code,
                    severity,
                    name,
                    ("TARGET",),
                    diagnostic_provenance,
                )
                target = task(
                    "TARGET",
                    lifecycle="Accepted",
                    diagnostic_ids=(diagnostic_id,),
                )
                current = task("CURRENT")
                dependency = DependencySpec(
                    "TARGET",
                    "lifecycle",
                    "Accepted",
                    provenance("depends_on", "TARGET#lifecycle=Accepted"),
                )
                edges, graph_diagnostics = self.relationships.build(
                    (current, target),
                    {
                        "CURRENT": profile(dependencies=(dependency,)),
                        "TARGET": profile(),
                    },
                    (diagnostic,),
                )
                dependency_edge = next(edge for edge in edges if edge.type == "depends_on")
                self.assertEqual("Accepted", dependency_edge.condition.actual)
                self.assertEqual("unknown", dependency_edge.condition.evaluation)
                actions = self.actions.recommend(
                    (current, target),
                    edges,
                    (diagnostic,) + graph_diagnostics,
                )
                current_action = next(item for item in actions if item.task_id == "CURRENT")
                self.assertEqual("execute", current_action.action_kind)
                self.assertEqual("unknown", current_action.eligibility)
                self.assertEqual(("DEPENDENCY_STATE_UNKNOWN",), current_action.reason_codes)

    def test_dependency_cycle_forces_unknown_action(self):
        a = task("A")
        b = task("B")
        dep_a = DependencySpec("B", "lifecycle", "Ready", provenance("depends_on", "B"))
        dep_b = DependencySpec("A", "lifecycle", "Ready", provenance("depends_on", "A"))
        profiles = {
            "A": profile(dependencies=(dep_a,)),
            "B": profile(dependencies=(dep_b,)),
        }
        edges, diagnostics = self.relationships.build((a, b), profiles)
        items = self.actions.recommend((a, b), edges, diagnostics)
        self.assertTrue(all(item.reason_codes == ("CONTRACT_STATE_INVALID",) for item in items))

    def test_dependency_cycle_propagates_unknown_to_downstream_dependency_action(self):
        a = task("A")
        b = task("B")
        c = task("C")
        profiles = {
            "A": profile(
                dependencies=(
                    DependencySpec("B", "lifecycle", "Ready", provenance("depends_on", "B")),
                )
            ),
            "B": profile(
                dependencies=(
                    DependencySpec("A", "lifecycle", "Ready", provenance("depends_on", "A")),
                )
            ),
            "C": profile(
                dependencies=(
                    DependencySpec("A", "lifecycle", "Ready", provenance("depends_on", "A")),
                )
            ),
        }
        edges, diagnostics = self.relationships.build((a, b, c), profiles)
        c_to_a = next(
            edge
            for edge in edges
            if edge.source_task_id == "C" and edge.target_task_id == "A"
        )
        self.assertEqual("unknown", c_to_a.condition.evaluation)
        items = self.actions.recommend((a, b, c), edges, diagnostics)
        c_action = next(item for item in items if item.task_id == "C")
        self.assertEqual("execute", c_action.action_kind)
        self.assertEqual("unknown", c_action.eligibility)
        self.assertEqual(("DEPENDENCY_STATE_UNKNOWN",), c_action.reason_codes)

    def test_replaces_cycle_does_not_overblock_unrelated_execution_action(self):
        a = task("A")
        b = task("B")
        profiles = {
            "A": profile(values={"replaces": ("B",)}),
            "B": profile(values={"replaces": ("A",)}),
        }
        edges, diagnostics = self.relationships.build((a, b), profiles)
        self.assertEqual({"REPLACES_CYCLE"}, {item.code for item in diagnostics})
        items = self.actions.recommend((a, b), edges, diagnostics)
        self.assertTrue(all(item.action_kind == "execute" for item in items))
        self.assertTrue(all(item.eligibility == "needs_authority" for item in items))


if __name__ == "__main__":
    unittest.main()
