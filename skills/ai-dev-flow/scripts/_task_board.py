"""Deterministic, read-only TASK_BOARD projection parser."""

from dataclasses import dataclass
import pathlib
import re
from typing import Tuple


FIELDS = ("task_id", "title", "task_class", "lifecycle", "review_status", "ua_level", "acceptance", "delivery", "task_path")
CANONICAL_HEADERS = ("任务", "名称", "等级", "状态", "Review", "UA", "验收", "交付", "任务文件")
ALIASES = {
    "task_id": {"任务", "任务编号", "Task", "Task ID"},
    "title": {"名称", "任务名称", "标题"},
    "task_class": {"等级", "任务等级"},
    "lifecycle": {"状态", "任务状态"},
    "review_status": {"Review", "Review 状态", "审查状态"},
    "ua_level": {"UA", "UA 等级", "用户动作等级"},
    "acceptance": {"验收", "验收状态"},
    "delivery": {"交付", "Delivery"},
    "task_path": {"任务文件", "路径", "Task Path", "备注"},
    "ua_status_part": {"UA 状态"},
    "acceptance_authority_part": {"验收权限"},
    "commit_status_part": {"Commit 状态"},
    "merge_status_part": {"Merge 状态"},
    "merge_authority_part": {"Merge 授权"},
}
REQUIRED = {"task_id", "title", "task_class", "lifecycle", "task_path"}


@dataclass(frozen=True)
class BoardCell:
    field: str
    value: str
    line: int
    raw_value: str
    source_type: str


@dataclass(frozen=True)
class BoardRow:
    values: Tuple[Tuple[str, str], ...]
    cells: Tuple[BoardCell, ...]
    line: int
    projected_fields: Tuple[str, ...]

    def get(self, field, default=None):
        return dict(self.values).get(field, default)


@dataclass(frozen=True)
class BoardParse:
    rows: Tuple[BoardRow, ...]
    canonical: bool
    error_line: int = 0
    error_message: str = ""


def _cells(line):
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _separator(line, width):
    cells = _cells(line)
    return len(cells) == width and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def _semantic(header):
    matches = [field for field, aliases in ALIASES.items() if header in aliases]
    return matches[0] if len(matches) == 1 else None


REVIEW = {"未审查":"Pending", "待独立审查":"Pending", "审查中":"In Review", "通过":"Passed", "已通过":"Passed", "复审通过":"Passed", "需要修改":"Needs Fix", "不建议合并":"Do Not Merge"}
LIFECYCLE = {"草稿":"Draft", "可执行":"Ready", "执行中":"In Progress", "阻塞":"Blocked", "待审查":"Review", "需修复":"Needs Fix", "已验收":"Accepted", "已关闭":"Closed", "延期":"Deferred", "已取消":"Cancelled"}
UA_STATUS = {"未验收":"Pending", "待确认":"Pending", "待验收":"Pending", "通过":"Passed", "已通过":"Passed", "未通过":"Failed", "失败":"Failed", "暂缓":"Deferred", "延期":"Deferred"}
AUTHORITY = {"用户已确认":"User Confirmed", "指定验收人已确认":"Designated Acceptor Confirmed", "无":"None", "待确认":"None"}
COMMIT = {"未提交":"Uncommitted", "已提交":"Committed", "不适用":"Not Applicable"}
MERGE = {"未合并":"Unmerged", "已合并":"Merged", "暂不合并":"Deferred", "不适用":"Not Applicable"}
MERGE_AUTHORITY = {"用户已确认":"User Authorized", "用户已确认待合并":"User Authorized", "无":"None", "待确认":"None"}


def _mapped(value, mapping):
    return mapping.get(value, value)


def _ua_parts(value):
    match = re.match(r"^(UA[0-7]|TBD)(?:\s+(.+))?$", value)
    if not match:
        return value, None
    suffix = match.group(2)
    return match.group(1), UA_STATUS.get(suffix) if suffix else None


def _path_value(raw, board_path, project_root, header):
    value = raw.strip()
    if header == "备注":
        match = re.fullmatch(r"任务文件：\s*(.+)", value)
        if not match:
            return None
        value = match.group(1).strip()
    link = re.fullmatch(r"\[[^\]]+\]\(([^)]+)\)", value)
    if link:
        value = link.group(1).strip()
    path = pathlib.PurePosixPath(value.replace("\\", "/"))
    if str(path).startswith("docs/"):
        return str(path)
    try:
        absolute = (board_path.parent / pathlib.Path(value)).resolve()
        return absolute.relative_to(project_root.resolve()).as_posix()
    except (OSError, ValueError):
        return None


def parse_board(board_path, project_root):
    try:
        lines = pathlib.Path(board_path).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        return BoardParse((), False, 1, f"无法读取 TASK_BOARD：{exc}")
    candidates = []
    for index in range(len(lines) - 2):
        if not lines[index].lstrip().startswith("|"):
            continue
        headers = _cells(lines[index])
        if not _separator(lines[index + 1], len(headers)):
            continue
        canonical = tuple(headers) == CANONICAL_HEADERS
        semantics = list(FIELDS) if canonical else [_semantic(header) for header in headers]
        if not canonical and not REQUIRED.issubset(set(semantics)):
            continue
        represented = [field for field in semantics if field is not None]
        if len(set(represented)) != len(represented):
            return BoardParse((), canonical, index + 1, "TASK_BOARD 同一语义表头重复")
        data = []
        cursor = index + 2
        while cursor < len(lines) and lines[cursor].lstrip().startswith("|"):
            values = _cells(lines[cursor])
            if len(values) != len(headers):
                return BoardParse((), canonical, cursor + 1, "TASK_BOARD 行列数不一致")
            data.append((cursor + 1, values))
            cursor += 1
        if data:
            candidates.append((headers, semantics, canonical, data))
    if len(candidates) != 1:
        return BoardParse((), False, 1, "TASK_BOARD 必须有唯一可识别且含数据行的任务表")
    headers, semantics, canonical, data = candidates[0]
    rows = []
    for line, raw_values in data:
        pairs = []
        cells = []
        parts = {}
        for header, field, raw in zip(headers, semantics, raw_values):
            if field is None:
                continue
            value = raw.strip()
            if field == "task_path":
                value = _path_value(value, pathlib.Path(board_path), pathlib.Path(project_root), header)
                if value is None:
                    return BoardParse((), canonical, line, "TASK_BOARD 任务文件路径无法解析")
            if not canonical:
                if field == "review_status":
                    value = _mapped(re.split(r" / |；", value, maxsplit=1)[0], REVIEW)
                elif field == "lifecycle":
                    value = _mapped(value, LIFECYCLE)
                elif field == "task_class":
                    match = re.search(r"\b([ABCD])\b", value)
                    value = match.group(1) if match else value
                elif field == "ua_level":
                    value, inferred = _ua_parts(value)
                    if inferred:
                        parts["ua_status_part"] = inferred
                elif field == "acceptance":
                    level, inferred = _ua_parts(value)
                    if inferred:
                        parts["ua_status_part"] = inferred
                        value = inferred
                    else:
                        value = _mapped(value, UA_STATUS)
                    parts["acceptance"] = value
                elif field.endswith("_part"):
                    mapping = {"ua_status_part":UA_STATUS, "acceptance_authority_part":AUTHORITY, "commit_status_part":COMMIT, "merge_status_part":MERGE, "merge_authority_part":MERGE_AUTHORITY}[field]
                    parts[field] = _mapped(value, mapping)
                    continue
            pairs.append((field, value))
            cells.append(BoardCell(field, value, line, raw, "canonical" if canonical else "legacy"))
        if not canonical:
            pair_map = dict(pairs)
            if "acceptance" in pair_map or "ua_status_part" in parts:
                status = parts.get("ua_status_part", pair_map.get("acceptance", "not_projected"))
                authority = parts.get("acceptance_authority_part", "not_projected")
                combined = f"{status} / {authority}"
                direct = pair_map.get("acceptance")
                if direct and "ua_status_part" in parts and direct.split(" / ")[0] != status:
                    combined = f"CONFLICT:{direct}|{combined}"
                pairs = [(key, value) for key, value in pairs if key != "acceptance"] + [("acceptance", combined)]
                cells.append(BoardCell("acceptance", combined, line, combined, "legacy"))
            if any(key in parts for key in ("commit_status_part", "merge_status_part", "merge_authority_part")):
                delivery = f"commit={parts.get('commit_status_part', 'not_projected')};merge={parts.get('merge_status_part', 'not_projected')};merge_authority={parts.get('merge_authority_part', 'not_projected')}"
                direct = pair_map.get("delivery")
                if direct:
                    direct_parts = dict(item.split("=", 1) for item in direct.split(";") if "=" in item)
                    split_parts = dict(item.split("=", 1) for item in delivery.split(";"))
                    if any(value != "not_projected" and direct_parts.get(key) != value for key, value in split_parts.items()):
                        delivery = f"CONFLICT:{direct}|{delivery}"
                pairs = [(key, value) for key, value in pairs if key != "delivery"] + [("delivery", delivery)]
                cells.append(BoardCell("delivery", delivery, line, delivery, "legacy"))
        projected = tuple(field for field, _ in pairs)
        rows.append(BoardRow(tuple(pairs), tuple(cells), line, projected))
    return BoardParse(tuple(rows), canonical)
