import copy
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[3]
SKILL_ROOT = ROOT / "skills" / "ai-dev-flow"
SCRIPT = SKILL_ROOT / "scripts" / "repair_gate.py"
CORE = SKILL_ROOT / "references" / "CORE.md"

SPEC = importlib.util.spec_from_file_location("repair_gate", SCRIPT)
repair_gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(repair_gate)
POLICY = repair_gate.load_policy(CORE)


def seal(record):
    record["receipt_hash"] = repair_gate.receipt_hash(record)
    return record


def base_chain():
    return {
        "repair_chain_id": "chain-001",
        "finding_ids": ["F-001"],
        "closure_contract_hash": repair_gate.canonical_hash(["criterion-1"]),
        "allowed_files_hash": repair_gate.canonical_hash(["src/a.py"]),
    }


def progress(red_to_green=True):
    return {
        "target_finding_id": "F-001",
        "closure_before": {"criterion-1": "RED"},
        "closure_after": {"criterion-1": "GREEN" if red_to_green else "RED"},
        "blocking_findings_before": ["F-001"],
        "blocking_findings_after": ["F-001"],
        "severity_before": {"F-001": "P1"},
        "severity_after": {"F-001": "P1"},
        "evidence_vector": ["unit", "integration"],
        "evidence_before": ["unit"],
        "evidence_after": ["unit", "integration"],
        "round_3_target": "close criterion-1",
    }


def review_receipt(chain, subject_id, subject_hash, decision="Needs Fix", progress_value=None):
    record = {
        "review_id": f"review-{subject_id.lower()}",
        "reviewer_ref": f"review:isolated-readonly:{subject_id.lower()}",
        "context_isolated": True,
        "write_isolated": True,
        "decision": decision,
        "subject_id": subject_id,
        "subject_hash": subject_hash,
        "repair_chain_digest": repair_gate.canonical_hash(chain),
        "policy_digest": repair_gate.policy_digest(POLICY),
        "finding_ids": chain["finding_ids"],
    }
    if progress_value is not None:
        record["progress"] = progress_value
    return seal(record)


def authority_receipt(chain, next_attempt_id="ER-1", authorized_attempt_ids=None):
    record = {
        "authority_id": f"authority-{next_attempt_id.lower()}",
        "source_kind": "user_message",
        "source_ref": f"conversation:thread-001#message-{next_attempt_id.lower()}",
        "source_text_sha256": repair_gate.canonical_hash(f"authorize {next_attempt_id}"),
        "repair_chain_digest": repair_gate.canonical_hash(chain),
        "closure_contract_hash": chain["closure_contract_hash"],
        "allowed_files_hash": chain["allowed_files_hash"],
        "target_finding_ids": chain["finding_ids"],
        "next_attempt_id_at_issue": next_attempt_id,
        "target": f"close {','.join(chain['finding_ids'])}",
    }
    if authorized_attempt_ids is not None:
        record["authorized_attempt_ids"] = authorized_attempt_ids
    return seal(record)


def base_ledger(**updates):
    chain = base_chain()
    trigger = review_receipt(
        chain,
        "TRIGGER",
        chain["closure_contract_hash"],
    )
    value = {
        "schema_version": "ai-dev-flow/repair-ledger-v1",
        "requested_mode": "AutoRepair",
        "current_task_id": "TASK-001",
        "current_model": "model-a",
        "repair_chain": chain,
        "safety": {
            "dependencies_frozen": True,
            "authority_frozen": True,
            "root_cause_known": True,
            "reviewer_capable": True,
            "repairer_capable": True,
            "within_cost_boundary": True,
            "external_side_effect": False,
        },
        "trigger_review": trigger,
        "authority_records": [],
        "attempts": [],
        "history_anchor": {
            "attempt_count": 0,
            "head_receipt_hash": trigger["receipt_hash"],
            "source_ref": "task:docs/tasks/TASK-001.md#repair-chain-ledger",
            "source_text_sha256": repair_gate.canonical_hash("initial ledger"),
        },
    }
    value.update(updates)
    return value


def add_attempt(
    ledger,
    attempt_id,
    mode,
    *,
    decision="Needs Fix",
    progress_value=None,
    authority_hash=None,
    gate_decision=None,
):
    chain = ledger["repair_chain"]
    patch_hash = repair_gate.canonical_hash({"patch": attempt_id})
    if gate_decision is None:
        gate_decision = (
            "AutoRepairAllowed"
            if mode == "AutoRepair" and attempt_id != "AR-3"
            else ("ExtendRound3" if mode == "AutoRepair" else "EscalatedRepairAllowed")
        )
    record = {
        "attempt_id": attempt_id,
        "mode": mode,
        "gate_decision": gate_decision,
        "previous_receipt_hash": ledger["history_anchor"]["head_receipt_hash"],
        "repair_chain_digest": repair_gate.canonical_hash(chain),
        "policy_digest": repair_gate.policy_digest(POLICY),
        "patch_hash": patch_hash,
        "authority_receipt_hash": authority_hash,
        "review": review_receipt(chain, attempt_id, patch_hash, decision, progress_value),
    }
    seal(record)
    ledger["attempts"].append(record)
    ledger["history_anchor"]["attempt_count"] = len(ledger["attempts"])
    ledger["history_anchor"]["head_receipt_hash"] = record["receipt_hash"]
    ledger["history_anchor"]["source_text_sha256"] = repair_gate.canonical_hash(
        [item["receipt_hash"] for item in ledger["attempts"]]
    )
    return record


def trusted_context(ledger):
    record = {
        "schema_version": "ai-dev-flow/repair-trusted-context-v1",
        "provider": "orchestrator_current_conversation",
        "source_ref": "conversation:thread-001#trusted-repair-context",
        "repair_chain_digest": repair_gate.canonical_hash(ledger["repair_chain"]),
        "expected_attempt_count": len(ledger["attempts"]),
        "expected_history_head_hash": ledger["history_anchor"]["head_receipt_hash"],
        "verified_review_receipt_hashes": [
            ledger["trigger_review"]["receipt_hash"],
            *[
                item["review"]["receipt_hash"]
                for item in ledger["attempts"]
                if isinstance(item.get("review"), dict)
            ],
        ],
        "verified_authority_receipt_hashes": [
            item["receipt_hash"] for item in ledger["authority_records"]
        ],
    }
    record["attestation_hash"] = repair_gate.attestation_hash(record)
    return record


class RepairGateTests(unittest.TestCase):
    def evaluate(self, ledger, context=None):
        return repair_gate.evaluate(
            ledger,
            POLICY,
            trusted_context(ledger) if context is None else context,
        )

    def auto_stopped_ledger(self):
        ledger = base_ledger()
        add_attempt(ledger, "AR-1", "AutoRepair")
        add_attempt(ledger, "AR-2", "AutoRepair", progress_value=progress(False))
        return ledger

    def test_base_auto_rounds_are_derived_from_receipt_history(self):
        ledger = base_ledger()
        first = self.evaluate(ledger)
        add_attempt(ledger, "AR-1", "AutoRepair")
        second = self.evaluate(ledger)
        self.assertEqual(
            (first["decision"], first["eligible_mode"], first["next_attempt_id"]),
            ("MechanicallyEligible", "AutoRepair", "AR-1"),
        )
        self.assertEqual(
            (second["decision"], second["eligible_mode"], second["next_attempt_id"]),
            ("MechanicallyEligible", "AutoRepair", "AR-2"),
        )
        self.assertEqual(second["auto_attempts_used"], 1)

    def test_history_anchor_prevents_count_reset_and_receipts_prevent_gaps(self):
        ledger = self.auto_stopped_ledger()
        original_context = trusted_context(ledger)
        reset = copy.deepcopy(ledger)
        reset["attempts"] = []
        reset["history_anchor"]["attempt_count"] = 0
        reset["history_anchor"]["head_receipt_hash"] = reset["trigger_review"]["receipt_hash"]
        reset["history_anchor"]["source_text_sha256"] = repair_gate.canonical_hash([])
        gap = base_ledger()
        add_attempt(gap, "AR-2", "AutoRepair")
        identity_change = copy.deepcopy(ledger)
        identity_change["repair_chain"]["repair_chain_id"] = "chain-forged"
        for candidate, context, reason in (
            (reset, original_context, "TRUSTED_CONTEXT_ATTEMPT_COUNT_MISMATCH"),
            (gap, trusted_context(gap), "ATTEMPT_SEQUENCE_GAP"),
            (identity_change, trusted_context(identity_change), "REVIEW_BINDING_REPAIR_CHAIN_DIGEST"),
        ):
            with self.subTest(reason=reason):
                result = self.evaluate(candidate, context)
                self.assertEqual(result["decision"], "Blocked")
                self.assertIn(reason, result["reason_codes"])

    def test_task_or_model_change_preserves_same_validated_history(self):
        ledger = self.auto_stopped_ledger()
        ledger["current_task_id"] = "TASK-002"
        ledger["current_model"] = "model-b"
        result = self.evaluate(ledger)
        self.assertEqual(result["decision"], "Stop")
        self.assertEqual(result["auto_attempts_used"], 2)

    def test_ledger_cannot_self_attest_without_trusted_context(self):
        result = repair_gate.evaluate(base_ledger(), POLICY)
        self.assertEqual(result["decision"], "Blocked")
        self.assertIn("TRUSTED_CONTEXT_REQUIRED", result["reason_codes"])

    def test_unattested_review_receipt_is_blocked(self):
        ledger = base_ledger()
        add_attempt(ledger, "AR-1", "AutoRepair")
        context = trusted_context(ledger)
        context["verified_review_receipt_hashes"] = [
            ledger["trigger_review"]["receipt_hash"]
        ]
        context["attestation_hash"] = repair_gate.attestation_hash(context)
        result = self.evaluate(ledger, context)
        self.assertEqual(result["decision"], "Blocked")
        self.assertIn("TRUSTED_CONTEXT_REVIEW_RECEIPTS_MISSING", result["reason_codes"])

    def test_third_round_compares_structured_review_progress(self):
        passed = base_ledger()
        add_attempt(passed, "AR-1", "AutoRepair")
        add_attempt(passed, "AR-2", "AutoRepair", progress_value=progress(True))
        failed = self.auto_stopped_ledger()
        passed_result = self.evaluate(passed)
        self.assertEqual(
            (passed_result["decision"], passed_result["eligible_mode"], passed_result["next_attempt_id"]),
            ("MechanicallyEligible", "ExtendRound3", "AR-3"),
        )
        stopped = self.evaluate(failed)
        self.assertEqual(stopped["decision"], "Stop")
        self.assertIn("ROUND3_NO_RED_TO_GREEN", stopped["reason_codes"])

    def test_green_regression_new_blocker_and_evidence_stall_stop_round3(self):
        cases = {}
        green_regression = progress(True)
        green_regression["closure_before"]["stable"] = "GREEN"
        green_regression["closure_after"]["stable"] = "RED"
        cases["ROUND3_GREEN_TO_RED"] = green_regression
        new_blocker = progress(True)
        new_blocker["blocking_findings_after"].append("F-NEW")
        cases["ROUND3_NEW_BLOCKING_FINDING"] = new_blocker
        stalled = progress(True)
        stalled["evidence_after"] = ["unit"]
        cases["ROUND3_EVIDENCE_NOT_INCREASED"] = stalled
        for reason, progress_value in cases.items():
            ledger = base_ledger()
            add_attempt(ledger, "AR-1", "AutoRepair")
            add_attempt(ledger, "AR-2", "AutoRepair", progress_value=progress_value)
            with self.subTest(reason=reason):
                result = self.evaluate(ledger)
                self.assertEqual(result["decision"], "Stop")
                self.assertIn(reason, result["reason_codes"])

    def test_zero_p1_count_edge_uses_closure_not_raw_severity_count(self):
        ledger = base_ledger()
        add_attempt(ledger, "AR-1", "AutoRepair")
        value = progress(True)
        value["severity_before"] = {"F-001": "P2"}
        value["severity_after"] = {"F-001": "P2"}
        add_attempt(ledger, "AR-2", "AutoRepair", progress_value=value)
        result = self.evaluate(ledger)
        self.assertEqual((result["decision"], result["eligible_mode"]), ("MechanicallyEligible", "ExtendRound3"))

    def test_default_one_attempt_authority_is_chain_and_scope_bound(self):
        ledger = self.auto_stopped_ledger()
        authority = authority_receipt(ledger["repair_chain"])
        ledger["authority_records"].append(authority)
        ledger["requested_mode"] = "EscalatedRepair"
        result = self.evaluate(ledger)
        self.assertEqual(
            (result["decision"], result["eligible_mode"], result["next_attempt_id"]),
            ("MechanicallyEligible", "EscalatedRepair", "ER-1"),
        )
        self.assertEqual(result["authority_receipt_hash"], authority["receipt_hash"])
        self.assertFalse(result["manual_implementation_required"])

    def test_unattested_authority_cannot_produce_escalation_eligibility(self):
        ledger = self.auto_stopped_ledger()
        ledger["authority_records"].append(authority_receipt(ledger["repair_chain"]))
        ledger["requested_mode"] = "EscalatedRepair"
        context = trusted_context(ledger)
        context["verified_authority_receipt_hashes"] = []
        context["attestation_hash"] = repair_gate.attestation_hash(context)
        result = self.evaluate(ledger, context)
        self.assertEqual(result["decision"], "Blocked")
        self.assertIn("CANDIDATE_AUTHORITY_NOT_ATTESTED", result["reason_codes"])

    def test_authority_cannot_replay_across_chain_or_use_empty_reference(self):
        ledger = self.auto_stopped_ledger()
        authority = authority_receipt(ledger["repair_chain"])
        ledger["authority_records"].append(authority)
        ledger["requested_mode"] = "EscalatedRepair"
        replay = copy.deepcopy(ledger)
        replay["repair_chain"]["allowed_files_hash"] = repair_gate.canonical_hash(["src/other.py"])
        empty = copy.deepcopy(ledger)
        empty["authority_records"][0]["source_ref"] = "x"
        empty["authority_records"][0]["receipt_hash"] = repair_gate.receipt_hash(empty["authority_records"][0])
        replay_result = self.evaluate(replay)
        self.assertEqual(replay_result["decision"], "Blocked")
        self.assertIn("REVIEW_BINDING_REPAIR_CHAIN_DIGEST", replay_result["reason_codes"])
        self.assertIn("INVALID_AUTHORITY_SOURCE_REF", self.evaluate(empty)["reason_codes"])

    def test_er2_requires_er1_review_and_separate_or_explicit_authority(self):
        ledger = self.auto_stopped_ledger()
        authority1 = authority_receipt(ledger["repair_chain"], "ER-1")
        ledger["authority_records"].append(authority1)
        add_attempt(
            ledger,
            "ER-1",
            "EscalatedRepair",
            authority_hash=authority1["receipt_hash"],
        )
        ledger["requested_mode"] = "EscalatedRepair"
        stopped = self.evaluate(ledger)
        self.assertEqual(stopped["decision"], "Stop")
        self.assertIn("ESCALATED_AUTHORITY_MISSING", stopped["reason_codes"])
        authority2 = authority_receipt(ledger["repair_chain"], "ER-2")
        ledger["authority_records"].append(authority2)
        allowed = self.evaluate(ledger)
        self.assertEqual(
            (allowed["decision"], allowed["eligible_mode"], allowed["next_attempt_id"]),
            ("MechanicallyEligible", "EscalatedRepair", "ER-2"),
        )

        no_review = copy.deepcopy(ledger)
        del no_review["attempts"][-1]["review"]
        no_review["attempts"][-1]["receipt_hash"] = repair_gate.receipt_hash(no_review["attempts"][-1])
        no_review["history_anchor"]["head_receipt_hash"] = no_review["attempts"][-1]["receipt_hash"]
        self.assertEqual(self.evaluate(no_review)["decision"], "Blocked")

    def test_blocked_review_prevents_next_escalated_attempt(self):
        ledger = self.auto_stopped_ledger()
        authority1 = authority_receipt(ledger["repair_chain"], "ER-1")
        authority2 = authority_receipt(ledger["repair_chain"], "ER-2")
        ledger["authority_records"].extend((authority1, authority2))
        add_attempt(
            ledger,
            "ER-1",
            "EscalatedRepair",
            decision="Blocked",
            authority_hash=authority1["receipt_hash"],
        )
        ledger["requested_mode"] = "EscalatedRepair"
        result = self.evaluate(ledger)
        self.assertEqual(result["decision"], "Blocked")
        self.assertIn("LATEST_REVIEW_BLOCKED", result["reason_codes"])

    def test_external_side_effect_is_hard_block_for_both_modes(self):
        auto = base_ledger()
        auto["safety"]["external_side_effect"] = True
        escalated = self.auto_stopped_ledger()
        escalated["safety"]["external_side_effect"] = True
        escalated["requested_mode"] = "EscalatedRepair"
        for ledger in (auto, escalated):
            result = self.evaluate(ledger)
            self.assertEqual(result["decision"], "Blocked")
            self.assertIn("REQUIRED_FALSE_EXTERNAL_SIDE_EFFECT", result["reason_codes"])

    def test_malformed_policy_is_structured_blocked(self):
        cases = {}
        missing = copy.deepcopy(POLICY)
        del missing["repair"]["history"]
        cases["POLICY_INVALID_HISTORY"] = missing
        empty = copy.deepcopy(POLICY)
        empty["repair"]["round_3_progress"] = {}
        cases["POLICY_CONFLICT_PROGRESS_SOURCE"] = empty
        schema = copy.deepcopy(POLICY)
        schema["repair"]["ledger_schema"] = "unknown"
        cases["POLICY_CONFLICT_LEDGER_SCHEMA"] = schema
        disabled = copy.deepcopy(POLICY)
        disabled["repair"]["history"]["require_trusted_context"] = False
        cases["POLICY_CONFLICT_HISTORY_REQUIRE_TRUSTED_CONTEXT"] = disabled
        base_limit = copy.deepcopy(POLICY)
        base_limit["repair"]["base_auto_rounds"] = 1
        cases["POLICY_CONFLICT_BASE_AUTO_ROUNDS"] = base_limit
        maximum = copy.deepcopy(POLICY)
        maximum["repair"]["autonomous_max_rounds"] = 2
        cases["POLICY_CONFLICT_AUTONOMOUS_MAX_ROUNDS"] = maximum
        escalation_default = copy.deepcopy(POLICY)
        escalation_default["repair"]["post_stop"]["default_authorized_attempts"] = 2
        cases["POLICY_CONFLICT_POST_STOP_DEFAULT_AUTHORIZED_ATTEMPTS"] = escalation_default
        unknown_repair = copy.deepcopy(POLICY)
        unknown_repair["repair"]["reset_budget_on_new_task"] = True
        cases["POLICY_UNKNOWN_REPAIR_FIELDS"] = unknown_repair
        unknown_history = copy.deepcopy(POLICY)
        unknown_history["repair"]["history"]["trust_ledger"] = True
        cases["POLICY_UNKNOWN_HISTORY_FIELDS"] = unknown_history
        for reason, malformed in cases.items():
            with self.subTest(reason=reason):
                result = repair_gate.evaluate(base_ledger(), malformed)
                self.assertEqual(result["decision"], "Blocked")
                self.assertIn(reason, result["reason_codes"])

    def test_cli_malformed_policy_returns_json_exit_2_without_traceback(self):
        malformed = copy.deepcopy(POLICY)
        malformed["repair"]["base_auto_rounds"] = "two"
        with tempfile.TemporaryDirectory() as temp:
            policy_path = pathlib.Path(temp) / "CORE.md"
            policy_path.write_text(
                "<!-- POLICY_JSON_BEGIN -->\n```json\n"
                + json.dumps(malformed, ensure_ascii=False)
                + "\n```\n<!-- POLICY_JSON_END -->\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-X",
                    "utf8",
                    str(SCRIPT),
                    "--policy",
                    str(policy_path),
                    "--policy-digest",
                    "--format",
                    "json",
                ],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
            )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["decision"], "Blocked")
        self.assertNotIn("Traceback", result.stdout + result.stderr)

    def test_policy_digest_is_canonical(self):
        reordered = json.loads(json.dumps(POLICY, ensure_ascii=False, sort_keys=True))
        self.assertEqual(repair_gate.policy_digest(POLICY), repair_gate.policy_digest(reordered))


if __name__ == "__main__":
    unittest.main()
