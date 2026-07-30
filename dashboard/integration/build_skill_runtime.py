"""Build and verify the generated Dashboard runtime shipped inside the Skill."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_ROOT = REPO_ROOT / "skills" / "ai-dev-flow"
TARGET_ROOT = SKILL_ROOT / "dashboard"
BACKEND_SOURCE = REPO_ROOT / "dashboard" / "backend" / "src" / "ai_dev_flow_dashboard"
CONTRACT_SOURCE = REPO_ROOT / "dashboard" / "contracts" / "dashboard-contracts-v1.schema.json"
FRONTEND_ROOT = REPO_ROOT / "dashboard" / "frontend"
FRONTEND_DIST = FRONTEND_ROOT / "dist"
MANIFEST_NAME = "runtime-manifest.json"
ATTRIBUTES_SOURCE = REPO_ROOT / "dashboard" / "integration" / "runtime.gitattributes"
CANONICAL_TEXT_SUFFIXES = frozenset(
    {".css", ".gitattributes", ".html", ".js", ".json", ".md", ".mjs", ".py", ".ts"}
)


class BundleError(RuntimeError):
    """The generated Skill runtime is incomplete or has drifted."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_payload(source: Path) -> bytes:
    """Return checkout-independent bytes for generated text artifacts."""

    payload = source.read_bytes()
    if (
        source.suffix.casefold() in CANONICAL_TEXT_SUFFIXES
        or source.name == ".gitattributes"
    ):
        text = payload.decode("utf-8-sig")
        return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return payload


def _source_fingerprint() -> str:
    sources = [
        *sorted(BACKEND_SOURCE.rglob("*.py")),
        CONTRACT_SOURCE,
        ATTRIBUTES_SOURCE,
        FRONTEND_ROOT / "index.html",
        FRONTEND_ROOT / "package.json",
        FRONTEND_ROOT / "package-lock.json",
        FRONTEND_ROOT / "tsconfig.json",
        FRONTEND_ROOT / "vite.config.ts",
        *sorted((FRONTEND_ROOT / "src").rglob("*.ts")),
        *sorted((FRONTEND_ROOT / "src").rglob("*.css")),
    ]
    digest = hashlib.sha256()
    for source in sources:
        relative = source.relative_to(REPO_ROOT).as_posix().encode("utf-8")
        payload = _canonical_payload(source)
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def _desired_files() -> dict[str, Path]:
    files: dict[str, Path] = {".gitattributes": ATTRIBUTES_SOURCE}
    for source in sorted(BACKEND_SOURCE.rglob("*.py")):
        if "__pycache__" in source.parts:
            continue
        relative = source.relative_to(BACKEND_SOURCE).as_posix()
        files[f"backend/src/ai_dev_flow_dashboard/{relative}"] = source
    files["contracts/dashboard-contracts-v1.schema.json"] = CONTRACT_SOURCE
    if not (FRONTEND_DIST / "index.html").is_file():
        raise BundleError("frontend dist is missing; run the frontend build first")
    for source in sorted(FRONTEND_DIST.rglob("*")):
        if not source.is_file() or source.suffix.casefold() == ".map":
            continue
        relative = source.relative_to(FRONTEND_DIST).as_posix()
        files[f"static/{relative}"] = source
    return files


def _manifest(files: dict[str, Path]) -> dict[str, object]:
    version = (SKILL_ROOT / "VERSION").read_text(encoding="utf-8-sig").strip()
    return {
        "schema_version": "ai-dev-flow/dashboard-runtime-bundle/v1",
        "skill_version": version,
        "supported_skill_series": "0.9.x",
        "workflow_contract_schema": "adf/v0.7.0",
        "scheduling_schema": "ai-dev-flow/scheduling/v1",
        "source_fingerprint": _source_fingerprint(),
        "files": {
            relative: _sha256(_canonical_payload(source))
            for relative, source in sorted(files.items())
        },
    }


def _actual_files() -> set[str]:
    if not TARGET_ROOT.is_dir():
        return set()
    return {
        path.relative_to(TARGET_ROOT).as_posix()
        for path in TARGET_ROOT.rglob("*")
        if path.is_file()
    }


def _assert_frontend_codegen_current() -> None:
    subprocess.run(
        [
            "npm.cmd" if sys.platform == "win32" else "npm",
            "run",
            "codegen:check",
        ],
        cwd=FRONTEND_ROOT,
        check=True,
    )


def _build_frontend() -> None:
    subprocess.run(
        [
            "npm.cmd" if sys.platform == "win32" else "npm",
            "run",
            "build",
            "--",
            "--sourcemap",
            "false",
        ],
        cwd=FRONTEND_ROOT,
        check=True,
    )


def verify(*, check_codegen: bool = True) -> dict[str, object]:
    if check_codegen:
        _assert_frontend_codegen_current()
    desired = _desired_files()
    expected = _manifest(desired)
    manifest_path = TARGET_ROOT / MANIFEST_NAME
    if not manifest_path.is_file():
        raise BundleError(f"runtime manifest is missing: {manifest_path}")
    try:
        actual_manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BundleError("runtime manifest cannot be read") from exc
    if actual_manifest != expected:
        raise BundleError("runtime manifest does not match canonical sources")
    expected_paths = set(desired) | {MANIFEST_NAME}
    actual_paths = _actual_files()
    if actual_paths != expected_paths:
        missing = sorted(expected_paths - actual_paths)
        extra = sorted(actual_paths - expected_paths)
        raise BundleError(f"runtime file set drifted: missing={missing}; extra={extra}")
    mismatches = [
        relative
        for relative, source in desired.items()
        if (TARGET_ROOT / relative).read_bytes() != _canonical_payload(source)
    ]
    if mismatches:
        raise BundleError(
            "runtime files differ from canonical sources: " + ", ".join(mismatches)
        )
    return {
        "ok": True,
        "file_count": len(desired),
        "manifest": str(manifest_path),
    }


def build() -> dict[str, object]:
    _assert_frontend_codegen_current()
    source_fingerprint = _source_fingerprint()
    _build_frontend()
    if _source_fingerprint() != source_fingerprint:
        raise BundleError("canonical sources changed during the frontend build")
    desired = _desired_files()
    expected_paths = set(desired) | {MANIFEST_NAME}
    target_resolved = TARGET_ROOT.resolve()
    skill_resolved = SKILL_ROOT.resolve()
    try:
        target_resolved.relative_to(skill_resolved)
    except ValueError as exc:
        raise BundleError("refusing to build outside the Skill root") from exc
    TARGET_ROOT.mkdir(parents=True, exist_ok=True)
    for relative, source in desired.items():
        destination = TARGET_ROOT / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = _canonical_payload(source)
        if not destination.is_file() or destination.read_bytes() != payload:
            destination.write_bytes(payload)
    for relative in sorted(_actual_files() - expected_paths, reverse=True):
        (TARGET_ROOT / relative).unlink()
    manifest_path = TARGET_ROOT / MANIFEST_NAME
    manifest_path.write_text(
        json.dumps(_manifest(desired), ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    for directory in sorted(
        (path for path in TARGET_ROOT.rglob("*") if path.is_dir()),
        key=lambda path: len(path.parts),
        reverse=True,
    ):
        try:
            directory.rmdir()
        except OSError:
            pass
    return verify(check_codegen=False)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = verify() if args.check else build()
    except (BundleError, OSError, subprocess.CalledProcessError) as exc:
        print(f"dashboard runtime bundle error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
