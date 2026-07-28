"""Small strict JSON Schema validator for the versioned dashboard contracts.

The project intentionally has no third-party dependencies.  This module
implements only the frozen JSON Schema subset used by dashboard/contracts.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


class ValidationError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = tuple(errors)


def _default_schema_path() -> Path:
    return Path(__file__).resolve().parents[4] / "contracts" / "dashboard-contracts-v1.schema.json"


def load_schema(schema_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(schema_path) if schema_path else _default_schema_path()
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValidationError(["$: schema root must be an object"])
    return value


def validate_contract(
    value: Any,
    *,
    schema_path: str | Path | None = None,
) -> None:
    schema = load_schema(schema_path)
    errors: list[str] = []
    _validate(value, schema, schema, "$", errors)
    if errors:
        raise ValidationError(errors)


def validate_sse_transcript(
    transcript: bytes | str,
    *,
    schema_path: str | Path | None = None,
) -> None:
    content = transcript.encode("utf-8") if isinstance(transcript, str) else transcript
    errors: list[str] = []
    if b"\r" in content:
        errors.append("$: SSE transcript must be LF-only")
    if not content.startswith(b"retry: 2000\n"):
        errors.append("$: SSE transcript must begin with retry: 2000")
    if not content.endswith(b"\n\n"):
        errors.append("$: SSE event must end with two LF bytes")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise ValidationError(["$: SSE transcript is not UTF-8"])
    blocks = [block for block in text.split("\n\n") if block]
    if not blocks:
        errors.append("$: SSE transcript contains no snapshot event")
    for index, block in enumerate(blocks):
        fields: dict[str, str] = {}
        for line_number, line in enumerate(block.split("\n")):
            if index == 0 and line_number == 0 and line == "retry: 2000":
                continue
            if line.startswith("retry:"):
                errors.append(f"$[{index}]: retry is only allowed as the first line")
                continue
            if ": " not in line:
                errors.append(f"$[{index}]: malformed SSE line")
                continue
            key, raw = line.split(": ", 1)
            if key in fields:
                errors.append(f"$[{index}]: duplicate SSE field {key}")
            fields[key] = raw
        expected_fields = {"event", "id", "data"}
        actual_fields = set(fields)
        for key in sorted(expected_fields - actual_fields):
            errors.append(f"$[{index}]: missing SSE field {key}")
        for key in sorted(actual_fields - expected_fields):
            errors.append(f"$[{index}]: unexpected SSE field {key}")
        if fields.get("event") != "snapshot":
            errors.append(f"$[{index}].event: expected snapshot")
        if not re.fullmatch(r"[0-9a-f]{64}", fields.get("id", "")):
            errors.append(f"$[{index}].id: expected a lowercase SHA256")
        try:
            payload = json.loads(fields.get("data", ""))
            validate_contract(payload, schema_path=schema_path)
            if not isinstance(payload, dict) or payload.get("schema_version") != "ai-dev-flow/dashboard-event/v1":
                errors.append(f"$[{index}].data: expected dashboard event v1")
            elif fields.get("id") != payload.get("revision"):
                errors.append(f"$[{index}]: id must equal data.revision")
        except (json.JSONDecodeError, ValidationError) as exc:
            errors.append(f"$[{index}].data: {exc}")
    if errors:
        raise ValidationError(errors)


def _validate(value: Any, schema: dict[str, Any], root: dict[str, Any], path: str, errors: list[str]) -> None:
    if "$ref" in schema:
        target: Any = root
        reference = schema["$ref"]
        if not isinstance(reference, str) or not reference.startswith("#/"):
            errors.append(f"{path}: unsupported $ref")
            return
        for segment in reference[2:].split("/"):
            target = target.get(segment) if isinstance(target, dict) else None
        if not isinstance(target, dict):
            errors.append(f"{path}: unresolved $ref {reference}")
            return
        _validate(value, target, root, path, errors)
        return

    if "oneOf" in schema:
        matching = 0
        branch_errors: list[list[str]] = []
        for branch in schema["oneOf"]:
            candidate: list[str] = []
            _validate(value, branch, root, path, candidate)
            branch_errors.append(candidate)
            if not candidate:
                matching += 1
        if matching != 1:
            errors.append(f"{path}: expected exactly one oneOf branch, matched {matching}")
            if matching == 0 and branch_errors:
                errors.extend(min(branch_errors, key=len))

    expected_type = schema.get("type")
    if expected_type is not None:
        allowed = expected_type if isinstance(expected_type, list) else [expected_type]
        if not any(_type_matches(value, item) for item in allowed):
            errors.append(f"{path}: expected type {'|'.join(allowed)}")
            return

    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: expected constant {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: invalid enum value {value!r}")
    if isinstance(value, str):
        if "pattern" in schema and re.fullmatch(schema["pattern"], value) is None:
            errors.append(f"{path}: value does not match pattern")
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path}: string is shorter than minLength")
    if isinstance(value, int) and not isinstance(value, bool) and "minimum" in schema:
        if value < schema["minimum"]:
            errors.append(f"{path}: value is below minimum")

    if isinstance(value, dict):
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append(f"{path}: missing required property {key}")
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in properties:
                    errors.append(f"{path}: additional property {key}")
        for key, item in value.items():
            if key in properties:
                _validate(item, properties[key], root, f"{path}.{key}", errors)
            elif isinstance(schema.get("additionalProperties"), dict):
                _validate(item, schema["additionalProperties"], root, f"{path}.{key}", errors)

    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: array is shorter than minItems")
        if schema.get("uniqueItems") and len({json.dumps(item, sort_keys=True) for item in value}) != len(value):
            errors.append(f"{path}: array items are not unique")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                _validate(item, item_schema, root, f"{path}[{index}]", errors)


def _type_matches(value: Any, expected: str) -> bool:
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
    }.get(expected, False)
