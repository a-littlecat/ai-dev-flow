"""TASK_BOARD 看板生成器（独立命令，workflow_lint 不接线、行为不变）。

三种互斥模式：
- ``--check``（默认）：纯只读校验。生成区内容与 TASK 投影 drift 为 0，
  否则报 BOARD_DRIFT（error）；人工区引用指向已 Closed/Cancelled 任务报
  BOARD_MANUAL_STALE_REF（warning），指向不存在任务报
  BOARD_MANUAL_UNKNOWN_REF（warning）。全程不写任何文件。
- ``--write``：只重写 docs/TASK_BOARD.md 生成区（ADF-GENERATED 标记之间），
  生成内容 byte-stable（重复写零 diff），生成区外人工内容 byte-preserve。
- ``--migrate-authority-log``：把 docs/TASK_BOARD.md 的 ``## 当前授权边界``
  H2 节（该 H2 起至下一 H2 止）整节机械归档到 docs/AUTHORITY_LOG.md。
  按空行分隔的连续文本块切分条目，条目 ID 为 AUTH-YYYYMMDD-NNN（按原文顺序），
  对账键 = 条目 ID + 原段落 UTF-8 内容 SHA256；不做任何"当前有效/历史"语义
  判定，整节一律视为历史。对账失败报 ARCHIVE_MIGRATION_MISMATCH（error）
  且不写任何文件；写盘先写临时文件再原子替换。重复执行幂等。

生成器只生成任务状态表，不做依赖链或"下一允许动作"推导，不自动改写人工区。
仅使用 Python 标准库。
"""

import sys

sys.dont_write_bytecode = True

import argparse
from dataclasses import asdict
import datetime
import hashlib
import json
import os
import pathlib
import re
import tempfile

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import _workflow_contract as reader
from _task_board import CANONICAL_HEADERS
from workflow_contract import _expected_board_projection


BOARD_RELATIVE = "docs/TASK_BOARD.md"
AUTHORITY_LOG_RELATIVE = "docs/AUTHORITY_LOG.md"
GENERATED_BEGIN = "<!-- ADF-GENERATED:BEGIN -->"
GENERATED_END = "<!-- ADF-GENERATED:END -->"
PROJECTION_FIELDS = (
    "task_id", "title", "task_class", "lifecycle", "review_status",
    "ua_level", "acceptance", "delivery", "task_path",
)
AUTHORITY_HEADING = "当前授权边界"
TERMINAL_LIFECYCLES = {"Closed", "Cancelled"}

ENTRY_HEADING_RE = re.compile(r"^## (AUTH-(\d{8})-(\d{3}))\s*$")
ENTRY_ID_RE = re.compile(r"^AUTH-\d{8}-\d{3}$")
ENTRY_SHA_RE = re.compile(r"^- sha256: ([0-9a-f]{64})\s*$")
DATE_RE = re.compile(r"^\d{8}$")
TASK_ID_RE = re.compile(r"(?<![A-Za-z0-9-])([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-\d{3})(?![A-Za-z0-9-])")
LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)\s]+)\)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$")
TASK_LINK_RE = re.compile(r"(?:^|/)tasks/[^/]+\.md$")
H2_RE = re.compile(r"^##\s")

LOG_HEADER = (
    "# 授权流水归档\n"
    "\n"
    "> 本文件由 `skills/ai-dev-flow/scripts/board_generator.py --migrate-authority-log` "
    "生成并维护；条目为 `docs/TASK_BOARD.md` `## 当前授权边界` 节的历史原文，"
    "逐字未改写；对账键 = 条目 ID + 原段落 UTF-8 内容 SHA256。\n"
)

SEVERITIES = {
    "BOARD_DRIFT": "error",
    "BOARD_MANUAL_STALE_REF": "warning",
    "BOARD_MANUAL_UNKNOWN_REF": "warning",
    "ARCHIVE_MIGRATION_MISMATCH": "error",
}
SUGGESTIONS = {
    "BOARD_DRIFT": "请运行 `board_generator.py <项目根> --write` 重新生成生成区；不要手改生成区。",
    "BOARD_MANUAL_STALE_REF": "人工区引用的任务已 Closed/Cancelled；请人工更新或删除该引用（生成器不改写人工区）。",
    "BOARD_MANUAL_UNKNOWN_REF": "人工区引用的任务不存在；请人工修正任务 ID 或链接（生成器不改写人工区）。",
    "ARCHIVE_MIGRATION_MISMATCH": "授权归档对账失败；未写入任何文件。请检查 docs/AUTHORITY_LOG.md 条目 ID 唯一性与原文一致性后重试。",
}


def _diagnostic(code, line, message, provenance=(), path=BOARD_RELATIVE, column=None):
    if column is None:
        column = 1 if line else 0
    return reader.Diagnostic(
        code,
        SEVERITIES[code],
        path,
        line,
        column,
        message,
        SUGGESTIONS[code],
        tuple(provenance),
    )


def _load_tasks(project_root):
    """读取 docs/tasks/*.md，返回 (paths, contracts)，路径均已解析。"""
    task_dir = project_root / "docs" / "tasks"
    paths = []
    if task_dir.is_dir():
        paths = sorted(
            (item for item in task_dir.glob("*.md") if item.is_file()),
            key=lambda item: item.as_posix(),
        )
    contracts = [reader.inspect_task(item, validate_filename=True) for item in paths]
    return paths, contracts


def _load_projections(project_root, paths, contracts):
    """复用 workflow_contract._expected_board_projection 的九字段投影逻辑。"""
    projections = []
    for path, contract in zip(paths, contracts):
        projection = _expected_board_projection(contract, path, project_root)
        if projection is not None:
            projections.append(projection)
    return projections


def _render_generated_lines(projections):
    """把投影渲染为生成区内的规范 Markdown 状态表（确定性顺序）。"""
    ordered = sorted(
        projections,
        key=lambda item: (item.get("task_id") or "", item.get("task_path") or ""),
    )
    lines = [
        "| " + " | ".join(CANONICAL_HEADERS) + " |",
        "|" + "|".join("---" for _ in CANONICAL_HEADERS) + "|",
    ]
    for projection in ordered:
        cells = [projection.get(field, "") or "" for field in PROJECTION_FIELDS]
        lines.append("| " + " | ".join(cells) + " |")
    return lines


def _read_board_text(project_root):
    board_path = project_root / "docs" / "TASK_BOARD.md"
    try:
        return board_path.read_bytes().decode("utf-8")
    except (OSError, UnicodeError):
        return None


def _locate_generated_zone(lines):
    """返回 (begin_index, end_index)；标记缺失、重复或不配对返回 None。"""
    begins = [i for i, line in enumerate(lines) if line.strip() == GENERATED_BEGIN]
    ends = [i for i, line in enumerate(lines) if line.strip() == GENERATED_END]
    if len(begins) != 1 or len(ends) != 1 or begins[0] >= ends[0]:
        return None
    return begins[0], ends[0]


def _drift_diagnostics(project_root, text, projections):
    if text is None:
        return [_diagnostic("BOARD_DRIFT", 0, "docs/TASK_BOARD.md 缺失或不是可读 UTF-8")]
    # CRLF 归一化：core.autocrlf 落盘的看板逐行差一个 \r，比较前统一为 LF。
    lines = text.replace("\r\n", "\n").split("\n")
    zone = _locate_generated_zone(lines)
    if zone is None:
        return [_diagnostic(
            "BOARD_DRIFT",
            0,
            "生成区标记缺失或不配对（需要唯一且顺序正确的 "
            f"{GENERATED_BEGIN} / {GENERATED_END}）",
        )]
    begin, end = zone
    expected = _render_generated_lines(projections)
    actual = lines[begin + 1:end]
    if actual == expected:
        return []
    width = max(len(actual), len(expected))
    for offset in range(width):
        expected_line = expected[offset] if offset < len(expected) else "<missing>"
        actual_line = actual[offset] if offset < len(actual) else "<missing>"
        if expected_line != actual_line:
            line_no = min(begin + 2 + offset, end)
            provenance = (reader.Provenance(
                "generated_zone",
                BOARD_RELATIVE,
                "ADF-GENERATED",
                line_no,
                "" if actual_line == "<missing>" else actual_line,
                "generated",
            ),)
            return [_diagnostic(
                "BOARD_DRIFT",
                line_no,
                f"生成区与 TASK 投影不一致：line={line_no};expected={expected_line};actual={actual_line}",
                provenance,
            )]
    return []


def _resolve_task_link(target, project_root):
    """把看板内相对链接解析为项目内路径；非法或站外链接返回 None。"""
    value = target.strip().replace("\\", "/")
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*://", value):
        return None
    pure = pathlib.PurePosixPath(value)
    if (
        pure.is_absolute()
        or not pure.parts
        or any(part in {"", ".", ".."} for part in pure.parts)
        or ":" in pure.parts[0]
    ):
        return None
    if pure.parts[0] == "docs":
        return project_root.joinpath(*pure.parts)
    return (project_root / "docs").joinpath(*pure.parts)


def _manual_ref_diagnostics(project_root, text, contracts, paths):
    """扫描生成区外的人工区，校验 TASK 链接与任务 ID 提及的指向一致性。"""
    if text is None:
        return []
    lines = text.split("\n")
    known = {}
    known_by_path = {}
    for contract, path in zip(contracts, paths):
        task_id = contract.get("task_id")
        if task_id and task_id not in known:
            lifecycle = contract.get("lifecycle") or ""
            known[task_id] = lifecycle
            known_by_path[path] = (task_id, lifecycle)
    diagnostics = []
    heading = ""
    in_zone = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped == GENERATED_BEGIN:
            in_zone = True
            continue
        if stripped == GENERATED_END:
            in_zone = False
            continue
        heading_match = HEADING_RE.match(line.rstrip("\r"))
        if heading_match:
            heading = heading_match.group(1)
        if in_zone:
            continue
        line_no = index + 1
        link_spans = []
        for match in LINK_RE.finditer(line):
            target = match.group(2).strip()
            if not TASK_LINK_RE.search(target.replace("\\", "/")):
                continue
            link_spans.append(match.span())
            provenance = (reader.Provenance(
                "manual_ref", BOARD_RELATIVE, heading, line_no, match.group(0), "manual",
            ),)
            column = match.start() + 1
            resolved = _resolve_task_link(target, project_root)
            found = known_by_path.get(resolved) if resolved is not None else None
            if found is None:
                diagnostics.append(_diagnostic(
                    "BOARD_MANUAL_UNKNOWN_REF", line_no,
                    f"人工区 TASK 链接指向不存在的任务：{target}",
                    provenance, column=column,
                ))
            elif found[1] in TERMINAL_LIFECYCLES:
                diagnostics.append(_diagnostic(
                    "BOARD_MANUAL_STALE_REF", line_no,
                    f"人工区 TASK 链接指向已 {found[1]} 任务：{found[0]}",
                    provenance, column=column,
                ))
        for match in TASK_ID_RE.finditer(line):
            if any(start <= match.start() < end for start, end in link_spans):
                continue
            task_id = match.group(1)
            provenance = (reader.Provenance(
                "manual_ref", BOARD_RELATIVE, heading, line_no, task_id, "manual",
            ),)
            column = match.start() + 1
            if task_id not in known:
                diagnostics.append(_diagnostic(
                    "BOARD_MANUAL_UNKNOWN_REF", line_no,
                    f"人工区提及不存在的任务 ID：{task_id}",
                    provenance, column=column,
                ))
            elif known[task_id] in TERMINAL_LIFECYCLES:
                diagnostics.append(_diagnostic(
                    "BOARD_MANUAL_STALE_REF", line_no,
                    f"人工区提及已 {known[task_id]} 任务：{task_id}",
                    provenance, column=column,
                ))
    return diagnostics


def check(project_root):
    """--check：纯只读，返回排序后的诊断列表。"""
    paths, contracts = _load_tasks(project_root)
    projections = _load_projections(project_root, paths, contracts)
    text = _read_board_text(project_root)
    diagnostics = _drift_diagnostics(project_root, text, projections)
    diagnostics.extend(_manual_ref_diagnostics(project_root, text, contracts, paths))
    diagnostics.sort(key=lambda item: (item.path, item.line, item.column, item.code, item.message))
    return diagnostics


def _write_temp(target_dir, name, data):
    fd, tmp = tempfile.mkstemp(dir=str(target_dir), prefix=name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return pathlib.Path(tmp)


def _replace_all(pairs):
    """pairs 为 [(tmp_path, target_path), ...]；逐个原子替换，失败清理全部残余临时文件。"""
    pending = list(pairs)
    while pending:
        tmp, target = pending[0]
        try:
            os.replace(tmp, target)
        except BaseException:
            for leftover, _ in pending:
                try:
                    os.unlink(leftover)
                except OSError:
                    pass
            raise
        pending.pop(0)


def write_board(project_root):
    """--write：只重写生成区。返回 (diagnostics, changed)。"""
    paths, contracts = _load_tasks(project_root)
    projections = _load_projections(project_root, paths, contracts)
    text = _read_board_text(project_root)
    if text is None:
        return [_diagnostic("BOARD_DRIFT", 0, "docs/TASK_BOARD.md 缺失或不是可读 UTF-8，--write 中止")], False
    # CRLF 归一化：比较与重组统一在 LF 视图进行，写回时恢复文件既有行尾风格。
    eol = "\r\n" if "\r\n" in text else "\n"
    lines = text.replace("\r\n", "\n").split("\n")
    zone = _locate_generated_zone(lines)
    if zone is None:
        return [_diagnostic(
            "BOARD_DRIFT", 0,
            "生成区标记缺失或不配对，--write 中止（请先人工在看板中加入 "
            f"{GENERATED_BEGIN} / {GENERATED_END} 标记）",
        )], False
    begin, end = zone
    expected = _render_generated_lines(projections)
    if lines[begin + 1:end] == expected:
        return [], False
    new_lines = lines[:begin + 1] + expected + lines[end:]
    data = eol.join(new_lines).encode("utf-8")
    board_path = project_root / "docs" / "TASK_BOARD.md"
    tmp = _write_temp(board_path.parent, board_path.name, data)
    _replace_all([(tmp, board_path)])
    return [], True


def _split_entries(body_lines):
    """空行分隔的连续文本块为一个条目；行尾 CR 归一化去除。"""
    entries = []
    current = []
    for line in body_lines:
        normalized = line.rstrip("\r")
        if normalized.strip():
            current.append(normalized)
        elif current:
            entries.append("\n".join(current))
            current = []
    if current:
        entries.append("\n".join(current))
    return entries


def _parse_authority_log(text):
    """解析 AUTHORITY_LOG，返回 (entries, error)；entries 为 (id, sha256, content)。

    解析即对账：条目 ID 必须唯一，记录 sha256 必须与原文内容一致。
    """
    lines = [line.rstrip("\r") for line in text.split("\n")]
    heads = [(i, ENTRY_HEADING_RE.match(line)) for i, line in enumerate(lines)]
    heads = [(i, match) for i, match in heads if match]
    ids = [match.group(1) for _, match in heads]
    if len(ids) != len(set(ids)):
        return None, "条目 ID 重复"
    entries = []
    for position, (index, match) in enumerate(heads):
        end = heads[position + 1][0] if position + 1 < len(heads) else len(lines)
        block = lines[index + 1:end]
        cursor = 0
        while cursor < len(block) and not block[cursor].strip():
            cursor += 1
        sha_match = ENTRY_SHA_RE.fullmatch(block[cursor]) if cursor < len(block) else None
        if sha_match is None:
            return None, f"条目 {match.group(1)} 缺少 sha256 对账行"
        content_lines = block[cursor + 1:]
        while content_lines and not content_lines[0].strip():
            content_lines = content_lines[1:]
        while content_lines and not content_lines[-1].strip():
            content_lines = content_lines[:-1]
        content = "\n".join(content_lines)
        sha = sha_match.group(1)
        if hashlib.sha256(content.encode("utf-8")).hexdigest() != sha:
            return None, f"条目 {match.group(1)} 原文内容 SHA256 与对账行不一致"
        entries.append((match.group(1), sha, content))
    return entries, None


def migrate_authority_log(project_root, datestamp):
    """--migrate-authority-log：整节机械归档。返回 (diagnostics, summary)。

    summary 键：migrated / skipped / changed / message。失败时 changed=False
    且不产生半迁移状态（先写临时文件，再原子替换；日志先于看板落盘，
    极端中断下重跑可收敛）。
    """
    board_path = project_root / "docs" / "TASK_BOARD.md"
    log_path = project_root / "docs" / "AUTHORITY_LOG.md"
    noop = {"migrated": 0, "skipped": 0, "changed": False}
    text = _read_board_text(project_root)
    if text is None:
        return [_diagnostic(
            "ARCHIVE_MIGRATION_MISMATCH", 0,
            "docs/TASK_BOARD.md 缺失或不是可读 UTF-8，迁移中止",
            path=AUTHORITY_LOG_RELATIVE,
        )], {**noop, "message": "board unreadable"}
    raw_lines = text.split("\n")
    norm_lines = [line.rstrip("\r") for line in raw_lines]
    heading_index = next(
        (i for i, line in enumerate(norm_lines) if line == f"## {AUTHORITY_HEADING}"),
        None,
    )
    if heading_index is None:
        return [], {**noop, "message": f"未找到 ## {AUTHORITY_HEADING} 节，无迁移动作"}
    end_index = next(
        (i for i in range(heading_index + 1, len(norm_lines)) if H2_RE.match(norm_lines[i])),
        len(norm_lines),
    )
    source_entries = _split_entries(norm_lines[heading_index + 1:end_index])
    if not source_entries:
        return [], {**noop, "message": f"## {AUTHORITY_HEADING} 节为空，无迁移动作"}

    log_text = None
    if log_path.is_file():
        try:
            log_text = log_path.read_bytes().decode("utf-8")
        except (OSError, UnicodeError):
            return [_diagnostic(
                "ARCHIVE_MIGRATION_MISMATCH", 0,
                "docs/AUTHORITY_LOG.md 存在但不是可读 UTF-8，迁移中止",
                path=AUTHORITY_LOG_RELATIVE,
            )], {**noop, "message": "log unreadable"}
    existing = []
    if log_text is not None:
        existing, error = _parse_authority_log(log_text)
        if error:
            return [_diagnostic(
                "ARCHIVE_MIGRATION_MISMATCH", 0,
                f"docs/AUTHORITY_LOG.md 对账失败：{error}",
                path=AUTHORITY_LOG_RELATIVE,
            )], {**noop, "message": "log reconciliation failed"}

    remaining = {}
    for _, sha, _ in existing:
        remaining[sha] = remaining.get(sha, 0) + 1
    sequence = 0
    for entry_id, _, _ in existing:
        match = ENTRY_HEADING_RE.match(f"## {entry_id}")
        if match and match.group(2) == datestamp:
            sequence = max(sequence, int(match.group(3)))
    new_entries = []
    skipped = 0
    for content in source_entries:
        sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if remaining.get(sha, 0) > 0:
            remaining[sha] -= 1
            skipped += 1
            continue
        sequence += 1
        new_entries.append((f"AUTH-{datestamp}-{sequence:03d}", sha, content))

    all_ids = [entry_id for entry_id, _, _ in existing + new_entries]
    if len(all_ids) != len(set(all_ids)):
        return [_diagnostic(
            "ARCHIVE_MIGRATION_MISMATCH", 0,
            "归档条目 ID 重复，迁移中止",
            path=AUTHORITY_LOG_RELATIVE,
        )], {**noop, "message": "duplicate entry id"}
    if skipped + len(new_entries) != len(source_entries):
        return [_diagnostic(
            "ARCHIVE_MIGRATION_MISMATCH", 0,
            f"来源条目数 {len(source_entries)} 与归档条目数 {skipped + len(new_entries)} 不一致，迁移中止",
            path=AUTHORITY_LOG_RELATIVE,
        )], {**noop, "message": "entry count mismatch"}
    new_board_lines = raw_lines[:heading_index + 1] + [""] + raw_lines[end_index:]
    new_board_data = "\n".join(new_board_lines).encode("utf-8")
    if not new_entries:
        # 来源条目全部已归档（例如上次迁移在看板落盘前中断）：日志不动，
        # 仅清空看板节，重跑即可收敛到一致状态。
        board_tmp = _write_temp(board_path.parent, board_path.name, new_board_data)
        _replace_all([(board_tmp, board_path)])
        return [], {
            "migrated": 0,
            "skipped": skipped,
            "changed": True,
            "message": (
                f"## {AUTHORITY_HEADING} 节 {skipped} 条均已归档，日志无新增；"
                "看板节已清空（H2 标题保留）"
            ),
        }

    if log_text is None:
        base = LOG_HEADER
    else:
        base = log_text.rstrip("\n") + "\n"
    blocks = "".join(
        f"\n## {entry_id}\n\n- sha256: {sha}\n\n{content}\n"
        for entry_id, sha, content in new_entries
    )
    new_log_data = (base + blocks).encode("utf-8")

    log_tmp = _write_temp(log_path.parent, log_path.name, new_log_data)
    board_tmp = _write_temp(board_path.parent, board_path.name, new_board_data)
    _replace_all([(log_tmp, log_path), (board_tmp, board_path)])
    return [], {
        "migrated": len(new_entries),
        "skipped": skipped,
        "changed": True,
        "message": (
            f"已归档 {len(new_entries)} 条（{new_entries[0][0]} ~ {new_entries[-1][0]}）"
            f"到 docs/AUTHORITY_LOG.md，跳过已归档 {skipped} 条；"
            f"看板 ## {AUTHORITY_HEADING} 节已清空（H2 标题保留）"
        ),
    }


class InvocationError(Exception):
    pass


class StrictParser(argparse.ArgumentParser):
    def error(self, message):
        raise InvocationError(message)


def _summary(diagnostics):
    errors = sum(item.severity == "error" for item in diagnostics)
    warnings = sum(item.severity == "warning" for item in diagnostics)
    return {"errors": errors, "warnings": warnings, "exit_code": 2 if errors else 0}


def _diagnostic_dict(item):
    data = asdict(item)
    data["provenance"] = list(data["provenance"])
    return data


def _emit_diagnostics(diagnostics, output_format):
    if output_format == "json":
        print(json.dumps(
            {"summary": _summary(diagnostics), "diagnostics": [_diagnostic_dict(item) for item in diagnostics]},
            ensure_ascii=False,
            sort_keys=True,
        ))
        return
    summary = _summary(diagnostics)
    print(f"TASK_BOARD generator: errors={summary['errors']}, warnings={summary['warnings']}")
    for item in diagnostics:
        print(f"[{item.severity}] {item.code} {item.path}:{item.line}:{item.column} {item.message}")
        print(f"  建议：{item.suggestion}")
        for provenance in item.provenance:
            print("  provenance: " + json.dumps(asdict(provenance), ensure_ascii=False, sort_keys=True))


def _emit_action(mode, payload, output_format):
    if output_format == "json":
        print(json.dumps({"mode": mode, **payload}, ensure_ascii=False, sort_keys=True))
    else:
        print(f"{mode}: {payload['message']}")


def main(argv=None):
    parser = StrictParser(
        description="TASK_BOARD 看板生成器（独立命令）：默认 --check 纯只读；"
                    "--write 只写生成区；--migrate-authority-log 归档授权流水。",
    )
    parser.add_argument("target", help="项目根（含 docs/tasks 与 docs/TASK_BOARD.md）")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="只读校验（默认）")
    mode.add_argument("--write", action="store_true", help="重写 docs/TASK_BOARD.md 生成区（byte-stable）")
    mode.add_argument("--migrate-authority-log", action="store_true", help="把 ## 当前授权边界 整节机械归档到 docs/AUTHORITY_LOG.md")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    parser.add_argument("--date", default=None, help="迁移条目日期戳 YYYYMMDD（默认今天）")
    try:
        args = parser.parse_args(argv)
    except InvocationError as exc:
        print(f"[error] E_PARSE {exc}")
        return 2
    target = pathlib.Path(args.target)
    if not target.is_dir() or not (target / "docs").is_dir():
        print(f"[error] E_PARSE target 必须是含 docs/ 的项目根：{args.target}")
        return 2
    project_root = target.resolve()

    if args.migrate_authority_log:
        datestamp = args.date or datetime.date.today().strftime("%Y%m%d")
        if not DATE_RE.fullmatch(datestamp):
            print(f"[error] E_PARSE --date 必须是 YYYYMMDD：{datestamp}")
            return 2
        try:
            diagnostics, result = migrate_authority_log(project_root, datestamp)
        except OSError as exc:
            diagnostics = [_diagnostic(
                "ARCHIVE_MIGRATION_MISMATCH", 0,
                f"迁移写盘失败（未产生半迁移状态，可重跑收敛）：{exc}",
                path=AUTHORITY_LOG_RELATIVE,
            )]
            result = None
        if diagnostics:
            _emit_diagnostics(diagnostics, args.format)
            return 2
        _emit_action("migrate-authority-log", result, args.format)
        return 0

    if args.write:
        try:
            diagnostics, changed = write_board(project_root)
        except OSError as exc:
            print(f"[error] BOARD_DRIFT 写盘失败：{exc}")
            return 2
        if diagnostics:
            _emit_diagnostics(diagnostics, args.format)
            return 2
        _emit_action("write", {
            "changed": changed,
            "message": "docs/TASK_BOARD.md 生成区已更新" if changed else "生成区已是最新，未写入（byte-stable）",
        }, args.format)
        return 0

    diagnostics = check(project_root)
    _emit_diagnostics(diagnostics, args.format)
    return _summary(diagnostics)["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
