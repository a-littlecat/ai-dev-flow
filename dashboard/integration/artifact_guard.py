"""Verify that Accepted dashboard artifacts still match the frozen Git baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Iterable


MANIFEST_NAME = "accepted-artifacts.json"


def _git(repo_root: Path, *arguments: str, text: bool = False) -> bytes | str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), *arguments],
        check=True,
        capture_output=True,
        text=text,
        encoding="utf-8" if text else None,
    )
    return result.stdout


def baseline_paths(repo_root: Path, base_commit: str, roots: Iterable[str]) -> tuple[str, ...]:
    output = _git(
        repo_root,
        "ls-tree",
        "-r",
        "--name-only",
        base_commit,
        "--",
        *roots,
        text=True,
    )
    assert isinstance(output, str)
    return tuple(sorted(line for line in output.splitlines() if line))


def working_paths(repo_root: Path, roots: Iterable[str]) -> tuple[str, ...]:
    """Return tracked plus non-ignored untracked files in the protected roots."""

    output = _git(
        repo_root,
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
        "--",
        *roots,
        text=True,
    )
    assert isinstance(output, str)
    return tuple(sorted(set(line for line in output.splitlines() if line)))


def baseline_digest(
    repo_root: Path,
    base_commit: str,
    paths: Iterable[str],
) -> tuple[str, dict[str, str]]:
    """Hash canonical Git blob bytes, independent of checkout EOL filters."""

    hashes: dict[str, str] = {}
    payload = bytearray()
    for relative in sorted(paths):
        content = _git(
            repo_root,
            "cat-file",
            "blob",
            f"{base_commit}:{relative}",
        )
        assert isinstance(content, bytes)
        digest = hashlib.sha256(content).hexdigest()
        hashes[relative] = digest
        payload.extend(relative.encode("utf-8"))
        payload.extend(b"\0")
        payload.extend(digest.encode("ascii"))
        payload.extend(b"\n")
    return hashlib.sha256(payload).hexdigest(), hashes


def changed_paths(
    repo_root: Path,
    base_commit: str,
    roots: Iterable[str],
) -> set[str]:
    """Return paths changed in either the index or the working tree."""

    changed: set[str] = set()
    for index_arguments in ((), ("--cached",)):
        output = _git(
            repo_root,
            "diff",
            *index_arguments,
            "--name-only",
            "--no-renames",
            base_commit,
            "--",
            *roots,
            text=True,
        )
        assert isinstance(output, str)
        changed.update(line for line in output.splitlines() if line)
    return changed


def canonical_working_mismatches(
    repo_root: Path,
    base_commit: str,
    paths: Iterable[str],
) -> set[str]:
    """Compare clean-filtered working files without trusting index flags."""

    mismatches: set[str] = set()
    for relative in sorted(paths):
        path = repo_root / Path(relative)
        if not path.is_file():
            continue
        expected = _git(
            repo_root,
            "rev-parse",
            f"{base_commit}:{relative}",
            text=True,
        )
        actual = _git(
            repo_root,
            "hash-object",
            f"--path={relative}",
            str(path),
            text=True,
        )
        assert isinstance(expected, str)
        assert isinstance(actual, str)
        if expected.strip() != actual.strip():
            mismatches.add(relative)
    return mismatches


def working_digest(repo_root: Path, paths: Iterable[str]) -> tuple[str, dict[str, str], list[str]]:
    hashes: dict[str, str] = {}
    missing: list[str] = []
    payload = bytearray()
    for relative in sorted(paths):
        path = repo_root / Path(relative)
        if not path.is_file():
            missing.append(relative)
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        hashes[relative] = digest
        payload.extend(relative.encode("utf-8"))
        payload.extend(b"\0")
        payload.extend(digest.encode("ascii"))
        payload.extend(b"\n")
    return hashlib.sha256(payload).hexdigest(), hashes, missing


def verify(repo_root: Path, manifest_path: Path) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "ai-dev-flow/dashboard-artifact-manifest/v1":
        raise ValueError("unsupported artifact manifest schema")
    if manifest.get("algorithm") != "sha256":
        raise ValueError("unsupported artifact manifest algorithm")
    base_commit = str(manifest["base_commit"])
    roots = tuple(str(item) for item in manifest["roots"])
    paths = baseline_paths(repo_root, base_commit, roots)
    current_paths = working_paths(repo_root, roots)
    expected_root, expected_hashes = baseline_digest(repo_root, base_commit, paths)
    actual_root, actual_hashes, missing = working_digest(repo_root, paths)
    tracked_changes = changed_paths(repo_root, base_commit, roots)
    working_mismatches = canonical_working_mismatches(repo_root, base_commit, paths)
    added = sorted(set(current_paths) - set(paths))
    changed = sorted(
        relative
        for relative in paths
        if relative in tracked_changes or relative in working_mismatches
    )
    if not changed and not missing:
        # A Git-clean checkout is byte-equivalent after clean filters even when
        # its physical line endings differ because of core.autocrlf.
        actual_root = expected_root
        actual_hashes = dict(expected_hashes)
    expected_count = int(manifest["file_count"])
    recorded_root = str(manifest["root_digest"])
    ok = (
        len(paths) == expected_count
        and expected_root == recorded_root
        and actual_root == recorded_root
        and not missing
        and not changed
        and not added
    )
    return {
        "schema_version": "ai-dev-flow/dashboard-artifact-verification/v1",
        "ok": ok,
        "base_commit": base_commit,
        "file_count": len(paths),
        "expected_file_count": expected_count,
        "recorded_root_digest": recorded_root,
        "baseline_root_digest": expected_root,
        "working_root_digest": actual_root,
        "missing": missing,
        "changed": changed,
        "added": added,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=".")
    parser.add_argument(
        "--manifest",
        default=str(Path(__file__).with_name(MANIFEST_NAME)),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    report = verify(Path(args.project_root).resolve(), Path(args.manifest).resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
