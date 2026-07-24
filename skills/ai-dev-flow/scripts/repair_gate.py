"""Read-only evaluator for receipt-backed AutoRepair and EscalatedRepair."""

import sys
sys.dont_write_bytecode = True

import argparse
import hashlib
import json
import pathlib
import re


LEDGER_SCHEMA = "ai-dev-flow/repair-ledger-v1"
TRUSTED_CONTEXT_SCHEMA = "ai-dev-flow/repair-trusted-context-v1"
ALLOWED_DECISIONS = {"MechanicallyEligible"}
REVIEW_DECISIONS = {"Passed", "Needs Fix", "Blocked"}
SEVERITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "Closed": 4}
HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
ATTEMPT_PATTERN = re.compile(r"^(AR|ER)-([1-9][0-9]*)$")
EVIDENCE_REF_PATTERN = re.compile(r"^(conversation|task):[^#]+#[^#]+$")
POLICY_PATTERN = re.compile(
    r"<!-- POLICY_JSON_BEGIN -->\s*```json\s*(\{.*?\})\s*```\s*<!-- POLICY_JSON_END -->",
    flags=re.DOTALL,
)


class InvocationError(Exception):
    pass


class ReadOnlyParser(argparse.ArgumentParser):
    def error(self, message):
        raise InvocationError(message)


def canonical_hash(value):
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def policy_digest(policy):
    return canonical_hash(policy)


def receipt_hash(record):
    return canonical_hash({key: value for key, value in record.items() if key != "receipt_hash"})


def attestation_hash(record):
    return canonical_hash({key: value for key, value in record.items() if key != "attestation_hash"})


def load_policy(path):
    try:
        text = pathlib.Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise InvocationError(f"cannot read policy: {exc}") from exc
    match = POLICY_PATTERN.search(text)
    if not match:
        raise InvocationError(f"POLICY_JSON block missing: {path}")
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise InvocationError(f"invalid POLICY_JSON: {exc}") from exc


def validate_policy(policy):
    if not isinstance(policy, dict):
        return ["POLICY_NOT_OBJECT"]
    repair = policy.get("repair")
    if not isinstance(repair, dict):
        return ["POLICY_REPAIR_SECTION_INVALID"]
    errors = []
    expected_repair_fields = {
        "repair_round_definition",
        "non_counting_actions",
        "chain_identity_fields",
        "ledger_schema",
        "evidence_trust_boundary",
        "record_only_finding",
        "base_auto_rounds",
        "autonomous_max_rounds",
        "history",
        "required_true_fields",
        "required_false_fields",
        "round_3_progress",
        "task_change_resets_budget",
        "model_change_resets_budget",
        "post_stop",
        "mechanical_decisions",
        "promotion_decisions",
        "promotion_requires_trusted_orchestrator",
        "eligible_modes",
    }
    if set(repair) - expected_repair_fields:
        errors.append("POLICY_UNKNOWN_REPAIR_FIELDS")
    exact_values = {
        "repair_round_definition": "patch_to_next_independent_review",
        "ledger_schema": LEDGER_SCHEMA,
        "evidence_trust_boundary": "ledger_is_untrusted_trusted_context_is_supplied_by_project_or_harness",
        "base_auto_rounds": 2,
        "autonomous_max_rounds": 3,
        "task_change_resets_budget": False,
        "model_change_resets_budget": False,
        "promotion_requires_trusted_orchestrator": True,
    }
    for name, expected in exact_values.items():
        if repair.get(name) != expected:
            errors.append(f"POLICY_CONFLICT_{name.upper()}")
    for name in ("base_auto_rounds", "autonomous_max_rounds"):
        value = repair.get(name)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            errors.append(f"POLICY_INVALID_{name.upper()}")
    if not errors and repair["base_auto_rounds"] >= repair["autonomous_max_rounds"]:
        errors.append("POLICY_INVALID_AUTO_ROUND_LIMITS")
    for name in (
        "chain_identity_fields",
        "non_counting_actions",
        "required_true_fields",
        "required_false_fields",
        "mechanical_decisions",
        "promotion_decisions",
        "eligible_modes",
    ):
        value = repair.get(name)
        if not isinstance(value, list) or not value or any(not isinstance(item, str) or not item for item in value):
            errors.append(f"POLICY_INVALID_{name.upper()}")
    expected_lists = {
        "chain_identity_fields": [
            "repair_chain_id",
            "finding_ids",
            "closure_contract_hash",
            "allowed_files_hash",
        ],
        "non_counting_actions": [
            "diagnostic_evidence_only",
            "record_only_correction",
            "review_only",
            "task_or_board_receipt_sync",
            "test_rerun_without_patch",
            "ua_without_patch",
        ],
        "required_true_fields": [
            "dependencies_frozen",
            "authority_frozen",
            "root_cause_known",
            "reviewer_capable",
            "repairer_capable",
            "within_cost_boundary",
        ],
        "required_false_fields": ["external_side_effect"],
        "mechanical_decisions": ["MechanicallyEligible", "Stop", "Blocked"],
        "promotion_decisions": [
            "AutoRepairAllowed",
            "ExtendRound3",
            "EscalatedRepairAllowed",
        ],
        "eligible_modes": ["AutoRepair", "ExtendRound3", "EscalatedRepair"],
    }
    for name, expected in expected_lists.items():
        if repair.get(name) != expected:
            errors.append(f"POLICY_CONFLICT_{name.upper()}")
    expected_record_only = {
        "default_severity": ["P2", "P3"],
        "p1_only_if": [
            "can_authorize_unsafe_action",
            "can_hide_blocking_finding",
        ],
    }
    record_only = repair.get("record_only_finding")
    if isinstance(record_only, dict) and set(record_only) - set(expected_record_only):
        errors.append("POLICY_UNKNOWN_RECORD_ONLY_FIELDS")
    if record_only != expected_record_only:
        errors.append("POLICY_CONFLICT_RECORD_ONLY_FINDING")
    for name in ("history", "round_3_progress", "post_stop"):
        if not isinstance(repair.get(name), dict):
            errors.append(f"POLICY_INVALID_{name.upper()}")
    history = repair.get("history")
    expected_history = {
        "attempt_count_source": "validated_receipt_chain",
        "receipt_hash_algorithm": "sha256_canonical_json",
        "require_history_anchor": True,
        "require_trusted_context": True,
        "trusted_context_schema": TRUSTED_CONTEXT_SCHEMA,
        "require_independent_review_receipt_after_each_attempt": True,
    }
    if isinstance(history, dict):
        if set(history) - set(expected_history):
            errors.append("POLICY_UNKNOWN_HISTORY_FIELDS")
        for name, expected in expected_history.items():
            if history.get(name) != expected:
                errors.append(f"POLICY_CONFLICT_HISTORY_{name.upper()}")
    progress = repair.get("round_3_progress")
    expected_progress = {
        "source": "latest_independent_review_receipt",
        "require_red_to_green": True,
        "forbid_green_to_red": True,
        "forbid_new_blocking_findings": True,
        "severity_must_not_increase": True,
        "evidence_coverage_must_strictly_increase": True,
        "round_3_target_required": True,
    }
    if isinstance(progress, dict):
        if set(progress) - set(expected_progress):
            errors.append("POLICY_UNKNOWN_PROGRESS_FIELDS")
        for name, expected in expected_progress.items():
            if progress.get(name) != expected:
                errors.append(f"POLICY_CONFLICT_PROGRESS_{name.upper()}")
    post_stop = repair.get("post_stop")
    if isinstance(post_stop, dict):
        exact_post_stop = {
            "state": "UserDecisionRequired",
            "mode": "EscalatedRepair",
            "ai_repair_allowed_with_explicit_authority": True,
            "manual_implementation_required": False,
            "default_authorized_attempts": 1,
            "authority_source": "trusted_context_attested_chain_bound_authority_receipt",
            "independent_review_after_each_attempt": True,
            "history_resets": False,
            "failure_decision": "Stop",
        }
        expected_post_stop_fields = set(exact_post_stop) | {"authority_must_bind"}
        if set(post_stop) - expected_post_stop_fields:
            errors.append("POLICY_UNKNOWN_POST_STOP_FIELDS")
        for name, expected in exact_post_stop.items():
            if post_stop.get(name) != expected:
                errors.append(f"POLICY_CONFLICT_POST_STOP_{name.upper()}")
        default = post_stop.get("default_authorized_attempts")
        if not isinstance(default, int) or isinstance(default, bool) or default < 1:
            errors.append("POLICY_INVALID_DEFAULT_AUTHORIZED_ATTEMPTS")
        binds = post_stop.get("authority_must_bind")
        expected_binds = [
            "repair_chain_digest",
            "closure_contract_hash",
            "allowed_files_hash",
            "target_finding_ids",
            "authorized_attempt_ids",
        ]
        if binds != expected_binds:
            errors.append("POLICY_CONFLICT_AUTHORITY_MUST_BIND")
    return errors


def _is_hash(value):
    return isinstance(value, str) and HASH_PATTERN.fullmatch(value) is not None


def _unique_strings(value):
    return (
        isinstance(value, list)
        and value
        and all(isinstance(item, str) and item for item in value)
        and len(value) == len(set(value))
    )


def _result(
    decision,
    reasons,
    policy,
    state=None,
    attempt=None,
    authority_hash=None,
    eligible_mode=None,
):
    state = state or {}
    chain = state.get("chain")
    return {
        "decision": decision,
        "eligible_mode": eligible_mode,
        "reason_codes": list(reasons),
        "next_attempt_id": attempt,
        "authority_receipt_hash": authority_hash,
        "auto_attempts_used": state.get("auto_attempts_used", 0),
        "escalated_attempts_used": state.get("escalated_attempts_used", 0),
        "history_head_hash": state.get("history_head_hash"),
        "repair_chain_digest": canonical_hash(chain) if isinstance(chain, dict) else None,
        "would_consume_auto_repair_budget": eligible_mode in {"AutoRepair", "ExtendRound3"},
        "would_consume_escalated_authority": eligible_mode == "EscalatedRepair",
        "manual_implementation_required": False,
        "requires_trusted_orchestrator_promotion": decision == "MechanicallyEligible",
        "policy_digest": policy_digest(policy),
    }


def _validate_chain(chain):
    errors = []
    if not isinstance(chain, dict):
        return ["INVALID_REPAIR_CHAIN"]
    if not isinstance(chain.get("repair_chain_id"), str) or not chain["repair_chain_id"]:
        errors.append("INVALID_REPAIR_CHAIN_ID")
    if not _unique_strings(chain.get("finding_ids")):
        errors.append("INVALID_FINDING_IDS")
    for name in ("closure_contract_hash", "allowed_files_hash"):
        if not _is_hash(chain.get(name)):
            errors.append(f"INVALID_{name.upper()}")
    return errors


def _validate_safety(safety, repair):
    if not isinstance(safety, dict):
        return ["INVALID_SAFETY_INPUT"]
    errors = []
    for name in repair["required_true_fields"]:
        if safety.get(name) is not True:
            errors.append(f"REQUIRED_TRUE_{name.upper()}")
    for name in repair["required_false_fields"]:
        if safety.get(name) is not False:
            errors.append(f"REQUIRED_FALSE_{name.upper()}")
    return errors


def _validate_review(review, chain, expected_subject_id, expected_subject_hash, digest):
    errors = []
    if not isinstance(review, dict):
        return ["INVALID_REVIEW_RECEIPT"]
    expected = {
        "subject_id": expected_subject_id,
        "subject_hash": expected_subject_hash,
        "repair_chain_digest": canonical_hash(chain),
        "policy_digest": digest,
        "finding_ids": chain["finding_ids"],
    }
    for name, value in expected.items():
        if review.get(name) != value:
            errors.append(f"REVIEW_BINDING_{name.upper()}")
    if not isinstance(review.get("review_id"), str) or not review["review_id"]:
        errors.append("INVALID_REVIEW_ID")
    if not isinstance(review.get("reviewer_ref"), str) or not review["reviewer_ref"].startswith("review:"):
        errors.append("INVALID_REVIEWER_REF")
    if review.get("context_isolated") is not True or review.get("write_isolated") is not True:
        errors.append("REVIEW_NOT_INDEPENDENT_READ_ONLY")
    if review.get("decision") not in REVIEW_DECISIONS:
        errors.append("INVALID_REVIEW_DECISION")
    if not _is_hash(review.get("receipt_hash")) or review.get("receipt_hash") != receipt_hash(review):
        errors.append("INVALID_REVIEW_RECEIPT_HASH")
    return errors


def _progress_reasons(review, chain):
    progress = review.get("progress") if isinstance(review, dict) else None
    if not isinstance(progress, dict):
        return ["ROUND3_PROGRESS_RECEIPT_MISSING"]
    reasons = []
    target = progress.get("target_finding_id")
    if target not in chain["finding_ids"]:
        reasons.append("ROUND3_TARGET_FINDING_NOT_FROZEN")

    before = progress.get("closure_before")
    after = progress.get("closure_after")
    if (
        not isinstance(before, dict)
        or not before
        or not isinstance(after, dict)
        or set(before) != set(after)
        or any(value not in {"RED", "GREEN"} for value in list(before.values()) + list(after.values()))
    ):
        reasons.append("ROUND3_CLOSURE_VECTOR_INVALID")
    else:
        if not any(before[key] == "RED" and after[key] == "GREEN" for key in before):
            reasons.append("ROUND3_NO_RED_TO_GREEN")
        if any(before[key] == "GREEN" and after[key] != "GREEN" for key in before):
            reasons.append("ROUND3_GREEN_TO_RED")

    blocking_before = progress.get("blocking_findings_before")
    blocking_after = progress.get("blocking_findings_after")
    if not isinstance(blocking_before, list) or not isinstance(blocking_after, list):
        reasons.append("ROUND3_BLOCKING_FINDINGS_INVALID")
    elif not set(blocking_after).issubset(set(blocking_before)):
        reasons.append("ROUND3_NEW_BLOCKING_FINDING")

    severity_before = progress.get("severity_before")
    severity_after = progress.get("severity_after")
    if not isinstance(severity_before, dict) or not isinstance(severity_after, dict):
        reasons.append("ROUND3_SEVERITY_VECTOR_INVALID")
    else:
        for finding_id, old in severity_before.items():
            new = severity_after.get(finding_id)
            if old not in SEVERITY_RANK or new not in SEVERITY_RANK or SEVERITY_RANK[new] < SEVERITY_RANK[old]:
                reasons.append("ROUND3_SEVERITY_INCREASED")
                break
        if any(
            finding_id not in severity_before and value in {"P0", "P1"}
            for finding_id, value in severity_after.items()
        ):
            reasons.append("ROUND3_NEW_BLOCKING_SEVERITY")

    vector = progress.get("evidence_vector")
    covered_before = progress.get("evidence_before")
    covered_after = progress.get("evidence_after")
    if not all(isinstance(item, list) for item in (vector, covered_before, covered_after)):
        reasons.append("ROUND3_EVIDENCE_VECTOR_INVALID")
    elif (
        len(vector) != len(set(vector))
        or not set(covered_before).issubset(set(vector))
        or not set(covered_after).issubset(set(vector))
        or not set(covered_before) < set(covered_after)
    ):
        reasons.append("ROUND3_EVIDENCE_NOT_INCREASED")
    if not isinstance(progress.get("round_3_target"), str) or not progress["round_3_target"].strip():
        reasons.append("ROUND3_TARGET_MISSING")
    return reasons


def _effective_authorized_attempt_ids(authority, repair):
    value = authority.get("authorized_attempt_ids")
    if value is None:
        start = authority.get("next_attempt_id_at_issue")
        match = ATTEMPT_PATTERN.fullmatch(start or "")
        if not match or match.group(1) != "ER":
            return []
        count = repair["post_stop"]["default_authorized_attempts"]
        first = int(match.group(2))
        return [f"ER-{first + offset}" for offset in range(count)]
    return value if isinstance(value, list) else []


def _validate_authority(authority, chain, repair):
    errors = []
    if not isinstance(authority, dict):
        return ["INVALID_AUTHORITY_RECEIPT"], []
    if not isinstance(authority.get("authority_id"), str) or not authority["authority_id"]:
        errors.append("INVALID_AUTHORITY_ID")
    if authority.get("source_kind") != "user_message":
        errors.append("AUTHORITY_SOURCE_NOT_USER_MESSAGE")
    if not isinstance(authority.get("source_ref"), str) or not EVIDENCE_REF_PATTERN.fullmatch(authority["source_ref"]):
        errors.append("INVALID_AUTHORITY_SOURCE_REF")
    if not _is_hash(authority.get("source_text_sha256")):
        errors.append("INVALID_AUTHORITY_SOURCE_HASH")
    bindings = {
        "repair_chain_digest": canonical_hash(chain),
        "closure_contract_hash": chain["closure_contract_hash"],
        "allowed_files_hash": chain["allowed_files_hash"],
    }
    for name, value in bindings.items():
        if authority.get(name) != value:
            errors.append(f"AUTHORITY_BINDING_{name.upper()}")
    targets = authority.get("target_finding_ids")
    if not _unique_strings(targets) or not set(targets).issubset(set(chain["finding_ids"])):
        errors.append("AUTHORITY_TARGETS_NOT_FROZEN")
    effective = _effective_authorized_attempt_ids(authority, repair)
    if not _unique_strings(effective):
        errors.append("INVALID_AUTHORIZED_ATTEMPT_IDS")
    else:
        parsed = [ATTEMPT_PATTERN.fullmatch(item) for item in effective]
        if any(match is None or match.group(1) != "ER" for match in parsed):
            errors.append("INVALID_AUTHORIZED_ATTEMPT_IDS")
        else:
            numbers = [int(match.group(2)) for match in parsed]
            expected = list(range(numbers[0], numbers[0] + len(numbers)))
            if numbers != expected or authority.get("next_attempt_id_at_issue") != effective[0]:
                errors.append("NONCONTIGUOUS_AUTHORIZED_ATTEMPTS")
    if not isinstance(authority.get("target"), str) or not authority["target"].strip():
        errors.append("AUTHORITY_TARGET_MISSING")
    if not _is_hash(authority.get("receipt_hash")) or authority.get("receipt_hash") != receipt_hash(authority):
        errors.append("INVALID_AUTHORITY_RECEIPT_HASH")
    return errors, effective


def _validate_history(ledger, chain, policy):
    repair = policy["repair"]
    digest = policy_digest(policy)
    errors = []
    trigger = ledger.get("trigger_review")
    errors.extend(_validate_review(trigger, chain, "TRIGGER", chain["closure_contract_hash"], digest))
    if errors:
        return errors, {}

    authorities = ledger.get("authority_records")
    if not isinstance(authorities, list):
        return ["INVALID_AUTHORITY_RECORDS"], {}
    authority_by_hash = {}
    authority_attempts = {}
    authority_ids = set()
    for authority in authorities:
        authority_errors, effective = _validate_authority(authority, chain, repair)
        errors.extend(authority_errors)
        if isinstance(authority, dict):
            authority_id = authority.get("authority_id")
            if authority_id in authority_ids:
                errors.append("DUPLICATE_AUTHORITY_ID")
            authority_ids.add(authority_id)
            authority_by_hash[authority.get("receipt_hash")] = authority
            for attempt_id in effective:
                authority_attempts.setdefault(attempt_id, []).append(authority.get("receipt_hash"))

    attempts = ledger.get("attempts")
    if not isinstance(attempts, list):
        return errors + ["INVALID_ATTEMPT_HISTORY"], {}
    previous_hash = trigger["receipt_hash"]
    previous_review = trigger
    review_receipt_hashes = [trigger["receipt_hash"]]
    used_authority_hashes = []
    auto_used = 0
    escalated_used = 0
    escalated_started = False
    seen_attempts = set()
    seen_receipts = {previous_hash}

    for attempt in attempts:
        if not isinstance(attempt, dict):
            errors.append("INVALID_ATTEMPT_RECEIPT")
            continue
        attempt_id = attempt.get("attempt_id")
        mode = attempt.get("mode")
        if previous_review.get("decision") != "Needs Fix":
            errors.append("ATTEMPT_AFTER_NON_REPAIRABLE_REVIEW")
        if attempt_id in seen_attempts:
            errors.append("DUPLICATE_ATTEMPT_ID")
        seen_attempts.add(attempt_id)
        if mode == "AutoRepair" and not escalated_started:
            auto_used += 1
            expected_id = f"AR-{auto_used}"
            expected_gate = "AutoRepairAllowed" if auto_used <= repair["base_auto_rounds"] else "ExtendRound3"
            if auto_used > repair["autonomous_max_rounds"]:
                errors.append("AUTO_HISTORY_EXCEEDS_MAX")
            if auto_used == repair["autonomous_max_rounds"]:
                errors.extend(_progress_reasons(previous_review, chain))
            if attempt.get("authority_receipt_hash") not in {None, ""}:
                errors.append("AUTO_ATTEMPT_HAS_ESCALATION_AUTHORITY")
        elif mode == "EscalatedRepair":
            escalated_started = True
            escalated_used += 1
            expected_id = f"ER-{escalated_used}"
            expected_gate = "EscalatedRepairAllowed"
            if auto_used < repair["base_auto_rounds"]:
                errors.append("ESCALATION_HISTORY_BEFORE_AUTO_STOP")
            if auto_used == repair["base_auto_rounds"] and not _progress_reasons(previous_review, chain):
                errors.append("ESCALATION_HISTORY_WHILE_AR3_ALLOWED")
            authority_hash = attempt.get("authority_receipt_hash")
            if authority_hash not in authority_by_hash or authority_hash not in authority_attempts.get(attempt_id, []):
                errors.append("ATTEMPT_AUTHORITY_NOT_BOUND")
            else:
                used_authority_hashes.append(authority_hash)
        else:
            errors.append("INVALID_ATTEMPT_MODE")
            expected_id = attempt_id
            expected_gate = None
        if attempt_id != expected_id:
            errors.append("ATTEMPT_SEQUENCE_GAP")
        if attempt.get("gate_decision") != expected_gate:
            errors.append("ATTEMPT_GATE_DECISION_MISMATCH")
        if attempt.get("previous_receipt_hash") != previous_hash:
            errors.append("ATTEMPT_HISTORY_LINK_MISMATCH")
        if attempt.get("repair_chain_digest") != canonical_hash(chain):
            errors.append("ATTEMPT_CHAIN_BINDING_MISMATCH")
        if attempt.get("policy_digest") != digest:
            errors.append("ATTEMPT_POLICY_BINDING_MISMATCH")
        patch_hash = attempt.get("patch_hash")
        if not _is_hash(patch_hash):
            errors.append("INVALID_PATCH_HASH")
        review = attempt.get("review")
        errors.extend(_validate_review(review, chain, attempt_id, patch_hash, digest))
        attempt_receipt = attempt.get("receipt_hash")
        if not _is_hash(attempt_receipt) or attempt_receipt != receipt_hash(attempt):
            errors.append("INVALID_ATTEMPT_RECEIPT_HASH")
        if attempt_receipt in seen_receipts:
            errors.append("DUPLICATE_RECEIPT_HASH")
        seen_receipts.add(attempt_receipt)
        previous_hash = attempt_receipt
        if isinstance(review, dict):
            previous_review = review
            if _is_hash(review.get("receipt_hash")):
                review_receipt_hashes.append(review["receipt_hash"])

    anchor = ledger.get("history_anchor")
    if not isinstance(anchor, dict):
        errors.append("INVALID_HISTORY_ANCHOR")
    else:
        if anchor.get("attempt_count") != len(attempts):
            errors.append("HISTORY_ANCHOR_COUNT_MISMATCH")
        if anchor.get("head_receipt_hash") != previous_hash:
            errors.append("HISTORY_ANCHOR_HEAD_MISMATCH")
        if not isinstance(anchor.get("source_ref"), str) or not EVIDENCE_REF_PATTERN.fullmatch(anchor["source_ref"]):
            errors.append("INVALID_HISTORY_ANCHOR_REF")
        if not _is_hash(anchor.get("source_text_sha256")):
            errors.append("INVALID_HISTORY_ANCHOR_SOURCE_HASH")

    state = {
        "chain": chain,
        "auto_attempts_used": auto_used,
        "escalated_attempts_used": escalated_used,
        "history_head_hash": previous_hash,
        "latest_review": previous_review,
        "authority_attempts": authority_attempts,
        "review_receipt_hashes": review_receipt_hashes,
        "used_authority_hashes": used_authority_hashes,
    }
    return errors, state


def _validate_trusted_context(context, state):
    if not isinstance(context, dict):
        return ["TRUSTED_CONTEXT_REQUIRED"], {}
    errors = []
    if context.get("schema_version") != TRUSTED_CONTEXT_SCHEMA:
        errors.append("TRUSTED_CONTEXT_SCHEMA_INVALID")
    if context.get("provider") not in {
        "harness",
        "project_readonly_snapshot",
        "orchestrator_current_conversation",
    }:
        errors.append("TRUSTED_CONTEXT_PROVIDER_INVALID")
    if not isinstance(context.get("source_ref"), str) or not EVIDENCE_REF_PATTERN.fullmatch(context["source_ref"]):
        errors.append("TRUSTED_CONTEXT_SOURCE_REF_INVALID")
    if context.get("repair_chain_digest") != canonical_hash(state["chain"]):
        errors.append("TRUSTED_CONTEXT_CHAIN_MISMATCH")
    if context.get("expected_attempt_count") != (
        state["auto_attempts_used"] + state["escalated_attempts_used"]
    ):
        errors.append("TRUSTED_CONTEXT_ATTEMPT_COUNT_MISMATCH")
    if context.get("expected_history_head_hash") != state["history_head_hash"]:
        errors.append("TRUSTED_CONTEXT_HISTORY_HEAD_MISMATCH")
    verified_reviews = context.get("verified_review_receipt_hashes")
    if (
        not _unique_strings(verified_reviews)
        or not set(state["review_receipt_hashes"]).issubset(set(verified_reviews))
    ):
        errors.append("TRUSTED_CONTEXT_REVIEW_RECEIPTS_MISSING")
        verified_reviews = []
    verified_authorities = context.get("verified_authority_receipt_hashes")
    if not isinstance(verified_authorities, list) or len(verified_authorities) != len(set(verified_authorities)):
        errors.append("TRUSTED_CONTEXT_AUTHORITY_RECEIPTS_INVALID")
        verified_authorities = []
    elif not all(_is_hash(item) for item in verified_authorities):
        errors.append("TRUSTED_CONTEXT_AUTHORITY_RECEIPTS_INVALID")
        verified_authorities = []
    elif not set(state["used_authority_hashes"]).issubset(set(verified_authorities)):
        errors.append("TRUSTED_CONTEXT_USED_AUTHORITY_MISSING")
    if not _is_hash(context.get("attestation_hash")) or context.get("attestation_hash") != attestation_hash(context):
        errors.append("TRUSTED_CONTEXT_ATTESTATION_HASH_INVALID")
    return errors, {
        "verified_review_receipt_hashes": verified_reviews,
        "verified_authority_receipt_hashes": verified_authorities,
    }


def _auto_decision(policy, state):
    repair = policy["repair"]
    latest = state["latest_review"]
    if latest["decision"] == "Passed":
        return "Stop", ["REPAIR_ALREADY_PASSED"], None
    if latest["decision"] == "Blocked":
        return "Blocked", ["LATEST_REVIEW_BLOCKED"], None
    used = state["auto_attempts_used"]
    if state["escalated_attempts_used"] > 0 or used >= repair["autonomous_max_rounds"]:
        return "Stop", ["AUTONOMOUS_MAX_REACHED", "USER_DECISION_REQUIRED"], None
    if used < repair["base_auto_rounds"]:
        return "AutoRepairAllowed", ["BASE_AUTO_BUDGET_AVAILABLE"], f"AR-{used + 1}"
    progress_errors = _progress_reasons(latest, state["chain"])
    if progress_errors:
        return "Stop", progress_errors + ["USER_DECISION_REQUIRED"], None
    return "ExtendRound3", ["ROUND3_PROGRESS_RECEIPT_VERIFIED"], "AR-3"


def evaluate(ledger, policy, trusted_context=None):
    policy_errors = validate_policy(policy)
    if policy_errors:
        return _result("Blocked", policy_errors, policy)
    if not isinstance(ledger, dict):
        return _result("Blocked", ["LEDGER_NOT_OBJECT"], policy)
    if ledger.get("schema_version") != LEDGER_SCHEMA:
        return _result("Blocked", ["UNSUPPORTED_LEDGER_SCHEMA"], policy)
    requested = ledger.get("requested_mode")
    if requested not in {"AutoRepair", "EscalatedRepair"}:
        return _result("Blocked", ["INVALID_REQUESTED_MODE"], policy)
    for name in ("current_task_id", "current_model"):
        if not isinstance(ledger.get(name), str) or not ledger[name]:
            return _result("Blocked", [f"INVALID_{name.upper()}"], policy)

    chain = ledger.get("repair_chain")
    errors = _validate_chain(chain)
    if errors:
        return _result("Blocked", errors, policy)
    errors.extend(_validate_safety(ledger.get("safety"), policy["repair"]))
    history_errors, state = _validate_history(ledger, chain, policy)
    errors.extend(history_errors)
    if errors:
        return _result("Blocked", errors, policy, state={"chain": chain})
    trusted_errors, trusted = _validate_trusted_context(trusted_context, state)
    if trusted_errors:
        return _result("Blocked", trusted_errors, policy, state)

    decision, reasons, attempt = _auto_decision(policy, state)
    if requested == "AutoRepair":
        if decision in {"AutoRepairAllowed", "ExtendRound3"}:
            mode = "AutoRepair" if decision == "AutoRepairAllowed" else "ExtendRound3"
            return _result(
                "MechanicallyEligible",
                reasons + ["TRUSTED_CONTEXT_VERIFIED"],
                policy,
                state,
                attempt,
                eligible_mode=mode,
            )
        return _result(decision, reasons, policy, state)
    if decision == "Blocked":
        return _result(decision, reasons, policy, state)
    if decision != "Stop":
        return _result(
            "Blocked",
            ["ESCALATION_ONLY_AFTER_AUTO_STOP", f"AUTO_DECISION_{decision.upper()}"],
            policy,
            state,
        )
    if "REPAIR_ALREADY_PASSED" in reasons:
        return _result("Stop", reasons, policy, state)

    next_attempt = f"ER-{state['escalated_attempts_used'] + 1}"
    candidates = state["authority_attempts"].get(next_attempt, [])
    if candidates and not any(
        item in trusted["verified_authority_receipt_hashes"] for item in candidates
    ):
        return _result(
            "Blocked",
            ["CANDIDATE_AUTHORITY_NOT_ATTESTED"],
            policy,
            state,
        )
    matching = candidates
    matching = [
        item
        for item in matching
        if item in trusted["verified_authority_receipt_hashes"]
    ]
    if not matching:
        return _result(
            "Stop",
            ["ESCALATED_AUTHORITY_MISSING", "USER_DECISION_REQUIRED"],
            policy,
            state,
        )
    authority_hash = matching[-1]
    return _result(
        "MechanicallyEligible",
        [
            "CHAIN_BOUND_USER_AUTHORITY_ATTESTED",
            "PRIOR_ATTEMPTS_INDEPENDENTLY_REVIEWED",
            "TRUSTED_CONTEXT_VERIFIED",
        ],
        policy,
        state,
        next_attempt,
        authority_hash,
        "EscalatedRepair",
    )


def _read_json_object(target, label):
    try:
        text = sys.stdin.read() if target == "-" else pathlib.Path(target).read_text(encoding="utf-8")
        value = json.loads(text)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InvocationError(f"cannot read {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise InvocationError(f"{label} must be a JSON object")
    return value


def _emit_human(result):
    print(f"repair gate: decision={result['decision']}")
    print(f"eligible_mode={result['eligible_mode'] or 'none'}")
    print("reason_codes=" + ",".join(result["reason_codes"]))
    print(f"next_attempt_id={result['next_attempt_id'] or 'none'}")
    print(f"policy_digest={result['policy_digest']}")
    print("只读判定不会修改 TASK、代码、Git 或外部系统；MechanicallyEligible 仍须由持有真实上游证据的 Orchestrator 提升为 Allowed。")


def _requested_format(argv):
    values = list(sys.argv[1:] if argv is None else argv)
    if "--format" in values:
        index = values.index("--format")
        if index + 1 < len(values) and values[index + 1] == "json":
            return "json"
    return "human"


def main(argv=None):
    output_format = _requested_format(argv)
    parser = ReadOnlyParser(description="只读判定 receipt-backed AutoRepair / EscalatedRepair 边界。")
    default_policy = pathlib.Path(__file__).resolve().parents[1] / "references" / "CORE.md"
    parser.add_argument("target", nargs="?", help="repair ledger JSON；使用 - 从 stdin 读取")
    parser.add_argument("--policy", default=str(default_policy))
    parser.add_argument("--trusted-context", help="由 harness / 只读项目快照 / 当前 Orchestrator 提供的独立 JSON")
    parser.add_argument("--policy-digest", action="store_true")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    try:
        args = parser.parse_args(argv)
        policy = load_policy(args.policy)
        policy_errors = validate_policy(policy)
        if policy_errors:
            result = _result("Blocked", policy_errors, policy)
        elif args.policy_digest:
            print(
                json.dumps({"policy_digest": policy_digest(policy)}, ensure_ascii=False, sort_keys=True)
                if args.format == "json"
                else policy_digest(policy)
            )
            return 0
        elif not args.target:
            raise InvocationError("target is required unless --policy-digest is used")
        else:
            trusted_context = (
                _read_json_object(args.trusted_context, "trusted context")
                if args.trusted_context
                else None
            )
            result = evaluate(
                _read_json_object(args.target, "repair ledger"),
                policy,
                trusted_context,
            )
    except InvocationError as exc:
        payload = {"decision": "Blocked", "reason_codes": ["INVOCATION_ERROR"], "message": str(exc)}
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True) if output_format == "json" else f"[error] {exc}")
        return 2
    except (KeyError, TypeError, ValueError) as exc:
        payload = {"decision": "Blocked", "reason_codes": ["POLICY_OR_LEDGER_EVALUATION_ERROR"], "message": str(exc)}
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True) if output_format == "json" else f"[error] {exc}")
        return 2

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        _emit_human(result)
    if result["decision"] in ALLOWED_DECISIONS:
        return 0
    return 1 if result["decision"] == "Stop" else 2


if __name__ == "__main__":
    raise SystemExit(main())
