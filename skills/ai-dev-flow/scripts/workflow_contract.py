"""Public read-only facade for Workflow Contract inspection."""

from dataclasses import dataclass
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


DISCLAIMER = "lint 通过只代表 Contract 结构和当前可确定规则通过，不代表 Review、用户验收、merge、release 或任务关闭已经完成。"
READY_STATES = {"Ready", "In Progress", "Blocked", "Review", "Needs Fix", "Accepted", "Closed"}
REVIEW_STATES = {"Review", "Needs Fix", "Accepted", "Closed"}
PLACEHOLDERS = {"", "待填写", "待确认", "TBD", "N/A", "不适用", "待执行时填写", "待执行后填写", "待审查", "待复测"}
TRANSITIONS = {("Draft","Ready"), ("Draft","Deferred"), ("Draft","Cancelled"), ("Ready","In Progress"), ("Ready","Blocked"), ("In Progress","Review"), ("In Progress","Blocked"), ("In Progress","Deferred"), ("Review","Needs Fix"), ("Review","Accepted"), ("Review","Blocked"), ("Needs Fix","In Progress"), ("Needs Fix","Review"), ("Accepted","Closed"), ("Blocked","Ready"), ("Blocked","Deferred"), ("Deferred","Ready"), ("Deferred","Cancelled")}


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
    return reader._diagnostic(code, pathlib.Path(contract.source_path), _field_line(contract, field), message, related=related)


def _section_values(contract, names):
    return [field for section in contract.sections for field in section.fields if field.name in names and field.value.strip() not in PLACEHOLDERS]


def _has_section_value(contract, name):
    return bool(_section_values(contract, {name}))


def _has_ua_outcome(contract):
    if _has_section_value(contract, "UA 动作与结果"):
        return True
    return any(field.value.strip() not in PLACEHOLDERS for section in contract.sections if section.heading in {"用户动作等级 / 验收建议", "用户验收反馈 / 实机测试反馈"} for field in section.fields)


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

    if lifecycle in {"Accepted", "Closed"} and review != "Passed":
        diagnostics.append(_diag(contract, "V_REVIEW_GUARD", "review_status", "Accepted/Closed 必须 Review Passed"))
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
    expected = (
        ("task_id", task_id),
        ("title", contract.title or ""),
        ("task_class", values.get("task_class") or ""),
        ("lifecycle", values.get("lifecycle") or ""),
        ("review_status", values.get("review_status") or ""),
        ("ua_level", values.get("ua_level") or ""),
        ("acceptance", f"{values.get('ua_status')} / {values.get('acceptance_authority')}"),
        ("delivery", f"commit={values.get('commit_status')};merge={values.get('merge_status')};merge_authority={values.get('merge_authority')}"),
        ("task_path", source_file.resolve().relative_to(project_root.resolve()).as_posix()),
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
    return reader.Provenance(cell.field, reader._source_path(board_path), "TASK_BOARD", cell.line, cell.raw_value, cell.source_type)


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
        return [reader._diagnostic("W_BOARD_MISSING", project_root, 0, f"expected={dict(item.values)};actual=TASK_BOARD missing", related=item.provenance) for item in projections]
    parsed = task_board.parse_board(board_path, project_root)
    if parsed.error_message:
        return [reader._diagnostic("E_BOARD_PARSE", board_path, parsed.error_line, parsed.error_message)]
    diagnostics = []
    by_id = {}
    for row in parsed.rows:
        task_id = row.get("task_id")
        if task_id in by_id:
            cell = next(item for item in row.cells if item.field == "task_id")
            diagnostics.append(reader._diagnostic("E_TASK_ID_CONFLICT", board_path, row.line, f"TASK_BOARD task_id 重复：{task_id}", related=(_board_cell_provenance(cell, board_path),)))
        else:
            by_id[task_id] = row
    expected_by_id = {item.get("task_id"): item for item in projections}
    expected_by_path = {item.get("task_path"): item for item in projections}
    for row in parsed.rows:
        expected_for_path = expected_by_path.get(row.get("task_path"))
        if expected_for_path is not None and row.get("task_id") != expected_for_path.get("task_id"):
            cell = next(item for item in row.cells if item.field == "task_id")
            related = _projection_provenance(expected_for_path, "task_id") + (_board_cell_provenance(cell, board_path),)
            diagnostics.append(reader._diagnostic("E_TASK_ID_CONFLICT", board_path, row.line, f"board_task_id={row.get('task_id')};task_id={expected_for_path.get('task_id')};path={row.get('task_path')}", related=related))
    for task_id, expected in expected_by_id.items():
        actual = by_id.get(task_id)
        if actual is None:
            diagnostics.append(reader._diagnostic("W_BOARD_MISSING", board_path, 0, f"expected={dict(expected.values)};actual=row missing", related=expected.provenance))
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
                diagnostics.append(reader._diagnostic("V_BOARD_DRIFT", board_path, actual.line, message, related=related))
    for task_id, row in by_id.items():
        if task_id not in expected_by_id and task_id not in known_task_ids:
            cell = next(item for item in row.cells if item.field == "task_id")
            diagnostics.append(reader._diagnostic("W_BOARD_ORPHAN", board_path, row.line, f"expected=TASK missing;actual={dict(row.values)}", related=tuple(_board_cell_provenance(item, board_path) for item in row.cells)))
    if not parsed.canonical:
        diagnostics.append(reader._diagnostic("W_LEGACY_INFERRED", board_path, 1, "TASK_BOARD 使用 Legacy partial projection"))
    return diagnostics


def _transition_code(before, after, verifiable=True):
    if not verifiable or not before or not after:
        return "W_TRANSITION_UNVERIFIABLE"
    if before == after or (before, after) in TRANSITIONS:
        return None
    return "V_ILLEGAL_TRANSITION"


def _git_transition_diagnostic(contract, source_file):
    try:
        root_result = subprocess.run(["git", "-C", str(source_file.parent), "rev-parse", "--show-toplevel"], text=True, encoding="utf-8", capture_output=True, check=True)
        root = pathlib.Path(root_result.stdout.strip())
        relative = source_file.resolve().relative_to(root.resolve()).as_posix()
        status = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "--", relative], text=True, encoding="utf-8", capture_output=True, check=True).stdout
        if status.strip():
            raise ValueError("dirty or untracked")
        subprocess.run(["git", "-C", str(root), "ls-files", "--error-unmatch", "--", relative], text=True, encoding="utf-8", capture_output=True, check=True)
        commit = subprocess.run(["git", "-C", str(root), "log", "-n", "1", "--format=%H", "--", relative], text=True, encoding="utf-8", capture_output=True, check=True).stdout.strip()
        if not commit:
            raise ValueError("no path history")
        names = subprocess.run(["git", "-C", str(root), "show", "--format=", "--name-status", commit, "--", relative], text=True, encoding="utf-8", capture_output=True, check=True).stdout
        if any(line.startswith(("R", "C")) for line in names.splitlines()):
            raise ValueError("rename history")
        current = subprocess.run(["git", "-C", str(root), "show", f"{commit}:{relative}"], text=True, encoding="utf-8", capture_output=True, check=True).stdout
        previous = subprocess.run(["git", "-C", str(root), "show", f"{commit}^:{relative}"], text=True, encoding="utf-8", capture_output=True, check=True).stdout
        before_report = reader.inspect_text(previous, source_file, validate_filename=False)
        after_report = reader.inspect_text(current, source_file, validate_filename=False)
        if any(item.severity == "error" for item in before_report.diagnostics + after_report.diagnostics):
            raise ValueError("history parse conflict")
        before = before_report.get("lifecycle")
        historical_after = after_report.get("lifecycle")
        after = contract.get("lifecycle")
        if historical_after != after:
            raise ValueError("working tree differs from HEAD blob")
        code = _transition_code(before, after, True)
    except (OSError, ValueError, subprocess.SubprocessError):
        code = "W_TRANSITION_UNVERIFIABLE"
    if code == "V_ILLEGAL_TRANSITION":
        return _diag(contract, code, "lifecycle", "Git 历史证明 lifecycle 发生非法流转")
    if code == "W_TRANSITION_UNVERIFIABLE":
        return _diag(contract, code, "lifecycle", "Git 历史不足，无法证明 lifecycle 流转")
    return None


class WorkflowContract:
    @staticmethod
    def inspect(target):
        path = pathlib.Path(target)
        if path.is_file() and path.suffix.lower() == ".md":
            paths = (path,)
            validate_filename = True
            project_target = False
        elif path.is_dir() and ((path / "docs" / "tasks").is_dir() or (path / "docs" / "TASK_BOARD.md").is_file()):
            task_dir = path / "docs" / "tasks"
            paths = tuple(sorted(task_dir.glob("*.md"), key=lambda item: item.as_posix())) if task_dir.is_dir() else ()
            validate_filename = True
            project_target = True
        else:
            diagnostic = reader._diagnostic("E_PARSE", path, 0, "target 必须是单个 Markdown TASK 或含 docs/tasks 的项目根")
            return WorkflowReport((), (diagnostic,), "not_evaluated", _summary((diagnostic,)))
        contracts = tuple(reader.inspect_task(item, validate_filename=validate_filename) for item in paths)
        diagnostics = []
        projections = []
        seen_ids = {}
        for contract, source_file in zip(contracts, paths):
            diagnostics.extend(_validate(contract, require_commit=True, source_file=source_file))
            transition = _git_transition_diagnostic(contract, source_file)
            if transition is not None:
                diagnostics.append(transition)
            task_id = contract.get("task_id")
            if task_id and task_id in seen_ids:
                diagnostics.append(_diag(contract, "E_TASK_ID_CONFLICT", "task_id", "项目中 task_id 重复"))
            elif task_id:
                seen_ids[task_id] = contract.source_path
            if project_target:
                projection = _expected_board_projection(contract, source_file, path)
                if projection is not None:
                    projections.append(projection)
        if project_target:
            diagnostics.extend(_board_diagnostics(path, projections, tuple(seen_ids)))
        if path.is_dir() and (path / "docs" / "PROJECT_OVERLAY.md").exists():
            diagnostics.append(reader._diagnostic("W_PROJECT_OVERLAY_UNEVALUATED", path / "docs" / "PROJECT_OVERLAY.md", 1, "发现 Project Overlay，但 CONTRACT-007 前不求值"))
        diagnostics.sort(key=lambda item: (item.path, item.line, item.column, item.code, item.message))
        projection_state = tuple(sorted(projections, key=lambda item: item.get("task_id", ""))) if project_target else "not_evaluated: single_task_target"
        return WorkflowReport(tuple(sorted(contracts, key=lambda item: (item.get("task_id", ""), item.source_path))), tuple(diagnostics), projection_state, _summary(diagnostics))
