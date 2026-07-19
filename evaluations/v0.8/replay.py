from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = EVAL_DIR / "manifest.json"
LEDGER_PATH = EVAL_DIR / "results" / "stage-a-ledger.jsonl"
REPORT_PATH = EVAL_DIR / "results" / "stage-a-report.md"

CONTROLLED_FLAGS = {
    "architecture",
    "data_migration",
    "delivery",
    "external_sync",
    "real_environment",
    "release",
    "security",
}
TRACKED_REVIEW_FLAGS = {
    "business_files_gt_3",
    "build_or_deploy_config",
    "core_execution_path",
    "core_writer_path",
    "explicit_independent_review",
    "historical_p1",
    "public_api",
    "shared_component",
    "tests_do_not_cover_oracle",
}


class EvalError(RuntimeError):
    pass


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def sha256_file_set(paths: list[str]) -> str:
    digest = hashlib.sha256()
    for path_text in sorted(paths):
        data = relative_path(path_text).read_bytes()
        digest.update(path_text.encode("utf-8"))
        digest.update(b"\0")
        digest.update(data)
        digest.update(b"\0")
    return digest.hexdigest()


def utf8_metrics(paths: list[str]) -> tuple[int, int]:
    byte_count = 0
    nonempty_lines = 0
    for path_text in paths:
        data = relative_path(path_text).read_bytes()
        text = data.decode("utf-8")
        byte_count += len(data)
        nonempty_lines += sum(bool(line.strip()) for line in text.splitlines())
    return byte_count, nonempty_lines


def git_bytes(*args: str) -> bytes:
    process = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode != 0:
        message = process.stderr.decode("utf-8", errors="replace").strip()
        raise EvalError(f"git {' '.join(args)} failed: {message}")
    return process.stdout


def git_text(*args: str) -> str:
    return git_bytes(*args).decode("utf-8")


def relative_path(value: str) -> Path:
    path = (ROOT / value).resolve()
    if ROOT not in path.parents and path != ROOT:
        raise EvalError(f"path escapes repository: {value}")
    return path


def verify_file_hash(path_text: str, expected: str) -> None:
    if expected == "TO_BE_FROZEN":
        raise EvalError(f"unfrozen hash: {path_text}")
    actual = sha256_file(relative_path(path_text))
    if actual != expected:
        raise EvalError(f"hash mismatch for {path_text}: {actual} != {expected}")


def verify_git_evidence(sample: dict[str, Any]) -> None:
    evidence = sample["git_evidence"]
    task_path = evidence["task_path"]
    for key in ("base_commit", "payload_commit", "review_commit", "validation_commit"):
        git_bytes("cat-file", "-e", f"{evidence[key]}^{{commit}}")

    snapshots = {
        "task_sha256": evidence["payload_commit"],
        "review_sha256": evidence["review_commit"],
        "validation_sha256": evidence["validation_commit"],
    }
    for hash_key, commit in snapshots.items():
        actual = sha256_bytes(git_bytes("show", f"{commit}:{task_path}"))
        if actual != evidence[hash_key]:
            raise EvalError(
                f"{sample['id']} {hash_key} mismatch: {actual} != {evidence[hash_key]}"
            )

    diff = git_bytes(
        "diff",
        "--binary",
        evidence["base_commit"],
        evidence["payload_commit"],
        "--",
    )
    actual_diff_hash = sha256_bytes(diff)
    if actual_diff_hash != evidence["payload_diff_sha256"]:
        raise EvalError(
            f"{sample['id']} payload diff mismatch: "
            f"{actual_diff_hash} != {evidence['payload_diff_sha256']}"
        )


def count_lines_at_commit(commit: str, path: str) -> int:
    return len(git_bytes("show", f"{commit}:{path}").decode("utf-8").splitlines())


def verify_baseline(manifest: dict[str, Any]) -> None:
    commit = manifest["freeze_commit"]
    git_bytes("cat-file", "-e", f"{commit}^{{commit}}")
    files = git_text("ls-tree", "-r", "--name-only", commit).splitlines()
    skill_files = [item for item in files if item.startswith("skills/ai-dev-flow/")]
    markdown_files = [item for item in skill_files if item.endswith(".md")]
    reference_files = [
        item for item in files if item.startswith("skills/ai-dev-flow/references/")
    ]
    reference_markdown = [item for item in reference_files if item.endswith(".md")]
    actual = {
        "skill_files": len(skill_files),
        "skill_markdown_files": len(markdown_files),
        "skill_markdown_lines": sum(count_lines_at_commit(commit, item) for item in markdown_files),
        "reference_files": len(reference_files),
        "reference_markdown_lines": sum(
            count_lines_at_commit(commit, item) for item in reference_markdown
        ),
        "skill_md_lines": count_lines_at_commit(commit, "skills/ai-dev-flow/SKILL.md"),
        "workflow_md_lines": count_lines_at_commit(
            commit, "skills/ai-dev-flow/references/WORKFLOW.md"
        ),
        "task_template_md_lines": count_lines_at_commit(
            commit, "skills/ai-dev-flow/references/TASK_TEMPLATE.md"
        ),
        "prompts_md_lines": count_lines_at_commit(
            commit, "skills/ai-dev-flow/references/PROMPTS.md"
        ),
    }
    if actual != manifest["baseline"]:
        raise EvalError(f"baseline mismatch: {actual} != {manifest['baseline']}")


def verify_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("schema_version") != "lean-eval-manifest/v1":
        raise EvalError("unsupported manifest schema")
    if len(manifest.get("routes", [])) != 6:
        raise EvalError("exactly six route samples are required")
    if manifest["phase_b"]["execution_order"] != ["no-skill", "lite", "full"]:
        raise EvalError("phase B execution order drifted")
    if manifest["phase_b"]["maximum_main_task_executions"] != 3:
        raise EvalError("phase B execution budget drifted")

    phase_b = manifest["phase_b"]
    if sha256_file_set(phase_b["benchmark_baseline_files"]) != phase_b[
        "benchmark_baseline_sha256"
    ]:
        raise EvalError("benchmark baseline digest drifted")
    if sha256_file_set(phase_b["no_skill_workflow_files"]) != phase_b[
        "no_skill_workflow_sha256"
    ]:
        raise EvalError("no-skill workflow digest drifted")
    if sha256_file_set(phase_b["full_workflow_files"]) != phase_b[
        "full_workflow_sha256"
    ]:
        raise EvalError("full workflow digest drifted")

    verify_baseline(manifest)
    for sample in manifest["routes"]:
        if sample.get("requested_action") in {None, ""}:
            raise EvalError(f"{sample['id']} requested_action is missing")
        if sample.get("action_authority") not in {"Allowed", "Denied", "Unknown"}:
            raise EvalError(f"{sample['id']} action_authority is invalid")
        for key in ("delivery_action", "real_environment_required", "real_environment_evidence"):
            if not isinstance(sample.get(key), bool):
                raise EvalError(f"{sample['id']} {key} must be boolean")
        if sample["source_kind"] == "git_history":
            verify_git_evidence(sample)
        else:
            verify_file_hash(sample["source_path"], sample["source_sha256"])

    for path_text, expected in manifest["phase_b"]["artifact_sha256"].items():
        verify_file_hash(path_text, expected)
    verify_file_hash(manifest["repair_trace_path"], manifest["repair_trace_sha256"])

    schema = load_json(EVAL_DIR / "ledger.schema.json")
    if schema.get("title") != "ai-dev-flow v0.8 evaluation ledger":
        raise EvalError("ledger schema title drifted")
    traces = load_json(relative_path(manifest["repair_trace_path"]))
    if [trace["id"] for trace in traces.get("traces", [])] != [
        "REPAIR-SYN-001",
        "REPAIR-SYN-002",
    ]:
        raise EvalError("repair trace IDs drifted")


def route_sample(sample: dict[str, Any]) -> dict[str, str]:
    flags = set(sample["risk_flags"])
    ua_level = int(sample["ua_level"].removeprefix("UA"))
    controlled = (
        sample["task_class"] == "D"
        or ua_level >= 5
        or bool(flags & CONTROLLED_FLAGS)
    )
    lite = (
        sample["task_class"] in {"A", "B"}
        and sample["deterministic_coverage"]
        and not sample["user_observation_required"]
        and not controlled
        and not bool(flags & TRACKED_REVIEW_FLAGS)
    )
    if controlled:
        route = "Controlled"
    elif lite:
        route = "Lite"
    else:
        route = "Tracked"

    if route == "Lite":
        review = "Skipped"
    elif route == "Controlled" or bool(flags & TRACKED_REVIEW_FLAGS):
        review = "Triggered"
    else:
        review = "Skipped"

    if review == "Triggered" and not (
        sample["review_authority"] and sample["review_capability"]
    ):
        review = "Blocked"

    safety_gate = "Allowed"
    if (
        sample["action_authority"] != "Allowed"
        or review == "Blocked"
        or (sample["real_environment_required"] and not sample["real_environment_evidence"])
        or (sample["delivery_action"] and route != "Controlled")
    ):
        safety_gate = "Blocked"
    return {"route": route, "review": review, "safety_gate": safety_gate}


def repair_decision(trace: dict[str, Any]) -> str:
    snapshots = trace["finding_snapshots"]
    if len(snapshots) != 3 or [item.get("round") for item in snapshots] != [0, 1, 2]:
        return "Stop"
    finding_maps: list[dict[str, str]] = []
    for snapshot in snapshots:
        findings = snapshot.get("findings")
        if not isinstance(findings, list):
            return "Stop"
        mapped: dict[str, str] = {}
        for finding in findings:
            finding_id = finding.get("id") if isinstance(finding, dict) else None
            severity = finding.get("severity") if isinstance(finding, dict) else None
            if not finding_id or severity not in {"P0", "P1"} or finding_id in mapped:
                return "Stop"
            mapped[finding_id] = severity
        finding_maps.append(mapped)
    counts = [len(item) for item in finding_maps]
    validations = trace["validation_scores"]
    scope_frozen = len(set(trace["scope_hashes"])) == 1
    findings_improve = counts[0] > counts[1] > counts[2]
    validation_improves = (
        len(validations) == 3 and validations[0] < validations[1] < validations[2]
    )
    severity_rank = {"P1": 1, "P0": 2}
    no_new_high_findings = True
    no_severity_regression = True
    for previous, current in zip(finding_maps, finding_maps[1:]):
        if set(current) - set(previous):
            no_new_high_findings = False
        for finding_id in set(previous) & set(current):
            if severity_rank[current[finding_id]] > severity_rank[previous[finding_id]]:
                no_severity_regression = False
    capabilities = trace["reviewer_capable"] and trace["repairer_capable"]
    monotonic_progress = all(
        [
            scope_frozen,
            trace["dependencies_frozen"],
            trace["authority_frozen"],
            findings_improve,
            no_new_high_findings,
            no_severity_regression,
            validation_improves,
            trace["root_cause_known"],
            bool(trace["round_3_target"]),
            capabilities,
            trace["within_cost_boundary"],
            not trace["external_side_effect"],
        ]
    )
    return "ExtendRound3" if monotonic_progress else "Stop"


def difference(expected: dict[str, Any], actual: dict[str, Any]) -> list[str]:
    keys = sorted(set(expected) | set(actual))
    return [key for key in keys if expected.get(key) != actual.get(key)]


def stage_a_records(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for sample in manifest["routes"]:
        actual = route_sample(sample)
        records.append(
            {
                "schema_version": "lean-eval-ledger/v1",
                "record_type": "stage_a_route",
                "evaluation_id": manifest["evaluation_id"],
                "sample_id": sample["id"],
                "expected": sample["expected"],
                "actual": actual,
                "difference": difference(sample["expected"], actual),
            }
        )
    traces = load_json(relative_path(manifest["repair_trace_path"]))
    for trace in traces["traces"]:
        expected = {"decision": trace["expected_decision"]}
        actual = {"decision": repair_decision(trace)}
        records.append(
            {
                "schema_version": "lean-eval-ledger/v1",
                "record_type": "stage_a_repair",
                "evaluation_id": manifest["evaluation_id"],
                "sample_id": trace["id"],
                "expected": expected,
                "actual": actual,
                "difference": difference(expected, actual),
            }
        )
    return records


def render_ledger(records: list[dict[str, Any]]) -> str:
    return "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in records)


def render_report(manifest: dict[str, Any], records: list[dict[str, Any]]) -> str:
    failures = [record for record in records if record["difference"]]
    lines = [
        "# LEAN-001 阶段 A 零额度回放报告",
        "",
        f"- 评估 ID：`{manifest['evaluation_id']}`",
        f"- 冻结 commit：`{manifest['freeze_commit']}`",
        "- 模型 / Reviewer / subagent 调用：0",
        f"- 原始记录：{len(records)}（6 个路由样本 + 2 个 repair trace）",
        f"- 差异：{len(failures)}",
        f"- 阶段 A 门禁：{'通过' if not failures else '失败'}",
        "",
        "## 逐样本结果",
        "",
        "| 样本 | 类型 | Expected | Actual | Difference |",
        "|---|---|---|---|---|",
    ]
    for record in records:
        expected = ", ".join(f"{k}={v}" for k, v in record["expected"].items())
        actual = ", ".join(f"{k}={v}" for k, v in record["actual"].items())
        diff = ", ".join(record["difference"]) or "无"
        lines.append(
            f"| `{record['sample_id']}` | `{record['record_type']}` | "
            f"{expected} | {actual} | {diff} |"
        )
    baseline = manifest["baseline"]
    lines.extend(
        [
            "",
            "## 冻结规模基线",
            "",
            f"- Skill 文件：{baseline['skill_files']}。",
            f"- Skill Markdown：{baseline['skill_markdown_files']} 文件 / {baseline['skill_markdown_lines']} 行。",
            f"- references：{baseline['reference_files']} 文件 / {baseline['reference_markdown_lines']} 行。",
            f"- `SKILL.md` / `WORKFLOW.md` / `TASK_TEMPLATE.md` / `PROMPTS.md`：{baseline['skill_md_lines']} / {baseline['workflow_md_lines']} / {baseline['task_template_md_lines']} / {baseline['prompts_md_lines']} 行。",
            "",
            "## 有限结论",
            "",
            "- Lite 两个固定合成样本均跳过 Reviewer，且只在 action authority 为 Allowed、无真实环境或 delivery 阻断时继续。",
            "- Tracked 两个历史 P1 样本均触发 Reviewer；Controlled 两个高风险样本均强制 Reviewer，缺少真实环境证据和 release authority 的动作均被 Blocked。",
            "- 收敛 trace 只获得一次第 3 轮，停滞/回退 trace 被停止；模型变化未重置预算。",
            "- 结论只适用于本 manifest；当前尚未验证真实任务的工作流输入、模型调用和用户问题是否下降。",
            "",
            "## 下一门禁",
            "",
            "只有本报告差异为 0、hash 校验通过且独立 Review 无 P0/P1，才允许创建默认关闭、可整体回退的 `LEAN-002` 最小原型。",
            "",
        ]
    )
    return "\n".join(lines)


def reduction(full: int, lite: int) -> dict[str, Any]:
    if full == 0:
        return {"status": "insufficient", "value": None, "pass": False}
    value = (full - lite) / full
    return {"status": "measured", "value": value, "pass": value >= 0.5}


def is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def require_nonnegative_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise EvalError(f"{label} must be a non-negative integer")
    return value


def verify_bound_artifact(path_text: Any, expected_hash: Any, label: str) -> Path:
    if not isinstance(path_text, str) or not path_text.startswith(
        "evaluations/v0.8/results/phase-b/"
    ):
        raise EvalError(f"{label} path is outside the phase B evidence root")
    if not is_sha256(expected_hash):
        raise EvalError(f"{label} hash is missing or invalid")
    path = relative_path(path_text)
    if not path.is_file() or sha256_file(path) != expected_hash:
        raise EvalError(f"{label} artifact is missing or hash-mismatched")
    return path


def normalize_workflow_inputs(
    manifest: dict[str, Any], mode: str, inputs: Any
) -> dict[str, Any]:
    if not isinstance(inputs, list) or not inputs:
        raise EvalError(f"{mode} workflow_inputs must be a non-empty list")
    if any(not isinstance(item, dict) or set(item) != {"path", "sha256"} for item in inputs):
        raise EvalError(f"{mode} workflow_inputs must contain only path/sha256 records")
    paths = [item["path"] for item in inputs]
    if any(not isinstance(path, str) or not path for path in paths) or len(paths) != len(set(paths)):
        raise EvalError(f"{mode} workflow input paths are empty or duplicated")
    for item in inputs:
        if not is_sha256(item["sha256"]):
            raise EvalError(f"{mode} workflow input hash is invalid")
        path = relative_path(item["path"])
        if not path.is_file() or sha256_file(path) != item["sha256"]:
            raise EvalError(f"{mode} workflow input is missing or hash-mismatched: {item['path']}")

    phase_b = manifest["phase_b"]
    if mode == "no-skill" and paths != phase_b["no_skill_workflow_files"]:
        raise EvalError("no-skill workflow input set drifted")
    if mode == "full" and paths != phase_b["full_workflow_files"]:
        raise EvalError("full workflow input set drifted")
    if mode == "lite":
        prefix = phase_b["lite_workflow_prefix"]
        if len(paths) > manifest["thresholds"]["new_core_files_max"]:
            raise EvalError("Lite prototype exceeds the frozen core-file budget")
        if any(not path.startswith(prefix) for path in paths):
            raise EvalError("Lite workflow input is outside the default-off prototype")
        if not any(path.endswith("/SKILL.md") for path in paths):
            raise EvalError("Lite workflow input is missing prototype SKILL.md")

    expected_bundle = sha256_file_set(paths)
    byte_count, nonempty_lines = utf8_metrics(paths)
    return {
        "paths": paths,
        "bundle_sha256": expected_bundle,
        "workflow_input_bytes": byte_count,
        "workflow_input_nonempty_lines": nonempty_lines,
    }


def normalize_model_calls(calls: Any, workflow_bundle_sha256: str, mode: str) -> dict[str, Any]:
    if not isinstance(calls, list) or not calls:
        raise EvalError(f"{mode} model_call_evidence must contain the main task call")
    allowed_keys = {"id", "kind", "evidence_path", "evidence_sha256", "input_manifest_sha256"}
    ids: set[str] = set()
    paths: set[str] = set()
    reviewer_calls = 0
    main_calls = 0
    for call in calls:
        if not isinstance(call, dict) or set(call) != allowed_keys:
            raise EvalError(f"{mode} model call evidence has missing or unknown fields")
        if not isinstance(call["id"], str) or not call["id"] or call["id"] in ids:
            raise EvalError(f"{mode} model call IDs are empty or duplicated")
        ids.add(call["id"])
        if call["kind"] not in {"main", "reviewer", "subagent", "retry"}:
            raise EvalError(f"{mode} model call kind is invalid")
        if call["input_manifest_sha256"] != workflow_bundle_sha256:
            raise EvalError(f"{mode} model call is not bound to its workflow input")
        verify_bound_artifact(call["evidence_path"], call["evidence_sha256"], f"{mode} model call")
        if call["evidence_path"] in paths:
            raise EvalError(f"{mode} model call evidence path is duplicated")
        paths.add(call["evidence_path"])
        reviewer_calls += call["kind"] == "reviewer"
        main_calls += call["kind"] == "main"
    if calls[0]["kind"] != "main":
        raise EvalError(f"{mode} first model call must be the main task execution")
    if main_calls != 1:
        raise EvalError(f"{mode} must contain exactly one main task execution")
    return {
        "model_calls": len(calls),
        "main_calls": main_calls,
        "reviewer_calls": reviewer_calls,
    }


def normalize_run(manifest: dict[str, Any], run: Any, mode: str, sequence: int) -> dict[str, Any]:
    allowed_keys = {
        "run_id",
        "mode",
        "sequence",
        "model_identity",
        "baseline_sha256",
        "brief_sha256",
        "workflow_inputs",
        "model_call_evidence",
        "blocking_questions",
        "test_exit",
        "test_passed",
        "test_total",
        "output_path",
        "output_sha256",
        "verification_evidence_path",
        "verification_evidence_sha256",
        "completion_criteria",
        "scope_violation",
        "sensitive_data_exposed",
    }
    if not isinstance(run, dict) or set(run) != allowed_keys:
        raise EvalError(f"{mode} run has missing or unknown fields")
    if run["run_id"] != f"{manifest['evaluation_id']}-{mode}" or run["mode"] != mode:
        raise EvalError(f"{mode} run identity mismatch")
    if run["sequence"] != sequence:
        raise EvalError(f"{mode} run sequence mismatch")
    if not isinstance(run["model_identity"], str) or not run["model_identity"].strip():
        raise EvalError(f"{mode} model identity is missing")
    if run["baseline_sha256"] != manifest["phase_b"]["benchmark_baseline_sha256"]:
        raise EvalError(f"{mode} baseline hash is not bound to the manifest")
    brief_path = manifest["phase_b"]["benchmark_brief"]
    if run["brief_sha256"] != manifest["phase_b"]["artifact_sha256"][brief_path]:
        raise EvalError(f"{mode} brief hash is not bound to the manifest")

    workflow = normalize_workflow_inputs(manifest, mode, run["workflow_inputs"])
    calls = normalize_model_calls(
        run["model_call_evidence"], workflow["bundle_sha256"], mode
    )
    questions = run["blocking_questions"]
    if not isinstance(questions, list) or any(
        not isinstance(item, str) or not item.strip() for item in questions
    ):
        raise EvalError(f"{mode} blocking questions must be non-empty strings")

    test_exit = run["test_exit"]
    if isinstance(test_exit, bool) or not isinstance(test_exit, int):
        raise EvalError(f"{mode} test_exit must be an integer")
    test_passed = require_nonnegative_int(run["test_passed"], f"{mode} test_passed")
    test_total = require_nonnegative_int(run["test_total"], f"{mode} test_total")
    verify_bound_artifact(run["output_path"], run["output_sha256"], f"{mode} output")
    verify_bound_artifact(
        run["verification_evidence_path"],
        run["verification_evidence_sha256"],
        f"{mode} verification",
    )

    criteria = run["completion_criteria"]
    required_criteria = manifest["phase_b"]["completion_criteria"]
    if (
        not isinstance(criteria, dict)
        or set(criteria) != set(required_criteria)
        or any(not isinstance(value, bool) for value in criteria.values())
    ):
        raise EvalError(f"{mode} completion criteria are incomplete or invalid")
    if not isinstance(run["scope_violation"], bool) or not isinstance(
        run["sensitive_data_exposed"], bool
    ):
        raise EvalError(f"{mode} scope/security flags must be boolean")

    return {
        "mode": mode,
        "sequence": sequence,
        "model_identity": run["model_identity"].strip(),
        **workflow,
        **calls,
        "blocking_user_questions": len(questions),
        "test_exit": test_exit,
        "test_passed": test_passed,
        "test_total": test_total,
        "output_sha256": run["output_sha256"],
        "completion_criteria": criteria,
        "scope_violation": run["scope_violation"],
        "sensitive_data_exposed": run["sensitive_data_exposed"],
    }


def path_exists_at_commit(commit: str, path_text: str) -> bool:
    process = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}:{path_text}"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return process.returncode == 0


def mechanical_costs(manifest: dict[str, Any], payload: dict[str, Any], lite_paths: list[str]) -> tuple[dict[str, Any], dict[str, Any]]:
    if payload.get("active_core_files") != lite_paths:
        raise EvalError("active_core_files must exactly match the Lite workflow inputs")
    active_bytes, active_lines = utf8_metrics(lite_paths)
    _, baseline_lines = utf8_metrics(manifest["phase_b"]["full_workflow_files"])
    maintenance = {
        "active_core_references": sum("/references/" in path for path in lite_paths),
        "new_core_files": sum(
            not path_exists_at_commit(manifest["freeze_commit"], path) for path in lite_paths
        ),
        "active_spec_utf8_bytes": active_bytes,
        "active_spec_nonempty_lines": active_lines,
        "frozen_baseline_nonempty_lines": baseline_lines,
    }

    migration_ref = payload.get("migration_evidence")
    if not isinstance(migration_ref, dict) or set(migration_ref) != {"path", "sha256"}:
        raise EvalError("migration_evidence must be a bound path/hash record")
    migration_path = verify_bound_artifact(
        migration_ref["path"], migration_ref["sha256"], "migration evidence"
    )
    migration_payload = load_json(migration_path)
    if migration_payload.get("schema_version") != "lean-migration-evidence/v1":
        raise EvalError("migration evidence schema is invalid")
    user_steps = migration_payload.get("user_steps")
    if not isinstance(user_steps, list) or any(
        not isinstance(item, str) or not item.strip() for item in user_steps
    ):
        raise EvalError("migration user steps must be a list of non-empty strings")

    task_changes = git_text(
        "diff", "--name-only", manifest["freeze_commit"], "--", "docs/tasks"
    ).splitlines()
    historical_rewrites = sum(
        not Path(path).name.startswith("LEAN-") for path in task_changes
    )
    dependency_names = {
        "package.json",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "pyproject.toml",
        "requirements.txt",
        "poetry.lock",
        "Pipfile",
        "Pipfile.lock",
    }
    all_changes = git_text("diff", "--name-only", manifest["freeze_commit"], "--").splitlines()
    dependency_changes = sum(Path(path).name in dependency_names for path in all_changes)
    migration = {
        "user_steps": len(user_steps),
        "historical_tasks_rewritten": historical_rewrites,
        "required_dependencies_added": dependency_changes,
        "implementation_tasks": len(list((ROOT / "docs" / "tasks").glob("LEAN-*.md"))),
    }
    return maintenance, migration


def score_phase_b(manifest: dict[str, Any], runs_path: Path) -> dict[str, Any]:
    payload = load_json(runs_path)
    required_payload_keys = {
        "schema_version",
        "evaluation_id",
        "execution_order",
        "runs",
        "active_core_files",
        "migration_evidence",
    }
    if not isinstance(payload, dict) or set(payload) != required_payload_keys:
        raise EvalError("phase B payload has missing or unknown fields")
    if payload.get("schema_version") != "lean-phase-b-runs/v1":
        raise EvalError("unsupported phase B runs schema")
    if payload.get("evaluation_id") != manifest["evaluation_id"]:
        raise EvalError("phase B evaluation_id mismatch")
    if payload.get("execution_order") != manifest["phase_b"]["execution_order"]:
        raise EvalError("phase B execution order mismatch")
    runs = payload.get("runs")
    if not isinstance(runs, list) or len(runs) != 3:
        raise EvalError("phase B requires exactly three ordered runs")
    normalized = [
        normalize_run(manifest, run, mode, sequence)
        for run, mode, sequence in zip(
            runs, manifest["phase_b"]["execution_order"], (1, 2, 3)
        )
    ]
    if len({item["model_identity"] for item in normalized}) != 1:
        raise EvalError("phase B model identity changed")
    if sum(item["main_calls"] for item in normalized) != manifest["phase_b"][
        "maximum_main_task_executions"
    ]:
        raise EvalError("phase B main task execution budget was exceeded")

    by_mode = {item["mode"]: item for item in normalized}
    lite = by_mode["lite"]
    full = by_mode["full"]
    no_skill = by_mode["no-skill"]
    efficiency = {
        "workflow_bytes": reduction(full["workflow_input_bytes"], lite["workflow_input_bytes"]),
        "workflow_nonempty_lines": reduction(
            full["workflow_input_nonempty_lines"], lite["workflow_input_nonempty_lines"]
        ),
        "model_calls": reduction(full["model_calls"], lite["model_calls"]),
        "blocking_user_questions": reduction(
            full["blocking_user_questions"], lite["blocking_user_questions"]
        ),
    }
    result_ok = all(
        run["test_exit"] == 0
        and run["test_passed"] == manifest["phase_b"]["oracle"]["tests_total"]
        and run["test_total"] == manifest["phase_b"]["oracle"]["tests_total"]
        and all(run["completion_criteria"].values())
        and not run["scope_violation"]
        and not run["sensitive_data_exposed"]
        for run in normalized
    )
    stage_a = stage_a_records(manifest)
    safety_ok = len(stage_a) == 8 and all(not record["difference"] for record in stage_a)
    maintenance, migration = mechanical_costs(
        manifest, payload, lite["paths"]
    )
    maintenance_ok = (
        maintenance.get("active_core_references", 10**9)
        <= manifest["thresholds"]["active_core_references_max"]
        and maintenance.get("new_core_files", 10**9)
        <= manifest["thresholds"]["new_core_files_max"]
        and maintenance.get("active_spec_nonempty_lines", 10**9)
        <= maintenance.get("frozen_baseline_nonempty_lines", -1)
    )
    migration_ok = (
        migration["user_steps"]
        <= manifest["thresholds"]["user_migration_steps_max"]
        and migration["historical_tasks_rewritten"] == 0
        and migration["required_dependencies_added"] == 0
        and migration["implementation_tasks"]
        <= manifest["thresholds"]["implementation_tasks_max"]
    )
    efficiency_ok = all(item["pass"] for item in efficiency.values())
    lite_review_ok = lite["reviewer_calls"] == 0
    all_gates_pass = all(
        [efficiency_ok, result_ok, safety_ok, maintenance_ok, migration_ok, lite_review_ok]
    )
    no_skill_same_quality = (
        no_skill["test_exit"] == lite["test_exit"] == 0
        and no_skill["completion_criteria"] == lite["completion_criteria"]
        and not no_skill["scope_violation"]
        and not lite["scope_violation"]
    )
    no_skill_lower_cost = (
        no_skill["workflow_input_bytes"] < lite["workflow_input_bytes"]
        and no_skill["model_calls"] <= lite["model_calls"]
        and no_skill["blocking_user_questions"] <= lite["blocking_user_questions"]
    )
    return {
        "schema_version": "lean-eval-ledger/v1",
        "record_type": "phase_b_summary",
        "evaluation_id": manifest["evaluation_id"],
        "efficiency": efficiency,
        "task_result_pass": result_ok,
        "safety_pass": safety_ok,
        "maintenance_pass": maintenance_ok,
        "migration_pass": migration_ok,
        "maintenance": maintenance,
        "migration": migration,
        "lite_reviewer_zero": lite_review_ok,
        "all_gates_pass": all_gates_pass,
        "normalized_runs": normalized,
        "lite_policy": (
            "DoNotUseSkill"
            if no_skill_same_quality and no_skill_lower_cost
            else "UseLitePrototype"
        ),
    }


def run_verify() -> int:
    manifest = load_json(MANIFEST_PATH)
    verify_manifest(manifest)
    print("VERIFY_OK routes=6 repair_traces=2 hashes=ok baseline=ok")
    return 0


def run_replay(write: bool, check: bool) -> int:
    manifest = load_json(MANIFEST_PATH)
    verify_manifest(manifest)
    records = stage_a_records(manifest)
    ledger = render_ledger(records)
    report = render_report(manifest, records)
    failures = [record for record in records if record["difference"]]
    if write:
        LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
        LEDGER_PATH.write_text(ledger, encoding="utf-8", newline="\n")
        REPORT_PATH.write_text(report, encoding="utf-8", newline="\n")
    if check:
        if not LEDGER_PATH.exists() or LEDGER_PATH.read_text(encoding="utf-8") != ledger:
            raise EvalError("stage A ledger is missing or stale")
        if not REPORT_PATH.exists() or REPORT_PATH.read_text(encoding="utf-8") != report:
            raise EvalError("stage A report is missing or stale")
    print(f"REPLAY_OK records={len(records)} differences={len(failures)} model_calls=0")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay frozen ai-dev-flow v0.8 evaluation")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("verify")
    replay_parser = subparsers.add_parser("replay")
    replay_parser.add_argument("--write", action="store_true")
    replay_parser.add_argument("--check", action="store_true")
    score_parser = subparsers.add_parser("score-phase-b")
    score_parser.add_argument("--runs", required=True, type=Path)
    args = parser.parse_args()

    if args.command == "verify":
        return run_verify()
    if args.command == "replay":
        if not args.write and not args.check:
            parser.error("replay requires --write or --check")
        return run_replay(args.write, args.check)
    if args.command == "score-phase-b":
        manifest = load_json(MANIFEST_PATH)
        verify_manifest(manifest)
        score = score_phase_b(manifest, args.runs.resolve())
        print(json.dumps(score, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if score["all_gates_pass"] else 1
    raise EvalError(f"unknown command: {args.command}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except EvalError as exc:
        print(f"EVAL_ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
