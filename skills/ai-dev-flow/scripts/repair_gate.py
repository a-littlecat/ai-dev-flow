"""Read-only evaluator for receipt-backed AutoRepair and repair authorities."""

import sys
sys.dont_write_bytecode = True

import argparse
import hashlib
import json
import pathlib
import re

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from policy_loader import (
    PolicyLoadError,
    load_policy_document,
    thaw_policy,
    validate_policy_value,
)


LEDGER_SCHEMA = "ai-dev-flow/repair-ledger-v1"
TRUSTED_CONTEXT_SCHEMA = "ai-dev-flow/repair-trusted-context-v1"
CAMPAIGN_STATE_SCHEMA = "ai-dev-flow/repair-campaign-state-v1"
CURRENT_POLICY_SCHEMA = "adf/repair-campaign/v1"
LEGACY_SINGLE_POLICY_SCHEMA = "ai-dev-flow/v0.8-policy-rc2"
LEGACY_CAMPAIGN_POLICY_SCHEMA = "ai-dev-flow/v0.8-policy-rc3"
ALLOWED_DECISIONS = {"MechanicallyEligible"}
REVIEW_DECISIONS = {"Passed", "Needs Fix", "Blocked"}
SEVERITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "Closed": 4}
HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
ATTEMPT_PATTERN = re.compile(r"^(AR|ER)-([1-9][0-9]*)$")
EVIDENCE_REF_PATTERN = re.compile(r"^(conversation|task):[^#]+#[^#]+$")
CAMPAIGN_PROFILES = {"core_product", "harness"}
CAMPAIGN_OUTCOMES = {"NotStarted", "MeasurableProgress", "NoProgress"}


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
        return thaw_policy(load_policy_document(path))
    except PolicyLoadError as exc:
        raise InvocationError(str(exc)) from exc


def _required_object_fields(value, required, code):
    if not isinstance(value, dict):
        return [f"POLICY_INVALID_{code}"]
    errors = []
    missing = set(required) - set(value)
    if missing:
        errors.append(f"POLICY_MISSING_{code}_FIELDS")
    return errors


def validate_policy(policy, *, allow_legacy_single=False):
    """Validate in-memory policies while preserving structured legacy reason codes."""

    if not isinstance(policy, dict):
        return ["POLICY_NOT_OBJECT"]
    schema = policy.get("schema_version")
    allowed_schemas = {CURRENT_POLICY_SCHEMA, LEGACY_CAMPAIGN_POLICY_SCHEMA}
    if allow_legacy_single:
        allowed_schemas.add(LEGACY_SINGLE_POLICY_SCHEMA)
    if schema not in allowed_schemas:
        return ["POLICY_CONFLICT_SCHEMA_VERSION"]

    try:
        validate_policy_value(policy)
        constraint_errors = []
    except PolicyLoadError:
        constraint_errors = ["POLICY_CONSTRAINT_VIOLATION"]

    legacy_single = schema == LEGACY_SINGLE_POLICY_SCHEMA
    allowed_top = (
        {"schema_version", "repair"}
        if schema == CURRENT_POLICY_SCHEMA
        else {
            "schema_version", "unknown_input", "routes", "review", "safety",
            "reviewer_selection", "repair",
        }
    )
    errors = list(constraint_errors)
    if set(policy) - allowed_top:
        errors.append("POLICY_UNKNOWN_TOP_LEVEL_FIELDS")
    repair = policy.get("repair")
    if not isinstance(repair, dict):
        return errors + ["POLICY_REPAIR_SECTION_INVALID"]

    required_repair = {
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
    if not legacy_single:
        required_repair.add("campaign")
    unknown = set(repair) - required_repair
    missing = required_repair - set(repair)
    if unknown:
        errors.append("POLICY_UNKNOWN_REPAIR_FIELDS")
    if missing:
        errors.append("POLICY_MISSING_REPAIR_FIELDS")

    for name in ("base_auto_rounds", "autonomous_max_rounds"):
        value = repair.get(name)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            errors.append(f"POLICY_INVALID_{name.upper()}")
    base = repair.get("base_auto_rounds")
    maximum = repair.get("autonomous_max_rounds")
    if isinstance(base, int) and isinstance(maximum, int) and base >= maximum:
        errors.append("POLICY_INVALID_AUTO_ROUND_LIMITS")

    for name in (
        "non_counting_actions",
        "chain_identity_fields",
        "required_true_fields",
        "required_false_fields",
        "mechanical_decisions",
        "promotion_decisions",
        "eligible_modes",
    ):
        value = repair.get(name)
        if (
            not isinstance(value, list)
            or not value
            or len(value) != len(set(value))
            or any(not isinstance(item, str) or not item for item in value)
        ):
            errors.append(f"POLICY_INVALID_{name.upper()}")

    for name in (
        "task_change_resets_budget",
        "model_change_resets_budget",
        "promotion_requires_trusted_orchestrator",
    ):
        if not isinstance(repair.get(name), bool):
            errors.append(f"POLICY_INVALID_{name.upper()}")

    errors.extend(_required_object_fields(
        repair.get("record_only_finding"),
        {"default_severity", "p1_only_if"},
        "RECORD_ONLY_FINDING",
    ))
    errors.extend(_required_object_fields(
        repair.get("history"),
        {
            "attempt_count_source",
            "receipt_hash_algorithm",
            "require_history_anchor",
            "require_trusted_context",
            "trusted_context_schema",
            "require_independent_review_receipt_after_each_attempt",
        },
        "HISTORY",
    ))
    errors.extend(_required_object_fields(
        repair.get("round_3_progress"),
        {
            "source",
            "require_red_to_green",
            "forbid_green_to_red",
            "forbid_new_blocking_findings",
            "severity_must_not_increase",
            "evidence_coverage_must_strictly_increase",
            "round_3_target_required",
        },
        "ROUND_3_PROGRESS",
    ))
    errors.extend(_required_object_fields(
        repair.get("post_stop"),
        {
            "state",
            "mode",
            "ai_repair_allowed_with_explicit_authority",
            "manual_implementation_required",
            "default_authorized_attempts",
            "authority_source",
            "authority_must_bind",
            "independent_review_after_each_attempt",
            "history_resets",
            "failure_decision",
        },
        "POST_STOP",
    ))
    if not legacy_single:
        errors.extend(_required_object_fields(
            repair.get("campaign"),
            {
                "authority_mode",
                "ai_repair_allowed_with_explicit_authority",
                "authority_source",
                "authority_must_bind",
                "profiles",
                "scope_manifest",
                "progress_source",
                "progress_resets_no_progress_streak",
                "task_change_resets_streak",
                "model_change_resets_streak",
                "chain_change_resets_streak",
                "hard_stop_flags",
                "independent_review_after_each_attempt",
                "delivery_authority_separate",
            },
            "CAMPAIGN",
        ))

    history = repair.get("history", {})
    if isinstance(history, dict):
        if history.get("trusted_context_schema") != TRUSTED_CONTEXT_SCHEMA:
            errors.append("POLICY_CONFLICT_HISTORY_TRUSTED_CONTEXT_SCHEMA")
        for name in (
            "require_history_anchor",
            "require_trusted_context",
            "require_independent_review_receipt_after_each_attempt",
        ):
            if not isinstance(history.get(name), bool):
                errors.append(f"POLICY_INVALID_HISTORY_{name.upper()}")

    post_stop = repair.get("post_stop", {})
    if isinstance(post_stop, dict):
        default = post_stop.get("default_authorized_attempts")
        if not isinstance(default, int) or isinstance(default, bool) or default < 1:
            errors.append("POLICY_INVALID_DEFAULT_AUTHORIZED_ATTEMPTS")

    campaign = repair.get("campaign")
    if isinstance(campaign, dict):
        profiles = campaign.get("profiles")
        if not isinstance(profiles, dict) or not profiles:
            errors.append("POLICY_INVALID_CAMPAIGN_PROFILES")
        else:
            for profile in profiles.values():
                limit = profile.get("max_consecutive_no_progress") if isinstance(profile, dict) else None
                if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
                    errors.append("POLICY_INVALID_CAMPAIGN_PROFILES")
                    break
        hard_stops = campaign.get("hard_stop_flags")
        if not isinstance(hard_stops, list) or not hard_stops or len(hard_stops) != len(set(hard_stops)):
            errors.append("POLICY_INVALID_CAMPAIGN_HARD_STOP_FLAGS")

    if repair.get("ledger_schema") != LEDGER_SCHEMA:
        errors.append("POLICY_CONFLICT_LEDGER_SCHEMA")
    return list(dict.fromkeys(errors))

def _ledger_uses_campaign(ledger):
    if not isinstance(ledger, dict):
        return False
    if ledger.get("repair_campaign") is not None:
        return True
    authorities = ledger.get("authority_records")
    return isinstance(authorities, list) and any(
        isinstance(authority, dict)
        and authority.get("authority_mode") == "repair_campaign"
        for authority in authorities
    )


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
    authority_mode=None,
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
        "authority_mode": authority_mode,
        "auto_attempts_used": state.get("auto_attempts_used", 0),
        "escalated_attempts_used": state.get("escalated_attempts_used", 0),
        "history_head_hash": state.get("history_head_hash"),
        "repair_chain_digest": canonical_hash(chain) if isinstance(chain, dict) else None,
        "would_consume_auto_repair_budget": eligible_mode in {"AutoRepair", "ExtendRound3"},
        "would_consume_escalated_authority": eligible_mode == "EscalatedRepair",
        "would_consume_campaign_authority": authority_mode == "repair_campaign",
        "campaign_id": state.get("campaign_id"),
        "campaign_profile": state.get("campaign_profile"),
        "campaign_attempts_used": state.get("campaign_attempts_used", 0),
        "campaign_consecutive_no_progress": state.get("campaign_consecutive_no_progress"),
        "campaign_no_progress_limit": state.get("campaign_no_progress_limit"),
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


def _is_normalized_relative_path(value, *, prefix=False):
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    if value.startswith("/") or re.match(r"^[A-Za-z]:", value):
        return False
    if prefix != value.endswith("/"):
        return False
    candidate = value[:-1] if prefix else value
    parts = candidate.split("/")
    return all(part not in {"", ".", ".."} for part in parts)


def _validate_scope_manifest(scope):
    if not isinstance(scope, dict):
        return ["INVALID_CAMPAIGN_SCOPE_MANIFEST"]
    if set(scope) != {"allowed_exact_files", "allowed_path_prefixes"}:
        return ["INVALID_CAMPAIGN_SCOPE_FIELDS"]
    exact = scope.get("allowed_exact_files")
    prefixes = scope.get("allowed_path_prefixes")
    errors = []
    for name, value, is_prefix in (
        ("EXACT_FILES", exact, False),
        ("PATH_PREFIXES", prefixes, True),
    ):
        if (
            not isinstance(value, list)
            or any(not isinstance(item, str) for item in value)
            or len(value) != len(set(value))
            or value != sorted(value)
            or any(not _is_normalized_relative_path(item, prefix=is_prefix) for item in value)
        ):
            errors.append(f"INVALID_CAMPAIGN_{name}")
    if isinstance(exact, list) and isinstance(prefixes, list) and not exact and not prefixes:
        errors.append("EMPTY_CAMPAIGN_SCOPE")
    return errors


def _file_in_scope(path, scope):
    return path in scope["allowed_exact_files"] or any(
        path.startswith(prefix) for prefix in scope["allowed_path_prefixes"]
    )


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


def _validate_campaign_safety(safety, campaign_policy):
    flags = campaign_policy["hard_stop_flags"]
    if not isinstance(safety, dict) or set(safety) != set(flags):
        return ["INVALID_CAMPAIGN_SAFETY_FIELDS"]
    return [
        f"CAMPAIGN_HARD_STOP_{name.upper()}"
        for name in flags
        if safety.get(name) is not False
    ]


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


def _validate_authority_source(authority):
    errors = []
    if not isinstance(authority, dict):
        return ["INVALID_AUTHORITY_RECEIPT"]
    if not isinstance(authority.get("authority_id"), str) or not authority["authority_id"]:
        errors.append("INVALID_AUTHORITY_ID")
    if authority.get("source_kind") != "user_message":
        errors.append("AUTHORITY_SOURCE_NOT_USER_MESSAGE")
    if not isinstance(authority.get("source_ref"), str) or not EVIDENCE_REF_PATTERN.fullmatch(authority["source_ref"]):
        errors.append("INVALID_AUTHORITY_SOURCE_REF")
    if not _is_hash(authority.get("source_text_sha256")):
        errors.append("INVALID_AUTHORITY_SOURCE_HASH")
    if not isinstance(authority.get("target"), str) or not authority["target"].strip():
        errors.append("AUTHORITY_TARGET_MISSING")
    return errors


def _validate_single_authority(authority, chain, repair):
    errors = _validate_authority_source(authority)
    if not isinstance(authority, dict):
        return errors, []
    if authority.get("authority_mode") not in {None, "single_attempt"}:
        errors.append("INVALID_SINGLE_AUTHORITY_MODE")
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
    if not _is_hash(authority.get("receipt_hash")) or authority.get("receipt_hash") != receipt_hash(authority):
        errors.append("INVALID_AUTHORITY_RECEIPT_HASH")
    return errors, effective


def _validate_campaign_authority(authority, ledger, chain, repair):
    errors = _validate_authority_source(authority)
    if not isinstance(authority, dict):
        return errors
    campaign = ledger.get("repair_campaign")
    if not isinstance(campaign, dict):
        return errors + ["REPAIR_CAMPAIGN_REQUIRED"]
    if authority.get("authority_mode") != "repair_campaign":
        errors.append("INVALID_CAMPAIGN_AUTHORITY_MODE")
    scope = authority.get("allowed_scope")
    errors.extend(_validate_scope_manifest(scope))
    if isinstance(scope, dict) and authority.get("allowed_scope_hash") != canonical_hash(scope):
        errors.append("CAMPAIGN_ALLOWED_SCOPE_HASH_MISMATCH")
    bindings = {
        "campaign_id": campaign.get("campaign_id"),
        "task_id": ledger.get("current_task_id"),
        "acceptance_contract_hash": campaign.get("acceptance_contract_hash"),
        "profile": campaign.get("profile"),
    }
    for name, expected in bindings.items():
        if authority.get(name) != expected:
            errors.append(f"CAMPAIGN_AUTHORITY_BINDING_{name.upper()}")
    for name in ("activation_chain_digest", "activation_history_head_hash"):
        if not _is_hash(authority.get(name)):
            errors.append(f"INVALID_CAMPAIGN_{name.upper()}")
    if (
        not isinstance(authority.get("profile"), str)
        or authority["profile"] not in CAMPAIGN_PROFILES
    ):
        errors.append("INVALID_CAMPAIGN_PROFILE")
    allowed_files = chain.get("allowed_files")
    if (
        not isinstance(allowed_files, list)
        or not allowed_files
        or any(not isinstance(item, str) for item in allowed_files)
        or len(allowed_files) != len(set(allowed_files))
        or allowed_files != sorted(allowed_files)
        or any(not _is_normalized_relative_path(item) for item in allowed_files)
    ):
        errors.append("INVALID_CAMPAIGN_CHAIN_ALLOWED_FILES")
    elif chain.get("allowed_files_hash") != canonical_hash(allowed_files):
        errors.append("CAMPAIGN_CHAIN_ALLOWED_FILES_HASH_MISMATCH")
    elif isinstance(scope, dict) and not errors:
        if any(not _file_in_scope(path, scope) for path in allowed_files):
            errors.append("CAMPAIGN_SCOPE_OUTSIDE_AUTHORITY")
    if not _is_hash(authority.get("receipt_hash")) or authority.get("receipt_hash") != receipt_hash(authority):
        errors.append("INVALID_AUTHORITY_RECEIPT_HASH")
    return errors


def _validate_campaign_state(campaign, campaign_authorities, repair):
    if campaign is None:
        return [], {}
    if not isinstance(campaign, dict):
        return ["INVALID_REPAIR_CAMPAIGN"], {}
    expected_fields = {
        "campaign_id",
        "acceptance_contract_hash",
        "profile",
        "authority_receipt_hash",
        "state",
        "safety",
    }
    errors = []
    if set(campaign) != expected_fields:
        errors.append("INVALID_REPAIR_CAMPAIGN_FIELDS")
    if not isinstance(campaign.get("campaign_id"), str) or not campaign["campaign_id"]:
        errors.append("INVALID_CAMPAIGN_ID")
    if not _is_hash(campaign.get("acceptance_contract_hash")):
        errors.append("INVALID_CAMPAIGN_ACCEPTANCE_CONTRACT_HASH")
    profile = campaign.get("profile")
    if not isinstance(profile, str) or profile not in CAMPAIGN_PROFILES:
        errors.append("INVALID_CAMPAIGN_PROFILE")
    authority_hash = campaign.get("authority_receipt_hash")
    if not _is_hash(authority_hash) or authority_hash not in campaign_authorities:
        errors.append("CAMPAIGN_AUTHORITY_RECEIPT_NOT_FOUND")
    errors.extend(_validate_campaign_safety(campaign.get("safety"), repair["campaign"]))

    state = campaign.get("state")
    if not isinstance(state, dict):
        return errors + ["INVALID_CAMPAIGN_STATE_RECEIPT"], {}
    expected_state_fields = {
        "schema_version",
        "campaign_id",
        "authority_receipt_hash",
        "attempt_count",
        "consecutive_no_progress",
        "history_head_hash",
        "latest_outcome",
        "latest_review_receipt_hash",
        "safety_hash",
        "source_ref",
        "source_text_sha256",
        "receipt_hash",
    }
    if set(state) != expected_state_fields:
        errors.append("INVALID_CAMPAIGN_STATE_FIELDS")
    if state.get("schema_version") != CAMPAIGN_STATE_SCHEMA:
        errors.append("INVALID_CAMPAIGN_STATE_SCHEMA")
    if state.get("campaign_id") != campaign.get("campaign_id"):
        errors.append("CAMPAIGN_STATE_ID_MISMATCH")
    if state.get("authority_receipt_hash") != authority_hash:
        errors.append("CAMPAIGN_STATE_AUTHORITY_MISMATCH")
    if state.get("safety_hash") != canonical_hash(campaign.get("safety")):
        errors.append("CAMPAIGN_STATE_SAFETY_MISMATCH")
    attempt_count = state.get("attempt_count")
    streak = state.get("consecutive_no_progress")
    if not isinstance(attempt_count, int) or isinstance(attempt_count, bool) or attempt_count < 0:
        errors.append("INVALID_CAMPAIGN_ATTEMPT_COUNT")
    if (
        not isinstance(streak, int)
        or isinstance(streak, bool)
        or streak < 0
        or isinstance(attempt_count, int)
        and streak > attempt_count
    ):
        errors.append("INVALID_CAMPAIGN_NO_PROGRESS_STREAK")
    if not _is_hash(state.get("history_head_hash")):
        errors.append("INVALID_CAMPAIGN_HISTORY_HEAD")
    outcome = state.get("latest_outcome")
    if not isinstance(outcome, str) or outcome not in CAMPAIGN_OUTCOMES:
        errors.append("INVALID_CAMPAIGN_LATEST_OUTCOME")
    latest_review = state.get("latest_review_receipt_hash")
    if attempt_count == 0:
        if streak != 0 or outcome != "NotStarted" or latest_review is not None:
            errors.append("INVALID_CAMPAIGN_INITIAL_STATE")
    else:
        if outcome == "NotStarted" or not _is_hash(latest_review):
            errors.append("INVALID_CAMPAIGN_PROGRESS_STATE")
        if outcome == "MeasurableProgress" and streak != 0:
            errors.append("CAMPAIGN_PROGRESS_DID_NOT_RESET_STREAK")
        if outcome == "NoProgress" and (not isinstance(streak, int) or streak < 1):
            errors.append("CAMPAIGN_NO_PROGRESS_STREAK_NOT_INCREMENTED")
    if not isinstance(state.get("source_ref"), str) or not EVIDENCE_REF_PATTERN.fullmatch(state["source_ref"]):
        errors.append("INVALID_CAMPAIGN_STATE_SOURCE_REF")
    if not _is_hash(state.get("source_text_sha256")):
        errors.append("INVALID_CAMPAIGN_STATE_SOURCE_HASH")
    if not _is_hash(state.get("receipt_hash")) or state.get("receipt_hash") != receipt_hash(state):
        errors.append("INVALID_CAMPAIGN_STATE_RECEIPT_HASH")
    limit = (
        repair["campaign"]["profiles"][profile]["max_consecutive_no_progress"]
        if isinstance(profile, str) and profile in CAMPAIGN_PROFILES
        else None
    )
    return errors, {
        "campaign_id": campaign.get("campaign_id"),
        "campaign_profile": profile,
        "campaign_acceptance_contract_hash": campaign.get(
            "acceptance_contract_hash"
        ),
        "campaign_authority_hash": authority_hash,
        "campaign_state_receipt_hash": state.get("receipt_hash"),
        "campaign_history_head_hash": state.get("history_head_hash"),
        "campaign_latest_review_receipt_hash": state.get(
            "latest_review_receipt_hash"
        ),
        "campaign_attempts_used": attempt_count if isinstance(attempt_count, int) else 0,
        "campaign_consecutive_no_progress": streak if isinstance(streak, int) else None,
        "campaign_no_progress_limit": limit,
    }


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
    authority_modes = {}
    campaign_authorities = {}
    authority_ids = set()
    for authority in authorities:
        authority_mode = (
            authority.get("authority_mode")
            if isinstance(authority, dict)
            else None
        )
        if authority_mode == "repair_campaign":
            authority_errors = _validate_campaign_authority(
                authority,
                ledger,
                chain,
                repair,
            )
            effective = []
        else:
            authority_errors, effective = _validate_single_authority(
                authority,
                chain,
                repair,
            )
        errors.extend(authority_errors)
        if isinstance(authority, dict):
            authority_id = authority.get("authority_id")
            authority_hash = authority.get("receipt_hash")
            if isinstance(authority_id, str):
                if authority_id in authority_ids:
                    errors.append("DUPLICATE_AUTHORITY_ID")
                authority_ids.add(authority_id)
            if _is_hash(authority_hash):
                authority_by_hash[authority_hash] = authority
                authority_modes[authority_hash] = (
                    "repair_campaign"
                    if authority_mode == "repair_campaign"
                    else "single_attempt"
                )
                if authority_mode == "repair_campaign":
                    campaign_authorities[authority_hash] = authority
                for attempt_id in effective:
                    authority_attempts.setdefault(attempt_id, []).append(
                        authority_hash
                    )

    campaign_errors, campaign_state = _validate_campaign_state(
        ledger.get("repair_campaign"),
        campaign_authorities,
        repair,
    )
    errors.extend(campaign_errors)

    attempts = ledger.get("attempts")
    if not isinstance(attempts, list):
        return errors + ["INVALID_ATTEMPT_HISTORY"], {}
    previous_hash = trigger["receipt_hash"]
    previous_review = trigger
    review_receipt_hashes = [trigger["receipt_hash"]]
    used_authority_hashes = []
    auto_used = 0
    escalated_used = 0
    attempt_records = []
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
        if isinstance(attempt_id, str):
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
            if not _is_hash(authority_hash) or authority_hash not in authority_by_hash:
                errors.append("ATTEMPT_AUTHORITY_NOT_BOUND")
            elif authority_modes.get(authority_hash) == "repair_campaign":
                if authority_hash != campaign_state.get("campaign_authority_hash"):
                    errors.append("ATTEMPT_CAMPAIGN_AUTHORITY_NOT_ACTIVE")
                else:
                    used_authority_hashes.append(authority_hash)
            elif authority_hash not in authority_attempts.get(attempt_id, []):
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
        if _is_hash(attempt_receipt):
            if attempt_receipt in seen_receipts:
                errors.append("DUPLICATE_RECEIPT_HASH")
            seen_receipts.add(attempt_receipt)
        previous_hash = attempt_receipt
        if isinstance(review, dict):
            previous_review = review
            if _is_hash(review.get("receipt_hash")):
                review_receipt_hashes.append(review["receipt_hash"])
        attempt_records.append(
            {
                "attempt_receipt_hash": (
                    attempt_receipt if _is_hash(attempt_receipt) else None
                ),
                "review_receipt_hash": (
                    review.get("receipt_hash") if isinstance(review, dict) else None
                ),
            }
        )

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
        "current_task_id": ledger.get("current_task_id"),
        "auto_attempts_used": auto_used,
        "escalated_attempts_used": escalated_used,
        "history_head_hash": previous_hash,
        "latest_review": previous_review,
        "authority_attempts": authority_attempts,
        "authority_modes": authority_modes,
        "campaign_authority_hashes": list(campaign_authorities),
        "review_receipt_hashes": review_receipt_hashes,
        "used_authority_hashes": used_authority_hashes,
    }
    state.update(campaign_state)
    campaign_attempt_records = []
    active_campaign_hash = state.get("campaign_authority_hash")
    active_campaign_authority = (
        campaign_authorities.get(active_campaign_hash)
        if _is_hash(active_campaign_hash)
        else None
    )
    if isinstance(active_campaign_authority, dict):
        activation_chain = active_campaign_authority.get(
            "activation_chain_digest"
        )
        if activation_chain == canonical_hash(chain):
            activation_head = active_campaign_authority.get(
                "activation_history_head_hash"
            )
            if activation_head == trigger.get("receipt_hash"):
                campaign_attempt_records = attempt_records
            else:
                activation_index = next(
                    (
                        index
                        for index, record in enumerate(attempt_records)
                        if record["attempt_receipt_hash"] == activation_head
                    ),
                    None,
                )
                if activation_index is None:
                    errors.append(
                        "CAMPAIGN_ACTIVATION_HISTORY_HEAD_NOT_FOUND"
                    )
                else:
                    campaign_attempt_records = attempt_records[
                        activation_index + 1 :
                    ]
        else:
            campaign_attempt_records = attempt_records
    if len(campaign_attempt_records) > state.get("campaign_attempts_used", 0):
        errors.append("CAMPAIGN_HISTORY_COUNT_BELOW_CURRENT_CHAIN")
    if campaign_attempt_records:
        latest_campaign_attempt = campaign_attempt_records[-1]
        if (
            state.get("campaign_history_head_hash")
            != latest_campaign_attempt["attempt_receipt_hash"]
        ):
            errors.append("CAMPAIGN_STATE_HISTORY_HEAD_STALE")
        if (
            state.get("campaign_latest_review_receipt_hash")
            != latest_campaign_attempt["review_receipt_hash"]
        ):
            errors.append("CAMPAIGN_STATE_LATEST_REVIEW_STALE")
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
    expected_campaign_state = context.get(
        "expected_campaign_state_receipt_hash"
    )
    if state.get("campaign_id") is not None:
        expected_task_id = context.get("expected_task_id")
        if not isinstance(expected_task_id, str) or not expected_task_id:
            errors.append("TRUSTED_CONTEXT_CAMPAIGN_TASK_MISSING")
        elif expected_task_id != state.get("current_task_id"):
            errors.append("TRUSTED_CONTEXT_CAMPAIGN_TASK_MISMATCH")
        expected_acceptance_contract = context.get(
            "expected_acceptance_contract_hash"
        )
        if not _is_hash(expected_acceptance_contract):
            errors.append(
                "TRUSTED_CONTEXT_CAMPAIGN_ACCEPTANCE_CONTRACT_MISSING"
            )
        elif expected_acceptance_contract != state.get(
            "campaign_acceptance_contract_hash"
        ):
            errors.append(
                "TRUSTED_CONTEXT_CAMPAIGN_ACCEPTANCE_CONTRACT_MISMATCH"
            )
        if not _is_hash(expected_campaign_state):
            errors.append("TRUSTED_CONTEXT_CAMPAIGN_STATE_MISSING")
            expected_campaign_state = None
        elif expected_campaign_state != state.get("campaign_state_receipt_hash"):
            errors.append("TRUSTED_CONTEXT_CAMPAIGN_STATE_MISMATCH")
    elif (
        expected_campaign_state is not None
        or context.get("expected_task_id") is not None
        or context.get("expected_acceptance_contract_hash") is not None
    ):
        errors.append("TRUSTED_CONTEXT_UNEXPECTED_CAMPAIGN_STATE")
    if not _is_hash(context.get("attestation_hash")) or context.get("attestation_hash") != attestation_hash(context):
        errors.append("TRUSTED_CONTEXT_ATTESTATION_HASH_INVALID")
    return errors, {
        "verified_review_receipt_hashes": verified_reviews,
        "verified_authority_receipt_hashes": verified_authorities,
        "expected_campaign_state_receipt_hash": expected_campaign_state,
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
    policy_errors = validate_policy(
        policy,
        allow_legacy_single=not _ledger_uses_campaign(ledger),
    )
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
    latest_review_decision = state["latest_review"]["decision"]
    if latest_review_decision == "Passed":
        return _result("Stop", ["REPAIR_ALREADY_PASSED"], policy, state)
    if latest_review_decision == "Blocked":
        return _result("Blocked", ["LATEST_REVIEW_BLOCKED"], policy, state)
    if (
        state.get("campaign_id") is not None
        and state.get("campaign_consecutive_no_progress")
        >= state.get("campaign_no_progress_limit")
    ):
        return _result(
            "Stop",
            [
                "CAMPAIGN_NO_PROGRESS_LIMIT_REACHED",
                "USER_DECISION_REQUIRED",
            ],
            policy,
            state,
        )

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
    single_candidates = state["authority_attempts"].get(next_attempt, [])
    campaign_hash = state.get("campaign_authority_hash")
    campaign_candidates = [campaign_hash] if campaign_hash else []
    candidates = [*single_candidates, *campaign_candidates]
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
    authority_mode = state["authority_modes"].get(authority_hash)
    if authority_mode == "repair_campaign":
        eligibility_reasons = [
            "TASK_BOUND_REPAIR_CAMPAIGN_AUTHORITY_ATTESTED",
            "CAMPAIGN_SCOPE_VERIFIED",
            "CAMPAIGN_NO_PROGRESS_BUDGET_AVAILABLE",
            "PRIOR_ATTEMPTS_INDEPENDENTLY_REVIEWED",
            "TRUSTED_CONTEXT_VERIFIED",
        ]
    else:
        eligibility_reasons = [
            "CHAIN_BOUND_USER_AUTHORITY_ATTESTED",
            "PRIOR_ATTEMPTS_INDEPENDENTLY_REVIEWED",
            "TRUSTED_CONTEXT_VERIFIED",
        ]
    return _result(
        "MechanicallyEligible",
        eligibility_reasons,
        policy,
        state,
        next_attempt,
        authority_hash,
        authority_mode,
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
    print(f"authority_mode={result['authority_mode'] or 'none'}")
    if result["campaign_id"]:
        print(
            "campaign="
            f"{result['campaign_id']} profile={result['campaign_profile']} "
            f"no_progress={result['campaign_consecutive_no_progress']}/"
            f"{result['campaign_no_progress_limit']}"
        )
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
    parser = ReadOnlyParser(
        description="只读判定 receipt-backed AutoRepair / EscalatedRepair / RepairCampaign 边界。"
    )
    default_policy = pathlib.Path(__file__).resolve().parents[1] / "policy" / "repair-campaign.json"
    parser.add_argument("target", nargs="?", help="repair ledger JSON；使用 - 从 stdin 读取")
    parser.add_argument("--policy", default=str(default_policy))
    parser.add_argument("--trusted-context", help="由 harness / 只读项目快照 / 当前 Orchestrator 提供的独立 JSON")
    parser.add_argument("--policy-digest", action="store_true")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    try:
        args = parser.parse_args(argv)
        policy = load_policy(args.policy)
        if args.policy_digest:
            policy_errors = validate_policy(policy, allow_legacy_single=True)
            if policy_errors:
                result = _result("Blocked", policy_errors, policy)
            else:
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
