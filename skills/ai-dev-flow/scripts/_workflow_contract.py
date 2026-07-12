"""Deterministic, read-only readers for v0.7 and legacy TASK Markdown."""

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict, Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class Provenance:
    field: str
    path: str
    heading: str
    line: int
    raw_value: str
    source_type: str


@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: str
    path: str
    line: int
    column: int
    message: str
    suggestion: str
    provenance: Tuple[Provenance, ...]


@dataclass(frozen=True)
class SectionField:
    name: str
    value: str
    line: int
    kind: str


@dataclass(frozen=True)
class Section:
    heading: str
    line: int
    fields: Tuple[SectionField, ...]


@dataclass(frozen=True)
class ReaderReport:
    title: Optional[str]
    source_path: str
    normalized: Tuple[Tuple[str, Optional[str]], ...]
    provenance: Tuple[Provenance, ...]
    sections: Tuple[Section, ...]
    diagnostics: Tuple[Diagnostic, ...]

    def get(self, key: str, default=None):
        return dict(self.normalized).get(key, default)


CORE_FIELDS = (
    "schema_version", "task_id", "task_type", "task_class", "lifecycle",
    "review_status", "ua_level", "ua_status",
)
CONDITIONAL_FIELDS = (
    "ua_evidence", "acceptance_authority", "close_authority", "commit_status",
    "merge_status", "merge_authority", "overlays", "extensions_optional",
    "extensions_required",
)
KNOWN_FIELDS = frozenset(CORE_FIELDS + CONDITIONAL_FIELDS)
ENUMS = {
    "schema_version": frozenset(("adf/v0.7.0",)),
    "task_type": frozenset(("document", "plan", "code", "review", "repair", "test")),
    "task_class": frozenset(("A", "B", "C", "D")),
    "lifecycle": frozenset(("Draft", "Ready", "In Progress", "Blocked", "Review", "Needs Fix", "Accepted", "Closed", "Deferred", "Cancelled")),
    "review_status": frozenset(("Pending", "In Review", "Passed", "Needs Fix", "Do Not Merge")),
    "ua_level": frozenset(("UA0", "UA1", "UA2", "UA3", "UA4", "UA5", "UA6", "UA7", "TBD")),
    "ua_status": frozenset(("Not Required", "Pending", "Passed", "Failed", "Deferred", "TBD")),
    "acceptance_authority": frozenset(("None", "User Confirmed", "Designated Acceptor Confirmed")),
    "close_authority": frozenset(("None", "User Authorized", "Rule Authorized", "Denied")),
    "commit_status": frozenset(("Not Applicable", "Uncommitted", "Committed")),
    "merge_status": frozenset(("Not Applicable", "Unmerged", "Merged", "Deferred")),
    "merge_authority": frozenset(("None", "User Authorized", "Denied")),
}
DEFAULT_FIELDS = (
    ("acceptance_authority", "None"), ("close_authority", "None"),
    ("commit_status", "Not Recorded"), ("merge_status", "Not Recorded"),
    ("merge_authority", "None"), ("overlays", "none"),
    ("extensions_optional", "none"), ("extensions_required", "none"),
)
FIELD_RE = re.compile(r"^- `([a-z][a-z0-9_]*)`: `([^`\r\n]+)`$")
H1_ID_RE = re.compile(r"^# ([A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*)[：:]\s*")

LIFECYCLE = dict(zip(
    "草稿 可执行 执行中 阻塞 待审查 需修复 已验收 已关闭 延期 已取消".split(),
    "Draft|Ready|In Progress|Blocked|Review|Needs Fix|Accepted|Closed|Deferred|Cancelled".split("|"),
))
REVIEW = {"未审查":"Pending", "待独立审查":"Pending", "审查中":"In Review", "通过":"Passed", "已通过":"Passed", "复审通过":"Passed", "需要修改":"Needs Fix", "不建议合并":"Do Not Merge"}
UA_STATUS = {"无反馈":"Pending", "待复测":"Pending", "通过":"Passed", "UA7 已确认通过":"Passed", "失败":"Failed", "UA7 已确认失败":"Failed", "延期":"Deferred", "UA7 已确认延期":"Deferred", "暂缓":"Deferred", "待确认":"TBD", "不适用":"Not Required"}
TASK_TYPE = {"文档":"document", "协议文档":"document", "模板":"document", "工作流核心改动":"document", "方案":"plan", "代码":"code", "审查":"review", "修复":"repair", "测试":"test", "测试数据":"test", "单元测试":"test"}
TASK_TYPE_COMPOSITE = {"方案 / 协议文档 / Schema":"plan", "测试数据 / 文档":"test", "代码 / 单元测试":"code", "代码 / CLI / 单元测试":"code", "工作流核心改动 / 模板 / Prompt":"document", "代码 / 投影 Adapter / 模板":"code", "文档 / 发布治理":"document"}
COMMIT = {"未提交":"Uncommitted", "已提交":"Committed", "已提交执行结果":"Committed", "不适用":"Not Applicable"}
MERGE = {"未合并":"Unmerged", "用户已确认待合并":"Unmerged", "已合并":"Merged", "暂不合并":"Deferred", "不适用":"Not Applicable"}
ACCEPTANCE = {"用户已确认":"User Confirmed", "UA7 已确认通过":"User Confirmed", "UA7 已确认失败":"User Confirmed", "UA7 已确认延期":"User Confirmed", "指定验收人已确认":"Designated Acceptor Confirmed", "无":"None", "待确认":"None"}
CLOSE = {"是（用户已确认）":"User Authorized", "是（项目规则已授权）":"Rule Authorized", "否":"Denied", "否 / 待用户确认":"None", "建议关闭":"None", "待确认":"None"}
MERGE_AUTHORITY = {"用户已确认待合并":"User Authorized", "User Authorized":"User Authorized", "否":"Denied", "待确认":"None"}


def _source_path(path: Path) -> str:
    resolved = path.resolve()
    parts = resolved.parts
    for index in range(len(parts) - 1):
        if parts[index:index + 2] == ("docs", "tasks") and index > 0:
            return resolved.relative_to(Path(*parts[:index])).as_posix()
    return resolved.name


def _diagnostic(code: str, path: Path, line: int, message: str, suggestion: str = "", related: Tuple[Provenance, ...] = ()) -> Diagnostic:
    severity = "error" if code.startswith("E_") else ("violation" if code.startswith("V_") else "warning")
    if not suggestion:
        suggestion = {
            "E_PARSE": "请使用精确 Markdown grammar，并删除重复或未知结构。",
            "E_UNKNOWN_VALUE": "请改为规范枚举或显式 Legacy 别名中的值。",
            "E_TASK_ID_CONFLICT": "请统一文件名、H1 与 Contract/TASK task_id。",
            "E_LEGACY_CONFLICT": "请统一该 Legacy 语义轴的所有来源值。",
            "W_LEGACY_INFERRED": "无需迁移；请确认显式 Legacy 映射符合预期。",
        }.get(code, "请按 Workflow Contract 规范修正该输入。")
    return Diagnostic(code, severity, _source_path(path), line, 1 if line else 0, message, suggestion, related)


def _title(lines: List[str], task_id: Optional[str], path: Path, diagnostics: List[Diagnostic]) -> Optional[str]:
    headings = [(index + 1, line[2:].strip()) for index, line in enumerate(lines) if line.startswith("# ") and not line.startswith("## ")]
    if len(headings) != 1 or not headings[0][1]:
        diagnostics.append(_diagnostic("E_PARSE", path, headings[0][0] if headings else 1, "TASK 必须有唯一非空 H1"))
        return None
    value = headings[0][1]
    if task_id:
        value = re.sub(rf"^{re.escape(task_id)}(?:：|: )\s*", "", value).strip()
    return value or None


def _sections(lines: List[str], canonical: bool) -> Tuple[Section, ...]:
    result: List[Section] = []
    legacy_heading_field = {"目标":"目标", "非目标":"非目标", "允许修改范围":"允许修改", "禁止修改范围":"禁止修改", "完成标准":"完成标准"}
    legacy_field_map = {"Base commit":"Base / Diff", "执行 Base commit":"Base / Diff", "Diff 范围":"Base / Diff", "当前分支":"隔离位置", "Worktree":"隔离位置", "回滚方式":"回滚方式", "修改文件清单":"修改文件", "实际验证结果":"验证证据", "审查结论":"Review findings", "合并目标":"合并目标与事实证据"}
    canonical_allowed = {
        "目标与边界": {"目标", "非目标", "允许修改", "禁止修改"},
        "完成标准与验证": {"完成标准", "验证命令或检查"},
        "Outcome": {"Base / Diff", "隔离位置", "回滚方式", "修改文件", "验证证据", "Review findings", "UA 动作与结果", "合并目标与事实证据"},
    }
    for index, line in enumerate(lines):
        if not line.startswith("## "):
            continue
        end = next((i for i in range(index + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
        fields: List[SectionField] = []
        in_fence = False
        fence_start = 0
        fence_lines: List[str] = []
        table_seen = False
        for field_index in range(index + 1, end):
            raw = lines[field_index]
            if not canonical and line[3:].strip() in ("验证方式", "自动验证命令"):
                if raw.startswith("```"):
                    if in_fence:
                        value = "\n".join(fence_lines).strip()
                        if value:
                            fields.append(SectionField("验证命令或检查", value, fence_start, "code_fence"))
                        in_fence = False
                        fence_lines = []
                    else:
                        in_fence = True
                        fence_start = field_index + 1
                    continue
                if in_fence:
                    fence_lines.append(raw)
                    continue
            if canonical:
                match = re.fullmatch(r"^- ([^：]+)：(.*)$", raw)
                if match and match.group(1).strip() in canonical_allowed.get(line[3:].strip(), set()):
                    fields.append(SectionField(match.group(1).strip(), match.group(2).strip(), field_index + 1, "field"))
                continue
            if line[3:].strip() in legacy_heading_field and raw.startswith("- "):
                checkbox = bool(re.match(r"^- \[[ xX]\]", raw))
                value = re.sub(r"^- \[[ xX]\]\s*", "", raw)
                value = value[2:] if value.startswith("- ") else value
                fields.append(SectionField(legacy_heading_field[line[3:].strip()], value.strip(), field_index + 1, "checkbox" if checkbox else "list"))
                continue
            if line[3:].strip() in ("验证方式", "自动验证命令") and raw.startswith("- "):
                fields.append(SectionField("验证命令或检查", raw[2:].strip(), field_index + 1, "list"))
                continue
            if line[3:].strip() in ("验证结果", "执行与验证记录") and raw.startswith("- "):
                fields.append(SectionField("验证证据", raw[2:].strip(), field_index + 1, "list"))
                continue
            if line[3:].strip() == "修改文件" and raw.startswith("|"):
                if not table_seen:
                    table_seen = True
                    continue
                if re.match(r"^\|[-:| ]+\|$", raw):
                    continue
                fields.append(SectionField("修改文件", raw.strip(), field_index + 1, "table_row"))
                continue
            match = re.match(r"^- ([^：:]+)(?:：|: )(.*)$", raw)
            if match:
                name = legacy_field_map.get(match.group(1).strip(), match.group(1).strip())
                fields.append(SectionField(name, match.group(2).strip(), field_index + 1, "field"))
        result.append(Section(line[3:].strip(), index + 1, tuple(fields)))
    return tuple(result)


def _finish(values: Dict[str, Optional[str]], provenance: List[Provenance], diagnostics: List[Diagnostic], path: Path, lines: List[str], validate_filename: bool) -> ReaderReport:
    task_id = values.get("task_id")
    if task_id and validate_filename:
        stem = path.stem
        if stem == task_id or stem.startswith(task_id + "-"):
            provenance.append(Provenance("task_id", _source_path(path), "", 0, stem, "filename"))
        else:
            diagnostics.append(_diagnostic("E_TASK_ID_CONFLICT", path, 0, "文件名与 task_id 不一致"))
    title = _title(lines, values.get("task_id"), path, diagnostics)
    has_error = any(item.code.startswith("E_") for item in diagnostics)
    if not has_error:
        for field, value in DEFAULT_FIELDS:
            if field not in values:
                values[field] = value
                provenance.append(Provenance(field, _source_path(path), "Workflow Contract", 0, value, "default"))
    order = CORE_FIELDS + CONDITIONAL_FIELDS
    normalized = tuple((key, values[key]) for key in order if key in values and values[key] is not None)
    provenance.sort(key=lambda item: (item.path, item.line, item.field, item.source_type))
    diagnostics.sort(key=lambda item: (item.path, item.line, item.column, item.code, item.message))
    diagnostics[:] = _dedupe_diagnostics(diagnostics)
    diagnostics.sort(key=lambda item: (item.path, item.line, item.column, item.code, item.message))
    return ReaderReport(title, _source_path(path), normalized, tuple(provenance), _sections(lines, values.get("schema_version") is not None), tuple(diagnostics))


def _canonical(path: Path, lines: List[str], validate_filename: bool) -> ReaderReport:
    values: Dict[str, Optional[str]] = {}
    provenance: List[Provenance] = []
    diagnostics: List[Diagnostic] = []
    headings = [i for i, line in enumerate(lines) if line == "## Workflow Contract"]
    if len(headings) != 1:
        diagnostics.append(_diagnostic("E_PARSE", path, (headings[0] + 1) if headings else 1, "Workflow Contract 区块必须唯一"))
        return _finish(values, provenance, diagnostics, path, lines, validate_filename)
    start = headings[0] + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("#")), len(lines))
    for index in range(start, end):
        raw = lines[index]
        if not raw.strip():
            continue
        match = FIELD_RE.fullmatch(raw)
        if not match:
            diagnostics.append(_diagnostic("E_PARSE", path, index + 1, "Contract 字段不符合受限语法"))
            continue
        key, value = match.groups()
        if key not in KNOWN_FIELDS or key in values:
            diagnostics.append(_diagnostic("E_PARSE", path, index + 1, "未知或重复 Contract key"))
            continue
        values[key] = value
        provenance.append(Provenance(key, _source_path(path), "Workflow Contract", index + 1, value, "canonical"))
    for key in CORE_FIELDS:
        if key not in values:
            diagnostics.append(_diagnostic("E_PARSE", path, headings[0] + 1, f"缺少核心字段 {key}"))
    for key, allowed in ENUMS.items():
        if key in values and values[key] not in allowed:
            related = tuple(p for p in provenance if p.field == key)
            diagnostics.append(_diagnostic("E_UNKNOWN_VALUE", path, related[0].line, f"{key} 值不在枚举中", related=related))
    task_id = values.get("task_id")
    if task_id and not re.fullmatch(r"[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*", task_id):
        diagnostics.append(_diagnostic("E_UNKNOWN_VALUE", path, next(p.line for p in provenance if p.field == "task_id"), "task_id 形状非法"))
    optional = set(values.get("extensions_optional", "none").split(";")) - {"none"}
    required = set(values.get("extensions_required", "none").split(";")) - {"none"}
    if optional & required:
        diagnostics.append(_diagnostic("E_PARSE", path, headings[0] + 1, "optional/required extension 必须互斥"))
    for key in ("overlays", "extensions_optional", "extensions_required", "ua_evidence"):
        if key not in values:
            continue
        tokens = values[key].split(";")
        if len(tokens) != len(set(tokens)) or ("none" in tokens and len(tokens) > 1) or any(not token or token != token.strip() for token in tokens):
            line = next(p.line for p in provenance if p.field == key)
            diagnostics.append(_diagnostic("E_UNKNOWN_VALUE", path, line, f"{key} 多值形状非法"))
    h1 = next((H1_ID_RE.match(line) for line in lines if line.startswith("# ")), None)
    if h1 and values.get("task_id") and h1.group(1) != values["task_id"]:
        values["task_id"] = None
        diagnostics.append(_diagnostic("E_TASK_ID_CONFLICT", path, 1, "H1 与 Contract task_id 冲突"))
    diagnostics = _dedupe_diagnostics(diagnostics)
    return _finish(values, provenance, diagnostics, path, lines, validate_filename)


def _trim_value(raw: str) -> str:
    value = raw.strip()
    if value.startswith("`") and value.endswith("`") and len(value) >= 2:
        value = value[1:-1]
    return value.strip()


def _mapped_alias(value: str, mapping: Dict[str, str]) -> str:
    if value in mapping:
        return mapping[value]
    for separator in ("（", ":", "：", "；"):
        if separator in value:
            prefix, suffix = value.split(separator, 1)
            if prefix.strip() in mapping and suffix.strip():
                return mapping[prefix.strip()]
    return "__UNKNOWN__"


def _legacy_value(field: str, raw: str) -> Optional[str]:
    value = _trim_value(raw)
    if field == "task_id":
        return value
    if field == "task_type":
        if value in TASK_TYPE_COMPOSITE:
            return TASK_TYPE_COMPOSITE[value]
        tokens = [token.strip() for token in value.split("/")]
        primary = tokens[0].split("：", 1)[0].split(":", 1)[0].strip()
        primary_value = TASK_TYPE.get(primary)
        if primary_value is None:
            return "__UNKNOWN__"
        for token in tokens[1:]:
            candidate = TASK_TYPE.get(token.split("：", 1)[0].split(":", 1)[0].strip())
            if candidate is not None and candidate != primary_value:
                return "__CONFLICT__"
        return primary_value
    if field == "task_class":
        match = re.match(r"^([ABCD])(?:$|[ ：:])", value)
        return match.group(1) if match else "__UNKNOWN__"
    if field == "lifecycle":
        chinese = value.split("（", 1)[0].strip()
        normalized = LIFECYCLE.get(chinese)
        if normalized is None:
            return "__UNKNOWN__"
        if "（" in value:
            match = re.fullmatch(r"[^（]+（`?([^`）]+)`?）", value)
            if not match:
                return "__UNKNOWN__"
            if match.group(1) != normalized:
                return "__CONFLICT__"
        return normalized
    if field == "review_status":
        return _mapped_alias(value, REVIEW)
    if field == "ua_level":
        match = re.match(r"^(UA[0-7])(?:$|[ ：:])", value)
        return match.group(1) if match else ("TBD" if value == "待确认" else "__UNKNOWN__")
    if field == "ua_status":
        return _mapped_alias(value, UA_STATUS)
    if field == "commit_status":
        return _mapped_alias(value, COMMIT)
    if field == "merge_status":
        return _mapped_alias(value, MERGE)
    if field == "acceptance_authority":
        return _mapped_alias(value, ACCEPTANCE)
    if field == "close_authority":
        return _mapped_alias(value, CLOSE)
    if field == "merge_authority":
        return _mapped_alias(value, MERGE_AUTHORITY)
    if field == "ua_evidence":
        return value
    return None


def _legacy(path: Path, lines: List[str], validate_filename: bool) -> ReaderReport:
    sources: Dict[str, List[Tuple[str, int, str, str]]] = {}
    provenance: List[Provenance] = []
    diagnostics: List[Diagnostic] = []
    heading = ""
    h1_item = next(((index + 1, H1_ID_RE.match(line)) for index, line in enumerate(lines) if line.startswith("# ") and H1_ID_RE.match(line)), None)
    if h1_item:
        sources.setdefault("task_id", []).append((h1_item[1].group(1), h1_item[0], "H1", "heading"))
    metadata_alias = {"任务编号":"task_id", "任务类型":"task_type", "任务分级":"task_class", "任务状态":"lifecycle", "用户动作等级":"ua_level"}
    scalar_alias = {"任务编号":"task_id", "任务类型":"task_type", "任务分级":"task_class", "任务状态":"lifecycle"}
    pending_scalar: Optional[Tuple[str, str]] = None
    for index, line in enumerate(lines, 1):
        if line.startswith("## "):
            heading = line[3:].strip()
            pending_scalar = (scalar_alias[heading], heading) if heading in scalar_alias else None
            continue
        if pending_scalar and line.strip() and not line.startswith("|"):
            scalar = line.strip()
            if scalar.startswith("- "):
                scalar = scalar[2:].strip()
            sources.setdefault(pending_scalar[0], []).append((scalar, index, pending_scalar[1], "legacy"))
            pending_scalar = None
        if heading == "任务元数据" and line.startswith("|"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) >= 2 and cells[0] in metadata_alias:
                sources.setdefault(metadata_alias[cells[0]], []).append((cells[1], index, heading, "legacy"))
        field = None
        if heading in ("代码审查", "Diff 审查") and line.startswith("- 审查状态："):
            if _trim_value(line.split("：", 1)[1]) != "不适用":
                field = "review_status"
        elif heading == "用户验收反馈 / 实机测试反馈" and line.startswith("- 验收反馈状态："):
            field = "ua_status"
        elif heading == "提交 / 合并" and line.startswith("- Commit 状态："):
            field = "commit_status"
        elif heading in ("合并状态", "提交 / 合并") and (line.startswith("- 合并状态：") or line.startswith("- Merge 状态：")):
            field = "merge_status"
        elif heading == "用户动作等级 / 验收建议" and line.startswith("- 验收确认："):
            field = "acceptance_authority"
        elif heading == "用户动作等级 / 验收建议" and line.startswith("- 用户动作等级："):
            field = "ua_level"
        elif heading == "用户动作等级 / 验收建议" and line.startswith("- 是否允许关闭任务："):
            field = "close_authority"
        elif heading in ("合并状态", "提交 / 合并") and line.startswith("- 合并授权："):
            field = "merge_authority"
        elif heading == "用户动作等级 / 验收建议" and line.startswith("- agent 已提供的证据："):
            raw_evidence = line.split("：", 1)[1].strip()
            if raw_evidence not in ("待执行后填写", "无"):
                sources.setdefault("ua_evidence", []).append((raw_evidence, index, heading, "legacy"))
        elif heading == "用户验收反馈 / 实机测试反馈" and (line.startswith("- 实际结果：") or line.startswith("- 日志 / 截图 / 视频：")):
            raw_evidence = line.split("：", 1)[1].strip()
            if raw_evidence not in ("待执行后填写", "无"):
                sources.setdefault("ua_evidence", []).append((raw_evidence, index, heading, "legacy"))
        if field:
            raw_field_value = line.split("：", 1)[1]
            sources.setdefault(field, []).append((raw_field_value, index, heading, "legacy"))
            if field == "merge_status" and _trim_value(raw_field_value) == "用户已确认待合并":
                sources.setdefault("merge_authority", []).append((raw_field_value, index, heading, "legacy"))
            status_value = _trim_value(raw_field_value)
            if field == "ua_status" and status_value in ("UA7 已确认通过", "UA7 已确认失败", "UA7 已确认延期"):
                sources.setdefault("acceptance_authority", []).append((raw_field_value, index, heading, "legacy"))
    values: Dict[str, Optional[str]] = {}
    conflict = False
    for field, items in sources.items():
        mapped: List[str] = []
        for raw, line, source_heading, source_type in items:
            if field == "ua_evidence":
                value = "#用户动作等级--验收建议" if source_heading == "用户动作等级 / 验收建议" else "#用户验收反馈--实机测试反馈"
            else:
                value = _legacy_value(field, raw)
            if value == "__CONFLICT__":
                conflict = True
                item_provenance = Provenance(field, _source_path(path), source_heading, line, _trim_value(raw), source_type)
                provenance.append(item_provenance)
                diagnostics.append(_diagnostic("E_LEGACY_CONFLICT", path, line, f"Legacy {field} 内部值冲突", related=(item_provenance,)))
                continue
            if value == "__UNKNOWN__":
                diagnostics.append(_diagnostic("E_UNKNOWN_VALUE", path, line, f"Legacy {field} 值不在显式别名表"))
                provenance.append(Provenance(field, _source_path(path), source_heading, line, _trim_value(raw), source_type))
                continue
            if value is not None:
                mapped.append(value)
                provenance.append(Provenance(field, _source_path(path), source_heading, line, _trim_value(raw), source_type))
        distinct = tuple(dict.fromkeys(mapped))
        if field == "ua_evidence" and distinct:
            values[field] = ";".join(distinct)
            continue
        if len(distinct) > 1:
            values[field] = None
            conflict = True
            related = tuple(item for item in provenance if item.field == field)
            diagnostics.append(_diagnostic("E_LEGACY_CONFLICT", path, items[0][1], f"Legacy {field} 来源冲突", related=related))
        elif distinct:
            values[field] = distinct[0]
    if not conflict and values:
        first_line = min((p.line for p in provenance), default=1)
        diagnostics.append(_diagnostic("W_LEGACY_INFERRED", path, first_line, "值来自显式 Legacy 映射"))
    return _finish(values, provenance, _dedupe_diagnostics(diagnostics), path, lines, validate_filename)


def _dedupe_diagnostics(items: Iterable[Diagnostic]) -> List[Diagnostic]:
    result: List[Diagnostic] = []
    seen = set()
    for item in items:
        key = (item.code, item.path, item.line, item.column, item.message)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def inspect_task(path: Path, *, validate_filename: bool = True) -> ReaderReport:
    """Read one TASK without writing it or consulting external state."""
    target = Path(path)
    try:
        text = target.read_text(encoding="utf-8-sig")
    except (UnicodeDecodeError, OSError) as exc:
        return ReaderReport(None, _source_path(target), (), (), (), (_diagnostic("E_PARSE", target, 1, f"UTF-8 读取失败：{exc.__class__.__name__}"),))
    lines = text.splitlines()
    declarations = [index for index, line in enumerate(lines) if FIELD_RE.fullmatch(line) and FIELD_RE.fullmatch(line).group(1) == "schema_version"]
    if not declarations:
        return _legacy(target, lines, validate_filename)
    report = _canonical(target, lines, validate_filename)
    headings = [index for index, line in enumerate(lines) if line == "## Workflow Contract"]
    block_contains = False
    if len(headings) == 1:
        end = next((i for i in range(headings[0] + 1, len(lines)) if lines[i].startswith("#")), len(lines))
        block_contains = len(declarations) == 1 and headings[0] < declarations[0] < end
    if len(declarations) != 1 or not block_contains:
        extra = _diagnostic("E_PARSE", target, declarations[0] + 1, "schema declaration 必须唯一且位于唯一 Contract block 内")
        diagnostics = _dedupe_diagnostics(report.diagnostics + (extra,))
        diagnostics.sort(key=lambda item: (item.path, item.line, item.column, item.code, item.message))
        provenance = tuple(item for item in report.provenance if item.source_type != "default")
        explicit = {item.field for item in provenance}
        normalized = tuple((key, value) for key, value in report.normalized if key in explicit)
        return ReaderReport(report.title, report.source_path, normalized, provenance, report.sections, tuple(diagnostics))
    return report
