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


def canonical_working_hashes(
    repo_root: Path,
    paths: Iterable[str],
) -> tuple[dict[str, str], list[str]]:
    """Return Git clean-filtered blob identities, independent of checkout EOL."""

    hashes: dict[str, str] = {}
    missing: list[str] = []
    for relative in sorted(paths):
        path = repo_root / Path(relative)
        if not path.is_file():
            missing.append(relative)
            continue
        output = _git(
            repo_root,
            "hash-object",
            f"--path={relative}",
            str(path),
            text=True,
        )
        assert isinstance(output, str)
        hashes[relative] = output.strip()
    return hashes, missing


def index_blob_hashes(
    repo_root: Path,
    paths: Iterable[str],
) -> tuple[dict[str, str], list[str]]:
    """Return stage-0 Git index blobs and paths with unmerged index stages."""

    requested = tuple(sorted(paths))
    if not requested:
        return {}, []
    output = _git(
        repo_root,
        "ls-files",
        "--stage",
        "-z",
        "--",
        *requested,
    )
    assert isinstance(output, bytes)
    hashes: dict[str, str] = {}
    unmerged: set[str] = set()
    for record in output.split(b"\0"):
        if not record:
            continue
        metadata, raw_path = record.split(b"\t", 1)
        _mode, digest, stage = metadata.decode("ascii").split()
        relative = raw_path.decode("utf-8", errors="strict")
        if stage != "0":
            unmerged.add(relative)
            continue
        hashes[relative] = digest
    return hashes, sorted(unmerged)


def baseline_blob_hashes(
    repo_root: Path,
    base_commit: str,
    paths: Iterable[str],
) -> dict[str, str]:
    """Return Git object identities for candidate paths present at the base."""

    hashes: dict[str, str] = {}
    for relative in sorted(paths):
        output = _git(
            repo_root,
            "rev-parse",
            f"{base_commit}:{relative}",
            text=True,
        )
        assert isinstance(output, str)
        hashes[relative] = output.strip()
    return hashes


def digest_from_hashes(hashes: dict[str, str]) -> str:
    payload = bytearray()
    for relative, digest in sorted(hashes.items()):
        payload.extend(relative.encode("utf-8"))
        payload.extend(b"\0")
        payload.extend(digest.encode("ascii"))
        payload.extend(b"\n")
    return hashlib.sha256(payload).hexdigest()


def verify(repo_root: Path, manifest_path: Path) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    schema_version = manifest.get("schema_version")
    if schema_version not in {
        "ai-dev-flow/dashboard-artifact-manifest/v1",
        "ai-dev-flow/dashboard-artifact-manifest/v2",
    }:
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
    candidate_paths: list[str] = []
    candidate_mismatches: list[str] = []
    candidate_index_mismatches: list[str] = []
    baseline_file_count = len(paths)
    recorded_baseline_root = recorded_root
    baseline_preserved = (
        baseline_file_count == expected_count
        and expected_root == recorded_baseline_root
    )
    accepted_ok = (
        baseline_preserved
        and actual_root == recorded_root
        and not missing
        and not changed
        and not added
    )
    candidate_consistent: bool | None = None
    candidate_root: str | None = None
    if schema_version == "ai-dev-flow/dashboard-artifact-manifest/v2":
        candidate = manifest.get("candidate")
        if not isinstance(candidate, dict) or not isinstance(candidate.get("files"), dict):
            raise ValueError("v2 artifact manifest requires candidate.files")
        if candidate.get("hash_algorithm") != "git-blob":
            raise ValueError("v2 candidate hash_algorithm must be git-blob")
        candidate_files = {
            str(relative): str(digest)
            for relative, digest in candidate["files"].items()
        }
        candidate_paths = sorted(candidate_files)
        root_prefixes = tuple(root.rstrip("/") + "/" for root in roots)
        if any(
            not relative.startswith(root_prefixes)
            or Path(relative).is_absolute()
            or ".." in Path(relative).parts
            for relative in candidate_paths
        ):
            raise ValueError("candidate path escapes protected roots")
        candidate_actual_hashes, candidate_missing = canonical_working_hashes(
            repo_root,
            candidate_paths,
        )
        candidate_mismatches = sorted(
            relative
            for relative, expected_hash in candidate_files.items()
            if candidate_actual_hashes.get(relative) != expected_hash
        )
        indexed_hashes, unmerged_paths = index_blob_hashes(
            repo_root,
            candidate_paths,
        )
        baseline_candidates = sorted(set(candidate_paths) & set(paths))
        base_blob_hashes = baseline_blob_hashes(
            repo_root,
            base_commit,
            baseline_candidates,
        )
        candidate_index_mismatches = sorted(
            set(unmerged_paths)
            | {
                relative
                for relative, candidate_hash in candidate_files.items()
                if (
                    relative in base_blob_hashes
                    and indexed_hashes.get(relative)
                    not in {base_blob_hashes[relative], candidate_hash}
                )
                or (
                    relative not in base_blob_hashes
                    and relative in indexed_hashes
                    and indexed_hashes[relative] != candidate_hash
                )
            }
        )
        recorded_baseline_root = str(manifest["baseline_root_digest"])
        baseline_preserved = (
            baseline_file_count == expected_count
            and expected_root == recorded_baseline_root
        )
        candidate_root = digest_from_hashes(candidate_files)
        actual_change_set = set(changed) | set(added)
        candidate_consistent = (
            baseline_preserved
            and int(candidate.get("file_count", -1)) == len(candidate_files)
            and candidate_root == str(candidate.get("root_digest"))
            and set(candidate_paths) == actual_change_set
            and not missing
            and not candidate_missing
            and not candidate_mismatches
            and not candidate_index_mismatches
        )
        accepted_ok = (
            baseline_preserved
            and not missing
            and not changed
            and not added
        )
    ok = accepted_ok
    return {
        "schema_version": "ai-dev-flow/dashboard-artifact-verification/v1",
        "ok": ok,
        "accepted_ok": accepted_ok,
        "baseline_preserved": baseline_preserved,
        "candidate_consistent": candidate_consistent,
        "base_commit": base_commit,
        "file_count": len(current_paths),
        "expected_file_count": expected_count,
        "recorded_root_digest": recorded_root,
        "baseline_root_digest": expected_root,
        "working_root_digest": actual_root,
        "missing": missing,
        "changed": changed,
        "added": added,
        "candidate_paths": candidate_paths,
        "candidate_root_digest": candidate_root,
        "candidate_mismatches": candidate_mismatches,
        "candidate_index_mismatches": candidate_index_mismatches,
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
