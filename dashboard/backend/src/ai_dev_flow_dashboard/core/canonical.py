"""Canonical JSON and stable SHA256 helpers."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Mapping
from dataclasses import is_dataclass
from pathlib import Path
from typing import Any

from .models import primitive


def _json_ready(value: Any) -> Any:
    """Convert domain values once while normalizing object keys."""

    if is_dataclass(value):
        # primitive() owns the public wire-field selection, including
        # metadata={"wire": False}.  Reuse it here so every canonical
        # dataclass path has exactly the same shape as the public payload.
        return _json_ready(primitive(value))
    if isinstance(value, dict):
        return {
            unicodedata.normalize("NFC", str(key)): _json_ready(item)
            for key, item in value.items()
        }
    if isinstance(value, Mapping):
        return {
            unicodedata.normalize("NFC", str(key)): _json_ready(item)
            for key, item in value.items()
        }
    if isinstance(value, (tuple, list)):
        return [_json_ready(item) for item in value]
    if isinstance(value, Path):
        return value.as_posix()
    return value


def _supports_direct_json(value: Any) -> bool:
    """Return whether JSON can encode the tree with canonical ASCII keys."""

    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            if any(not isinstance(key, str) or not key.isascii() for key in item):
                return False
            pending.extend(item.values())
        elif isinstance(item, (tuple, list)):
            pending.extend(item)
        elif is_dataclass(item) or isinstance(item, (Path, Mapping)):
            return False
    return True


def canonical_bytes(value: Any) -> bytes:
    """Serialize a logical value as NFC, compact, key-sorted UTF-8 JSON."""

    schema_version = value.get("schema_version") if isinstance(value, dict) else None
    trusted_wire = (
        isinstance(schema_version, str)
        and schema_version.startswith("ai-dev-flow/dashboard-")
    )
    prepared = value if trusted_wire or _supports_direct_json(value) else _json_ready(value)
    encoded = json.dumps(
        prepared,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return unicodedata.normalize("NFC", encoded).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def snapshot_revision(snapshot: Any) -> str:
    """Hash snapshot semantics while excluding time and the revision itself."""

    payload = dict(snapshot) if isinstance(snapshot, dict) else dict(primitive(snapshot))
    payload.pop("revision", None)
    payload.pop("generated_at", None)
    return canonical_sha256(payload)


def stable_text_id(*parts: str) -> str:
    payload = b"\x00".join(unicodedata.normalize("NFC", part).encode("utf-8") for part in parts)
    return hashlib.sha256(payload).hexdigest()
