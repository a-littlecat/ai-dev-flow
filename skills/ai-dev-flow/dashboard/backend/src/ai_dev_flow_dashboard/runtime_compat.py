"""Resolve and freeze the external ai-dev-flow Skill used by a dashboard instance."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping


SKILL_ROOT_ENV = "AI_DEV_FLOW_SKILL_ROOT"
SUPPORTED_SKILL_SERIES = (0, 9)
SUPPORTED_WORKFLOW_SCHEMA = "adf/v0.7.0"
SUPPORTED_SCHEDULING_SCHEMA = "ai-dev-flow/scheduling/v1"
_VERSION_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_CANONICAL_FIELD_RE = re.compile(r"^- `([^`\r\n]+)`: `([^`\r\n]*)`$")
_FINGERPRINT_FILES = (
    "VERSION",
    "SKILL.md",
    "references/CORE.md",
    "schemas/workflow-contract.schema.json",
    "scripts/workflow_contract.py",
    "scripts/_workflow_contract.py",
    "scripts/_task_board.py",
)
_BUNDLE_MANIFEST = "dashboard/runtime-manifest.json"


class RuntimeCompatibilityError(RuntimeError):
    """The selected Skill cannot be used safely by this dashboard runtime."""


@dataclass(frozen=True)
class SkillRuntime:
    root: Path
    version: str
    workflow_schema: str
    scheduling_schema: str
    fingerprint: str


def _read_runtime_manifest(skill_root: str | Path) -> tuple[Path, dict[str, object]]:
    root = Path(skill_root).resolve()
    bundle_root = root / "dashboard"
    manifest_path = bundle_root / "runtime-manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise RuntimeCompatibilityError(
            "installed Dashboard runtime manifest cannot be read"
        ) from exc
    if not isinstance(manifest, dict):
        raise RuntimeCompatibilityError(
            "installed Dashboard runtime manifest must be an object"
        )
    return bundle_root, manifest


def verify_runtime_bundle(skill_root: str | Path) -> None:
    root = Path(skill_root).resolve()
    bundle_root, manifest = _read_runtime_manifest(root)
    files = manifest.get("files")
    expected_identity = {
        "schema_version": "ai-dev-flow/dashboard-runtime-bundle/v1",
        "skill_version": (root / "VERSION").read_text(encoding="utf-8-sig").strip(),
        "supported_skill_series": "0.9.x",
        "workflow_contract_schema": SUPPORTED_WORKFLOW_SCHEMA,
        "scheduling_schema": SUPPORTED_SCHEDULING_SCHEMA,
    }
    for key, expected in expected_identity.items():
        if manifest.get(key) != expected:
            raise RuntimeCompatibilityError(
                f"installed Dashboard runtime {key} is incompatible"
            )
    if not isinstance(files, dict) or not files:
        raise RuntimeCompatibilityError(
            "installed Dashboard runtime manifest has no files"
        )
    expected_paths = set(files) | {"runtime-manifest.json"}
    actual_paths = {
        path.relative_to(bundle_root).as_posix()
        for path in bundle_root.rglob("*")
        if path.is_file()
    }
    if actual_paths != expected_paths:
        raise RuntimeCompatibilityError(
            "installed Dashboard runtime file set differs from its manifest"
        )
    for relative, expected_hash in sorted(files.items()):
        if not isinstance(relative, str) or not isinstance(expected_hash, str):
            raise RuntimeCompatibilityError(
                "installed Dashboard runtime manifest has invalid file entries"
            )
        candidate = (bundle_root / relative).resolve()
        try:
            candidate.relative_to(bundle_root)
        except ValueError as exc:
            raise RuntimeCompatibilityError(
                "installed Dashboard runtime manifest escapes its bundle root"
            ) from exc
        try:
            actual_hash = hashlib.sha256(candidate.read_bytes()).hexdigest()
        except OSError as exc:
            raise RuntimeCompatibilityError(
                f"installed Dashboard runtime file is missing: {relative}"
            ) from exc
        if actual_hash != expected_hash:
            raise RuntimeCompatibilityError(
                f"installed Dashboard runtime file changed: {relative}"
            )


def runtime_bundle_fingerprint(skill_root: str | Path) -> str:
    """Fingerprint manifest content plus the complete actual Dashboard file set."""

    root = Path(skill_root).resolve()
    bundle_root, manifest = _read_runtime_manifest(root)
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise RuntimeCompatibilityError(
            "installed Dashboard runtime manifest has no files"
        )
    if any(not isinstance(relative, str) for relative in files):
        raise RuntimeCompatibilityError(
            "installed Dashboard runtime manifest has invalid file entries"
        )
    actual_paths = sorted(
        path.relative_to(bundle_root).as_posix()
        for path in bundle_root.rglob("*")
        if path.is_file()
        and path.name != "runtime-manifest.json"
    )
    paths = [_BUNDLE_MANIFEST, *(f"dashboard/{relative}" for relative in actual_paths)]
    return _fingerprint_paths(root, paths)


def _candidate_roots(
    project_root: Path,
    *,
    explicit: str | Path | None,
    entry_skill_root: str | Path | None,
    environ: Mapping[str, str],
    home: Path,
) -> tuple[Path, ...]:
    if explicit is not None:
        return (Path(explicit).expanduser(),)
    candidates: list[Path] = []
    configured = environ.get(SKILL_ROOT_ENV)
    if configured:
        candidates.append(Path(configured).expanduser())
    if entry_skill_root is not None:
        candidates.append(Path(entry_skill_root).expanduser())
    candidates.extend(
        (
            home / ".agents" / "skills" / "ai-dev-flow",
            home / ".codex" / "skills" / "ai-dev-flow",
            project_root / "skills" / "ai-dev-flow",
        )
    )
    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = os.path.normcase(os.path.abspath(candidate))
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return tuple(unique)


def resolve_skill_runtime(
    project_root: str | Path,
    *,
    explicit: str | Path | None = None,
    entry_skill_root: str | Path | None = None,
    environ: Mapping[str, str] | None = None,
    home: str | Path | None = None,
) -> SkillRuntime:
    """Resolve the documented priority order and validate one immutable startup view."""

    project = Path(project_root).resolve()
    env = os.environ if environ is None else environ
    home_path = Path.home() if home is None else Path(home)
    candidates = _candidate_roots(
        project,
        explicit=explicit,
        entry_skill_root=entry_skill_root,
        environ=env,
        home=home_path,
    )
    if explicit is not None:
        return validate_skill_runtime(candidates[0])
    failures: list[str] = []
    for candidate in candidates:
        try:
            return validate_skill_runtime(candidate)
        except RuntimeCompatibilityError as exc:
            failures.append(f"{candidate}: {exc}")
    searched = "; ".join(str(path) for path in candidates)
    detail = f" ({'; '.join(failures)})" if failures else ""
    raise RuntimeCompatibilityError(
        f"no compatible ai-dev-flow Skill found; searched: {searched}{detail}"
    )


def validate_skill_runtime(skill_root: str | Path) -> SkillRuntime:
    root = Path(skill_root).resolve()
    required = tuple(root / relative for relative in _FINGERPRINT_FILES)
    missing = tuple(str(path) for path in required if not path.is_file())
    if missing:
        raise RuntimeCompatibilityError(
            "Skill installation is incomplete; missing: " + ", ".join(missing)
        )

    version = (root / "VERSION").read_text(encoding="utf-8-sig").strip()
    match = _VERSION_RE.fullmatch(version)
    if match is None:
        raise RuntimeCompatibilityError(f"invalid Skill VERSION: {version!r}")
    series = (int(match.group(1)), int(match.group(2)))
    if series != SUPPORTED_SKILL_SERIES:
        expected = ".".join(str(item) for item in SUPPORTED_SKILL_SERIES) + ".x"
        raise RuntimeCompatibilityError(
            f"unsupported Skill VERSION {version}; dashboard supports {expected}"
        )

    schema_path = root / "schemas" / "workflow-contract.schema.json"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8-sig"))
        workflow_schema = schema["properties"]["schema_version"]["const"]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise RuntimeCompatibilityError(
            "Workflow Contract schema identity cannot be read"
        ) from exc
    if workflow_schema != SUPPORTED_WORKFLOW_SCHEMA:
        raise RuntimeCompatibilityError(
            "unsupported Workflow Contract schema "
            f"{workflow_schema!r}; expected {SUPPORTED_WORKFLOW_SCHEMA!r}"
        )

    fingerprint = skill_fingerprint(root)
    return SkillRuntime(
        root=root,
        version=version,
        workflow_schema=workflow_schema,
        scheduling_schema=SUPPORTED_SCHEDULING_SCHEMA,
        fingerprint=fingerprint,
    )


def validate_project_schemas(project_root: str | Path, runtime: SkillRuntime) -> None:
    """Validate every schema version a TASK explicitly declares.

    Workflow Contract sections are canonical and must declare their schema.
    Historical Scheduling sections can predate ``scheduling_schema``; their
    absent version remains unknown while any attempted declaration is still
    parsed and checked strictly.
    """

    tasks_root = Path(project_root).resolve() / "docs" / "tasks"
    if not tasks_root.is_dir():
        raise RuntimeCompatibilityError("project root must contain docs/tasks")
    task_paths = sorted(tasks_root.glob("*.md"))
    if not task_paths:
        raise RuntimeCompatibilityError("project docs/tasks contains no TASK files")
    for path in task_paths:
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError) as exc:
            raise RuntimeCompatibilityError(
                f"TASK schema declarations cannot be read: {path.name}"
            ) from exc
        for heading, expected_key, expected_value, declaration_optional in (
            (
                "Workflow Contract",
                "schema_version",
                runtime.workflow_schema,
                False,
            ),
            (
                "Scheduling",
                "scheduling_schema",
                runtime.scheduling_schema,
                True,
            ),
        ):
            if f"## {heading}" not in text.splitlines():
                # Legacy TASKs can predate either canonical section. Their
                # absent evidence stays unknown; an opted-in canonical section
                # is always validated strictly below.
                continue
            values = [
                value
                for key, value in _section_fields(
                    text,
                    heading,
                    path=path,
                    required_key=expected_key,
                )
                if key == expected_key
            ]
            label = f"{heading} schema"
            if declaration_optional and not values:
                continue
            if len(values) != 1:
                raise RuntimeCompatibilityError(
                    f"{label} declaration must appear exactly once in {path.name}"
                )
            if values[0] != expected_value:
                raise RuntimeCompatibilityError(
                    f"unsupported {label} {values[0]!r} in {path.name}; "
                    f"expected {expected_value!r}"
                )


def _section_fields(
    text: str,
    heading: str,
    *,
    path: Path,
    required_key: str,
) -> tuple[tuple[str, str], ...]:
    heading_line = f"## {heading}"
    lines = text.splitlines()
    headings = [index for index, line in enumerate(lines) if line == heading_line]
    if len(headings) != 1:
        raise RuntimeCompatibilityError(
            f"{heading} section must appear exactly once in {path.name}"
        )
    start = headings[0] + 1
    result: list[tuple[str, str]] = []
    for line in lines[start:]:
        if line.startswith("#"):
            break
        match = _CANONICAL_FIELD_RE.fullmatch(line)
        if required_key in line and match is None:
            raise RuntimeCompatibilityError(
                f"{heading} schema declaration is malformed in {path.name}"
            )
        if match is not None:
            result.append((match.group(1), match.group(2)))
    return tuple(result)


def skill_fingerprint(skill_root: str | Path) -> str:
    root = Path(skill_root).resolve()
    return _fingerprint_paths(root, _FINGERPRINT_FILES)


def _fingerprint_paths(root: Path, paths: Iterable[str]) -> str:
    digest = hashlib.sha256()
    for relative in paths:
        if not isinstance(relative, str):
            raise RuntimeCompatibilityError("cannot fingerprint non-string Skill path")
        path = root / relative
        try:
            payload = path.read_bytes()
        except OSError as exc:
            raise RuntimeCompatibilityError(
                f"cannot fingerprint Skill file: {path}"
            ) from exc
        encoded = relative.encode("utf-8")
        digest.update(len(encoded).to_bytes(4, "big"))
        digest.update(encoded)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()
