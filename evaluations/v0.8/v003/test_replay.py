from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("replay.py")
SPEC = importlib.util.spec_from_file_location("lean_eval_v003_replay_test", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load V003 replay module")
REPLAY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPLAY)


class V003ReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = REPLAY.load_json(REPLAY.MANIFEST_PATH)
        cls.policy, cls.effective, cls.protocol = REPLAY.verify_manifest(cls.manifest)

    def test_stage_a_has_eight_policy_bound_zero_difference_records(self) -> None:
        records = REPLAY.stage_a_records(self.manifest, self.policy, self.effective)
        self.assertEqual(8, len(records))
        self.assertTrue(all(not record["difference"] for record in records))
        self.assertEqual(
            {self.manifest["policy"]["path"]},
            {record["decision_source"] for record in records},
        )

    def test_route_result_changes_when_policy_changes(self) -> None:
        sample = copy.deepcopy(self.effective["routes"][4])
        original = REPLAY.route_sample(sample, self.policy)
        changed_policy = copy.deepcopy(self.policy)
        controlled = changed_policy["routes"]["controlled"]
        controlled["task_classes"] = []
        controlled["ua_min"] = 99
        controlled["risk_flags"] = []
        controlled["requested_actions"] = []
        controlled["when_real_environment_required"] = False
        changed = REPLAY.route_sample(sample, changed_policy)
        self.assertEqual("Controlled", original["route"])
        self.assertEqual("Tracked", changed["route"])

    def test_policy_covers_required_controlled_and_tracked_risks(self) -> None:
        controlled = set(self.policy["routes"]["controlled"]["risk_flags"])
        self.assertTrue(
            {
                "architecture",
                "data_migration",
                "security",
                "release",
                "real_environment",
                "irreversible_action",
            }.issubset(controlled)
        )
        tracked = set(self.policy["review"]["Tracked"]["trigger_risk_flags"])
        self.assertTrue(
            {
                "public_api",
                "shared_component",
                "build_or_deploy_config",
                "core_execution_path",
                "core_writer_path",
                "tests_do_not_cover_oracle",
            }.issubset(tracked)
        )

    def test_controlled_review_enforcement_points_are_frozen(self) -> None:
        points = self.policy["review"]["Controlled"]["enforcement_points"]
        self.assertEqual(
            ["acceptance_recommendation", "delivery", "merge", "release"], points
        )

    def test_repair_policy_extends_only_the_progress_trace(self) -> None:
        traces = REPLAY.load_json(
            REPLAY.relative_path(self.effective["repair_trace_path"])
        )["traces"]
        self.assertEqual(
            ["ExtendRound3", "Stop"],
            [REPLAY.repair_decision(trace, self.policy) for trace in traces],
        )

    def test_protocol_explicitly_bounds_unexposed_backend_version(self) -> None:
        backend = self.protocol["backend_identity"]
        self.assertFalse(backend["exact_version_exposed_by_platform"])
        self.assertEqual("same-parent-task-session-only", backend["comparison_scope"])

    def test_migration_measurement_starts_after_authorization_amendment(self) -> None:
        self.assertEqual(
            self.manifest["authorization_commit"],
            self.manifest["migration_measurement_base_commit"],
        )
        counts = REPLAY.migration_change_counts(self.manifest)
        self.assertEqual(0, counts["historical_tasks_rewritten"])
        self.assertEqual(0, counts["required_dependencies_added"])

    def _valid_provenance(self) -> dict:
        order = self.protocol["execution_order"]
        receipts = []
        previous = None
        for sequence, mode in enumerate(order, 1):
            final_hash = f"{sequence}" * 64
            receipts.append(
                {
                    "sequence": sequence,
                    "mode": mode,
                    "canonical_agent_path": self.protocol["canonical_main_agents"][mode],
                    "spawn_receipt_path": f"evaluations/v0.8/v003/results/phase-b/receipts/{sequence:02d}-{mode}-spawn.json",
                    "spawn_receipt_sha256": f"{sequence + 3}" * 64,
                    "final_receipt_path": f"evaluations/v0.8/v003/results/phase-b/receipts/{sequence:02d}-{mode}-final.json",
                    "final_receipt_sha256": final_hash,
                    "previous_final_receipt_sha256": previous,
                }
            )
            previous = final_hash
        return {
            "schema_version": "lean-run-provenance/v1",
            "evaluation_id": self.manifest["evaluation_id"],
            "parent_task_path": "/root",
            "fork_turns": "none",
            "model_override": None,
            "reasoning_effort_override": None,
            "backend_exact_model_version": "not-exposed-by-platform",
            "execution_order": order,
            "receipts": receipts,
        }

    def test_provenance_rejects_wrong_agent_path(self) -> None:
        provenance = self._valid_provenance()
        provenance["receipts"][1]["canonical_agent_path"] = "/root/wrong"
        with self.assertRaises(REPLAY.EvalError):
            REPLAY.validate_provenance_structure(
                provenance, self.manifest, self.protocol
            )

    def test_provenance_rejects_model_override(self) -> None:
        provenance = self._valid_provenance()
        provenance["model_override"] = "some-model"
        with self.assertRaises(REPLAY.EvalError):
            REPLAY.validate_provenance_structure(
                provenance, self.manifest, self.protocol
            )

    def test_provenance_rejects_broken_receipt_chain(self) -> None:
        provenance = self._valid_provenance()
        provenance["receipts"][2]["previous_final_receipt_sha256"] = "0" * 64
        with self.assertRaises(REPLAY.EvalError):
            REPLAY.validate_provenance_structure(
                provenance, self.manifest, self.protocol
            )

    def _receipt_contents(self) -> tuple[list[dict], list[dict], list[dict]]:
        provenance = self._valid_provenance()
        spawns = []
        finals = []
        runs = []
        for receipt in provenance["receipts"]:
            sequence = receipt["sequence"]
            mode = receipt["mode"]
            canonical = receipt["canonical_agent_path"]
            workflow_paths = (
                self.manifest["phase_b"]["lite_workflow_files"]
                if mode == "lite"
                else self.effective["phase_b"][f"{mode.replace('-', '_')}_workflow_files"]
            )
            workflow_bundle = REPLAY.sha256_file_set(workflow_paths)
            main_path = f"evaluations/v0.8/v003/results/phase-b/{mode}/model-call-main.md"
            main_hash = f"{sequence + 6}" * 64
            runs.append(
                {
                    "mode": mode,
                    "workflow_inputs": [
                        {"path": path, "sha256": REPLAY.sha256_file(REPLAY.relative_path(path))}
                        for path in workflow_paths
                    ],
                    "model_call_evidence": [
                        {
                            "kind": "main",
                            "evidence_path": main_path,
                            "evidence_sha256": main_hash,
                        }
                    ],
                }
            )
            spawns.append(
                {
                    "schema_version": self.protocol["receipt_contract"]["spawn_schema"],
                    "evaluation_id": self.manifest["evaluation_id"],
                    "sequence": sequence,
                    "mode": mode,
                    "parent_task_path": "/root",
                    "tool": "collaboration.spawn_agent",
                    "request": {
                        "task_name": canonical.removeprefix("/root/"),
                        "fork_turns": "none",
                        "model_override": None,
                        "reasoning_effort_override": None,
                    },
                    "tool_result": {"task_name": canonical},
                    "previous_final_receipt_sha256": receipt[
                        "previous_final_receipt_sha256"
                    ],
                    "workflow_bundle_sha256": workflow_bundle,
                }
            )
            finals.append(
                {
                    "schema_version": self.protocol["receipt_contract"]["final_schema"],
                    "evaluation_id": self.manifest["evaluation_id"],
                    "sequence": sequence,
                    "mode": mode,
                    "canonical_task_name": canonical,
                    "completion_status": "completed",
                    "spawn_receipt_sha256": receipt["spawn_receipt_sha256"],
                    "previous_final_receipt_sha256": receipt[
                        "previous_final_receipt_sha256"
                    ],
                    "workflow_bundle_sha256": workflow_bundle,
                    "main_evidence_path": main_path,
                    "main_evidence_sha256": main_hash,
                }
            )
        return runs, spawns, finals

    def test_receipt_contents_bind_spawn_request_workflow_and_main_evidence(self) -> None:
        provenance = self._valid_provenance()
        runs, spawns, finals = self._receipt_contents()
        REPLAY.validate_receipt_contents(
            provenance, self.manifest, self.protocol, runs, spawns, finals
        )

    def test_receipt_contents_reject_fabricated_spawn_result_path(self) -> None:
        provenance = self._valid_provenance()
        runs, spawns, finals = self._receipt_contents()
        spawns[1]["tool_result"] = {"task_name": "/root/fabricated"}
        with self.assertRaises(REPLAY.EvalError):
            REPLAY.validate_receipt_contents(
                provenance, self.manifest, self.protocol, runs, spawns, finals
            )

    def test_receipt_contents_reject_unbound_final_evidence(self) -> None:
        provenance = self._valid_provenance()
        runs, spawns, finals = self._receipt_contents()
        finals[2]["main_evidence_sha256"] = "0" * 64
        with self.assertRaises(REPLAY.EvalError):
            REPLAY.validate_receipt_contents(
                provenance, self.manifest, self.protocol, runs, spawns, finals
            )


if __name__ == "__main__":
    unittest.main()
