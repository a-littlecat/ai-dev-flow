from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
EVAL_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = EVAL_DIR / "manifest.json"
LEDGER_PATH = EVAL_DIR / "results" / "stage-a-ledger.jsonl"
REPORT_PATH = EVAL_DIR / "results" / "stage-a-report.md"
SUMMARY_PATH = EVAL_DIR / "results" / "phase-b" / "summary.json"
POLICY_PATTERN = re.compile(
    r"<!-- POLICY_JSON_BEGIN -->\s*```json\s*(?P<json>.*?)\s*```\s*"
    r"<!-- POLICY_JSON_END -->",
    re.DOTALL,
)


def _load_v002() -> Any:
    path = EVAL_DIR.parent / "replay.py"
    spec = importlib.util.spec_from_file_location("lean_eval_v002_replay", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load V002 replay module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


V002 = _load_v002()
EvalError = V002.EvalError


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def relative_path(value: str) -> Path:
    path = (ROOT / value).resolve()
    if ROOT not in path.parents and path != ROOT:
        raise EvalError(f"path escapes repository: {value}")
    return path


def sha256_file_set(paths: list[str]) -> str:
    digest = hashlib.sha256()
    for path_text in sorted(paths):
        digest.update(path_text.encode("utf-8"))
        digest.update(b"\0")
        digest.update(relative_path(path_text).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def verify_file(path_text: str, expected_hash: str, label: str) -> Path:
    path = relative_path(path_text)
    if not path.is_file() or sha256_file(path) != expected_hash:
        raise EvalError(f"{label} is missing or hash-mismatched: {path_text}")
    return path


def load_policy(manifest: dict[str, Any]) -> dict[str, Any]:
    policy_ref = manifest["policy"]
    path = verify_file(policy_ref["path"], policy_ref["file_sha256"], "prototype policy")
    match = POLICY_PATTERN.search(path.read_text(encoding="utf-8"))
    if not match:
        raise EvalError("prototype POLICY_JSON block is missing")
    try:
        policy = json.loads(match.group("json"))
    except json.JSONDecodeError as exc:
        raise EvalError(f"prototype POLICY_JSON is invalid: {exc}") from exc
    if policy.get("schema_version") != policy_ref["schema_version"]:
        raise EvalError("prototype policy schema drifted")
    required = {"schema_version", "unknown_input", "routes", "review", "safety", "repair"}
    if set(policy) != required:
        raise EvalError("prototype policy has missing or unknown top-level fields")
    return policy


def effective_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    base_ref = manifest["base_manifest"]
    base_path = verify_file(base_ref["path"], base_ref["sha256"], "V002 base manifest")
    base = load_json(base_path)
    V002.verify_manifest(base)
    effective = copy.deepcopy(base)
    effective["evaluation_id"] = manifest["evaluation_id"]
    return effective


def load_protocol(manifest: dict[str, Any]) -> dict[str, Any]:
    protocol_ref = manifest["protocol"]
    path = verify_file(protocol_ref["path"], protocol_ref["sha256"], "V003 protocol")
    protocol = load_json(path)
    if protocol.get("schema_version") != "lean-eval-protocol/v1":
        raise EvalError("unsupported V003 protocol schema")
    if protocol.get("evaluation_id") != manifest["evaluation_id"]:
        raise EvalError("protocol evaluation_id mismatch")
    return protocol


def verify_manifest(manifest: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if manifest.get("schema_version") != "lean-eval-manifest/v2":
        raise EvalError("unsupported V003 manifest schema")
    if manifest.get("evaluation_id") != "V08-LEAN-EVAL-003":
        raise EvalError("unexpected V003 evaluation_id")
    if manifest.get("replacement_for") != "V08-LEAN-EVAL-002":
        raise EvalError("replacement relationship drifted")
    phase_b = manifest["phase_b"]
    if phase_b.get("execution_order") != ["no-skill", "lite", "full"]:
        raise EvalError("V003 execution order drifted")
    if phase_b.get("maximum_main_task_executions") != 3:
        raise EvalError("V003 main execution budget drifted")
    if sha256_file_set(phase_b["lite_workflow_files"]) != phase_b["lite_workflow_sha256"]:
        raise EvalError("V003 Lite workflow digest drifted")
    protocol = load_protocol(manifest)
    if protocol["execution_order"] != phase_b["execution_order"]:
        raise EvalError("manifest/protocol execution order mismatch")
    if protocol["maximum_main_task_executions"] != phase_b["maximum_main_task_executions"]:
        raise EvalError("manifest/protocol main budget mismatch")
    backend = protocol.get("backend_identity", {})
    if backend.get("exact_version_exposed_by_platform") is not False:
        raise EvalError("protocol must state the platform backend-version limitation")
    if backend.get("comparison_scope") != "same-parent-task-session-only":
        raise EvalError("protocol comparison scope is too broad")
    policy = load_policy(manifest)
    effective = effective_manifest(manifest)
    return policy, effective, protocol


def _require_bool(sample: dict[str, Any], key: str) -> bool:
    value = sample.get(key)
    if not isinstance(value, bool):
        raise EvalError(f"{sample.get('id', '<sample>')} {key} must be boolean")
    return value


def route_sample(sample: dict[str, Any], policy: dict[str, Any]) -> dict[str, str]:
    routes = policy["routes"]
    controlled_policy = routes["controlled"]
    lite_policy = routes["lite"]
    flags = set(sample["risk_flags"])
    ua_level = int(sample["ua_level"].removeprefix("UA"))
    delivery_action = _require_bool(sample, "delivery_action")
    real_environment_required = _require_bool(sample, "real_environment_required")
    real_environment_evidence = _require_bool(sample, "real_environment_evidence")
    controlled = any(
        (
            sample["task_class"] in set(controlled_policy["task_classes"]),
            ua_level >= controlled_policy["ua_min"],
            bool(flags & set(controlled_policy["risk_flags"])),
            sample["requested_action"] in set(controlled_policy["requested_actions"]),
            controlled_policy["when_delivery_action"] and delivery_action,
            controlled_policy["when_real_environment_required"]
            and real_environment_required,
        )
    )
    lite = all(
        (
            sample["task_class"] in set(lite_policy["task_classes"]),
            sample["action_authority"] == lite_policy["requires_action_authority"],
            sample["deterministic_coverage"]
            is lite_policy["requires_deterministic_coverage"],
            sample["user_observation_required"]
            is lite_policy["requires_user_observation"],
            not bool(flags & set(lite_policy["disallowed_risk_flags"])),
            not controlled,
        )
    )
    route = "Controlled" if controlled else "Lite" if lite else routes["fallback"]

    review_policy = policy["review"]
    if route == "Lite":
        review = review_policy["Lite"]
    elif route == "Controlled" and review_policy["Controlled"]["required"]:
        review = "Triggered"
    elif route == "Tracked" and flags & set(review_policy["Tracked"]["trigger_risk_flags"]):
        review = "Triggered"
    else:
        review = review_policy["Tracked"]["otherwise"]
    if review == "Triggered" and not (
        _require_bool(sample, "review_authority")
        and _require_bool(sample, "review_capability")
    ):
        review = review_policy["missing_authority_or_capability"]

    safety = policy["safety"]
    blocked = any(
        (
            sample["action_authority"] != safety["allowed_action_authority"],
            review == "Blocked",
            safety["require_real_environment_evidence"]
            and real_environment_required
            and not real_environment_evidence,
            safety["delivery_requires_controlled"]
            and delivery_action
            and route != "Controlled",
        )
    )
    return {
        "route": route,
        "review": review,
        "safety_gate": safety["missing_required_evidence"] if blocked else "Allowed",
    }


def repair_decision(trace: dict[str, Any], policy: dict[str, Any]) -> str:
    repair = policy["repair"]
    snapshots = trace.get("finding_snapshots")
    expected_rounds = list(range(repair["base_rounds"] + 1))
    if (
        repair["absolute_max_rounds"] != repair["base_rounds"] + 1
        or not isinstance(snapshots, list)
        or [item.get("round") for item in snapshots] != expected_rounds
    ):
        return repair["stop_decision"]
    if any(trace.get(key) is not True for key in repair["required_true_fields"]):
        return repair["stop_decision"]
    if any(trace.get(key) is not False for key in repair["required_false_fields"]):
        return repair["stop_decision"]
    if repair["round_3_target_required"] and not trace.get("round_3_target"):
        return repair["stop_decision"]
    if repair["scope_hashes_must_match"] and len(set(trace.get("scope_hashes", []))) != 1:
        return repair["stop_decision"]

    finding_maps: list[dict[str, str]] = []
    for snapshot in snapshots:
        findings = snapshot.get("findings")
        if not isinstance(findings, list):
            return repair["stop_decision"]
        mapped: dict[str, str] = {}
        for finding in findings:
            finding_id = finding.get("id") if isinstance(finding, dict) else None
            severity = finding.get("severity") if isinstance(finding, dict) else None
            if not finding_id or severity not in {"P0", "P1"} or finding_id in mapped:
                return repair["stop_decision"]
            mapped[finding_id] = severity
        finding_maps.append(mapped)
    if repair["p0_p1_counts_strictly_decrease"]:
        counts = [len(item) for item in finding_maps]
        if not all(left > right for left, right in zip(counts, counts[1:])):
            return repair["stop_decision"]
    severity_rank = {"P1": 1, "P0": 2}
    for previous, current in zip(finding_maps, finding_maps[1:]):
        if repair["finding_ids_must_be_stable"] and set(current) - set(previous):
            return repair["stop_decision"]
        if repair["severity_must_not_increase"] and any(
            severity_rank[current[finding_id]] > severity_rank[previous[finding_id]]
            for finding_id in set(previous) & set(current)
        ):
            return repair["stop_decision"]
    validations = trace.get("validation_scores", [])
    if repair["validation_scores_strictly_increase"] and (
        len(validations) != len(snapshots)
        or not all(left < right for left, right in zip(validations, validations[1:]))
    ):
        return repair["stop_decision"]
    return repair["extend_decision"]


def stage_a_records(
    manifest: dict[str, Any], policy: dict[str, Any], effective: dict[str, Any]
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for sample in effective["routes"]:
        actual = route_sample(sample, policy)
        records.append(
            {
                "schema_version": "lean-eval-ledger/v1",
                "record_type": "stage_a_route",
                "evaluation_id": manifest["evaluation_id"],
                "sample_id": sample["id"],
                "expected": sample["expected"],
                "actual": actual,
                "difference": V002.difference(sample["expected"], actual),
                "decision_source": manifest["policy"]["path"],
            }
        )
    traces = load_json(relative_path(effective["repair_trace_path"]))
    for trace in traces["traces"]:
        expected = {"decision": trace["expected_decision"]}
        actual = {"decision": repair_decision(trace, policy)}
        records.append(
            {
                "schema_version": "lean-eval-ledger/v1",
                "record_type": "stage_a_repair",
                "evaluation_id": manifest["evaluation_id"],
                "sample_id": trace["id"],
                "expected": expected,
                "actual": actual,
                "difference": V002.difference(expected, actual),
                "decision_source": manifest["policy"]["path"],
            }
        )
    return records


def render_ledger(records: list[dict[str, Any]]) -> str:
    return "".join(
        json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in records
    )


def render_report(manifest: dict[str, Any], records: list[dict[str, Any]]) -> str:
    failures = [record for record in records if record["difference"]]
    lines = [
        "# LEAN-002 V003 阶段 A 零额度回放报告",
        "",
        f"- 评估 ID：`{manifest['evaluation_id']}`",
        f"- Repair base：`{manifest['repair_base_commit']}`",
        f"- 续做授权 commit：`{manifest['authorization_commit']}`",
        f"- 决策源：`{manifest['policy']['path']}`",
        "- 模型 / Reviewer / subagent 调用：0",
        f"- 原始记录：{len(records)}（6 个路由样本 + 2 个 repair trace）",
        f"- 差异：{len(failures)}",
        f"- 阶段 A 门禁：{'通过' if not failures else '失败'}",
        "",
        "| 样本 | 类型 | Expected | Actual | Difference |",
        "|---|---|---|---|---|",
    ]
    for record in records:
        expected = ", ".join(f"{key}={value}" for key, value in record["expected"].items())
        actual = ", ".join(f"{key}={value}" for key, value in record["actual"].items())
        difference = ", ".join(record["difference"]) or "无"
        lines.append(
            f"| `{record['sample_id']}` | `{record['record_type']}` | "
            f"{expected} | {actual} | {difference} |"
        )
    lines.extend(
        [
            "",
            "## 结论边界",
            "",
            "- 本结果证明实际原型 policy 对冻结的 6 个 route 与 2 个 repair trace 给出预期结果。",
            "- 本结果不证明所有项目均无漏检，也不证明 phase B 的效率或任务质量。",
            "- 独立 Review 无 P0/P1 前，V003 的三次 main 调用必须保持 0。",
            "",
        ]
    )
    return "\n".join(lines)


def verify_bound_artifact(path_text: Any, expected_hash: Any, label: str) -> Path:
    prefix = "evaluations/v0.8/v003/results/phase-b/"
    if not isinstance(path_text, str) or not path_text.startswith(prefix):
        raise EvalError(f"{label} path is outside the V003 phase B evidence root")
    if not V002.is_sha256(expected_hash):
        raise EvalError(f"{label} hash is missing or invalid")
    path = relative_path(path_text)
    if not path.is_file() or sha256_file(path) != expected_hash:
        raise EvalError(f"{label} artifact is missing or hash-mismatched")
    return path


def validate_provenance_structure(
    provenance: dict[str, Any], manifest: dict[str, Any], protocol: dict[str, Any]
) -> None:
    required = {
        "schema_version",
        "evaluation_id",
        "parent_task_path",
        "fork_turns",
        "model_override",
        "reasoning_effort_override",
        "backend_exact_model_version",
        "execution_order",
        "receipts",
    }
    if not isinstance(provenance, dict) or set(provenance) != required:
        raise EvalError("run provenance has missing or unknown fields")
    if provenance["schema_version"] != "lean-run-provenance/v1":
        raise EvalError("unsupported run provenance schema")
    if provenance["evaluation_id"] != manifest["evaluation_id"]:
        raise EvalError("run provenance evaluation_id mismatch")
    if provenance["parent_task_path"] != protocol["parent_task_path"]:
        raise EvalError("run provenance parent task mismatch")
    if provenance["fork_turns"] != protocol["context_creation"]["fork_turns"]:
        raise EvalError("run provenance fork_turns mismatch")
    if provenance["model_override"] is not None or provenance["reasoning_effort_override"] is not None:
        raise EvalError("run provenance contains a forbidden model/reasoning override")
    if provenance["backend_exact_model_version"] != "not-exposed-by-platform":
        raise EvalError("run provenance overstates backend exact-version evidence")
    order = protocol["execution_order"]
    if provenance["execution_order"] != order:
        raise EvalError("run provenance execution order mismatch")
    receipts = provenance["receipts"]
    if not isinstance(receipts, list) or len(receipts) != 3:
        raise EvalError("run provenance requires exactly three main receipts")
    for sequence, (receipt, mode) in enumerate(zip(receipts, order), 1):
        required_receipt = {
            "sequence",
            "mode",
            "canonical_agent_path",
            "spawn_receipt_path",
            "spawn_receipt_sha256",
            "final_receipt_path",
            "final_receipt_sha256",
            "previous_final_receipt_sha256",
        }
        if not isinstance(receipt, dict) or set(receipt) != required_receipt:
            raise EvalError(f"{mode} provenance receipt has missing or unknown fields")
        if receipt["sequence"] != sequence or receipt["mode"] != mode:
            raise EvalError(f"{mode} provenance sequence mismatch")
        if receipt["canonical_agent_path"] != protocol["canonical_main_agents"][mode]:
            raise EvalError(f"{mode} canonical agent path mismatch")
        expected_previous = None if sequence == 1 else receipts[sequence - 2]["final_receipt_sha256"]
        if receipt["previous_final_receipt_sha256"] != expected_previous:
            raise EvalError(f"{mode} provenance receipt chain is broken")
        receipt_root = protocol["receipt_contract"]["artifact_root"]
        slug = f"{sequence:02d}-{mode}"
        if receipt["spawn_receipt_path"] != f"{receipt_root}{slug}-spawn.json":
            raise EvalError(f"{mode} spawn receipt path drifted")
        if receipt["final_receipt_path"] != f"{receipt_root}{slug}-final.json":
            raise EvalError(f"{mode} final receipt path drifted")


def validate_receipt_contents(
    provenance: dict[str, Any],
    manifest: dict[str, Any],
    protocol: dict[str, Any],
    runs: list[dict[str, Any]],
    spawn_receipts: list[dict[str, Any]],
    final_receipts: list[dict[str, Any]],
) -> None:
    for sequence, (receipt, spawn, final, run) in enumerate(
        zip(provenance["receipts"], spawn_receipts, final_receipts, runs), 1
    ):
        mode = receipt["mode"]
        canonical = protocol["canonical_main_agents"][mode]
        workflow_paths = [item.get("path") for item in run.get("workflow_inputs", [])]
        workflow_bundle = sha256_file_set(workflow_paths)
        model_calls = run.get("model_call_evidence", [])
        main_calls = [item for item in model_calls if item.get("kind") == "main"]
        if len(main_calls) != 1:
            raise EvalError(f"{mode} receipt cannot bind exactly one main evidence")
        main_call = main_calls[0]

        spawn_keys = {
            "schema_version",
            "evaluation_id",
            "sequence",
            "mode",
            "parent_task_path",
            "tool",
            "request",
            "tool_result",
            "previous_final_receipt_sha256",
            "workflow_bundle_sha256",
        }
        if not isinstance(spawn, dict) or set(spawn) != spawn_keys:
            raise EvalError(f"{mode} spawn receipt has missing or unknown fields")
        if spawn["schema_version"] != protocol["receipt_contract"]["spawn_schema"]:
            raise EvalError(f"{mode} spawn receipt schema mismatch")
        if (
            spawn["evaluation_id"] != manifest["evaluation_id"]
            or spawn["sequence"] != sequence
            or spawn["mode"] != mode
            or spawn["parent_task_path"] != protocol["parent_task_path"]
            or spawn["tool"] != "collaboration.spawn_agent"
        ):
            raise EvalError(f"{mode} spawn receipt identity mismatch")
        expected_request = {
            "task_name": canonical.removeprefix(f"{protocol['parent_task_path']}/"),
            "fork_turns": protocol["context_creation"]["fork_turns"],
            "model_override": protocol["context_creation"]["model_override"],
            "reasoning_effort_override": protocol["context_creation"][
                "reasoning_effort_override"
            ],
        }
        if spawn["request"] != expected_request:
            raise EvalError(f"{mode} actual spawn request drifted")
        if spawn["tool_result"] != {"task_name": canonical}:
            raise EvalError(f"{mode} actual spawn result path drifted")
        if spawn["previous_final_receipt_sha256"] != receipt[
            "previous_final_receipt_sha256"
        ]:
            raise EvalError(f"{mode} spawn was not chained after the previous final")
        if spawn["workflow_bundle_sha256"] != workflow_bundle:
            raise EvalError(f"{mode} spawn receipt workflow bundle mismatch")

        final_keys = {
            "schema_version",
            "evaluation_id",
            "sequence",
            "mode",
            "canonical_task_name",
            "completion_status",
            "spawn_receipt_sha256",
            "previous_final_receipt_sha256",
            "workflow_bundle_sha256",
            "main_evidence_path",
            "main_evidence_sha256",
        }
        if not isinstance(final, dict) or set(final) != final_keys:
            raise EvalError(f"{mode} final receipt has missing or unknown fields")
        if final["schema_version"] != protocol["receipt_contract"]["final_schema"]:
            raise EvalError(f"{mode} final receipt schema mismatch")
        if (
            final["evaluation_id"] != manifest["evaluation_id"]
            or final["sequence"] != sequence
            or final["mode"] != mode
            or final["canonical_task_name"] != canonical
            or final["completion_status"] != "completed"
        ):
            raise EvalError(f"{mode} final receipt identity/status mismatch")
        if final["spawn_receipt_sha256"] != receipt["spawn_receipt_sha256"]:
            raise EvalError(f"{mode} final receipt is not bound to its spawn receipt")
        if final["previous_final_receipt_sha256"] != receipt[
            "previous_final_receipt_sha256"
        ]:
            raise EvalError(f"{mode} final receipt chain mismatch")
        if final["workflow_bundle_sha256"] != workflow_bundle:
            raise EvalError(f"{mode} final receipt workflow bundle mismatch")
        if (
            final["main_evidence_path"] != main_call.get("evidence_path")
            or final["main_evidence_sha256"] != main_call.get("evidence_sha256")
        ):
            raise EvalError(f"{mode} final receipt is not bound to main-call evidence")


def verify_provenance(
    provenance_path: Path,
    manifest: dict[str, Any],
    protocol: dict[str, Any],
    runs: list[dict[str, Any]],
) -> dict[str, Any]:
    provenance = load_json(provenance_path)
    validate_provenance_structure(provenance, manifest, protocol)
    spawn_receipts: list[dict[str, Any]] = []
    final_receipts: list[dict[str, Any]] = []
    for receipt in provenance["receipts"]:
        spawn_path = verify_bound_artifact(
            receipt["spawn_receipt_path"],
            receipt["spawn_receipt_sha256"],
            f"{receipt['mode']} spawn receipt",
        )
        final_path = verify_bound_artifact(
            receipt["final_receipt_path"],
            receipt["final_receipt_sha256"],
            f"{receipt['mode']} final receipt",
        )
        spawn_receipts.append(load_json(spawn_path))
        final_receipts.append(load_json(final_path))
    validate_receipt_contents(
        provenance, manifest, protocol, runs, spawn_receipts, final_receipts
    )
    return {
        "pass": True,
        "same_parent_task": True,
        "fork_turns_none": True,
        "no_model_or_reasoning_override": True,
        "canonical_order_and_agent_paths": True,
        "receipt_content_and_chain_valid": True,
        "workflow_and_main_evidence_bound": True,
        "platform_agent_or_call_id": "not-exposed-by-platform",
        "platform_signed_receipts": False,
        "independent_live_cross_check_required": True,
        "backend_exact_model_version": "not-exposed-by-platform",
        "claim_scope": "same-parent-task-session-only",
    }


def score_phase_b(
    manifest: dict[str, Any], effective: dict[str, Any], policy: dict[str, Any],
    protocol: dict[str, Any], runs_path: Path, provenance_path: Path
) -> dict[str, Any]:
    payload = load_json(runs_path)
    runs = payload.get("runs", []) if isinstance(payload, dict) else []
    expected_lite_paths = manifest["phase_b"]["lite_workflow_files"]
    if len(runs) != 3 or [run.get("mode") for run in runs] != protocol["execution_order"]:
        raise EvalError("V003 runs are missing or out of order")
    lite_inputs = [item.get("path") for item in runs[1].get("workflow_inputs", [])]
    if lite_inputs != expected_lite_paths:
        raise EvalError("V003 Lite workflow inputs drifted from the frozen prototype")
    provenance = verify_provenance(provenance_path, manifest, protocol, runs)

    original_verify = V002.verify_bound_artifact
    original_stage_a = V002.stage_a_records
    try:
        V002.verify_bound_artifact = verify_bound_artifact
        V002.stage_a_records = lambda _manifest: stage_a_records(manifest, policy, effective)
        result = V002.score_phase_b(effective, runs_path)
    finally:
        V002.verify_bound_artifact = original_verify
        V002.stage_a_records = original_stage_a
    result["schema_version"] = "lean-eval-ledger/v2"
    result["provenance"] = provenance
    result["all_gates_pass"] = bool(result["all_gates_pass"] and provenance["pass"])
    result["conclusion_boundary"] = {
        "lite": "same frozen benchmark in this parent task session",
        "tracked_controlled": "six frozen route samples only",
        "repair": "two frozen repair traces only",
        "backend_exact_version": "not exposed; no cross-session equivalence claim",
    }
    return result


def run_verify() -> int:
    manifest = load_json(MANIFEST_PATH)
    policy, effective, protocol = verify_manifest(manifest)
    records = stage_a_records(manifest, policy, effective)
    if len(records) != 8 or any(record["difference"] for record in records):
        raise EvalError("V003 stage A has an unexpected difference")
    print(
        "V003 manifest, protocol, prototype policy and stage A verified; "
        "phase B main calls remain unauthorized until independent Review passes"
    )
    return 0


def run_replay(write: bool, check: bool) -> int:
    manifest = load_json(MANIFEST_PATH)
    policy, effective, _ = verify_manifest(manifest)
    records = stage_a_records(manifest, policy, effective)
    ledger = render_ledger(records)
    report = render_report(manifest, records)
    if write:
        LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
        LEDGER_PATH.write_text(ledger, encoding="utf-8", newline="\n")
        REPORT_PATH.write_text(report, encoding="utf-8", newline="\n")
    if check:
        if not LEDGER_PATH.is_file() or LEDGER_PATH.read_text(encoding="utf-8") != ledger:
            raise EvalError("saved V003 stage A ledger drifted")
        if not REPORT_PATH.is_file() or REPORT_PATH.read_text(encoding="utf-8") != report:
            raise EvalError("saved V003 stage A report drifted")
    print(f"V003 stage A: records={len(records)} differences={sum(bool(r['difference']) for r in records)}")
    return 0


def run_score(runs_path: Path, provenance_path: Path, write: bool, check: bool) -> int:
    manifest = load_json(MANIFEST_PATH)
    policy, effective, protocol = verify_manifest(manifest)
    result = score_phase_b(manifest, effective, policy, protocol, runs_path, provenance_path)
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if write:
        SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
        SUMMARY_PATH.write_text(rendered, encoding="utf-8", newline="\n")
    if check and (
        not SUMMARY_PATH.is_file() or SUMMARY_PATH.read_text(encoding="utf-8") != rendered
    ):
        raise EvalError("saved V003 phase B summary drifted")
    print(rendered, end="")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay V08-LEAN-EVAL-003")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("verify")
    replay_parser = subparsers.add_parser("replay")
    replay_parser.add_argument("--write", action="store_true")
    replay_parser.add_argument("--check", action="store_true")
    score_parser = subparsers.add_parser("score-phase-b")
    score_parser.add_argument("--runs", type=Path, required=True)
    score_parser.add_argument(
        "--provenance",
        type=Path,
        default=relative_path(
            "evaluations/v0.8/v003/results/phase-b/run-provenance.json"
        ),
    )
    score_parser.add_argument("--write", action="store_true")
    score_parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "verify":
            return run_verify()
        if args.command == "replay":
            return run_replay(args.write, args.check)
        return run_score(args.runs.resolve(), args.provenance.resolve(), args.write, args.check)
    except (EvalError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
