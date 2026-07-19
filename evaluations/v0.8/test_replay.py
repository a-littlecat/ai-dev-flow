import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import replay


class ReplayContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = replay.load_json(replay.MANIFEST_PATH)

    def test_manifest_and_stage_a_are_fully_bound(self):
        replay.verify_manifest(self.manifest)
        records = replay.stage_a_records(self.manifest)
        self.assertEqual(8, len(records))
        self.assertTrue(all(not record["difference"] for record in records))
        by_id = {record["sample_id"]: record for record in records}
        self.assertEqual(
            "Blocked", by_id["CONTROLLED-HIST-001"]["actual"]["safety_gate"]
        )
        self.assertEqual(
            "Blocked", by_id["CONTROLLED-HIST-002"]["actual"]["safety_gate"]
        )

    def test_denied_or_unknown_authority_blocks_action(self):
        sample = dict(self.manifest["routes"][0])
        for authority in ("Denied", "Unknown"):
            sample["action_authority"] = authority
            self.assertEqual("Blocked", replay.route_sample(sample)["safety_gate"])

    def test_new_p0_stops_even_when_total_findings_decrease(self):
        trace = {
            "scope_hashes": ["same", "same", "same"],
            "finding_snapshots": [
                {
                    "round": 0,
                    "findings": [
                        {"id": "F-1", "severity": "P1"},
                        {"id": "F-2", "severity": "P1"},
                        {"id": "F-3", "severity": "P1"},
                    ],
                },
                {
                    "round": 1,
                    "findings": [
                        {"id": "NEW-P0", "severity": "P0"},
                        {"id": "F-3", "severity": "P1"},
                    ],
                },
                {
                    "round": 2,
                    "findings": [{"id": "NEW-P0", "severity": "P0"}],
                },
            ],
            "validation_scores": [6, 8, 10],
            "dependencies_frozen": True,
            "authority_frozen": True,
            "root_cause_known": True,
            "round_3_target": "close NEW-P0",
            "reviewer_capable": True,
            "repairer_capable": True,
            "within_cost_boundary": True,
            "external_side_effect": False,
        }
        self.assertEqual("Stop", replay.repair_decision(trace))

    def test_severity_regression_and_invalid_rounds_stop(self):
        trace = replay.load_json(
            replay.relative_path(self.manifest["repair_trace_path"])
        )["traces"][0]
        changed = json.loads(json.dumps(trace))
        changed["finding_snapshots"][1]["findings"][0]["severity"] = "P0"
        self.assertEqual("Stop", replay.repair_decision(changed))
        changed = json.loads(json.dumps(trace))
        changed["finding_snapshots"][2]["round"] = 3
        self.assertEqual("Stop", replay.repair_decision(changed))

    def test_old_forged_phase_b_shape_is_rejected(self):
        payload = {
            "schema_version": "lean-phase-b-runs/v1",
            "evaluation_id": self.manifest["evaluation_id"],
            "execution_order": ["no-skill", "lite", "full"],
            "runs": [{"mode": mode} for mode in ("no-skill", "lite", "full")],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "runs.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(replay.EvalError):
                replay.score_phase_b(self.manifest, path)

    def test_wrong_baseline_hash_and_empty_oracle_are_rejected(self):
        run = self._base_run("no-skill", 1)
        run["baseline_sha256"] = "0" * 64
        with self.assertRaises(replay.EvalError):
            replay.normalize_run(self.manifest, run, "no-skill", 1)

        run = self._base_run("no-skill", 1)
        run["completion_criteria"] = {}
        workflow = {
            "paths": self.manifest["phase_b"]["no_skill_workflow_files"],
            "bundle_sha256": "a" * 64,
            "workflow_input_bytes": 1,
            "workflow_input_nonempty_lines": 1,
        }
        with mock.patch.object(replay, "normalize_workflow_inputs", return_value=workflow), mock.patch.object(
            replay,
            "normalize_model_calls",
            return_value={"model_calls": 1, "reviewer_calls": 0},
        ), mock.patch.object(replay, "verify_bound_artifact", return_value=Path("evidence")):
            with self.assertRaises(replay.EvalError):
                replay.normalize_run(self.manifest, run, "no-skill", 1)

    def test_negative_metric_is_rejected(self):
        with self.assertRaises(replay.EvalError):
            replay.require_nonnegative_int(-1, "test")

    def test_multiple_main_calls_in_one_run_are_rejected(self):
        bundle = "a" * 64
        calls = [
            {
                "id": f"main-{index}",
                "kind": "main",
                "evidence_path": f"evaluations/v0.8/results/phase-b/main-{index}.txt",
                "evidence_sha256": "b" * 64,
                "input_manifest_sha256": bundle,
            }
            for index in (1, 2)
        ]
        with mock.patch.object(replay, "verify_bound_artifact", return_value=Path("evidence")):
            with self.assertRaises(replay.EvalError):
                replay.normalize_model_calls(calls, bundle, "lite")

    def _base_run(self, mode, sequence):
        brief = self.manifest["phase_b"]["benchmark_brief"]
        return {
            "run_id": f"{self.manifest['evaluation_id']}-{mode}",
            "mode": mode,
            "sequence": sequence,
            "model_identity": "current-model-version",
            "baseline_sha256": self.manifest["phase_b"]["benchmark_baseline_sha256"],
            "brief_sha256": self.manifest["phase_b"]["artifact_sha256"][brief],
            "workflow_inputs": [{"path": "unused", "sha256": "a" * 64}],
            "model_call_evidence": [],
            "blocking_questions": [],
            "test_exit": 0,
            "test_passed": 4,
            "test_total": 4,
            "output_path": "evaluations/v0.8/results/phase-b/output.py",
            "output_sha256": "a" * 64,
            "verification_evidence_path": "evaluations/v0.8/results/phase-b/verify.txt",
            "verification_evidence_sha256": "b" * 64,
            "completion_criteria": {
                key: True for key in self.manifest["phase_b"]["completion_criteria"]
            },
            "scope_violation": False,
            "sensitive_data_exposed": False,
        }


if __name__ == "__main__":
    unittest.main()
