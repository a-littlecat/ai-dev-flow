"""Fail-closed manifest and SHA256 preflight for installed Runtime Bundle entry points."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath


class BundlePreflightError(RuntimeError):
    """The installed bundle cannot be imported without violating its manifest."""


def preflight_bundle(skill_root: Path) -> Path:
    """Validate every bundle file and return its backend source directory."""

    bundle_root = skill_root / "dashboard"
    manifest_path = bundle_root / "runtime-manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        skill_version = (skill_root / "VERSION").read_text(
            encoding="utf-8-sig"
        ).strip()
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BundlePreflightError(
            "installed Dashboard runtime manifest cannot be read"
        ) from exc
    if not isinstance(manifest, dict):
        raise BundlePreflightError(
            "installed Dashboard runtime manifest must be an object"
        )
    expected_identity = {
        "schema_version": "ai-dev-flow/dashboard-runtime-bundle/v1",
        "skill_version": skill_version,
        "supported_skill_series": "0.9.x",
        "workflow_contract_schema": "adf/v0.7.0",
        "scheduling_schema": "ai-dev-flow/scheduling/v1",
    }
    for key, expected in expected_identity.items():
        if manifest.get(key) != expected:
            raise BundlePreflightError(
                f"installed Dashboard runtime {key} is incompatible"
            )
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise BundlePreflightError(
            "installed Dashboard runtime manifest has no files"
        )
    if any(
        not isinstance(relative, str) or not isinstance(expected_hash, str)
        for relative, expected_hash in files.items()
    ):
        raise BundlePreflightError(
            "installed Dashboard runtime manifest has invalid file entries"
        )
    expected_paths = set(files) | {"runtime-manifest.json"}
    actual_paths = {
        path.relative_to(bundle_root).as_posix()
        for path in bundle_root.rglob("*")
        if path.is_file()
    }
    if actual_paths != expected_paths:
        raise BundlePreflightError(
            "installed Dashboard runtime file set differs from its manifest"
        )
    bundle_resolved = bundle_root.resolve()
    for relative, expected_hash in sorted(files.items()):
        posix_path = PurePosixPath(relative)
        if (
            posix_path.is_absolute()
            or relative != posix_path.as_posix()
            or ".." in posix_path.parts
        ):
            raise BundlePreflightError(
                "installed Dashboard runtime manifest escapes its bundle root"
            )
        candidate = (bundle_root / Path(*posix_path.parts)).resolve()
        try:
            candidate.relative_to(bundle_resolved)
        except ValueError as exc:
            raise BundlePreflightError(
                "installed Dashboard runtime manifest escapes its bundle root"
            ) from exc
        try:
            actual_hash = hashlib.sha256(candidate.read_bytes()).hexdigest()
        except OSError as exc:
            raise BundlePreflightError(
                f"installed Dashboard runtime file is missing: {relative}"
            ) from exc
        if actual_hash != expected_hash:
            raise BundlePreflightError(
                f"installed Dashboard runtime file changed: {relative}"
            )
    return bundle_root / "backend" / "src"
