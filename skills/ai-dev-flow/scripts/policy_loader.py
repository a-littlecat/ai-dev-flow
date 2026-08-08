"""Strict, read-only loader for ai-dev-flow policy documents."""

import json
import pathlib
import re
import warnings
from types import MappingProxyType


LEGACY_POLICY_PATTERN = re.compile(
    r"<!-- POLICY_JSON_BEGIN -->\s*```json\s*(\{.*?\})\s*```\s*<!-- POLICY_JSON_END -->",
    flags=re.DOTALL,
)

SCHEMA_FIELDS = {
    "adf/policy-core/v1": {
        "schema_version", "unknown_input", "routes", "review", "independent_review", "safety",
    },
    "adf/repair-basic/v1": {
        "schema_version", "finding_id_required", "base_auto_rounds",
        "optional_progress_rounds", "independent_review_after_patch",
        "progress_gate", "on_budget_exhausted",
    },
    "adf/repair-campaign/v1": {"schema_version", "repair"},
    "ai-dev-flow/v0.8-policy-rc2": {
        "schema_version", "unknown_input", "routes", "review", "safety",
        "repair",
    },
    "ai-dev-flow/v0.8-policy-rc3": {
        "schema_version", "unknown_input", "routes", "review", "safety",
        "reviewer_selection", "repair",
    },
}


class PolicyLoadError(ValueError):
    pass


class LegacyPolicyWarning(FutureWarning):
    pass


def _freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def thaw_policy(value):
    if isinstance(value, MappingProxyType):
        return {key: thaw_policy(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [thaw_policy(item) for item in value]
    return value


def _object(value, label, fields):
    if not isinstance(value, dict):
        raise PolicyLoadError(f"{label} must be an object")
    unknown = set(value) - set(fields)
    missing = set(fields) - set(value)
    if unknown:
        raise PolicyLoadError(f"unknown {label} fields: {sorted(unknown)}")
    if missing:
        raise PolicyLoadError(f"missing {label} fields: {sorted(missing)}")
    return value


def _string(value, label, choices=None):
    if not isinstance(value, str) or not value:
        raise PolicyLoadError(f"{label} must be a non-empty string")
    if choices is not None and value not in choices:
        raise PolicyLoadError(f"invalid {label}: {value!r}")


def _boolean(value, label, expected=None):
    if not isinstance(value, bool):
        raise PolicyLoadError(f"{label} must be boolean")
    if expected is not None and value is not expected:
        raise PolicyLoadError(f"{label} must be {str(expected).lower()}")


def _integer(value, label, minimum=0):
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise PolicyLoadError(f"{label} must be an integer >= {minimum}")


def _string_list(value, label, choices=None, exact=None):
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item for item in value)
        or len(value) != len(set(value))
    ):
        raise PolicyLoadError(f"{label} must be a non-empty unique string array")
    if choices is not None and any(item not in choices for item in value):
        raise PolicyLoadError(f"{label} contains an invalid enum value")
    if exact is not None and value != exact:
        raise PolicyLoadError(f"{label} must match the required ordered values")


def _validate_routes_review_safety(value, legacy=False):
    unknown = value["unknown_input"]
    if legacy:
        _string(unknown, "unknown_input", {"Blocked"})
    else:
        _object(
            unknown,
            "unknown_input",
            {"discoverable", "authority", "external_evidence", "rule_conflict", "unresolved_final"},
        )
        _string(unknown["discoverable"], "unknown_input.discoverable", {"InspectAndResolve"})
        for name in ("authority", "external_evidence", "rule_conflict", "unresolved_final"):
            _string(unknown[name], f"unknown_input.{name}", {"Blocked"})

    routes = _object(value["routes"], "routes", {"controlled", "lite", "fallback"})
    controlled = _object(
        routes["controlled"],
        "routes.controlled",
        {"task_classes", "ua_min", "risk_flags", "requested_actions", "when_delivery_action", "when_real_environment_required"},
    )
    _string_list(controlled["task_classes"], "routes.controlled.task_classes", exact=["D"])
    _integer(controlled["ua_min"], "routes.controlled.ua_min")
    if controlled["ua_min"] != 5:
        raise PolicyLoadError("routes.controlled.ua_min must be 5")
    _string_list(controlled["risk_flags"], "routes.controlled.risk_flags", exact=[
        "architecture", "data_migration", "delivery", "external_sync",
        "irreversible_action", "parallel_writers", "real_environment", "release", "security",
    ])
    _string_list(
        controlled["requested_actions"],
        "routes.controlled.requested_actions",
        exact=["acceptance_recommendation", "delivery", "merge", "release"],
    )
    _boolean(controlled["when_delivery_action"], "routes.controlled.when_delivery_action", True)
    _boolean(controlled["when_real_environment_required"], "routes.controlled.when_real_environment_required", True)
    lite = _object(
        routes["lite"],
        "routes.lite",
        {"task_classes", "requires_action_authority", "requires_deterministic_coverage", "requires_user_observation", "disallowed_risk_flags"},
    )
    _string_list(lite["task_classes"], "routes.lite.task_classes", exact=["A", "B"])
    _string(lite["requires_action_authority"], "routes.lite.requires_action_authority", {"Allowed"})
    _boolean(lite["requires_deterministic_coverage"], "routes.lite.requires_deterministic_coverage", True)
    _boolean(lite["requires_user_observation"], "routes.lite.requires_user_observation", False)
    _string_list(lite["disallowed_risk_flags"], "routes.lite.disallowed_risk_flags", exact=[
        "business_files_gt_3", "build_or_deploy_config", "core_execution_path",
        "core_writer_path", "explicit_independent_review", "historical_p1", "public_api",
        "shared_component", "tests_do_not_cover_oracle",
    ])
    _string(routes["fallback"], "routes.fallback", {"Tracked"})

    review = _object(value["review"], "review", {"Lite", "Tracked", "Controlled", "missing_authority_or_capability"})
    _string(review["Lite"], "review.Lite", {"Skipped", "NotRequired"})
    tracked = _object(review["Tracked"], "review.Tracked", {"trigger_risk_flags", "otherwise"})
    _string_list(tracked["trigger_risk_flags"], "review.Tracked.trigger_risk_flags", exact=[
        "business_files_gt_3", "build_or_deploy_config", "core_execution_path",
        "core_writer_path", "explicit_independent_review", "historical_p1", "public_api",
        "shared_component", "tests_do_not_cover_oracle",
    ])
    _string(tracked["otherwise"], "review.Tracked.otherwise", {"Skipped"})
    required = _object(review["Controlled"], "review.Controlled", {"required", "enforcement_points"})
    _boolean(required["required"], "review.Controlled.required", True)
    _string_list(
        required["enforcement_points"],
        "review.Controlled.enforcement_points",
        exact=["acceptance_recommendation", "delivery", "merge", "release"],
    )
    _string(review["missing_authority_or_capability"], "review.missing_authority_or_capability", {"Blocked"})

    if not legacy:
        independent = _object(
            value["independent_review"],
            "independent_review",
            {"context_isolation", "frozen_diff_input", "stable_finding_ids", "write_isolation"},
        )
        for name in ("context_isolation", "frozen_diff_input", "stable_finding_ids"):
            _string(independent[name], f"independent_review.{name}", {"required"})
        write_isolation = _object(
            independent["write_isolation"],
            "independent_review.write_isolation",
            {"one_of"},
        )
        _string_list(
            write_isolation["one_of"],
            "independent_review.write_isolation.one_of",
            exact=["native_read_only", "sandbox_read_only", "readonly_copy"],
        )

    safety = _object(
        value["safety"],
        "safety",
        {"allowed_action_authority", "require_real_environment_evidence", "delivery_requires_controlled", "missing_required_evidence"},
    )
    _string(safety["allowed_action_authority"], "safety.allowed_action_authority", {"Allowed"})
    _boolean(safety["require_real_environment_evidence"], "safety.require_real_environment_evidence", True)
    _boolean(safety["delivery_requires_controlled"], "safety.delivery_requires_controlled", True)
    _string(safety["missing_required_evidence"], "safety.missing_required_evidence", {"Blocked"})


def _validate_repair_basic(value):
    _boolean(value["finding_id_required"], "finding_id_required", True)
    _integer(value["base_auto_rounds"], "base_auto_rounds", 1)
    _integer(value["optional_progress_rounds"], "optional_progress_rounds", 0)
    if value["base_auto_rounds"] != 2 or value["optional_progress_rounds"] != 1:
        raise PolicyLoadError("repair-basic round limits must be base=2 and optional=1")
    _boolean(value["independent_review_after_patch"], "independent_review_after_patch", True)
    progress = _object(
        value["progress_gate"],
        "progress_gate",
        {"require_red_to_green", "forbid_green_to_red", "forbid_new_blocking_finding", "severity_must_not_increase"},
    )
    for name in progress:
        _boolean(progress[name], f"progress_gate.{name}", True)
    _string(value["on_budget_exhausted"], "on_budget_exhausted", {"UserDecisionRequired"})


def _validate_repair_campaign(value, legacy_single=False):
    repair_fields = {
        "repair_round_definition", "non_counting_actions", "chain_identity_fields",
        "ledger_schema", "evidence_trust_boundary", "record_only_finding",
        "base_auto_rounds", "autonomous_max_rounds", "history",
        "required_true_fields", "required_false_fields", "round_3_progress",
        "task_change_resets_budget", "model_change_resets_budget", "post_stop",
        "mechanical_decisions", "promotion_decisions",
        "promotion_requires_trusted_orchestrator", "eligible_modes",
    }
    if not legacy_single:
        repair_fields.add("campaign")
    repair = _object(value["repair"], "repair", repair_fields)
    _string(
        repair["repair_round_definition"],
        "repair.repair_round_definition",
        {"patch_to_next_independent_review"},
    )
    _string(
        repair["evidence_trust_boundary"],
        "repair.evidence_trust_boundary",
        {"ledger_is_untrusted_trusted_context_is_supplied_by_project_or_harness"},
    )
    _string(repair["ledger_schema"], "repair.ledger_schema", {"ai-dev-flow/repair-ledger-v1"})
    _string_list(repair["non_counting_actions"], "repair.non_counting_actions", exact=[
        "diagnostic_evidence_only", "record_only_correction", "review_only",
        "task_or_board_receipt_sync", "test_rerun_without_patch", "ua_without_patch",
    ])
    _string_list(repair["chain_identity_fields"], "repair.chain_identity_fields", exact=[
        "repair_chain_id", "finding_ids", "closure_contract_hash", "allowed_files_hash",
    ])
    _string_list(repair["required_true_fields"], "repair.required_true_fields", exact=[
        "dependencies_frozen", "authority_frozen", "root_cause_known", "reviewer_capable",
        "repairer_capable", "within_cost_boundary",
    ])
    _string_list(repair["required_false_fields"], "repair.required_false_fields", exact=["external_side_effect"])
    _string_list(
        repair["mechanical_decisions"],
        "repair.mechanical_decisions",
        exact=["MechanicallyEligible", "Stop", "Blocked"],
    )
    _string_list(
        repair["promotion_decisions"],
        "repair.promotion_decisions",
        exact=["AutoRepairAllowed", "ExtendRound3", "EscalatedRepairAllowed"],
    )
    _string_list(
        repair["eligible_modes"],
        "repair.eligible_modes",
        exact=["AutoRepair", "ExtendRound3", "EscalatedRepair"],
    )
    _integer(repair["base_auto_rounds"], "repair.base_auto_rounds", 1)
    _integer(repair["autonomous_max_rounds"], "repair.autonomous_max_rounds", 1)
    if repair["base_auto_rounds"] != 2 or repair["autonomous_max_rounds"] != 3:
        raise PolicyLoadError("repair round limits must be base=2 and autonomous=3")
    _boolean(repair["task_change_resets_budget"], "repair.task_change_resets_budget", False)
    _boolean(repair["model_change_resets_budget"], "repair.model_change_resets_budget", False)
    _boolean(
        repair["promotion_requires_trusted_orchestrator"],
        "repair.promotion_requires_trusted_orchestrator",
        True,
    )

    record = _object(repair["record_only_finding"], "repair.record_only_finding", {"default_severity", "p1_only_if"})
    _string_list(record["default_severity"], "repair.record_only_finding.default_severity", exact=["P2", "P3"])
    _string_list(record["p1_only_if"], "repair.record_only_finding.p1_only_if", exact=[
        "can_authorize_unsafe_action", "can_hide_blocking_finding",
    ])
    history = _object(
        repair["history"],
        "repair.history",
        {"attempt_count_source", "receipt_hash_algorithm", "require_history_anchor", "require_trusted_context", "trusted_context_schema", "require_independent_review_receipt_after_each_attempt"},
    )
    _string(history["attempt_count_source"], "repair.history.attempt_count_source", {"validated_receipt_chain"})
    _string(history["receipt_hash_algorithm"], "repair.history.receipt_hash_algorithm", {"sha256_canonical_json"})
    _string(history["trusted_context_schema"], "repair.history.trusted_context_schema", {"ai-dev-flow/repair-trusted-context-v1"})
    for name in ("require_history_anchor", "require_trusted_context", "require_independent_review_receipt_after_each_attempt"):
        _boolean(history[name], f"repair.history.{name}", True)
    round3 = _object(
        repair["round_3_progress"],
        "repair.round_3_progress",
        {"source", "require_red_to_green", "forbid_green_to_red", "forbid_new_blocking_findings", "severity_must_not_increase", "evidence_coverage_must_strictly_increase", "round_3_target_required"},
    )
    _string(round3["source"], "repair.round_3_progress.source", {"latest_independent_review_receipt"})
    for name in set(round3) - {"source"}:
        _boolean(round3[name], f"repair.round_3_progress.{name}", True)
    post = _object(
        repair["post_stop"],
        "repair.post_stop",
        {"state", "mode", "ai_repair_allowed_with_explicit_authority", "manual_implementation_required", "default_authorized_attempts", "authority_source", "authority_must_bind", "independent_review_after_each_attempt", "history_resets", "failure_decision"},
    )
    _string(post["state"], "repair.post_stop.state", {"UserDecisionRequired"})
    _string(post["mode"], "repair.post_stop.mode", {"EscalatedRepair"})
    _string(
        post["authority_source"],
        "repair.post_stop.authority_source",
        {"trusted_context_attested_chain_bound_authority_receipt"},
    )
    _string(post["failure_decision"], "repair.post_stop.failure_decision", {"Stop"})
    _string_list(post["authority_must_bind"], "repair.post_stop.authority_must_bind", exact=[
        "repair_chain_digest", "closure_contract_hash", "allowed_files_hash",
        "target_finding_ids", "authorized_attempt_ids",
    ])
    _integer(post["default_authorized_attempts"], "repair.post_stop.default_authorized_attempts", 1)
    if post["default_authorized_attempts"] != 1:
        raise PolicyLoadError("repair.post_stop.default_authorized_attempts must be 1")
    _boolean(post["ai_repair_allowed_with_explicit_authority"], "repair.post_stop.ai_repair_allowed_with_explicit_authority", True)
    _boolean(post["manual_implementation_required"], "repair.post_stop.manual_implementation_required", False)
    _boolean(post["independent_review_after_each_attempt"], "repair.post_stop.independent_review_after_each_attempt", True)
    _boolean(post["history_resets"], "repair.post_stop.history_resets", False)

    if not legacy_single:
        campaign = _object(
            repair["campaign"],
            "repair.campaign",
            {"authority_mode", "ai_repair_allowed_with_explicit_authority", "authority_source", "authority_must_bind", "profiles", "scope_manifest", "progress_source", "progress_resets_no_progress_streak", "task_change_resets_streak", "model_change_resets_streak", "chain_change_resets_streak", "hard_stop_flags", "independent_review_after_each_attempt", "delivery_authority_separate"},
        )
        _string(campaign["authority_mode"], "repair.campaign.authority_mode", {"RepairCampaignAuthority"})
        _string(
            campaign["authority_source"],
            "repair.campaign.authority_source",
            {"trusted_context_attested_task_bound_campaign_receipt"},
        )
        _string(
            campaign["progress_source"],
            "repair.campaign.progress_source",
            {"trusted_context_attested_campaign_state_receipt"},
        )
        _string_list(campaign["authority_must_bind"], "repair.campaign.authority_must_bind", exact=[
            "campaign_id", "task_id", "acceptance_contract_hash", "allowed_scope_hash",
            "profile", "activation_chain_digest", "activation_history_head_hash",
        ])
        _string_list(campaign["hard_stop_flags"], "repair.campaign.hard_stop_flags", exact=[
            "p0_finding", "security_boundary_change", "data_integrity_risk",
            "scope_outside_campaign", "irreversible_action", "external_side_effect",
            "test_oracle_weakened", "unapproved_dependency_change", "required_evidence_missing",
        ])
        _boolean(campaign["ai_repair_allowed_with_explicit_authority"], "repair.campaign.ai_repair_allowed_with_explicit_authority", True)
        _boolean(campaign["progress_resets_no_progress_streak"], "repair.campaign.progress_resets_no_progress_streak", True)
        for name in ("task_change_resets_streak", "model_change_resets_streak", "chain_change_resets_streak"):
            _boolean(campaign[name], f"repair.campaign.{name}", False)
        _boolean(campaign["independent_review_after_each_attempt"], "repair.campaign.independent_review_after_each_attempt", True)
        _boolean(campaign["delivery_authority_separate"], "repair.campaign.delivery_authority_separate", True)
        profiles = _object(campaign["profiles"], "repair.campaign.profiles", {"core_product", "harness"})
        for name, profile in profiles.items():
            item = _object(profile, f"repair.campaign.profiles.{name}", {"max_consecutive_no_progress"})
            _integer(item["max_consecutive_no_progress"], f"repair.campaign.profiles.{name}.max_consecutive_no_progress", 1)
            expected_limit = 4 if name == "core_product" else 5
            if item["max_consecutive_no_progress"] != expected_limit:
                raise PolicyLoadError(f"repair.campaign.profiles.{name}.max_consecutive_no_progress must be {expected_limit}")
        scope = _object(campaign["scope_manifest"], "repair.campaign.scope_manifest", {"exact_files_field", "path_prefixes_field", "require_relative_normalized_paths", "current_chain_files_must_be_subset"})
        _string(
            scope["exact_files_field"],
            "repair.campaign.scope_manifest.exact_files_field",
            {"allowed_exact_files"},
        )
        _string(
            scope["path_prefixes_field"],
            "repair.campaign.scope_manifest.path_prefixes_field",
            {"allowed_path_prefixes"},
        )
        for name in ("require_relative_normalized_paths", "current_chain_files_must_be_subset"):
            _boolean(scope[name], f"repair.campaign.scope_manifest.{name}", True)


def _validate_document(value):
    schema = value["schema_version"]
    if schema == "adf/policy-core/v1":
        _validate_routes_review_safety(value)
    elif schema == "adf/repair-basic/v1":
        _validate_repair_basic(value)
    elif schema == "adf/repair-campaign/v1":
        _validate_repair_campaign(value)
    elif schema in {"ai-dev-flow/v0.8-policy-rc2", "ai-dev-flow/v0.8-policy-rc3"}:
        _validate_routes_review_safety(value, legacy=True)
        if schema == "ai-dev-flow/v0.8-policy-rc3":
            reviewer = _object(value["reviewer_selection"], "reviewer_selection", {"default", "cross_harness", "native_unavailable", "same_context_self_review"})
            expected = {
                "default": "same_harness_native_isolated",
                "cross_harness": "explicit_user_authority_only",
                "native_unavailable": "Blocked",
                "same_context_self_review": "Pending",
            }
            for name, item in reviewer.items():
                _string(item, f"reviewer_selection.{name}", {expected[name]})
        _validate_repair_campaign(value, legacy_single=schema.endswith("rc2"))


def _parse_json(text, source):
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PolicyLoadError(f"invalid policy JSON in {source}: {exc}") from exc
    validate_policy_value(value)
    return value


def validate_policy_value(value):
    """Validate an already parsed policy with the same fail-closed rules as file loading."""

    if not isinstance(value, dict):
        raise PolicyLoadError("policy must be a JSON object")
    schema = value.get("schema_version")
    allowed = SCHEMA_FIELDS.get(schema)
    if allowed is None:
        raise PolicyLoadError(f"unsupported policy schema: {schema!r}")
    unknown = set(value) - allowed
    missing = allowed - set(value)
    if unknown:
        raise PolicyLoadError(f"unknown top-level policy fields: {sorted(unknown)}")
    if missing:
        raise PolicyLoadError(f"missing top-level policy fields: {sorted(missing)}")
    _validate_document(value)


def load_policy_document(path):
    source = pathlib.Path(path)
    try:
        text = source.read_text(encoding="utf-8", errors="strict")
    except (OSError, UnicodeError) as exc:
        raise PolicyLoadError(f"cannot read policy {source}: {exc}") from exc
    stripped = text.lstrip()
    if stripped.startswith("{"):
        value = _parse_json(text, source)
    else:
        match = LEGACY_POLICY_PATTERN.search(text)
        if not match:
            raise PolicyLoadError(f"legacy POLICY_JSON block missing: {source}")
        warnings.warn(
            f"Markdown POLICY_JSON is deprecated; use policy/*.json: {source}",
            LegacyPolicyWarning,
            stacklevel=2,
        )
        value = _parse_json(match.group(1), source)
    return _freeze(value)
