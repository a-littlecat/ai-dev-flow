"""Strict parser and normalizer for ``ai-dev-flow/scheduling/v1``."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any, Iterable

from .canonical import stable_text_id
from .models import (
    DependencySpec,
    Diagnostic,
    FrozenTaskInput,
    Provenance,
    SCHEDULING_FIELDS,
    SchedulingProfile,
    ScopeEntry,
)


SCHEDULING_SCHEMA = "ai-dev-flow/scheduling/v1"
FIELD_RE = re.compile(r"^- `([a-z][a-z0-9_]*)`: `([^`\r\n]+)`$")
TASK_ID_RE = re.compile(r"^[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*$")
LOCK_RE = re.compile(r"^[a-z][a-z0-9._-]*$")
DEPENDENCY_RE = re.compile(
    r"^(?P<target>[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*)"
    r"#(?P<axis>[a-z_]+)=(?P<expected>.+)$"
)

AXIS_VALUES = {
    "lifecycle": (
        "Draft",
        "Ready",
        "In Progress",
        "Blocked",
        "Review",
        "Needs Fix",
        "Accepted",
        "Closed",
        "Deferred",
        "Cancelled",
    ),
    "review_status": ("Pending", "In Review", "Passed", "Needs Fix", "Do Not Merge"),
    "ua_status": ("Not Required", "Pending", "Passed", "Failed", "Deferred", "TBD"),
    "acceptance_authority": ("None", "User Confirmed", "Designated Acceptor Confirmed"),
    "commit_status": ("Not Applicable", "Uncommitted", "Committed"),
    "merge_status": ("Not Applicable", "Unmerged", "Merged", "Deferred"),
    "merge_authority": ("None", "User Authorized", "Denied"),
    "close_authority": ("None", "User Authorized", "Rule Authorized", "Denied"),
}

RISK_FLAGS = (
    "architecture",
    "business_files_gt_3",
    "build_or_deploy_config",
    "core_execution_path",
    "core_writer_path",
    "data_migration",
    "delivery",
    "explicit_independent_review",
    "external_sync",
    "historical_p1",
    "irreversible_action",
    "parallel_writers",
    "public_api",
    "real_environment",
    "release",
    "security",
    "shared_component",
    "tests_do_not_cover_oracle",
)

WINDOWS_RESERVED = re.compile(r"^(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", re.IGNORECASE)
BRANCH_FORBIDDEN = set(" ~^:?*[\\")


def _prov(source_path: str, field: str | None, line: int, raw: str | None, source_type: str) -> Provenance:
    return Provenance(source_path, "Scheduling", field, line, raw, source_type)


def _diag(
    code: str,
    message: str,
    source_path: str,
    task_id: str,
    line: int,
    field: str | None = None,
    raw: str | None = None,
    *,
    severity: str = "error",
    source_type: str = "canonical",
) -> Diagnostic:
    provenance = (_prov(source_path, field, line, raw, source_type),)
    return Diagnostic(
        stable_text_id("diagnostic", code, source_path, str(line), message),
        code,
        severity,
        message,
        (task_id,) if task_id else (),
        provenance,
    )


def _split_list(value: str) -> tuple[str, ...] | None:
    if value == "none":
        return ()
    parts = value.split(";")
    if not parts or any(not part or part != part.strip() for part in parts):
        return None
    if "none" in parts or len(set(parts)) != len(parts):
        return None
    return tuple(parts)


def _branch_valid(value: str) -> bool:
    if value == "none":
        return True
    if not value or value.startswith(("-", ".", "/")) or value.endswith((".", "/")):
        return False
    if ".." in value or "@{" in value or "//" in value:
        return False
    if any(ord(char) < 32 or ord(char) == 127 or char in BRANCH_FORBIDDEN for char in value):
        return False
    return all(part and part not in {".", ".."} and not part.endswith(".lock") for part in value.split("/"))


def _canonical_scope(
    token: str,
    provenance: Provenance,
    project_root: Path,
    prefix_cache: dict[tuple[str, ...], Path | None] | None = None,
) -> ScopeEntry | None:
    if ":" not in token:
        return None
    kind, raw_path = token.split(":", 1)
    if kind not in {"file", "dir"} or not raw_path:
        return None
    canonical = canonical_repo_path(raw_path, project_root, prefix_cache)
    if canonical is None:
        return None
    path, comparison_segments = canonical
    return ScopeEntry(kind, path, comparison_segments, provenance)


def canonical_repo_path(
    raw_path: str,
    project_root: Path | None = None,
    prefix_cache: dict[tuple[str, ...], Path | None] | None = None,
) -> tuple[str, tuple[str, ...]] | None:
    path = unicodedata.normalize("NFC", raw_path)
    if (
        "\\" in path
        or path.startswith("/")
        or re.match(r"^[A-Za-z]:", path)
        or path.startswith("//")
        or "://" in path
        or any(ord(char) < 32 or ord(char) == 127 for char in path)
    ):
        return None
    segments = path.split("/")
    if any(
        not segment
        or segment in {".", ".."}
        or segment.endswith((" ", "."))
        or WINDOWS_RESERVED.match(segment)
        for segment in segments
    ):
        return None

    if project_root is not None:
        resolved_root = project_root
        current = resolved_root
        for index, segment in enumerate(segments):
            key = tuple(segments[: index + 1])
            if prefix_cache is not None and key in prefix_cache:
                cached = prefix_cache[key]
                if cached is None:
                    break
                current = cached
                continue
            candidate = current / segment
            if candidate.exists() or candidate.is_symlink():
                try:
                    resolved = candidate.resolve(strict=True)
                except OSError:
                    return None
                if not resolved.is_relative_to(resolved_root):
                    return None
                current = resolved
                if prefix_cache is not None:
                    prefix_cache[key] = resolved
            else:
                if prefix_cache is not None:
                    prefix_cache[key] = None
                break
    return "/".join(segments), tuple(item.casefold() for item in segments)


def _scope_paths_from_text(text: str) -> tuple[str, ...]:
    """Extract lexical scope paths for cache invalidation, without accepting them."""

    lines = text.splitlines()
    in_scheduling = False
    for line in lines:
        if line.startswith("## "):
            in_scheduling = line == "## Scheduling"
            continue
        if not in_scheduling:
            continue
        match = FIELD_RE.fullmatch(line)
        if match is None or match.group(1) != "write_scope":
            continue
        parts = _split_list(match.group(2))
        if parts is None:
            return ()
        return tuple(
            token.split(":", 1)[1]
            for token in parts
            if ":" in token
        )
    return ()


def _scope_topology_key(
    raw_paths: tuple[str, ...],
    project_root: Path,
    probe_cache: dict[str, tuple[Any, Path | None]],
) -> tuple[Any, ...]:
    """Fingerprint every existing prefix and the first missing prefix of each scope."""

    signatures: list[Any] = []
    for raw_path in raw_paths:
        normalized = unicodedata.normalize("NFC", raw_path)
        segments = normalized.split("/")
        current = project_root
        prefix: list[Any] = []
        for segment in segments:
            candidate = current / segment
            cache_key = str(candidate.absolute()).casefold()
            cached = probe_cache.get(cache_key)
            if cached is not None:
                entry, resolved = cached
                prefix.append(entry)
                if resolved is None:
                    break
                current = resolved
                continue
            try:
                stat = candidate.lstat()
            except FileNotFoundError:
                entry = (segment.casefold(), "missing")
                probe_cache[cache_key] = (entry, None)
                prefix.append(entry)
                break
            except OSError as exc:
                entry = (segment.casefold(), "error", type(exc).__name__)
                probe_cache[cache_key] = (entry, None)
                prefix.append(entry)
                break
            try:
                resolved = candidate.resolve(strict=True)
            except OSError as exc:
                entry = (
                    segment.casefold(),
                    "unresolved",
                    stat.st_dev,
                    stat.st_ino,
                    stat.st_mtime_ns,
                    stat.st_ctime_ns,
                    getattr(stat, "st_file_attributes", 0),
                    type(exc).__name__,
                )
                probe_cache[cache_key] = (entry, None)
                prefix.append(entry)
                break
            entry = (
                segment.casefold(),
                "present",
                stat.st_dev,
                stat.st_ino,
                stat.st_mtime_ns,
                stat.st_ctime_ns,
                getattr(stat, "st_file_attributes", 0),
                str(resolved).casefold(),
            )
            probe_cache[cache_key] = (entry, resolved)
            prefix.append(entry)
            current = resolved
        signatures.append((normalized, tuple(prefix)))
    return tuple(signatures)


class SchedulingParser:
    """Parse canonical Scheduling sections from already-frozen UTF-8 text."""

    def __init__(self, project_root: str | Path):
        self.project_root = Path(project_root).resolve()
        self._topology_probe_cache: dict[str, tuple[Any, Path | None]] = {}
        self._canonical_prefix_cache: dict[tuple[str, ...], Path | None] = {}
        self._scope_path_cache: dict[tuple[str, str], tuple[str, ...]] = {}
        self._profile_cache: dict[
            tuple[str, str, str, frozenset[str], tuple[Any, ...]],
            SchedulingProfile,
        ] = {}

    def begin_inspection(self) -> None:
        """Start a new filesystem topology generation for one frozen core read."""

        self._topology_probe_cache = {}
        self._canonical_prefix_cache = {}

    def parse(
        self,
        frozen: FrozenTaskInput,
        task_id: str,
        known_task_ids: Iterable[str],
    ) -> SchedulingProfile:
        known = (
            known_task_ids
            if isinstance(known_task_ids, frozenset)
            else frozenset(known_task_ids)
        )
        scope_path_key = (frozen.source_path, frozen.sha256)
        raw_scope_paths = self._scope_path_cache.get(scope_path_key)
        if raw_scope_paths is None:
            raw_scope_paths = _scope_paths_from_text(frozen.text)
            if len(self._scope_path_cache) >= 4096:
                self._scope_path_cache.pop(next(iter(self._scope_path_cache)))
            self._scope_path_cache[scope_path_key] = raw_scope_paths
        key = (
            frozen.source_path,
            frozen.sha256,
            task_id,
            known,
            _scope_topology_key(
                raw_scope_paths,
                self.project_root,
                self._topology_probe_cache,
            ),
        )
        cached = self._profile_cache.get(key)
        if cached is not None:
            return cached
        result = self._parse_uncached(frozen, task_id, known)
        if len(self._profile_cache) >= 4096:
            self._profile_cache.pop(next(iter(self._profile_cache)))
        self._profile_cache[key] = result
        return result

    def _parse_uncached(
        self,
        frozen: FrozenTaskInput,
        task_id: str,
        known_task_ids: Iterable[str],
    ) -> SchedulingProfile:
        lines = frozen.text.splitlines()
        headings = [index for index, line in enumerate(lines) if line == "## Scheduling"]
        if not headings:
            return self._legacy_or_absent(frozen, task_id, set(known_task_ids))
        if len(headings) != 1:
            diagnostic = _diag(
                "SCHEDULING_PARSE_ERROR",
                "Scheduling section must appear exactly once",
                frozen.source_path,
                task_id,
                headings[1] + 1,
            )
            return SchedulingProfile("invalid", (), (), (), (diagnostic,), (),)

        start = headings[0]
        end = len(lines)
        for index in range(start + 1, len(lines)):
            if lines[index].startswith("## ") and not lines[index].startswith("### "):
                end = index
                break

        raw_fields: dict[str, tuple[str, int]] = {}
        diagnostics: list[Diagnostic] = []
        provenance: list[Provenance] = []
        for index in range(start + 1, end):
            line = lines[index]
            if not line:
                continue
            match = FIELD_RE.fullmatch(line)
            if match is None:
                diagnostics.append(
                    _diag(
                        "SCHEDULING_PARSE_ERROR",
                        "Scheduling contains a non-canonical line",
                        frozen.source_path,
                        task_id,
                        index + 1,
                        raw=line,
                    )
                )
                continue
            key, value = match.groups()
            if key not in SCHEDULING_FIELDS:
                diagnostics.append(
                    _diag(
                        "SCHEDULING_UNKNOWN_FIELD",
                        f"unknown Scheduling field: {key}",
                        frozen.source_path,
                        task_id,
                        index + 1,
                        key,
                        value,
                    )
                )
                continue
            if key in raw_fields:
                diagnostics.append(
                    _diag(
                        "SCHEDULING_DUPLICATE_FIELD",
                        f"duplicate Scheduling field: {key}",
                        frozen.source_path,
                        task_id,
                        index + 1,
                        key,
                        value,
                    )
                )
                continue
            raw_fields[key] = (value, index + 1)
            provenance.append(_prov(frozen.source_path, key, index + 1, value, "canonical"))

        missing = [field for field in SCHEDULING_FIELDS if field not in raw_fields]
        for field in missing:
            diagnostics.append(
                _diag(
                    "SCHEDULING_MISSING_FIELD",
                    f"missing Scheduling field: {field}",
                    frozen.source_path,
                    task_id,
                    start + 1,
                    field,
                )
            )
        structural_codes = {
            "SCHEDULING_PARSE_ERROR",
            "SCHEDULING_UNKNOWN_FIELD",
            "SCHEDULING_DUPLICATE_FIELD",
            "SCHEDULING_MISSING_FIELD",
        }
        if any(item.code in structural_codes for item in diagnostics):
            return SchedulingProfile(
                "invalid",
                (),
                (),
                (),
                tuple(sorted(diagnostics, key=lambda item: item.diagnostic_id)),
                tuple(provenance),
            )

        values: dict[str, Any] = {}
        dependencies: tuple[DependencySpec, ...] = ()
        scopes: tuple[ScopeEntry, ...] = ()
        known = (
            known_task_ids
            if isinstance(known_task_ids, (set, frozenset))
            else set(known_task_ids)
        )
        for field in SCHEDULING_FIELDS:
            raw, line = raw_fields[field]
            parsed, field_dependencies, field_scopes, field_diagnostics = self._parse_field(
                field, raw, line, frozen.source_path, task_id, known
            )
            values[field] = parsed
            if field == "depends_on":
                dependencies = field_dependencies
            elif field == "write_scope":
                scopes = field_scopes
            diagnostics.extend(field_diagnostics)

        ordered_values = tuple((field, values[field]) for field in SCHEDULING_FIELDS)
        state = (
            "invalid"
            if any(item.code == "SCHEDULING_SCHEMA_UNSUPPORTED" for item in diagnostics)
            else "canonical"
        )
        return SchedulingProfile(
            state,
            ordered_values,
            dependencies,
            scopes,
            tuple(sorted(diagnostics, key=lambda item: item.diagnostic_id)),
            tuple(provenance),
        )

    def _parse_field(
        self,
        field: str,
        raw: str,
        line: int,
        source_path: str,
        task_id: str,
        known: set[str],
    ) -> tuple[Any, tuple[DependencySpec, ...], tuple[ScopeEntry, ...], list[Diagnostic]]:
        diagnostics: list[Diagnostic] = []
        dependencies: list[DependencySpec] = []
        scopes: list[ScopeEntry] = []
        provenance = _prov(source_path, field, line, raw, "canonical")

        def invalid(code: str, message: str) -> tuple[Any, tuple[DependencySpec, ...], tuple[ScopeEntry, ...], list[Diagnostic]]:
            diagnostics.append(_diag(code, message, source_path, task_id, line, field, raw))
            return None, (), (), diagnostics

        if field == "scheduling_schema":
            return (raw, (), (), diagnostics) if raw == SCHEDULING_SCHEMA else invalid(
                "SCHEDULING_SCHEMA_UNSUPPORTED", "unsupported scheduling_schema"
            )
        if field == "priority":
            return (raw, (), (), diagnostics) if raw in {"high", "medium", "low", "TBD"} else invalid(
                "SCHEDULING_VALUE_INVALID", "invalid priority"
            )
        if field == "parallel_intent":
            return (raw, (), (), diagnostics) if raw in {"serial", "consider", "unknown"} else invalid(
                "SCHEDULING_VALUE_INVALID", "invalid parallel_intent"
            )
        if field == "worktree":
            return (raw, (), (), diagnostics) if raw in {"required", "optional", "forbidden", "unknown"} else invalid(
                "SCHEDULING_VALUE_INVALID", "invalid worktree requirement"
            )
        if field == "branch_hint":
            if not _branch_valid(raw):
                return invalid("SCHEDULING_BRANCH_INVALID", "branch_hint is not a safe Git branch short name")
            return (None if raw == "none" else unicodedata.normalize("NFC", raw), (), (), diagnostics)
        if field == "parent":
            if raw == "none":
                return None, (), (), diagnostics
            if not TASK_ID_RE.fullmatch(raw):
                return invalid("SCHEDULING_REFERENCE_INVALID", "parent is not a valid TASK ID")
            if raw not in known:
                return invalid("SCHEDULING_REFERENCE_DANGLING", f"parent TASK does not exist: {raw}")
            return raw, (), (), diagnostics

        parts = _split_list(raw)
        if parts is None:
            return invalid("SCHEDULING_LIST_INVALID", f"{field} is not a canonical semicolon list")

        if field == "depends_on":
            seen_axes: dict[tuple[str, str], str] = {}
            seen_conditions: set[tuple[str, str, str]] = set()
            for part in parts:
                match = DEPENDENCY_RE.fullmatch(part)
                if match is None:
                    return invalid("DEPENDENCY_CONDITION_INVALID", f"invalid dependency condition: {part}")
                target, axis, expected = match.group("target", "axis", "expected")
                if axis not in AXIS_VALUES:
                    return invalid("DEPENDENCY_AXIS_UNKNOWN", f"unknown dependency axis: {axis}")
                if expected not in AXIS_VALUES[axis]:
                    return invalid("DEPENDENCY_EXPECTED_INVALID", f"invalid expected value for {axis}: {expected}")
                if target not in known:
                    return invalid("SCHEDULING_REFERENCE_DANGLING", f"dependency TASK does not exist: {target}")
                condition = (target, axis, expected)
                key = (target, axis)
                if condition in seen_conditions:
                    return invalid("DEPENDENCY_CONDITION_DUPLICATE", f"duplicate dependency condition: {part}")
                if key in seen_axes and seen_axes[key] != expected:
                    return invalid("DEPENDENCY_CONDITION_CONFLICT", f"conflicting dependency condition: {part}")
                seen_conditions.add(condition)
                seen_axes[key] = expected
                dependencies.append(DependencySpec(target, axis, expected, provenance))
            dependencies.sort(key=lambda item: (item.target_task_id, item.axis, item.expected))
            normalized = tuple(
                f"{item.target_task_id}#{item.axis}={item.expected}" for item in dependencies
            )
            return normalized, tuple(dependencies), (), diagnostics

        if field in {"replaces", "discovered_from", "conflicts_with"}:
            if any(not TASK_ID_RE.fullmatch(part) for part in parts):
                return invalid("SCHEDULING_REFERENCE_INVALID", f"{field} contains an invalid TASK ID")
            dangling = sorted(set(parts) - known)
            if dangling:
                return invalid("SCHEDULING_REFERENCE_DANGLING", f"{field} references missing TASK: {dangling[0]}")
            return tuple(sorted(parts)), (), (), diagnostics

        if field == "write_scope":
            for part in parts:
                entry = _canonical_scope(
                    part,
                    provenance,
                    self.project_root,
                    self._canonical_prefix_cache,
                )
                if entry is None:
                    return invalid("SCHEDULING_PATH_INVALID", f"invalid Windows-safe repo path: {part}")
                scopes.append(entry)
            scopes.sort(key=lambda item: (item.comparison_segments, item.kind))
            deduplicated: list[ScopeEntry] = []
            for entry in scopes:
                if any(_scope_covers(existing, entry) for existing in deduplicated):
                    diagnostics.append(
                        _diag(
                            "SCHEDULING_SCOPE_REDUNDANT",
                            f"write_scope is already covered: {entry.token}",
                            source_path,
                            task_id,
                            line,
                            field,
                            raw,
                            severity="warning",
                        )
                    )
                    continue
                deduplicated = [item for item in deduplicated if not _scope_covers(entry, item)]
                deduplicated.append(entry)
            deduplicated.sort(key=lambda item: (item.comparison_segments, item.kind))
            return tuple(item.token for item in deduplicated), (), tuple(deduplicated), diagnostics

        if field == "module_locks":
            if any(not LOCK_RE.fullmatch(part) for part in parts):
                return invalid("SCHEDULING_LOCK_INVALID", "module_locks contains an invalid token")
            return tuple(sorted(parts)), (), (), diagnostics
        if field == "risk_flags":
            if any(part not in RISK_FLAGS for part in parts):
                return invalid("SCHEDULING_RISK_UNKNOWN", "risk_flags contains an unknown v1 flag")
            return tuple(sorted(parts)), (), (), diagnostics
        raise AssertionError(f"unhandled Scheduling field: {field}")

    def _legacy_or_absent(
        self,
        frozen: FrozenTaskInput,
        task_id: str,
        known: set[str],
    ) -> SchedulingProfile:
        # Legacy input is intentionally narrow: only already-canonical tokens in
        # explicitly named bullets are recognized. Natural-language relations
        # remain absent/unknown.
        values: dict[str, Any] = {field: None for field in SCHEDULING_FIELDS}
        dependencies: list[DependencySpec] = []
        scopes: list[ScopeEntry] = []
        provenance: list[Provenance] = []
        diagnostics: list[Diagnostic] = []
        found = False
        for line_number, line in enumerate(frozen.text.splitlines(), start=1):
            if line.startswith("- 前置依赖："):
                raw = line.split("：", 1)[1].strip().strip("`")
                match = DEPENDENCY_RE.fullmatch(raw)
                if match and match.group("axis") in AXIS_VALUES and match.group("expected") in AXIS_VALUES[match.group("axis")]:
                    target = match.group("target")
                    if target in known:
                        prov = _prov(frozen.source_path, "depends_on", line_number, raw, "legacy_inferred")
                        dependencies.append(
                            DependencySpec(target, match.group("axis"), match.group("expected"), prov)
                        )
                        provenance.append(prov)
                        found = True
            if line.startswith("- 允许修改："):
                for token in re.findall(r"(?:file|dir):[^`;,\s]+", line):
                    prov = _prov(frozen.source_path, "write_scope", line_number, token, "legacy_inferred")
                    entry = _canonical_scope(
                        token,
                        prov,
                        self.project_root,
                        self._canonical_prefix_cache,
                    )
                    if entry:
                        scopes.append(entry)
                        provenance.append(prov)
                        found = True
        if not found:
            return SchedulingProfile("absent", (), (), (), (), ())
        values["depends_on"] = tuple(
            f"{item.target_task_id}#{item.axis}={item.expected}"
            for item in sorted(dependencies, key=lambda item: (item.target_task_id, item.axis, item.expected))
        )
        scopes.sort(key=lambda item: (item.comparison_segments, item.kind))
        values["write_scope"] = tuple(item.token for item in scopes)
        diagnostics.append(
            _diag(
                "SCHEDULING_LEGACY_INFERRED",
                "Scheduling values were narrowly inferred from explicit legacy tokens",
                frozen.source_path,
                task_id,
                1,
                severity="warning",
                source_type="legacy_inferred",
            )
        )
        return SchedulingProfile(
            "legacy_inferred",
            tuple((field, values[field]) for field in SCHEDULING_FIELDS),
            tuple(dependencies),
            tuple(scopes),
            tuple(diagnostics),
            tuple(provenance),
        )


def _scope_covers(left: ScopeEntry, right: ScopeEntry) -> bool:
    if left.comparison_segments == right.comparison_segments:
        return left.kind == "dir" or left.kind == right.kind
    return (
        left.kind == "dir"
        and len(left.comparison_segments) < len(right.comparison_segments)
        and right.comparison_segments[: len(left.comparison_segments)] == left.comparison_segments
    )


def scopes_overlap(left: ScopeEntry, right: ScopeEntry) -> bool:
    return _scope_covers(left, right) or _scope_covers(right, left)
