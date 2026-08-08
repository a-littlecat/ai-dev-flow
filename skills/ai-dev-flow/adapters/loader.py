"""Strict read-only loader for Harness capability adapters."""

import json
import pathlib
import re
from types import MappingProxyType


FIELDS = {
    "adapter_id", "verified_at", "skill_loading", "read_files", "write_files",
    "run_commands", "git", "context_isolation", "write_isolation", "subagents",
    "approval_gate", "runtime_hooks", "session_events", "preferred_review_recipe",
    "fallback_review_recipe", "runtime_sync_method", "version_sensitive_notes",
}
ENUMS = {
    "skill_loading": {"native", "markdown", "unsupported"},
    "context_isolation": {"native", "independent_process", "independent_session", "none"},
    "write_isolation": {"native_read_only", "sandbox_read_only", "readonly_copy", "none"},
    "subagents": {"native", "opaque", "none"},
    "approval_gate": {"native", "manual", "none"},
    "runtime_hooks": {"native", "plugin", "none"},
    "session_events": {"native", "adapter", "manual", "none"},
    "preferred_review_recipe": {"R1", "R2", "R3", "R4", "R5"},
    "fallback_review_recipe": {"R1", "R2", "R3", "R4", "R5"},
}
BOOLEAN_FIELDS = {"read_files", "write_files", "run_commands", "git"}
ADAPTER_ID = re.compile(r"^[a-z][a-z0-9-]*$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class AdapterLoadError(ValueError):
    pass


def load_adapter(path):
    source = pathlib.Path(path)
    try:
        value = json.loads(source.read_text(encoding="utf-8", errors="strict"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AdapterLoadError(f"cannot load adapter {source}: {exc}") from exc
    if not isinstance(value, dict) or set(value) != FIELDS:
        raise AdapterLoadError("adapter must contain exactly the required fields")
    if not isinstance(value["adapter_id"], str) or ADAPTER_ID.fullmatch(value["adapter_id"]) is None:
        raise AdapterLoadError("adapter_id is invalid")
    if not isinstance(value["verified_at"], str) or DATE.fullmatch(value["verified_at"]) is None:
        raise AdapterLoadError("verified_at must be YYYY-MM-DD")
    for field in BOOLEAN_FIELDS:
        if not isinstance(value[field], bool):
            raise AdapterLoadError(f"{field} must be boolean")
    for field, allowed in ENUMS.items():
        if value[field] not in allowed:
            raise AdapterLoadError(f"{field} has an unsupported value")
    for field in ("runtime_sync_method", "version_sensitive_notes"):
        if not isinstance(value[field], str) or not value[field].strip():
            raise AdapterLoadError(f"{field} must be a non-empty string")
    return MappingProxyType(value)


def load_adapter_directory(path):
    root = pathlib.Path(path)
    adapters = tuple(load_adapter(item) for item in sorted(root.glob("*.json")))
    ids = [item["adapter_id"] for item in adapters]
    if len(ids) != len(set(ids)):
        raise AdapterLoadError("adapter_id values must be unique")
    return adapters


def _can_review(adapter):
    return (
        adapter is not None
        and adapter["read_files"] is True
        and adapter["context_isolation"] != "none"
        and adapter["write_isolation"]
        in {"native_read_only", "sandbox_read_only", "readonly_copy"}
    )


def select_review_recipe(
    adapter,
    *,
    frozen_diff=False,
    stable_finding_ids=False,
    cross_harness_authorized=False,
    external_adapter=None,
):
    """Select by proven capability and invocation evidence, never adapter_id."""

    if not frozen_diff or not stable_finding_ids:
        return "R5"

    if _can_review(adapter):
        context = adapter["context_isolation"]
        write = adapter["write_isolation"]
        if context == "native" and write == "native_read_only":
            return "R1"
        if context == "independent_process" and write == "sandbox_read_only":
            return "R2"
        if context == "independent_session" and write == "readonly_copy":
            return "R3"
    if (
        cross_harness_authorized
        and _can_review(external_adapter)
    ):
        return "R4"
    return "R5"
