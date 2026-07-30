"""Small strict JSON Schema validator for the versioned dashboard contracts.

The project intentionally has no third-party dependencies.  This module
implements only the frozen JSON Schema subset used by dashboard/contracts.
"""

from __future__ import annotations

import json
import hashlib
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from .canonical import canonical_bytes


class ValidationError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = tuple(errors)


def _default_schema_path() -> Path:
    return Path(__file__).resolve().parents[4] / "contracts" / "dashboard-contracts-v1.schema.json"


def contract_schema_path(schema_path: str | Path | None = None) -> Path:
    return (Path(schema_path) if schema_path else _default_schema_path()).resolve()


def _schema_bytes(path: Path) -> tuple[bytes, str]:
    content = path.read_bytes()
    return content, hashlib.sha256(content).hexdigest()


def contract_schema_digest(schema_path: str | Path | None = None) -> str:
    return _schema_bytes(contract_schema_path(schema_path))[1]


def load_schema(schema_path: str | Path | None = None) -> dict[str, Any]:
    content, digest = _schema_bytes(contract_schema_path(schema_path))
    value = _load_schema_cached(digest, content)
    if not isinstance(value, dict):
        raise ValidationError(["$: schema root must be an object"])
    return value


@lru_cache(maxsize=8)
def _load_schema_cached(digest: str, content: bytes) -> Any:
    del digest
    return json.loads(content.decode("utf-8", errors="strict"))


def validate_contract(
    value: Any,
    *,
    schema_path: str | Path | None = None,
    schema_content: bytes | None = None,
) -> None:
    if schema_content is None:
        content, digest = _schema_bytes(contract_schema_path(schema_path))
    else:
        content = bytes(schema_content)
        digest = hashlib.sha256(content).hexdigest()
    schema = _load_schema_cached(digest, content)
    if not isinstance(schema, dict):
        raise ValidationError(["$: schema root must be an object"])
    if _compiled_validator_cached(digest, content)(value):
        return
    errors: list[str] = []
    _validate(value, schema, schema, [], errors, {})
    if errors:
        raise ValidationError(errors)


def validated_canonical_bytes(
    value: Any,
    *,
    schema_path: str | Path | None = None,
    schema_content: bytes | None = None,
) -> bytes:
    """Strictly validate the logical wire tree, then serialize it canonically."""

    if schema_content is None:
        content, digest = _schema_bytes(contract_schema_path(schema_path))
    else:
        content = bytes(schema_content)
        digest = hashlib.sha256(content).hexdigest()
    schema = _load_schema_cached(digest, content)
    if not isinstance(schema, dict):
        raise ValidationError(["$: schema root must be an object"])
    if not _compiled_validator_cached(digest, content)(value):
        errors: list[str] = []
        _validate(value, schema, schema, [], errors, {})
        raise ValidationError(errors)
    return canonical_bytes(value)


@lru_cache(maxsize=8)
def _validate_canonical_payload(
    payload: bytes,
    schema_digest: str,
    schema_content: bytes,
) -> None:
    schema = _load_schema_cached(schema_digest, schema_content)
    value = json.loads(payload)
    if _compiled_validator_cached(schema_digest, schema_content)(value):
        return
    errors: list[str] = []
    _validate(value, schema, schema, [], errors, {})
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


def _validate(
    value: Any,
    schema: dict[str, Any],
    root: dict[str, Any],
    path: list[str | int],
    errors: list[str],
    references: dict[str, dict[str, Any]],
) -> None:
    if "$ref" in schema:
        reference = schema["$ref"]
        if not isinstance(reference, str) or not reference.startswith("#/"):
            errors.append(f"{_path_text(path)}: unsupported $ref")
            return
        target = references.get(reference)
        if target is None:
            target = root
            for segment in reference[2:].split("/"):
                target = target.get(segment) if isinstance(target, dict) else None
        if not isinstance(target, dict):
            errors.append(f"{_path_text(path)}: unresolved $ref {reference}")
            return
        references[reference] = target
        _validate(value, target, root, path, errors, references)
        return

    if "oneOf" in schema:
        selected = _discriminated_branch(value, schema["oneOf"], root, references)
        if selected is not None:
            candidate: list[str] = []
            _validate(value, selected, root, path, candidate, references)
            if candidate:
                errors.append(
                    f"{_path_text(path)}: expected exactly one oneOf branch, matched 0"
                )
                errors.extend(candidate)
        else:
            matching = 0
            branch_errors: list[list[str]] = []
            for branch in schema["oneOf"]:
                candidate = []
                _validate(value, branch, root, path, candidate, references)
                branch_errors.append(candidate)
                if not candidate:
                    matching += 1
            if matching != 1:
                errors.append(
                    f"{_path_text(path)}: expected exactly one oneOf branch, matched {matching}"
                )
                if matching == 0 and branch_errors:
                    errors.extend(min(branch_errors, key=len))

    expected_type = schema.get("type")
    if expected_type is not None:
        allowed = expected_type if isinstance(expected_type, list) else [expected_type]
        if not any(_type_matches(value, item) for item in allowed):
            errors.append(f"{_path_text(path)}: expected type {'|'.join(allowed)}")
            return

    if "const" in schema and value != schema["const"]:
        errors.append(f"{_path_text(path)}: expected constant {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{_path_text(path)}: invalid enum value {value!r}")
    if isinstance(value, str):
        if "pattern" in schema and re.fullmatch(schema["pattern"], value) is None:
            errors.append(f"{_path_text(path)}: value does not match pattern")
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{_path_text(path)}: string is shorter than minLength")
    if isinstance(value, int) and not isinstance(value, bool) and "minimum" in schema:
        if value < schema["minimum"]:
            errors.append(f"{_path_text(path)}: value is below minimum")

    if isinstance(value, dict):
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append(f"{_path_text(path)}: missing required property {key}")
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in properties:
                    errors.append(f"{_path_text(path)}: additional property {key}")
        for key, item in value.items():
            if key in properties:
                path.append(key)
                _validate(item, properties[key], root, path, errors, references)
                path.pop()
            elif isinstance(schema.get("additionalProperties"), dict):
                path.append(key)
                _validate(
                    item,
                    schema["additionalProperties"],
                    root,
                    path,
                    errors,
                    references,
                )
                path.pop()

    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{_path_text(path)}: array is shorter than minItems")
        if schema.get("uniqueItems") and len({json.dumps(item, sort_keys=True) for item in value}) != len(value):
            errors.append(f"{_path_text(path)}: array items are not unique")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                path.append(index)
                _validate(
                    item,
                    item_schema,
                    root,
                    path,
                    errors,
                    references,
                )
                path.pop()


def _type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return False


@lru_cache(maxsize=8)
def _compiled_validator_cached(schema_digest: str, schema_content: bytes):
    """Compile at most eight immutable, content-addressed schema versions."""

    schema = _load_schema_cached(schema_digest, schema_content)
    if not isinstance(schema, dict):
        return lambda value: False
    return _compile_schema(schema, schema, {})


def _compile_schema(
    schema: dict[str, Any],
    root: dict[str, Any],
    memo: dict[int, Any],
):
    resolved = _resolved_schema(schema, root, {})
    if resolved is None:
        return lambda value: False
    schema = resolved
    key = id(schema)
    if key in memo:
        return memo[key]

    branches = schema.get("oneOf")
    branch_validator = None
    if branches is not None:
        resolved_branches = [
            _resolved_schema(branch, root, {})
            for branch in branches
        ]
        if all(branch is not None for branch in resolved_branches):
            discriminator_keys: set[str] | None = None
            for branch in resolved_branches:
                properties = branch.get("properties")
                if not isinstance(properties, dict):
                    discriminator_keys = set()
                    break
                keys = {
                    name
                    for name, child in properties.items()
                    if isinstance(child, dict) and "const" in child
                }
                discriminator_keys = (
                    keys
                    if discriminator_keys is None
                    else discriminator_keys & keys
                )
            discriminator = next(
                (
                    name
                    for name in sorted(discriminator_keys or ())
                    if len(
                        {
                            branch["properties"][name]["const"]
                            for branch in resolved_branches
                        }
                    )
                    == len(resolved_branches)
                ),
                None,
            )
            compiled_branches = [
                _compile_schema(branch, root, memo)
                for branch in resolved_branches
            ]
            if discriminator is not None:
                mapping = {
                    branch["properties"][discriminator]["const"]: validator
                    for branch, validator in zip(
                        resolved_branches,
                        compiled_branches,
                    )
                }

                def branch_validator(value):
                    if not isinstance(value, dict):
                        return False
                    selected = mapping.get(value.get(discriminator))
                    return selected(value) if selected is not None else False

            else:

                def branch_validator(value):
                    matching = 0
                    for validator in compiled_branches:
                        if validator(value):
                            matching += 1
                            if matching > 1:
                                return False
                    return matching == 1

    expected_type = schema.get("type")
    allowed_types = (
        tuple(expected_type)
        if isinstance(expected_type, list)
        else (expected_type,)
        if expected_type is not None
        else ()
    )
    single_type = allowed_types[0] if len(allowed_types) == 1 else None
    has_const = "const" in schema
    const_value = schema.get("const")
    enum_values = tuple(schema["enum"]) if "enum" in schema else None
    pattern = re.compile(schema["pattern"]) if "pattern" in schema else None
    min_length = schema.get("minLength")
    minimum = schema.get("minimum")

    properties = schema.get("properties", {})
    property_validators = tuple(
        (name, _compile_schema(child, root, memo))
        for name, child in properties.items()
    )
    required = tuple(schema.get("required", ()))
    allowed_properties = frozenset(properties)
    additional = schema.get("additionalProperties")
    additional_validator = (
        _compile_schema(additional, root, memo)
        if isinstance(additional, dict)
        else None
    )
    min_items = schema.get("minItems")
    unique_items = bool(schema.get("uniqueItems"))
    item_validator = (
        _compile_schema(schema["items"], root, memo)
        if isinstance(schema.get("items"), dict)
        else None
    )

    def validator(value):
        if branch_validator is not None and not branch_validator(value):
            return False
        if single_type is not None:
            if not _type_matches(value, single_type):
                return False
        elif allowed_types and not any(
            _type_matches(value, expected)
            for expected in allowed_types
        ):
            return False
        if has_const and value != const_value:
            return False
        if enum_values is not None and value not in enum_values:
            return False
        if isinstance(value, str):
            if pattern is not None and pattern.fullmatch(value) is None:
                return False
            if min_length is not None and len(value) < min_length:
                return False
        if (
            minimum is not None
            and isinstance(value, int)
            and not isinstance(value, bool)
            and value < minimum
        ):
            return False
        if isinstance(value, dict):
            if required and any(name not in value for name in required):
                return False
            if additional is False and any(
                name not in allowed_properties
                for name in value
            ):
                return False
            for name, child_validator in property_validators:
                if name in value and not child_validator(value[name]):
                    return False
            if additional_validator is not None:
                for name, item in value.items():
                    if (
                        name not in allowed_properties
                        and not additional_validator(item)
                    ):
                        return False
        if isinstance(value, list):
            if min_items is not None and len(value) < min_items:
                return False
            if unique_items and len(
                {json.dumps(item, sort_keys=True) for item in value}
            ) != len(value):
                return False
            if item_validator is not None and not all(
                item_validator(item)
                for item in value
            ):
                return False
        return True

    memo[key] = validator
    return validator


def _path_text(path: list[str | int]) -> str:
    return "$" + "".join(
        f"[{segment}]" if isinstance(segment, int) else f".{segment}"
        for segment in path
    )


def _discriminated_branch(
    value: Any,
    branches: list[dict[str, Any]],
    root: dict[str, Any],
    references: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    if not isinstance(value, dict) or not branches:
        return None
    discriminator_keys: set[str] | None = None
    for branch in branches:
        resolved = _resolved_schema(branch, root, references)
        if resolved is None:
            return None
        properties = resolved.get("properties")
        if not isinstance(properties, dict):
            return None
        keys = {
            key
            for key, property_schema in properties.items()
            if isinstance(property_schema, dict) and "const" in property_schema
        }
        discriminator_keys = keys if discriminator_keys is None else discriminator_keys & keys
    for key in sorted(discriminator_keys or ()):
        matches = [
            resolved
            for branch in branches
            if (resolved := _resolved_schema(branch, root, references)) is not None
            and resolved["properties"][key]["const"] == value.get(key)
        ]
        if len(matches) == 1:
            return matches[0]
    return None


def _resolved_schema(
    schema: dict[str, Any],
    root: dict[str, Any],
    references: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    reference = schema.get("$ref")
    if reference is None:
        return schema
    if not isinstance(reference, str) or not reference.startswith("#/"):
        return None
    target = references.get(reference)
    if target is None:
        candidate: Any = root
        for segment in reference[2:].split("/"):
            candidate = candidate.get(segment) if isinstance(candidate, dict) else None
        if not isinstance(candidate, dict):
            return None
        target = candidate
        references[reference] = target
    return target


def _is_valid(
    value: Any,
    schema: dict[str, Any],
    root: dict[str, Any],
    references: dict[str, dict[str, Any]],
) -> bool:
    resolved = _resolved_schema(schema, root, references)
    if resolved is None:
        return False
    schema = resolved

    branches = schema.get("oneOf")
    if branches is not None:
        selected = _discriminated_branch(value, branches, root, references)
        if selected is not None:
            if not _is_valid(value, selected, root, references):
                return False
        else:
            matching = 0
            for branch in branches:
                if _is_valid(value, branch, root, references):
                    matching += 1
                    if matching > 1:
                        return False
            if matching != 1:
                return False

    expected_type = schema.get("type")
    if expected_type is not None:
        allowed = expected_type if isinstance(expected_type, list) else (expected_type,)
        if not any(_type_matches(value, item) for item in allowed):
            return False

    if "const" in schema and value != schema["const"]:
        return False
    if "enum" in schema and value not in schema["enum"]:
        return False
    if isinstance(value, str):
        pattern = schema.get("pattern")
        if pattern is not None and re.fullmatch(pattern, value) is None:
            return False
        if len(value) < schema.get("minLength", 0):
            return False
    if (
        isinstance(value, int)
        and not isinstance(value, bool)
        and "minimum" in schema
        and value < schema["minimum"]
    ):
        return False

    if isinstance(value, dict):
        properties = schema.get("properties", {})
        if any(key not in value for key in schema.get("required", ())):
            return False
        additional = schema.get("additionalProperties")
        if additional is False and any(key not in properties for key in value):
            return False
        for key, item in value.items():
            item_schema = properties.get(key)
            if item_schema is not None:
                if not _is_valid(item, item_schema, root, references):
                    return False
            elif isinstance(additional, dict):
                if not _is_valid(item, additional, root, references):
                    return False

    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            return False
        if schema.get("uniqueItems"):
            encoded = {json.dumps(item, sort_keys=True) for item in value}
            if len(encoded) != len(value):
                return False
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            return all(
                _is_valid(item, item_schema, root, references)
                for item in value
            )
    return True
