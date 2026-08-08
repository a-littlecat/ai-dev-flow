"""Safe, atomic and project-isolated Runtime Session v1 storage."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import secrets
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable

from ai_dev_flow_dashboard.core.canonical import canonical_bytes


SCHEMA_VERSION = "adf/runtime-session/v1"
PHASES = frozenset(
    {
        "planning",
        "implementing",
        "validating",
        "reviewing",
        "repairing",
        "waiting_user",
        "blocked",
        "done",
    }
)
SESSION_ID_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]{0,127})")
TOKEN_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]{0,127})")
FIELDS = frozenset(
    {
        "schema_version",
        "project_id",
        "session_id",
        "task_id",
        "harness_id",
        "phase",
        "next_step",
        "status_summary",
        "branch",
        "worktree",
        "started_at",
        "updated_at",
        "stale_after_seconds",
        "ended_at",
        "end_reason",
    }
)
MAX_CLOCK_SKEW_SECONDS = 300


class RuntimeSessionError(ValueError):
    """Runtime session input or storage violates the frozen contract."""


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _timestamp(value: dt.datetime) -> str:
    value = value.astimezone(dt.timezone.utc).replace(microsecond=0)
    return value.isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: Any) -> dt.datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise RuntimeSessionError("runtime timestamp must be UTC with Z suffix")
    try:
        parsed = dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise RuntimeSessionError("runtime timestamp is invalid") from exc
    if parsed.utcoffset() != dt.timedelta(0):
        raise RuntimeSessionError("runtime timestamp must be UTC")
    return parsed


def canonical_project_id(project_root: str | Path) -> str:
    root = Path(project_root).expanduser().resolve(strict=True)
    if not (root / "docs" / "tasks").is_dir():
        raise RuntimeSessionError("project root must contain docs/tasks")
    canonical = os.path.normcase(str(root)).replace("\\", "/")
    return hashlib.sha256(canonical.encode("utf-8", errors="strict")).hexdigest()


def default_runtime_root() -> Path:
    override = os.environ.get("ADF_RUNTIME_ROOT")
    if override:
        candidate = Path(override).expanduser()
    elif os.environ.get("LOCALAPPDATA"):
        candidate = Path(os.environ["LOCALAPPDATA"]) / "ai-dev-flow" / "runtime"
    else:
        candidate = Path(tempfile.gettempdir()) / "ai-dev-flow-runtime"
    if ".." in candidate.parts:
        raise RuntimeSessionError("runtime root must not contain parent traversal")
    return candidate.resolve(strict=False)


def _plain_text(value: Any, field: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise RuntimeSessionError(f"{field} must be a string")
    if (not allow_empty and not value.strip()) or len(value) > 1000:
        raise RuntimeSessionError(f"{field} has invalid length")
    if any(ord(character) < 32 for character in value):
        raise RuntimeSessionError(f"{field} contains control characters")
    return value.strip()


class RuntimeSessionStore:
    def __init__(
        self,
        project_root: str | Path,
        *,
        runtime_root: str | Path | None = None,
        now: Callable[[], dt.datetime] = _utc_now,
    ) -> None:
        self.project_root = Path(project_root).expanduser().resolve(strict=True)
        self.project_id = canonical_project_id(self.project_root)
        candidate = Path(runtime_root).expanduser() if runtime_root else default_runtime_root()
        if ".." in candidate.parts:
            raise RuntimeSessionError("runtime root must not contain parent traversal")
        if candidate.exists() and self._is_link_or_reparse(candidate):
            raise RuntimeSessionError("runtime root must not be a link or reparse point")
        self.runtime_root = candidate.resolve(strict=False)
        try:
            self.runtime_root.relative_to(self.project_root)
        except ValueError:
            pass
        else:
            raise RuntimeSessionError("runtime root must be outside the project")
        self.project_dir = self.runtime_root / self.project_id
        self.sessions_dir = self.project_dir / "sessions"
        self._now = now

    def start(
        self,
        *,
        session_id: str,
        task_id: str,
        harness_id: str,
        phase: str,
        next_step: str,
        status_summary: str = "",
        branch: str | None = None,
        worktree: str | None = None,
        stale_after_seconds: int = 180,
        replace: bool = False,
    ) -> dict[str, Any]:
        session_id = self._session_id(session_id)
        path = self._session_path(session_id)
        now = _timestamp(self._now())
        payload = {
            "schema_version": SCHEMA_VERSION,
            "project_id": self.project_id,
            "session_id": session_id,
            "task_id": self._token(task_id, "task_id"),
            "harness_id": self._token(harness_id, "harness_id"),
            "phase": self._phase(phase),
            "next_step": _plain_text(next_step, "next_step"),
            "status_summary": _plain_text(status_summary, "status_summary", allow_empty=True),
            "branch": self._optional_text(branch, "branch"),
            "worktree": self._worktree(worktree),
            "started_at": now,
            "updated_at": now,
            "stale_after_seconds": self._stale_after(stale_after_seconds),
            "ended_at": None,
            "end_reason": None,
        }
        with self._mutation_lock(session_id):
            existing = self._read_path(path) if path.exists() else None
            if existing is not None and not replace:
                raise RuntimeSessionError(
                    "session already exists; use --replace explicitly"
                )
            if existing is not None and existing["project_id"] != self.project_id:
                raise RuntimeSessionError("cannot replace a session from another project")
            self._write(path, self._validate(payload))
        return payload

    def update(
        self,
        session_id: str,
        *,
        phase: str | None = None,
        next_step: str | None = None,
        status_summary: str | None = None,
    ) -> dict[str, Any]:
        session_id = self._session_id(session_id)
        with self._mutation_lock(session_id):
            payload = self._required(session_id)
            if payload["ended_at"] is not None:
                raise RuntimeSessionError("ended session cannot be updated")
            if phase is not None:
                payload["phase"] = self._phase(phase)
            if next_step is not None:
                payload["next_step"] = _plain_text(next_step, "next_step")
            if status_summary is not None:
                payload["status_summary"] = _plain_text(
                    status_summary, "status_summary", allow_empty=True
                )
            payload["updated_at"] = _timestamp(self._now())
            self._write(
                self._session_path(payload["session_id"]), self._validate(payload)
            )
        return payload

    def wait(self, session_id: str, reason: str) -> dict[str, Any]:
        return self.update(
            session_id,
            phase="waiting_user",
            next_step=_plain_text(reason, "reason"),
            status_summary="等待用户处理",
        )

    def end(self, session_id: str, reason: str) -> dict[str, Any]:
        session_id = self._session_id(session_id)
        with self._mutation_lock(session_id):
            payload = self._required(session_id)
            if payload["ended_at"] is not None:
                return payload
            now = _timestamp(self._now())
            payload["phase"] = "done"
            payload["updated_at"] = now
            payload["ended_at"] = now
            payload["end_reason"] = _plain_text(reason, "reason")
            self._write(
                self._session_path(payload["session_id"]), self._validate(payload)
            )
        return payload

    def list(self) -> list[dict[str, Any]]:
        if not self.sessions_dir.exists():
            return []
        self._assert_safe_existing(self.runtime_root)
        self._assert_safe_existing(self.project_dir)
        self._assert_safe_existing(self.sessions_dir)
        result = []
        for path in sorted(self.sessions_dir.glob("*.json")):
            if self._is_link_or_reparse(path) or path.parent != self.sessions_dir:
                result.append(self._invalid(path.stem, "UNSAFE_SESSION_PATH"))
                continue
            try:
                payload = self._read_path(path)
                result.append({**payload, "freshness": self._freshness(payload)})
            except (OSError, UnicodeError, json.JSONDecodeError, RuntimeSessionError):
                result.append(self._invalid(path.stem, "INVALID_SESSION"))
        return sorted(
            result,
            key=lambda item: (item.get("updated_at") or "", item["session_id"]),
            reverse=True,
        )

    def _freshness(self, payload: dict[str, Any]) -> str:
        if payload["ended_at"] is not None:
            return "ended"
        age = (self._now() - _parse_timestamp(payload["updated_at"])).total_seconds()
        return "live" if age <= payload["stale_after_seconds"] else "stale"

    def _required(self, session_id: str) -> dict[str, Any]:
        path = self._session_path(self._session_id(session_id))
        if not path.is_file() or self._is_link_or_reparse(path):
            raise RuntimeSessionError("session does not exist")
        return self._read_path(path)

    def _read_path(self, path: Path) -> dict[str, Any]:
        if self._is_link_or_reparse(path):
            raise RuntimeSessionError("session file must not be a symlink")
        payload = self._validate(
            json.loads(path.read_text(encoding="utf-8", errors="strict"))
        )
        if payload["session_id"] != path.stem:
            raise RuntimeSessionError("session_id does not match its file name")
        return payload

    def _validate(self, payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict) or set(payload) != FIELDS:
            raise RuntimeSessionError("runtime session fields are invalid")
        if payload.get("schema_version") != SCHEMA_VERSION:
            raise RuntimeSessionError("runtime session schema is invalid")
        if payload.get("project_id") != self.project_id:
            raise RuntimeSessionError("runtime session project binding is invalid")
        payload = dict(payload)
        payload["session_id"] = self._session_id(payload["session_id"])
        payload["task_id"] = self._token(payload["task_id"], "task_id")
        payload["harness_id"] = self._token(payload["harness_id"], "harness_id")
        payload["phase"] = self._phase(payload["phase"])
        payload["next_step"] = _plain_text(payload["next_step"], "next_step")
        payload["status_summary"] = _plain_text(
            payload["status_summary"], "status_summary", allow_empty=True
        )
        payload["branch"] = self._optional_text(payload["branch"], "branch")
        payload["worktree"] = self._worktree(payload["worktree"])
        payload["stale_after_seconds"] = self._stale_after(payload["stale_after_seconds"])
        started = _parse_timestamp(payload["started_at"])
        updated = _parse_timestamp(payload["updated_at"])
        latest_allowed = self._now() + dt.timedelta(seconds=MAX_CLOCK_SKEW_SECONDS)
        if started > latest_allowed or updated > latest_allowed:
            raise RuntimeSessionError("runtime timestamp is too far in the future")
        if updated < started:
            raise RuntimeSessionError("updated_at precedes started_at")
        if payload["ended_at"] is None:
            if payload["end_reason"] is not None:
                raise RuntimeSessionError("active session cannot have end_reason")
        else:
            ended = _parse_timestamp(payload["ended_at"])
            if ended > latest_allowed:
                raise RuntimeSessionError("runtime end timestamp is too far in the future")
            if ended < updated or not isinstance(payload["end_reason"], str):
                raise RuntimeSessionError("ended session time or reason is invalid")
            payload["end_reason"] = _plain_text(payload["end_reason"], "end_reason")
        return payload

    def _write(self, path: Path, payload: dict[str, Any]) -> None:
        self._prepare_directories()
        if self._is_link_or_reparse(path):
            raise RuntimeSessionError("refusing to replace a session symlink")
        temporary = self.sessions_dir / f".{path.stem}.{secrets.token_hex(8)}.tmp"
        try:
            with temporary.open("xb") as handle:
                handle.write(canonical_bytes(payload))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if temporary.exists():
                temporary.unlink()

    def _prepare_directories(self) -> None:
        if not self.runtime_root.exists():
            self.runtime_root.mkdir(parents=True, exist_ok=False)
        self._assert_safe_existing(self.runtime_root)
        if not self.project_dir.exists():
            self.project_dir.mkdir(exist_ok=False)
        self._assert_safe_existing(self.project_dir)
        if not self.sessions_dir.exists():
            self.sessions_dir.mkdir(exist_ok=False)
        self._assert_safe_existing(self.sessions_dir)
        if self.sessions_dir.resolve() != self.sessions_dir:
            raise RuntimeSessionError("runtime session directory escaped its root")

    @classmethod
    def _assert_safe_existing(cls, path: Path) -> None:
        if cls._is_link_or_reparse(path) or not path.is_dir():
            raise RuntimeSessionError("runtime directory must be a real directory")

    @staticmethod
    def _is_link_or_reparse(path: Path) -> bool:
        is_junction = getattr(path, "is_junction", None)
        if path.is_symlink() or bool(is_junction and is_junction()):
            return True
        try:
            attributes = getattr(path.lstat(), "st_file_attributes", 0)
        except OSError:
            return False
        return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))

    @contextmanager
    def _mutation_lock(self, session_id: str):
        self._prepare_directories()
        lock = self.sessions_dir / f".{session_id}.lock"
        flags = os.O_RDWR
        if hasattr(os, "O_BINARY"):
            flags |= os.O_BINARY
        descriptor = None
        try:
            if self._is_link_or_reparse(lock):
                raise RuntimeSessionError("session lock must not be a reparse point")
            try:
                descriptor = os.open(lock, flags | os.O_CREAT | os.O_EXCL, 0o600)
                os.write(descriptor, b"0")
                os.fsync(descriptor)
            except FileExistsError:
                descriptor = os.open(lock, flags)
            with os.fdopen(descriptor, "r+b", closefd=True) as handle:
                descriptor = None
                if self._is_link_or_reparse(lock) or not lock.is_file():
                    raise RuntimeSessionError("session lock must be a real file")
                handle.seek(0)
                self._acquire_file_lock(handle)
                try:
                    yield
                finally:
                    self._release_file_lock(handle)
        finally:
            if descriptor is not None:
                os.close(descriptor)

    @staticmethod
    def _acquire_file_lock(handle) -> None:
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeSessionError("session mutation is already in progress") from exc

    @staticmethod
    def _release_file_lock(handle) -> None:
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _session_path(self, session_id: str) -> Path:
        path = self.sessions_dir / f"{session_id}.json"
        if path.parent != self.sessions_dir:
            raise RuntimeSessionError("session path escaped runtime root")
        return path

    @staticmethod
    def _session_id(value: Any) -> str:
        if not isinstance(value, str) or SESSION_ID_RE.fullmatch(value) is None:
            raise RuntimeSessionError("session_id is invalid")
        return value

    @staticmethod
    def _token(value: Any, field: str) -> str:
        if not isinstance(value, str) or TOKEN_RE.fullmatch(value) is None:
            raise RuntimeSessionError(f"{field} is invalid")
        return value

    @staticmethod
    def _phase(value: Any) -> str:
        if value not in PHASES:
            raise RuntimeSessionError("phase is invalid")
        return value

    @staticmethod
    def _stale_after(value: Any) -> int:
        if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 86400:
            raise RuntimeSessionError("stale_after_seconds is invalid")
        return value

    @staticmethod
    def _optional_text(value: Any, field: str) -> str | None:
        return None if value is None else _plain_text(value, field)

    @staticmethod
    def _worktree(value: Any) -> str | None:
        if value is None:
            return None
        text = _plain_text(value, "worktree")
        path = Path(text).expanduser()
        if not path.is_absolute() or ".." in path.parts:
            raise RuntimeSessionError("worktree must be an absolute normalized path")
        return path.resolve(strict=False).as_posix()

    def _invalid(self, session_id: str, code: str) -> dict[str, Any]:
        safe_id = session_id if SESSION_ID_RE.fullmatch(session_id) else "invalid-session"
        return {
            "schema_version": SCHEMA_VERSION,
            "project_id": self.project_id,
            "session_id": safe_id,
            "task_id": None,
            "harness_id": None,
            "phase": None,
            "next_step": "需要补充证据",
            "status_summary": "运行时会话无效",
            "branch": None,
            "worktree": None,
            "started_at": None,
            "updated_at": None,
            "stale_after_seconds": None,
            "ended_at": None,
            "end_reason": None,
            "freshness": "invalid",
            "error_codes": [code],
        }
