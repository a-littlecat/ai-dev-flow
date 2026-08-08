"""Public read-only facade for Workflow Contract inspection."""

from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import hashlib
import os
import pathlib
import re
import subprocess
import sys
from typing import Tuple


SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import _workflow_contract as reader
import _task_board as task_board
from policy_loader import PolicyLoadError, load_policy_document


# The private parser asks for the same normalized source path once per field and
# diagnostic.  Cache that pure lookup inside this public facade so large project
# inspection preserves identical provenance without repeated Win32 realpath I/O.
_original_source_path = reader._source_path


@lru_cache(maxsize=8192)
def _cached_source_path(path):
    target = pathlib.Path(path)
    if target.is_absolute():
        parts = target.parts
        for index in range(len(parts) - 1):
            if parts[index:index + 2] == ("docs", "tasks") and index > 0:
                return pathlib.PurePosixPath(*parts[index:]).as_posix()
    return _original_source_path(target)


reader._source_path = _cached_source_path


@lru_cache(maxsize=4096)
def _cached_reader_inspect(text, source_path, validate_filename):
    """Reuse immutable Reader reports only when path and complete text match."""

    return reader.inspect_text(
        text,
        pathlib.Path(source_path),
        validate_filename=validate_filename,
    )


@lru_cache(maxsize=4096)
def _cached_contract_validation(contract, source_file, source_sha256):
    """Cache pure validation by immutable report and complete frozen content."""

    del source_sha256
    return tuple(
        _validate(
            contract,
            require_commit=True,
            source_file=pathlib.Path(source_file),
        )
    )


@lru_cache(maxsize=4096)
def _cached_board_projection(contract, source_file, project_root):
    return _expected_board_projection(
        contract,
        pathlib.Path(source_file),
        pathlib.Path(project_root),
    )


@lru_cache(maxsize=64)
def _cached_board_diagnostics(project_root, projections, known_task_ids, board_sha256):
    del board_sha256
    return tuple(
        _board_diagnostics(
            pathlib.Path(project_root),
            projections,
            known_task_ids,
        )
    )


_original_board_path_value = task_board._path_value
_project_task_paths = frozenset()


def _fast_board_path_value(raw, board_path, project_root, header):
    value = raw.strip()
    if header == "备注":
        match = re.fullmatch(r"任务文件：\s*(.+)", value)
        if not match:
            return None
        value = match.group(1).strip()
    link = re.fullmatch(r"\[[^\]]+\]\(([^)]+)\)", value)
    if not link:
        return _original_board_path_value(
            raw,
            board_path,
            project_root,
            header,
        )
    normalized = link.group(1).strip().replace("\\", "/")
    relative = pathlib.PurePosixPath(normalized)
    if (
        relative.is_absolute()
        or not relative.parts
        or any(part in {"", ".", ".."} for part in relative.parts)
        or ":" in relative.parts[0]
    ):
        return None
    candidate = pathlib.Path(board_path).parent.joinpath(*relative.parts)
    if candidate in _project_task_paths:
        return candidate.relative_to(project_root).as_posix()
    return _original_board_path_value(
        raw,
        board_path,
        project_root,
        header,
    )


task_board._path_value = _fast_board_path_value
_transition_cache = {}


DISCLAIMER = "lint 通过只代表 Contract 结构和当前可确定规则通过，不代表 Review、用户验收、merge、release 或任务关闭已经完成。"
READY_STATES = {"Ready", "In Progress", "Blocked", "Review", "Needs Fix", "Accepted", "Closed"}
REVIEW_STATES = {"Review", "Needs Fix", "Accepted", "Closed"}
PLACEHOLDERS = {"", "待填写", "待确认", "TBD", "N/A", "不适用", "待执行时填写", "待执行后填写", "待审查", "待复测"}
TRANSITIONS = {("Draft","Ready"), ("Draft","Deferred"), ("Draft","Cancelled"), ("Ready","In Progress"), ("Ready","Blocked"), ("In Progress","Review"), ("In Progress","Blocked"), ("In Progress","Deferred"), ("Review","Needs Fix"), ("Review","Accepted"), ("Review","Blocked"), ("Needs Fix","In Progress"), ("Needs Fix","Review"), ("Accepted","Closed"), ("Blocked","Ready"), ("Blocked","Deferred"), ("Deferred","Ready"), ("Deferred","Cancelled")}
CORE_POLICY_PATH = SCRIPT_DIR.parent / "policy" / "core.json"


@dataclass(frozen=True)
class Summary:
    errors: int
    violations: int
    warnings: int
    exit_code: int


@dataclass(frozen=True)
class WorkflowReport:
    contracts: Tuple[reader.ReaderReport, ...]
    diagnostics: Tuple[reader.Diagnostic, ...]
    projections: object
    summary: Summary
    disclaimer: str = DISCLAIMER


@dataclass(frozen=True)
class BoardProjection:
    values: Tuple[Tuple[str, str], ...]
    provenance: Tuple[reader.Provenance, ...]

    def get(self, field, default=None):
        return dict(self.values).get(field, default)


def _field_line(contract, field):
    matches = [item.line for item in contract.provenance if item.field == field and item.line]
    return min(matches) if matches else 0


def _diag(contract, code, field, message):
    related = tuple(item for item in contract.provenance if item.field == field)
    line = _field_line(contract, field)
    severity = (
        "error"
        if code.startswith("E_")
        else "violation"
        if code.startswith("V_")
        else "warning"
    )
    suggestion = {
        "E_PARSE": "请使用精确 Markdown grammar，并删除重复或未知结构。",
        "E_UNKNOWN_VALUE": "请改为规范枚举或显式 Legacy 别名中的值。",
        "E_TASK_ID_CONFLICT": "请统一文件名、H1 与 Contract/TASK task_id。",
        "E_LEGACY_CONFLICT": "请统一该 Legacy 语义轴的所有来源值。",
        "W_LEGACY_INFERRED": "无需迁移；请确认显式 Legacy 映射符合预期。",
    }.get(code, "请按 Workflow Contract 规范修正该输入。")
    return reader.Diagnostic(
        code,
        severity,
        contract.source_path,
        line,
        1 if line else 0,
        message,
        suggestion,
        related,
    )


def _section_values(contract, names):
    return [field for section in contract.sections for field in section.fields if field.name in names and field.value.strip() not in PLACEHOLDERS]


def _has_section_value(contract, name):
    return bool(_section_values(contract, {name}))


def _has_ua_outcome(contract):
    if _has_section_value(contract, "UA 动作与结果"):
        return True
    return any(field.value.strip() not in PLACEHOLDERS for section in contract.sections if section.heading in {"用户动作等级 / 验收建议", "用户验收反馈 / 实机测试反馈"} for field in section.fields)


@lru_cache(maxsize=1)
def _review_policy_inputs():
    policy = load_policy_document(CORE_POLICY_PATH)
    controlled = policy["routes"]["controlled"]
    return (
        frozenset(controlled["task_classes"]),
        controlled["ua_min"],
        frozenset(controlled["risk_flags"]),
        frozenset(policy["review"]["Tracked"]["trigger_risk_flags"]),
    )


def _scheduling_risk_flags(source_file):
    if source_file is None:
        return frozenset()
    try:
        text = pathlib.Path(source_file).read_text(encoding="utf-8", errors="strict")
    except (OSError, UnicodeError):
        return frozenset()
    match = re.search(
        r"^## Scheduling\s*$([\s\S]*?)(?=^## |\Z)",
        text,
        flags=re.MULTILINE,
    )
    if match is None:
        return frozenset()
    values = re.findall(
        r"^- `risk_flags`: `([^`\r\n]+)`$",
        match.group(1),
        flags=re.MULTILINE,
    )
    if len(values) != 1 or values[0] == "none":
        return frozenset()
    return frozenset(values[0].split(";"))


def _policy_requires_review(contract, source_file):
    if contract.get("schema_version") != "adf/v0.10.0":
        return False
    try:
        task_classes, ua_min, controlled_risks, tracked_risks = _review_policy_inputs()
    except (OSError, UnicodeError, PolicyLoadError, KeyError, TypeError):
        return True
    ua_level = contract.get("ua_level") or ""
    ua_number = int(ua_level[2:]) if re.fullmatch(r"UA[0-7]", ua_level) else -1
    risks = _scheduling_risk_flags(source_file)
    return (
        contract.get("task_class") in task_classes
        or ua_number >= ua_min
        or bool(risks & (controlled_risks | tracked_risks))
        or "real_env_signal" in (contract.get("overlays") or "").split(";")
    )


def _single_value_conflicts(contract):
    diagnostics = []
    for name in ("Base / Diff", "隔离位置", "回滚方式"):
        fields = [field for section in contract.sections if section.heading == "Outcome" for field in section.fields if field.name == name]
        values = {field.value.strip() for field in fields}
        if len(values) > 1:
            diagnostics.append(_diag(contract, "E_PARSE", name, f"单值字段 {name} 重复且内容冲突"))
    return diagnostics


def _ua_evidence_is_locatable(contract, evidence, source_file):
    references = [item.strip() for item in evidence.split(";") if item.strip()]
    if not references:
        return False
    try:
        text = pathlib.Path(source_file).read_text(encoding="utf-8") if source_file else ""
    except (OSError, UnicodeError):
        text = ""
    headings = {match.group(1).strip().lower().replace("`", "").replace(" ", "-").replace("/", "") for match in re.finditer(r"^#{1,6}\s+(.+?)\s*$", text, flags=re.MULTILINE)}
    explicit = set(re.findall(r'<a\s+(?:id|name)=["\']([^"\']+)["\']\s*>\s*</a>', text, flags=re.IGNORECASE))
    return all(not reference.startswith("#") or reference[1:] in headings | explicit for reference in references)


def _validate(contract, *, require_commit=True, source_file=None):
    diagnostics = list(contract.diagnostics)
    diagnostics.extend(_single_value_conflicts(contract))
    if any(item.severity == "error" for item in diagnostics):
        return diagnostics
    values = dict(contract.normalized)
    lifecycle = values.get("lifecycle")
    review = values.get("review_status")
    review_requirement = values.get("review_requirement")
    ua_level = values.get("ua_level")
    ua_status = values.get("ua_status")
    authority = values.get("acceptance_authority")
    close = values.get("close_authority")
    merge = values.get("merge_status")
    merge_authority = values.get("merge_authority")
    task_type = values.get("task_type")
    task_class = values.get("task_class")

    state_bad = False
    if lifecycle in READY_STATES:
        required = {"目标", "非目标", "允许修改", "禁止修改", "完成标准", "验证命令或检查"}
        present = {item.name for item in _section_values(contract, required)}
        if present != required:
            state_bad = True
    if lifecycle in REVIEW_STATES:
        required = {"修改文件", "验证证据", "Review findings"}
        present = {item.name for item in _section_values(contract, required)}
        if present != required or (require_commit and values.get("commit_status") == "Not Recorded"):
            state_bad = True
    base_fields = _section_values(contract, {"Base / Diff"})
    base_value = base_fields[0].value if base_fields else ""
    if task_type in {"code", "test", "repair"} and lifecycle == "In Progress":
        if not re.fullmatch(r"base=[^\s`;]+(?:;diff=[^\s`;]+)?", base_value):
            state_bad = True
        if task_class in {"C", "D"} and (not _has_section_value(contract, "隔离位置") or not _has_section_value(contract, "回滚方式")):
            state_bad = True
    if task_type in {"code", "test", "repair"} and lifecycle in REVIEW_STATES:
        if not re.fullmatch(r"base=[^\s`;]+;diff=(?!pending|TBD)[^\s`;]+", base_value):
            state_bad = True
        if task_class in {"C", "D"} and (not _has_section_value(contract, "隔离位置") or not _has_section_value(contract, "回滚方式")):
            state_bad = True
    if lifecycle == "Needs Fix":
        findings = [item.value for item in _section_values(contract, {"Review findings"})]
        if not findings or all(value == "none" for value in findings):
            state_bad = True
    if merge == "Merged" and not _has_section_value(contract, "合并目标与事实证据"):
        state_bad = True
    if "real_env_signal" in values.get("overlays", "").split(";"):
        signal_section = next((section for section in contract.sections if section.heading == "实机测试信号复现（real_env_signal）"), None)
        if signal_section is None or not signal_section.fields:
            state_bad = True
    if state_bad:
        diagnostics.append(_diag(contract, "V_STATE_GUARD", "lifecycle", "当前 lifecycle 缺少必需正文、Outcome 或 Git 状态"))

    if lifecycle in {"Accepted", "Closed"}:
        review_blocked = (
            review_requirement in {"Required", "Legacy Unspecified"}
            and review != "Passed"
        ) or (
            review_requirement == "Not Required"
            and review not in {"Not Run", "Passed"}
        )
        if review_blocked:
            diagnostics.append(_diag(
                contract,
                "V_REVIEW_GUARD",
                "review_status",
                "Accepted/Closed 的 Review requirement/status 组合不满足完成门禁",
            ))
    if review_requirement == "Not Required" and _policy_requires_review(
        contract,
        source_file,
    ):
        diagnostics.append(_diag(
            contract,
            "V_REVIEW_REQUIREMENT_GUARD",
            "review_requirement",
            "canonical policy 输入要求独立 Review，不能声明 Not Required",
        ))
    ua_bad = False
    if lifecycle in {"Accepted", "Closed"} and (ua_status not in {"Passed", "Not Required"} or authority not in {"User Confirmed", "Designated Acceptor Confirmed"}):
        ua_bad = True
    if ua_level == "UA7" and ua_status in {"Passed", "Failed", "Deferred"} and authority != "User Confirmed":
        ua_bad = True
    if ua_status in {"Passed", "Failed", "Deferred"}:
        evidence = values.get("ua_evidence", "")
        if not evidence or not _ua_evidence_is_locatable(contract, evidence, source_file):
            ua_bad = True
    if ua_status == "Passed" and authority not in {"User Confirmed", "Designated Acceptor Confirmed"}:
        ua_bad = True
    if ua_level != "UA7" and ua_status in {"Failed", "Deferred"} and authority != "None":
        ua_bad = True
    if ua_status in {"Passed", "Failed", "Deferred"} and not _has_ua_outcome(contract):
        ua_bad = True
    if ua_level == "UA0" and ua_status not in {"Not Required", "Pending", "TBD"}:
        ua_bad = True
    if ua_status == "Not Required" and ua_level != "UA0":
        ua_bad = True
    if ua_status in {"Pending", "TBD"} and (values.get("ua_evidence") or authority != "None"):
        ua_bad = True
    if ua_status == "Not Required" and (values.get("ua_evidence") or (lifecycle not in {"Accepted", "Closed"} and authority != "None")):
        ua_bad = True
    if ua_bad:
        diagnostics.append(_diag(contract, "V_UA_GUARD", "ua_status", "UA 结果、证据或确认主体不满足门禁"))
    if lifecycle == "Closed" and close not in {"User Authorized", "Rule Authorized"}:
        diagnostics.append(_diag(contract, "V_CLOSE_AUTHORITY", "close_authority", "Closed 缺少有效关闭授权"))
    if lifecycle != "Closed" and close in {"User Authorized", "Rule Authorized"}:
        diagnostics.append(_diag(contract, "V_CLOSE_AUTHORITY", "close_authority", "非 Closed 不得提前声明关闭授权"))
    if merge == "Merged" and lifecycle not in {"Accepted", "Closed"}:
        diagnostics.append(_diag(contract, "V_DELIVERY_ORDER", "merge_status", "merge 发生早于 Accepted"))
    if merge == "Merged" and merge_authority != "User Authorized":
        diagnostics.append(_diag(contract, "V_DELIVERY_AUTHORITY", "merge_authority", "Merged 缺少本次用户授权"))

    if values.get("extensions_required") not in {None, "none"}:
        diagnostics.append(_diag(contract, "V_EXTENSION_REQUIRED_UNKNOWN", "extensions_required", "存在当前实现未知的 required extension"))
    if values.get("extensions_optional") not in {None, "none"}:
        diagnostics.append(_diag(contract, "W_EXTENSION_OPTIONAL_UNKNOWN", "extensions_optional", "存在当前实现未知的 optional extension"))

    section_fields = {field.name: field.value for section in contract.sections for field in section.fields}
    feedback = {"原任务未完成":"original_incomplete", "本轮回归":"regression", "新需求或范围扩大":"scope_expansion", "环境或配置问题":"environment", "证据不足":"insufficient_evidence"}.get(section_fields.get("反馈分类"))
    scope = {"是":"current", "否":"outside", "待确认":"unknown"}.get(section_fields.get("是否属于当前 TASK 范围"))
    repair = section_fields.get("下一步建议") in {"进入修复任务（repair_task）", "进入审查-修复循环（review_repair_loop）"}
    if repair:
        if lifecycle in {"Accepted", "Closed"} or feedback not in {"original_incomplete", "regression"} or scope != "current":
            diagnostics.append(_diag(contract, "V_ACCEPTANCE_SCOPE", "ua_status", "验收反馈不允许进入当前任务修复"))
        else:
            signals = {"RED 失败信号", "GREEN 通过信号", "SIGNAL 证据来源"}
            if not signals.issubset(section_fields):
                diagnostics.append(_diag(contract, "V_SIGNAL_GATE", "ua_status", "修复前缺少 RED/GREEN/SIGNAL"))

    if any(value in {"User Confirmed", "Designated Acceptor Confirmed", "User Authorized"} for value in (authority, close, merge_authority)):
        diagnostics.append(_diag(contract, "W_AUTHORITY_UNVERIFIABLE", "acceptance_authority", "当前 Markdown 只能证明授权记录形状，不能证明主体身份"))
    diagnostics.sort(key=lambda item: (item.path, item.line, item.column, item.code, item.message))
    return diagnostics


def _summary(diagnostics):
    errors = sum(item.severity == "error" for item in diagnostics)
    violations = sum(item.severity == "violation" for item in diagnostics)
    warnings = sum(item.severity == "warning" for item in diagnostics)
    return Summary(errors, violations, warnings, 2 if errors else (1 if violations else 0))


def _expected_board_projection(contract, source_file, project_root):
    values = dict(contract.normalized)
    task_id = values.get("task_id")
    if not task_id or any(item.severity == "error" for item in contract.diagnostics):
        return None
    review_status = values.get("review_status") or ""
    if values.get("schema_version") == "adf/v0.7.0":
        review_status = {
            "Not Run": "Pending",
            "Blocked": "Do Not Merge",
        }.get(review_status, review_status)
    expected = (
        ("task_id", task_id),
        ("title", contract.title or ""),
        ("task_class", values.get("task_class") or ""),
        ("lifecycle", values.get("lifecycle") or ""),
        ("review_status", review_status),
        ("ua_level", values.get("ua_level") or ""),
        ("acceptance", f"{values.get('ua_status')} / {values.get('acceptance_authority')}"),
        ("delivery", f"commit={values.get('commit_status')};merge={values.get('merge_status')};merge_authority={values.get('merge_authority')}"),
        ("task_path", source_file.relative_to(project_root).as_posix()),
    )
    provenance = list(contract.provenance)
    provenance.append(reader.Provenance("title", contract.source_path, "H1", 1, contract.title or "", "canonical"))
    provenance.append(reader.Provenance("task_path", contract.source_path, "filesystem", 0, expected[-1][1], "canonical"))
    return BoardProjection(expected, tuple(provenance))


def _projection_provenance(projection, field):
    aliases = {"acceptance": {"ua_status", "acceptance_authority"}, "delivery": {"commit_status", "merge_status", "merge_authority"}}
    fields = aliases.get(field, {field})
    return tuple(item for item in projection.provenance if item.field in fields)


def _board_cell_provenance(cell, board_path):
    return reader.Provenance(cell.field, "docs/TASK_BOARD.md", "TASK_BOARD", cell.line, cell.raw_value, cell.source_type)


def _board_diagnostic(code, board_path, line, message, related=()):
    item = reader._diagnostic(code, board_path, line, message, related=related)
    return reader.Diagnostic(item.code, item.severity, "docs/TASK_BOARD.md", item.line, item.column, item.message, item.suggestion, item.provenance)


def _board_values_match(field, expected, actual):
    if actual.startswith("CONFLICT:"):
        return False
    if "not_projected" not in actual:
        return expected == actual
    if field == "acceptance":
        return all(right == "not_projected" or left == right for left, right in zip(expected.split(" / "), actual.split(" / ")))
    if field == "delivery":
        expected_parts = dict(item.split("=", 1) for item in expected.split(";"))
        actual_parts = dict(item.split("=", 1) for item in actual.split(";"))
        return all(value == "not_projected" or expected_parts.get(key) == value for key, value in actual_parts.items())
    return expected == actual


def _board_diagnostics(project_root, projections, known_task_ids=()):
    board_path = project_root / "docs" / "TASK_BOARD.md"
    if not board_path.exists():
        return [_board_diagnostic("W_BOARD_MISSING", board_path, 0, f"expected={dict(item.values)};actual=TASK_BOARD missing", related=item.provenance) for item in projections]
    parsed = task_board.parse_board(board_path, project_root)
    if parsed.error_message:
        return [_board_diagnostic("E_BOARD_PARSE", board_path, parsed.error_line, parsed.error_message)]
    diagnostics = []
    by_id = {}
    duplicate_ids = set()
    for row in parsed.rows:
        task_id = row.get("task_id")
        if task_id in by_id:
            duplicate_ids.add(task_id)
            cell = next(item for item in row.cells if item.field == "task_id")
            diagnostics.append(_board_diagnostic("E_TASK_ID_CONFLICT", board_path, row.line, f"TASK_BOARD task_id 重复：{task_id}", related=(_board_cell_provenance(cell, board_path),)))
        else:
            by_id[task_id] = row
    expected_by_id = {item.get("task_id"): item for item in projections}
    expected_by_path = {item.get("task_path"): item for item in projections}
    conflicted_rows = set()
    conflicted_expected = set()
    for row in parsed.rows:
        expected_for_path = expected_by_path.get(row.get("task_path"))
        if expected_for_path is not None and row.get("task_id") != expected_for_path.get("task_id"):
            cell = next(item for item in row.cells if item.field == "task_id")
            related = _projection_provenance(expected_for_path, "task_id") + (_board_cell_provenance(cell, board_path),)
            diagnostics.append(_board_diagnostic("E_TASK_ID_CONFLICT", board_path, row.line, f"board_task_id={row.get('task_id')};task_id={expected_for_path.get('task_id')};path={row.get('task_path')}", related=related))
            conflicted_rows.add(row.line)
            conflicted_expected.add(expected_for_path.get("task_id"))
    for task_id, expected in expected_by_id.items():
        if task_id in duplicate_ids:
            continue
        actual = by_id.get(task_id)
        if actual is None:
            if task_id not in conflicted_expected:
                diagnostics.append(_board_diagnostic("W_BOARD_MISSING", board_path, 0, f"expected={dict(expected.values)};actual=row missing", related=expected.provenance))
            continue
        actual_values = dict(actual.values)
        cells = {item.field: item for item in actual.cells}
        for field, expected_value in expected.values:
            if field not in actual.projected_fields:
                continue
            actual_value = actual_values.get(field)
            if not _board_values_match(field, expected_value, actual_value):
                related = _projection_provenance(expected, field) + (_board_cell_provenance(cells[field], board_path),)
                message = f"field={field};expected={expected_value};actual={actual_value};task_id={task_id}"
                diagnostics.append(_board_diagnostic("V_BOARD_DRIFT", board_path, actual.line, message, related=related))
    for task_id, row in by_id.items():
        if task_id not in duplicate_ids and task_id not in expected_by_id and task_id not in known_task_ids and row.line not in conflicted_rows:
            cell = next(item for item in row.cells if item.field == "task_id")
            diagnostics.append(_board_diagnostic("W_BOARD_ORPHAN", board_path, row.line, f"expected=TASK missing;actual={dict(row.values)}", related=tuple(_board_cell_provenance(item, board_path) for item in row.cells)))
    if not parsed.canonical:
        diagnostics.append(_board_diagnostic("W_LEGACY_INFERRED", board_path, 1, "TASK_BOARD 使用 Legacy partial projection"))
    return diagnostics


def _transition_code(before, after, verifiable=True):
    if not verifiable or not before or not after:
        return "W_TRANSITION_UNVERIFIABLE"
    if before == after or (before, after) in TRANSITIONS:
        return None
    return "V_ILLEGAL_TRANSITION"


def _transition_diagnostic(contract, code):
    if code == "V_ILLEGAL_TRANSITION":
        return _diag(contract, code, "lifecycle", "Git 历史证明 lifecycle 发生非法流转")
    if code == "W_TRANSITION_UNVERIFIABLE":
        return _diag(contract, code, "lifecycle", "Git 历史不足，无法证明 lifecycle 流转")
    return None


def _review_transition_diagnostic(contract, history_reports, after_report):
    if after_report.get("schema_version") != "adf/v0.10.0":
        return None
    after = after_report.get("review_status")
    historical_states = {
        report.get("review_status")
        for report in history_reports
        if report.get("schema_version") == "adf/v0.10.0"
    }
    if historical_states & {"In Review", "Needs Fix", "Blocked", "Passed"} and after == "Not Run":
        return _diag(
            contract,
            "V_REVIEW_REGRESSION",
            "review_status",
            "Git 历史证明 Review 已开始或已有结论，不能回退为 Not Run",
        )
    return None


def _path_chunks(paths, *, limit=200, character_limit=12000):
    chunks = []
    current = []
    characters = 0
    for path in paths:
        cost = len(path) + 1
        if current and (len(current) >= limit or characters + cost > character_limit):
            chunks.append(tuple(current))
            current = []
            characters = 0
        current.append(path)
        characters += cost
    if current:
        chunks.append(tuple(current))
    return tuple(chunks)


GIT_TRANSITION_TIMEOUT_SECONDS = 5.0


def _run_git_text(root, arguments, *, input_text=None):
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        input=input_text,
        text=True,
        encoding="utf-8",
        errors="strict",
        capture_output=True,
        check=True,
        timeout=GIT_TRANSITION_TIMEOUT_SECONDS,
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
    ).stdout


def _history_commits(root, relatives):
    commits = {}
    ambiguous = set()
    scopes = tuple(
        sorted(
            {
                pathlib.PurePosixPath(relative).parent.as_posix()
                for relative in relatives
            }
        )
    )
    for chunk in _path_chunks(scopes):
        output = _run_git_text(
            root,
            [
                "log",
                "--format=format:%x00COMMIT%x00%H%x00",
                "--name-status",
                "--find-renames",
                "--find-copies",
                "--find-copies-harder",
                "-z",
                "--",
                *chunk,
            ],
        )
        wanted = set(relatives)
        fields = output.split("\0")
        current = None
        index = 0
        while index < len(fields):
            token = fields[index].lstrip("\n")
            if not token:
                index += 1
                continue
            if token == "COMMIT":
                if index + 1 >= len(fields):
                    raise ValueError("truncated history commit")
                current = fields[index + 1].strip()
                if not re.fullmatch(r"[0-9a-f]{40}", current or ""):
                    raise ValueError("invalid history commit")
                index += 2
                continue
            if current is None or index + 1 >= len(fields):
                raise ValueError("history status precedes commit")
            status = token
            if status.startswith(("R", "C")):
                if index + 2 >= len(fields):
                    raise ValueError("truncated rename history")
                paths = (fields[index + 1], fields[index + 2])
                for relative in paths:
                    if relative in wanted:
                        ambiguous.add(relative)
                index += 3
                continue
            relative = fields[index + 1]
            if relative in wanted and relative not in ambiguous:
                commits.setdefault(relative, []).append(current)
            index += 2
    for relative in ambiguous:
        commits[relative] = []
    return {
        relative: tuple(values)
        for relative, values in commits.items()
    }


def _history_commit(root, relative):
    output = _run_git_text(
        root,
        ["log", "-n", "1", "--format=format:%H%x00", "--name-status", "-z", "--", relative],
    )
    fields = output.split("\0")
    commit = fields[0].strip()
    if not commit:
        raise ValueError("no path history")
    if any(field.startswith(("R", "C")) for field in fields[1:] if field):
        raise ValueError("rename history")
    return commit


def _cat_file_batch(root, queries):
    if not queries:
        return {}
    encoded_queries = tuple(query.encode("utf-8") for query in queries)
    result = subprocess.run(
        ["git", "-C", str(root), "cat-file", "--batch"],
        input=b"".join(query + b"\n" for query in encoded_queries),
        capture_output=True,
        check=True,
        timeout=GIT_TRANSITION_TIMEOUT_SECONDS,
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
    )
    output = result.stdout
    offset = 0
    blobs = {}
    for query, encoded_query in zip(queries, encoded_queries):
        line_end = output.find(b"\n", offset)
        if line_end < 0:
            raise ValueError("truncated cat-file header")
        header = output[offset:line_end]
        offset = line_end + 1
        if header == encoded_query + b" missing":
            blobs[query] = None
            continue
        parts = header.rsplit(b" ", 2)
        if len(parts) != 3 or parts[1] != b"blob":
            raise ValueError("unexpected cat-file object")
        size = int(parts[2])
        end = offset + size
        if end >= len(output) or output[end:end + 1] != b"\n":
            raise ValueError("truncated cat-file blob")
        blobs[query] = output[offset:end]
        offset = end + 1
    if output[offset:]:
        raise ValueError("unexpected cat-file output")
    return blobs


def _git_transition_diagnostics(contracts, source_files):
    pairs = tuple(zip(contracts, source_files))
    if not pairs:
        return {}
    unavailable = {
        source_file: (_transition_diagnostic(contract, "W_TRANSITION_UNVERIFIABLE"),)
        for contract, source_file in pairs
    }
    try:
        root_output = _run_git_text(
            source_files[0].parent,
            ["rev-parse", "--show-toplevel", "HEAD", "HEAD^"],
        )
        root_lines = root_output.splitlines()
        if len(root_lines) < 3 or not re.fullmatch(r"[0-9a-f]{40}", root_lines[1].strip()):
            raise ValueError("invalid repository revision")
        root = pathlib.Path(root_lines[0].strip()).resolve()
        head = root_lines[1].strip()
        by_relative = {}
        for contract, source_file in pairs:
            relative = source_file.relative_to(root).as_posix()
            by_relative[relative] = (contract, source_file)

        dirty_paths = set()
        tracked_paths = set()
        relatives = tuple(sorted(by_relative))
        for chunk in _path_chunks(relatives):
            status = _run_git_text(root, ["status", "--porcelain=v1", "-z", "--", *chunk])
            for field in status.split("\0"):
                if not field:
                    continue
                dirty_paths.add(field[3:] if len(field) > 3 and field[2] == " " else field)
            tracked = _run_git_text(root, ["ls-files", "-z", "--", *chunk])
            tracked_paths.update(field for field in tracked.split("\0") if field)

        eligible = tuple(
            relative
            for relative in relatives
            if relative in tracked_paths and relative not in dirty_paths
        )
        cached = {}
        uncached = []
        for relative in eligible:
            contract, source_file = by_relative[relative]
            key = (contract, str(source_file), head)
            if key in _transition_cache:
                cached[relative] = _transition_cache[key]
            else:
                uncached.append(relative)
        commits = _history_commits(root, tuple(uncached)) if uncached else {}

        queries = []
        for relative in sorted(commits):
            commit_chain = commits[relative]
            if not commit_chain:
                continue
            latest = commit_chain[0]
            queries.extend((f"{latest}:{relative}", f"{latest}^:{relative}"))
            queries.extend(f"{commit}:{relative}" for commit in commit_chain)
        blobs = _cat_file_batch(root, tuple(dict.fromkeys(queries)))
    except (OSError, UnicodeError, ValueError, subprocess.SubprocessError):
        return unavailable

    diagnostics = dict(unavailable)
    for relative, diagnostic in cached.items():
        diagnostics[by_relative[relative][1]] = diagnostic
    for relative, commit_chain in commits.items():
        contract, source_file = by_relative[relative]
        if not commit_chain:
            result = (
                _diag(
                    contract,
                    "V_REVIEW_HISTORY_AMBIGUOUS",
                    "review_status",
                    "TASK Git 历史包含重命名或复制，无法证明 Review 历史完整，必须人工核验",
                ),
            )
            diagnostics[source_file] = result
            if len(_transition_cache) >= 4096:
                _transition_cache.pop(next(iter(_transition_cache)))
            _transition_cache[(contract, str(source_file), head)] = result
            continue
        try:
            latest = commit_chain[0]
            current = blobs[f"{latest}:{relative}"]
            previous = blobs[f"{latest}^:{relative}"]
            if current is None or previous is None:
                raise ValueError("missing historical blob")
            before_report = _cached_reader_inspect(
                previous.decode("utf-8"),
                str(source_file),
                False,
            )
            after_report = _cached_reader_inspect(
                current.decode("utf-8"),
                str(source_file),
                False,
            )
            if any(
                item.severity == "error"
                for item in before_report.diagnostics + after_report.diagnostics
            ):
                raise ValueError("history parse conflict")
            before = before_report.get("lifecycle")
            historical_after = after_report.get("lifecycle")
            after = contract.get("lifecycle")
            if historical_after != after:
                raise ValueError("working tree differs from HEAD blob")
            code = _transition_code(before, after, True)
            history_reports = tuple(
                _cached_reader_inspect(
                    blobs[f"{commit}:{relative}"].decode("utf-8"),
                    str(source_file),
                    False,
                )
                for commit in commit_chain
                if blobs[f"{commit}:{relative}"] is not None
            )
            review_diagnostic = _review_transition_diagnostic(
                contract,
                history_reports,
                after_report,
            )
        except (UnicodeError, ValueError):
            code = "W_TRANSITION_UNVERIFIABLE"
            review_diagnostic = None
        diagnostic = _transition_diagnostic(contract, code)
        result = tuple(
            item for item in (diagnostic, review_diagnostic) if item is not None
        )
        diagnostics[source_file] = result
        if len(_transition_cache) >= 4096:
            _transition_cache.pop(next(iter(_transition_cache)))
        _transition_cache[(contract, str(source_file), head)] = result
    return diagnostics


def _git_transition_diagnostic(contract, source_file):
    return _git_transition_diagnostics((contract,), (source_file,)).get(source_file, ())


class WorkflowContract:
    @staticmethod
    def inspect(target, *, frozen_task_texts=None):
        global _project_task_paths
        path = pathlib.Path(target)
        if path.is_file() and path.suffix.lower() == ".md":
            path = path.resolve()
            paths = (path,)
            _project_task_paths = frozenset()
            validate_filename = True
            project_target = False
        elif path.is_dir() and (path / "docs" / "tasks").is_dir():
            path = path.resolve()
            task_dir = (path / "docs" / "tasks").resolve()
            if not task_dir.is_relative_to(path):
                diagnostic = reader._diagnostic(
                    "E_PARSE",
                    task_dir,
                    0,
                    "docs/tasks 必须位于项目根内",
                )
                return WorkflowReport(
                    (),
                    (diagnostic,),
                    "not_evaluated",
                    _summary((diagnostic,)),
                )
            paths = tuple(
                sorted(
                    (
                        item.resolve()
                        if getattr(item.lstat(), "st_file_attributes", 0) & 0x400
                        else item.absolute()
                        for item in task_dir.glob("*.md")
                    ),
                    key=lambda item: item.as_posix(),
                )
            )
            if any(not item.is_relative_to(task_dir) for item in paths):
                diagnostic = reader._diagnostic(
                    "E_PARSE",
                    task_dir,
                    0,
                    "TASK path 必须位于 docs/tasks 内",
                )
                return WorkflowReport(
                    (),
                    (diagnostic,),
                    "not_evaluated",
                    _summary((diagnostic,)),
                )
            _project_task_paths = frozenset(paths)
            validate_filename = True
            project_target = True
        else:
            diagnostic = reader._diagnostic("E_PARSE", path, 0, "target 必须是单个 Markdown TASK 或含 docs/tasks 的项目根")
            return WorkflowReport((), (diagnostic,), "not_evaluated", _summary((diagnostic,)))
        frozen = {
            pathlib.Path(key).absolute(): value
            for key, value in (frozen_task_texts or {}).items()
        }
        frozen_sha256 = {
            item: hashlib.sha256(text.encode("utf-8")).digest()
            for item, text in frozen.items()
        }
        contracts = tuple(
            _cached_reader_inspect(
                frozen[item].removeprefix("\ufeff"),
                str(item),
                validate_filename,
            )
            if item in frozen
            else reader.inspect_task(item, validate_filename=validate_filename)
            for item in paths
        )
        diagnostics = []
        projections = []
        seen_ids = {}
        with ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="workflow-transition-read",
        ) as executor:
            transitions_future = executor.submit(
                _git_transition_diagnostics,
                contracts,
                paths,
            )
            for contract, source_file in zip(contracts, paths):
                if source_file in frozen_sha256:
                    diagnostics.extend(
                        _cached_contract_validation(
                            contract,
                            str(source_file),
                            frozen_sha256[source_file],
                        )
                    )
                else:
                    diagnostics.extend(
                        _validate(
                            contract,
                            require_commit=True,
                            source_file=source_file,
                        )
                    )
                task_id = contract.get("task_id")
                if task_id and task_id in seen_ids:
                    diagnostics.append(_diag(contract, "E_TASK_ID_CONFLICT", "task_id", "项目中 task_id 重复"))
                elif task_id:
                    seen_ids[task_id] = contract.source_path
                if project_target:
                    projection = (
                        _cached_board_projection(
                            contract,
                            str(source_file),
                            str(path),
                        )
                        if source_file in frozen_sha256
                        else _expected_board_projection(contract, source_file, path)
                    )
                    if projection is not None:
                        projections.append(projection)
            if project_target:
                board_path = path / "docs" / "TASK_BOARD.md"
                if frozen and board_path.is_file():
                    board_sha256 = hashlib.sha256(board_path.read_bytes()).digest()
                    diagnostics.extend(
                        _cached_board_diagnostics(
                            str(path),
                            tuple(projections),
                            tuple(seen_ids),
                            board_sha256,
                        )
                    )
                else:
                    diagnostics.extend(
                        _board_diagnostics(path, projections, tuple(seen_ids))
                    )
            transitions = transitions_future.result()
        for source_file in paths:
            diagnostics.extend(transitions.get(source_file, ()))
        if path.is_dir() and (path / "docs" / "PROJECT_OVERLAY.md").exists():
            diagnostics.append(reader._diagnostic("W_PROJECT_OVERLAY_UNEVALUATED", path / "docs" / "PROJECT_OVERLAY.md", 1, "发现 Project Overlay，但 CONTRACT-007 前不求值"))
        diagnostics.sort(key=lambda item: (item.path, item.line, item.column, item.code, item.message))
        projection_state = tuple(sorted(projections, key=lambda item: item.get("task_id", ""))) if project_target else "not_evaluated: single_task_target"
        return WorkflowReport(tuple(sorted(contracts, key=lambda item: (item.get("task_id", ""), item.source_path))), tuple(diagnostics), projection_state, _summary(diagnostics))
