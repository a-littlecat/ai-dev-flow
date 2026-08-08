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
CORE = SKILL_ROOT / "policy" / "repair-campaign.json"

SPEC = importlib.util.spec_from_file_location("repair_gate", SCRIPT)
repair_gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(repair_gate)
POLICY = repair_gate.load_policy(CORE)
CORE_POLICY = json.loads((SKILL_ROOT / "policy" / "core.json").read_text(encoding="utf-8"))


def legacy_rc2_policy():
    return {
        "schema_version": "ai-dev-flow/v0.8-policy-rc2",
        "unknown_input": "Blocked",
        "routes": copy.deepcopy(CORE_POLICY["routes"]),
        "review": copy.deepcopy(CORE_POLICY["review"]),
        "safety": copy.deepcopy(CORE_POLICY["safety"]),
        "repair": {
            key: copy.deepcopy(value)
            for key, value in POLICY["repair"].items()
            if key != "campaign"
        },
    }


def seal(record):
    record["receipt_hash"] = repair_gate.receipt_hash(record)
    return record


def base_chain(*, chain_id="chain-001", finding_ids=None, allowed_files=None):
    allowed_files = allowed_files or ["src/a.py"]
    return {
        "repair_chain_id": chain_id,
        "finding_ids": finding_ids or ["F-001"],
        "closure_contract_hash": repair_gate.canonical_hash(["criterion-1"]),
        "allowed_files": allowed_files,
        "allowed_files_hash": repair_gate.canonical_hash(allowed_files),
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


def campaign_authority_receipt(
    ledger,
    *,
    campaign_id="campaign-001",
    profile="core_product",
    allowed_scope=None,
):
    allowed_scope = allowed_scope or {
        "allowed_exact_files": ["docs/tasks/TASK-001.md"],
        "allowed_path_prefixes": ["src/", "tests/"],
    }
    record = {
        "authority_id": f"authority-{campaign_id}",
        "authority_mode": "repair_campaign",
        "source_kind": "user_message",
        "source_ref": f"conversation:thread-001#message-{campaign_id}",
        "source_text_sha256": repair_gate.canonical_hash(f"authorize {campaign_id}"),
        "campaign_id": campaign_id,
        "task_id": ledger["current_task_id"],
        "acceptance_contract_hash": repair_gate.canonical_hash(["acceptance-ready"]),
        "allowed_scope": allowed_scope,
        "allowed_scope_hash": repair_gate.canonical_hash(allowed_scope),
        "profile": profile,
        "activation_chain_digest": repair_gate.canonical_hash(
            ledger["repair_chain"]
        ),
        "activation_history_head_hash": ledger["history_anchor"][
            "head_receipt_hash"
        ],
        "target": "reach acceptance readiness inside the frozen task scope",
    }
    return seal(record)


def campaign_state_receipt(
    authority,
    *,
    attempt_count=0,
    consecutive_no_progress=0,
    latest_outcome=None,
    safety=None,
    history_head_hash=None,
    latest_review_receipt_hash=None,
):
    safety = safety or {
        name: False
        for name in POLICY["repair"]["campaign"]["hard_stop_flags"]
    }
    if latest_outcome is None:
        latest_outcome = "NotStarted" if attempt_count == 0 else (
            "MeasurableProgress" if consecutive_no_progress == 0 else "NoProgress"
        )
    record = {
        "schema_version": "ai-dev-flow/repair-campaign-state-v1",
        "campaign_id": authority["campaign_id"],
        "authority_receipt_hash": authority["receipt_hash"],
        "attempt_count": attempt_count,
        "consecutive_no_progress": consecutive_no_progress,
        "history_head_hash": history_head_hash or (
            authority["receipt_hash"]
            if attempt_count == 0
            else repair_gate.canonical_hash(
                {
                    "campaign_id": authority["campaign_id"],
                    "attempt_count": attempt_count,
                }
            )
        ),
        "latest_outcome": latest_outcome,
        "latest_review_receipt_hash": latest_review_receipt_hash or (
            None
            if attempt_count == 0
            else repair_gate.canonical_hash(
                {
                    "campaign_id": authority["campaign_id"],
                    "latest_review": attempt_count,
                }
            )
        ),
        "safety_hash": repair_gate.canonical_hash(safety),
        "source_ref": "task:docs/tasks/TASK-001.md#repair-campaign-state",
        "source_text_sha256": repair_gate.canonical_hash(
            [
                attempt_count,
                consecutive_no_progress,
                latest_outcome,
                history_head_hash,
                latest_review_receipt_hash,
            ]
        ),
    }
    return seal(record)


def attach_campaign(
    ledger,
    *,
    profile="core_product",
    attempt_count=0,
    consecutive_no_progress=0,
    authority=None,
    state=None,
):
    authority = authority or campaign_authority_receipt(ledger, profile=profile)
    safety = {
        name: False
        for name in POLICY["repair"]["campaign"]["hard_stop_flags"]
    }
    state = state or campaign_state_receipt(
        authority,
        attempt_count=attempt_count,
        consecutive_no_progress=consecutive_no_progress,
        safety=safety,
    )
    ledger["authority_records"].append(authority)
    ledger["repair_campaign"] = {
        "campaign_id": authority["campaign_id"],
        "acceptance_contract_hash": authority["acceptance_contract_hash"],
        "profile": authority["profile"],
        "authority_receipt_hash": authority["receipt_hash"],
        "state": state,
        "safety": safety,
    }
    return authority


def base_ledger(chain=None, **updates):
    chain = chain or base_chain()
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
    if isinstance(ledger.get("repair_campaign"), dict):
        record["expected_task_id"] = ledger["current_task_id"]
        record["expected_acceptance_contract_hash"] = ledger[
            "repair_campaign"
        ]["acceptance_contract_hash"]
        record["expected_campaign_state_receipt_hash"] = ledger[
            "repair_campaign"
        ]["state"]["receipt_hash"]
    record["attestation_hash"] = repair_gate.attestation_hash(record)
    return record


def rebind_ledger_policy(ledger, policy):
    digest = repair_gate.policy_digest(policy)
    trigger = ledger["trigger_review"]
    trigger["policy_digest"] = digest
    seal(trigger)
    previous_hash = trigger["receipt_hash"]
    for attempt in ledger["attempts"]:
        attempt["previous_receipt_hash"] = previous_hash
        attempt["policy_digest"] = digest
        attempt["review"]["policy_digest"] = digest
        seal(attempt["review"])
        seal(attempt)
        previous_hash = attempt["receipt_hash"]
    ledger["history_anchor"]["head_receipt_hash"] = previous_hash
    ledger["history_anchor"]["source_text_sha256"] = repair_gate.canonical_hash(
        [item["receipt_hash"] for item in ledger["attempts"]]
    )
    return ledger


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

    def campaign_ledger(
        self,
        *,
        profile="core_product",
        attempt_count=0,
        consecutive_no_progress=0,
    ):
        ledger = self.auto_stopped_ledger()
        authority = attach_campaign(
            ledger,
            profile=profile,
            attempt_count=attempt_count,
            consecutive_no_progress=consecutive_no_progress,
        )
        ledger["requested_mode"] = "EscalatedRepair"
        return ledger, authority

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
        self.assertEqual(result["authority_mode"], "single_attempt")
        self.assertFalse(result["would_consume_campaign_authority"])
        self.assertFalse(result["manual_implementation_required"])

    def test_legacy_rc2_single_authority_receipts_remain_verifiable(self):
        legacy_policy = legacy_rc2_policy()
        ledger = self.auto_stopped_ledger()
        authority = authority_receipt(ledger["repair_chain"])
        ledger["authority_records"].append(authority)
        ledger["requested_mode"] = "EscalatedRepair"
        rebind_ledger_policy(ledger, legacy_policy)
        context = trusted_context(ledger)

        result = repair_gate.evaluate(ledger, legacy_policy, context)
        self.assertEqual(
            (result["decision"], result["eligible_mode"], result["next_attempt_id"]),
            ("MechanicallyEligible", "EscalatedRepair", "ER-1"),
        )

        campaign, _ = self.campaign_ledger()
        blocked = repair_gate.evaluate(
            campaign,
            legacy_policy,
            trusted_context(campaign),
        )
        self.assertEqual(blocked["decision"], "Blocked")
        self.assertIn("POLICY_CONFLICT_SCHEMA_VERSION", blocked["reason_codes"])

    def test_cli_accepts_legacy_rc2_policy_for_non_campaign_ledger(self):
        legacy_policy = legacy_rc2_policy()
        ledger = self.auto_stopped_ledger()
        authority = authority_receipt(ledger["repair_chain"])
        ledger["authority_records"].append(authority)
        ledger["requested_mode"] = "EscalatedRepair"
        rebind_ledger_policy(ledger, legacy_policy)
        context = trusted_context(ledger)
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            policy_path = root / "CORE.md"
            ledger_path = root / "ledger.json"
            context_path = root / "context.json"
            policy_path.write_text(
                "<!-- POLICY_JSON_BEGIN -->\n```json\n"
                + json.dumps(legacy_policy, ensure_ascii=False)
                + "\n```\n<!-- POLICY_JSON_END -->\n",
                encoding="utf-8",
            )
            ledger_path.write_text(
                json.dumps(ledger, ensure_ascii=False),
                encoding="utf-8",
            )
            context_path.write_text(
                json.dumps(context, ensure_ascii=False),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-X",
                    "utf8",
                    str(SCRIPT),
                    str(ledger_path),
                    "--policy",
                    str(policy_path),
                    "--trusted-context",
                    str(context_path),
                    "--format",
                    "json",
                ],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
            )
            digest_result = subprocess.run(
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
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["decision"], "MechanicallyEligible")
        self.assertEqual(digest_result.returncode, 0)
        self.assertEqual(
            json.loads(digest_result.stdout)["policy_digest"],
            repair_gate.policy_digest(legacy_policy),
        )

    def test_core_campaign_allows_three_no_progress_attempts_and_stops_at_four(self):
        for streak in range(4):
            ledger, authority = self.campaign_ledger(
                attempt_count=streak,
                consecutive_no_progress=streak,
            )
            with self.subTest(streak=streak):
                result = self.evaluate(ledger)
                self.assertEqual(
                    (
                        result["decision"],
                        result["eligible_mode"],
                        result["authority_mode"],
                        result["next_attempt_id"],
                    ),
                    (
                        "MechanicallyEligible",
                        "EscalatedRepair",
                        "repair_campaign",
                        "ER-1",
                    ),
                )
                self.assertEqual(
                    result["authority_receipt_hash"],
                    authority["receipt_hash"],
                )
                self.assertEqual(result["campaign_no_progress_limit"], 4)
                self.assertEqual(
                    result["campaign_consecutive_no_progress"],
                    streak,
                )
        stopped, _ = self.campaign_ledger(
            attempt_count=4,
            consecutive_no_progress=4,
        )
        result = self.evaluate(stopped)
        self.assertEqual(result["decision"], "Stop")
        self.assertIn(
            "CAMPAIGN_NO_PROGRESS_LIMIT_REACHED",
            result["reason_codes"],
        )

    def test_harness_campaign_allows_four_no_progress_attempts_and_stops_at_five(self):
        allowed, _ = self.campaign_ledger(
            profile="harness",
            attempt_count=4,
            consecutive_no_progress=4,
        )
        allowed_result = self.evaluate(allowed)
        self.assertEqual(
            (allowed_result["decision"], allowed_result["campaign_no_progress_limit"]),
            ("MechanicallyEligible", 5),
        )
        stopped, _ = self.campaign_ledger(
            profile="harness",
            attempt_count=5,
            consecutive_no_progress=5,
        )
        stopped_result = self.evaluate(stopped)
        self.assertEqual(stopped_result["decision"], "Stop")
        self.assertIn(
            "CAMPAIGN_NO_PROGRESS_LIMIT_REACHED",
            stopped_result["reason_codes"],
        )

    def test_latest_review_terminal_state_precedes_campaign_limit(self):
        cases = (
            ("Blocked", "Blocked", "LATEST_REVIEW_BLOCKED"),
            ("Passed", "Stop", "REPAIR_ALREADY_PASSED"),
        )
        for review_decision, expected_decision, expected_reason in cases:
            ledger = base_ledger()
            add_attempt(ledger, "AR-1", "AutoRepair")
            add_attempt(
                ledger,
                "AR-2",
                "AutoRepair",
                decision=review_decision,
                progress_value=progress(False),
            )
            attach_campaign(
                ledger,
                attempt_count=4,
                consecutive_no_progress=4,
            )
            ledger["requested_mode"] = "EscalatedRepair"
            with self.subTest(review_decision=review_decision):
                result = self.evaluate(ledger)
                self.assertEqual(result["decision"], expected_decision)
                self.assertEqual(result["reason_codes"], [expected_reason])

    def test_campaign_progress_resets_streak_but_inconsistent_state_is_blocked(self):
        progressed, _ = self.campaign_ledger(
            attempt_count=7,
            consecutive_no_progress=0,
        )
        allowed = self.evaluate(progressed)
        self.assertEqual(allowed["decision"], "MechanicallyEligible")

        inconsistent, _ = self.campaign_ledger(
            attempt_count=7,
            consecutive_no_progress=1,
        )
        inconsistent["repair_campaign"]["state"]["latest_outcome"] = "MeasurableProgress"
        seal(inconsistent["repair_campaign"]["state"])
        context = trusted_context(inconsistent)
        blocked = self.evaluate(inconsistent, context)
        self.assertEqual(blocked["decision"], "Blocked")
        self.assertIn(
            "CAMPAIGN_PROGRESS_DID_NOT_RESET_STREAK",
            blocked["reason_codes"],
        )

    def test_campaign_state_must_cover_latest_campaign_attempt_and_review(self):
        ledger, authority = self.campaign_ledger(
            attempt_count=3,
            consecutive_no_progress=3,
        )
        attempt = add_attempt(
            ledger,
            "ER-1",
            "EscalatedRepair",
            authority_hash=authority["receipt_hash"],
        )
        stale = self.evaluate(ledger)
        self.assertEqual(stale["decision"], "Blocked")
        self.assertIn("CAMPAIGN_STATE_HISTORY_HEAD_STALE", stale["reason_codes"])
        self.assertIn("CAMPAIGN_STATE_LATEST_REVIEW_STALE", stale["reason_codes"])

        ledger["repair_campaign"]["state"] = campaign_state_receipt(
            authority,
            attempt_count=4,
            consecutive_no_progress=4,
            history_head_hash=attempt["receipt_hash"],
            latest_review_receipt_hash=attempt["review"]["receipt_hash"],
        )
        stopped = self.evaluate(ledger)
        self.assertEqual(stopped["decision"], "Stop")
        self.assertIn(
            "CAMPAIGN_NO_PROGRESS_LIMIT_REACHED",
            stopped["reason_codes"],
        )

    def test_campaign_streak_cannot_be_reset_by_new_chain_task_or_model(self):
        original, authority = self.campaign_ledger(
            attempt_count=4,
            consecutive_no_progress=4,
        )

        new_chain = base_chain(
            chain_id="chain-002",
            finding_ids=["F-002"],
            allowed_files=["tests/harness.py"],
        )
        inherited = base_ledger(chain=new_chain)
        add_attempt(inherited, "AR-1", "AutoRepair")
        add_attempt(
            inherited,
            "AR-2",
            "AutoRepair",
            progress_value={
                **progress(False),
                "target_finding_id": "F-002",
                "blocking_findings_before": ["F-002"],
                "blocking_findings_after": ["F-002"],
                "severity_before": {"F-002": "P1"},
                "severity_after": {"F-002": "P1"},
            },
        )
        latest_attempt = inherited["attempts"][-1]
        state = campaign_state_receipt(
            authority,
            attempt_count=6,
            consecutive_no_progress=6,
            history_head_hash=latest_attempt["receipt_hash"],
            latest_review_receipt_hash=latest_attempt["review"]["receipt_hash"],
        )
        attach_campaign(inherited, authority=authority, state=state)
        inherited["requested_mode"] = "EscalatedRepair"
        inherited["current_model"] = "model-b"
        stopped = self.evaluate(inherited)
        self.assertEqual(stopped["decision"], "Stop")
        self.assertIn(
            "CAMPAIGN_NO_PROGRESS_LIMIT_REACHED",
            stopped["reason_codes"],
        )

        changed_task = copy.deepcopy(inherited)
        changed_task["current_task_id"] = "TASK-002"
        blocked = self.evaluate(changed_task)
        self.assertEqual(blocked["decision"], "Blocked")
        self.assertIn(
            "CAMPAIGN_AUTHORITY_BINDING_TASK_ID",
            blocked["reason_codes"],
        )

    def test_campaign_state_cannot_replay_across_chains(self):
        original, authority = self.campaign_ledger(
            attempt_count=3,
            consecutive_no_progress=3,
        )
        stale_state = copy.deepcopy(original["repair_campaign"]["state"])

        new_chain = base_chain(
            chain_id="chain-002",
            finding_ids=["F-002"],
            allowed_files=["tests/harness.py"],
        )
        replayed = base_ledger(chain=new_chain)
        add_attempt(replayed, "AR-1", "AutoRepair")
        add_attempt(
            replayed,
            "AR-2",
            "AutoRepair",
            progress_value={
                **progress(False),
                "target_finding_id": "F-002",
                "blocking_findings_before": ["F-002"],
                "blocking_findings_after": ["F-002"],
                "severity_before": {"F-002": "P1"},
                "severity_after": {"F-002": "P1"},
            },
        )
        attach_campaign(replayed, authority=authority, state=stale_state)
        replayed["requested_mode"] = "EscalatedRepair"

        blocked = self.evaluate(replayed)
        self.assertEqual(blocked["decision"], "Blocked")
        self.assertIn(
            "CAMPAIGN_STATE_HISTORY_HEAD_STALE",
            blocked["reason_codes"],
        )
        self.assertIn(
            "CAMPAIGN_STATE_LATEST_REVIEW_STALE",
            blocked["reason_codes"],
        )

        latest_attempt = replayed["attempts"][-1]
        replayed["repair_campaign"]["state"] = campaign_state_receipt(
            authority,
            attempt_count=5,
            consecutive_no_progress=5,
            history_head_hash=latest_attempt["receipt_hash"],
            latest_review_receipt_hash=latest_attempt["review"]["receipt_hash"],
        )
        stopped = self.evaluate(replayed)
        self.assertEqual(stopped["decision"], "Stop")
        self.assertIn(
            "CAMPAIGN_NO_PROGRESS_LIMIT_REACHED",
            stopped["reason_codes"],
        )

    def test_campaign_authority_cannot_replay_across_task_or_acceptance_context(self):
        ledger, _ = self.campaign_ledger(
            attempt_count=1,
            consecutive_no_progress=1,
        )
        cases = (
            (
                "expected_task_id",
                "TASK-002",
                "TRUSTED_CONTEXT_CAMPAIGN_TASK_MISMATCH",
            ),
            (
                "expected_acceptance_contract_hash",
                repair_gate.canonical_hash(["different-acceptance-contract"]),
                "TRUSTED_CONTEXT_CAMPAIGN_ACCEPTANCE_CONTRACT_MISMATCH",
            ),
        )
        for field, value, reason in cases:
            context = trusted_context(ledger)
            context[field] = value
            context["attestation_hash"] = repair_gate.attestation_hash(context)
            with self.subTest(field=field):
                blocked = self.evaluate(ledger, context)
                self.assertEqual(blocked["decision"], "Blocked")
                self.assertIn(reason, blocked["reason_codes"])

        missing_cases = (
            ("expected_task_id", "TRUSTED_CONTEXT_CAMPAIGN_TASK_MISSING"),
            (
                "expected_acceptance_contract_hash",
                "TRUSTED_CONTEXT_CAMPAIGN_ACCEPTANCE_CONTRACT_MISSING",
            ),
        )
        for field, reason in missing_cases:
            context = trusted_context(ledger)
            del context[field]
            context["attestation_hash"] = repair_gate.attestation_hash(context)
            with self.subTest(missing=field):
                blocked = self.evaluate(ledger, context)
                self.assertEqual(blocked["decision"], "Blocked")
                self.assertIn(reason, blocked["reason_codes"])

    def test_campaign_ledger_cannot_forge_streak_reset_without_trusted_state(self):
        ledger, _ = self.campaign_ledger(
            attempt_count=4,
            consecutive_no_progress=4,
        )
        context = trusted_context(ledger)
        authority = ledger["authority_records"][-1]
        ledger["repair_campaign"]["state"] = campaign_state_receipt(
            authority,
            attempt_count=4,
            consecutive_no_progress=0,
        )
        result = self.evaluate(ledger, context)
        self.assertEqual(result["decision"], "Blocked")
        self.assertIn(
            "TRUSTED_CONTEXT_CAMPAIGN_STATE_MISMATCH",
            result["reason_codes"],
        )

    def test_campaign_scope_and_hard_stops_block_before_attempt_budget(self):
        outside = self.auto_stopped_ledger()
        outside["repair_chain"]["allowed_files"] = ["frontend/app.py"]
        outside["repair_chain"]["allowed_files_hash"] = repair_gate.canonical_hash(
            outside["repair_chain"]["allowed_files"]
        )
        outside["trigger_review"] = review_receipt(
            outside["repair_chain"],
            "TRIGGER",
            outside["repair_chain"]["closure_contract_hash"],
        )
        outside["attempts"] = []
        outside["history_anchor"]["attempt_count"] = 0
        outside["history_anchor"]["head_receipt_hash"] = outside["trigger_review"]["receipt_hash"]
        add_attempt(outside, "AR-1", "AutoRepair")
        add_attempt(outside, "AR-2", "AutoRepair", progress_value=progress(False))
        attach_campaign(outside)
        outside["requested_mode"] = "EscalatedRepair"
        outside_result = self.evaluate(outside)
        self.assertEqual(outside_result["decision"], "Blocked")
        self.assertIn(
            "CAMPAIGN_SCOPE_OUTSIDE_AUTHORITY",
            outside_result["reason_codes"],
        )

        hard_stop, _ = self.campaign_ledger()
        hard_stop["repair_campaign"]["safety"]["p0_finding"] = True
        hard_stop_result = self.evaluate(hard_stop)
        self.assertEqual(hard_stop_result["decision"], "Blocked")
        self.assertIn(
            "CAMPAIGN_HARD_STOP_P0_FINDING",
            hard_stop_result["reason_codes"],
        )
        self.assertIn(
            "CAMPAIGN_STATE_SAFETY_MISMATCH",
            hard_stop_result["reason_codes"],
        )

    def test_campaign_limit_stops_auto_repair_in_a_new_chain(self):
        ledger = base_ledger()
        attach_campaign(
            ledger,
            attempt_count=4,
            consecutive_no_progress=4,
        )
        result = self.evaluate(ledger)
        self.assertEqual(result["decision"], "Stop")
        self.assertEqual(result["auto_attempts_used"], 0)
        self.assertIn(
            "CAMPAIGN_NO_PROGRESS_LIMIT_REACHED",
            result["reason_codes"],
        )

    def test_malformed_campaign_types_are_structured_blocked(self):
        cases = {}

        malformed_scope, _ = self.campaign_ledger()
        malformed_scope["authority_records"][-1]["allowed_scope"][
            "allowed_exact_files"
        ] = [{}]
        seal(malformed_scope["authority_records"][-1])
        malformed_scope["repair_campaign"]["authority_receipt_hash"] = (
            malformed_scope["authority_records"][-1]["receipt_hash"]
        )
        malformed_scope["repair_campaign"]["state"]["authority_receipt_hash"] = (
            malformed_scope["authority_records"][-1]["receipt_hash"]
        )
        seal(malformed_scope["repair_campaign"]["state"])
        cases["INVALID_CAMPAIGN_EXACT_FILES"] = malformed_scope

        malformed_profile, _ = self.campaign_ledger()
        malformed_profile["repair_campaign"]["profile"] = []
        cases["INVALID_CAMPAIGN_PROFILE"] = malformed_profile

        malformed_authority_hash, _ = self.campaign_ledger()
        malformed_authority_hash["repair_campaign"]["authority_receipt_hash"] = {}
        cases["CAMPAIGN_AUTHORITY_RECEIPT_NOT_FOUND"] = malformed_authority_hash

        malformed_activation, _ = self.campaign_ledger()
        malformed_activation_authority = malformed_activation[
            "authority_records"
        ][-1]
        malformed_activation_authority["activation_chain_digest"] = []
        seal(malformed_activation_authority)
        malformed_activation["repair_campaign"]["authority_receipt_hash"] = (
            malformed_activation_authority["receipt_hash"]
        )
        malformed_activation["repair_campaign"]["state"][
            "authority_receipt_hash"
        ] = malformed_activation_authority["receipt_hash"]
        seal(malformed_activation["repair_campaign"]["state"])
        cases["INVALID_CAMPAIGN_ACTIVATION_CHAIN_DIGEST"] = (
            malformed_activation
        )

        for reason, ledger in cases.items():
            with self.subTest(reason=reason):
                result = self.evaluate(ledger)
                self.assertEqual(result["decision"], "Blocked")
                self.assertIn(reason, result["reason_codes"])

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
        cases["POLICY_MISSING_REPAIR_FIELDS"] = missing
        empty = copy.deepcopy(POLICY)
        empty["repair"]["round_3_progress"] = {}
        cases["POLICY_MISSING_ROUND_3_PROGRESS_FIELDS"] = empty
        schema = copy.deepcopy(POLICY)
        schema["repair"]["ledger_schema"] = "unknown"
        cases["POLICY_CONFLICT_LEDGER_SCHEMA"] = schema
        base_limit = copy.deepcopy(POLICY)
        base_limit["repair"]["base_auto_rounds"] = "two"
        cases["POLICY_INVALID_BASE_AUTO_ROUNDS"] = base_limit
        maximum = copy.deepcopy(POLICY)
        maximum["repair"]["autonomous_max_rounds"] = 2
        maximum["repair"]["base_auto_rounds"] = 2
        cases["POLICY_INVALID_AUTO_ROUND_LIMITS"] = maximum
        campaign_profile = copy.deepcopy(POLICY)
        campaign_profile["repair"]["campaign"]["profiles"]["core_product"]["max_consecutive_no_progress"] = 0
        cases["POLICY_INVALID_CAMPAIGN_PROFILES"] = campaign_profile
        campaign_hard_stops = copy.deepcopy(POLICY)
        campaign_hard_stops["repair"]["campaign"]["hard_stop_flags"] = []
        cases["POLICY_INVALID_CAMPAIGN_HARD_STOP_FLAGS"] = campaign_hard_stops
        unknown_repair = copy.deepcopy(POLICY)
        unknown_repair["repair"]["reset_budget_on_new_task"] = True
        cases["POLICY_UNKNOWN_REPAIR_FIELDS"] = unknown_repair
        for reason, malformed in cases.items():
            with self.subTest(reason=reason):
                result = repair_gate.evaluate(base_ledger(), malformed)
                self.assertEqual(result["decision"], "Blocked")
                self.assertIn(reason, result["reason_codes"])

    def test_security_critical_policy_mutations_block_in_memory_evaluation(self):
        mutations = (
            lambda value: value["repair"]["post_stop"]["authority_must_bind"].pop(),
            lambda value: value["repair"]["campaign"]["authority_must_bind"].pop(),
            lambda value: value["repair"]["campaign"]["hard_stop_flags"].remove("test_oracle_weakened"),
            lambda value: value["repair"]["history"].update({"require_trusted_context": False}),
            lambda value: value["repair"]["campaign"].update({"task_change_resets_streak": True}),
        )
        for index, change in enumerate(mutations):
            malformed = copy.deepcopy(POLICY)
            change(malformed)
            with self.subTest(index=index):
                result = repair_gate.evaluate(base_ledger(), malformed)
                self.assertEqual(result["decision"], "Blocked")
                self.assertIn("POLICY_CONSTRAINT_VIOLATION", result["reason_codes"])

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
