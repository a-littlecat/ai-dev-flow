"""Canonical JSON and stable SHA256 helpers."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from typing import Any

from .models import primitive


def _nfc(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, dict):
        return {_nfc(str(key)): _nfc(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_nfc(item) for item in value]
    return value


def canonical_bytes(value: Any) -> bytes:
    """Serialize a logical value as NFC, compact, key-sorted UTF-8 JSON."""

    normalized = _nfc(primitive(value))
    return json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def snapshot_revision(snapshot: Any) -> str:
    """Hash snapshot semantics while excluding time and the revision itself."""

    payload = dict(primitive(snapshot))
    payload.pop("revision", None)
    payload.pop("generated_at", None)
    return canonical_sha256(payload)


def stable_text_id(*parts: str) -> str:
    payload = b"\x00".join(unicodedata.normalize("NFC", part).encode("utf-8") for part in parts)
    return hashlib.sha256(payload).hexdigest()
