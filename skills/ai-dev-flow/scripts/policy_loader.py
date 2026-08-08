"""Strict, read-only loader for ai-dev-flow policy documents.

Policy values live only in the canonical JSON documents.  This module is a
generic JSON Schema interpreter plus a few value-agnostic cross-field checks;
it deliberately does not mirror the current risk flags, ordered arrays,
round limits, authority bindings, or other policy decisions in Python.
"""

import json
import pathlib
import re
import warnings
from types import MappingProxyType


LEGACY_POLICY_PATTERN = re.compile(
    r"<!-- POLICY_JSON_BEGIN -->\s*```json\s*(\{.*?\})\s*```\s*<!-- POLICY_JSON_END -->",
    flags=re.DOTALL,
)
SCHEMA_ROOT = pathlib.Path(__file__).resolve().parents[1] / "policy" / "schemas"
SCHEMA_REGISTRY = SCHEMA_ROOT / "registry.json"
SCHEMA_KEYWORDS = {
    "$schema", "$ref", "x-policy-schema-version", "x-optional-required",
    "type", "const", "enum", "properties", "required",
    "additionalProperties", "minItems", "uniqueItems", "items", "minimum",
    "minLength", "pattern", "allOf", "contains", "minContains", "maxContains",
}


class PolicyLoadError(ValueError):
    pass


class LegacyPolicyWarning(FutureWarning):
    pass


def _freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def thaw_policy(value):
    if isinstance(value, MappingProxyType):
        return {key: thaw_policy(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [thaw_policy(item) for item in value]
    return value


def _json_type_matches(value, expected):
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }.get(expected, False)


def _validate_schema(value, schema, path="$", *, schema_source="schema"):
    """Validate the JSON Schema subset used by shipped policy schemas."""

    if not isinstance(schema, dict):
        raise PolicyLoadError(f"invalid {schema_source}: {path} schema must be an object")
    unknown_keywords = set(schema) - SCHEMA_KEYWORDS
    if unknown_keywords:
        raise PolicyLoadError(f"invalid {schema_source}: unknown schema keywords {sorted(unknown_keywords)}")
    branches = schema.get("allOf", [])
    if not isinstance(branches, list):
        raise PolicyLoadError(f"invalid {schema_source}: {path}.allOf must be an array")
    for branch in branches:
        _validate_schema(value, branch, path, schema_source=schema_source)
    reference = schema.get("$ref")
    if reference is not None:
        allowed_siblings = {"$ref", "x-optional-required"}
        if set(schema) - allowed_siblings:
            raise PolicyLoadError(f"unsupported $ref sibling keywords in {schema_source}")
        resolved, resolved_source = _resolve_schema_reference(reference, schema_source)
        if "x-optional-required" in schema:
            optional = schema["x-optional-required"]
            if (
                not isinstance(optional, list)
                or not optional
                or any(not isinstance(item, str) for item in optional)
                or len(optional) != len(set(optional))
            ):
                raise PolicyLoadError(f"invalid x-optional-required in {schema_source}")
            entry = _trusted_schema_entry(schema_source)
            if (
                reference != entry.get("legacy_optional_ref")
                or optional != entry.get("legacy_optional_required", [])
            ):
                raise PolicyLoadError(f"unapproved x-optional-required in {schema_source}")
            required = resolved.get("required", [])
            if any(item not in required for item in optional):
                raise PolicyLoadError(f"x-optional-required names are not required by {reference}")
            resolved = dict(resolved)
            resolved["required"] = [item for item in required if item not in optional]
        _validate_schema(value, resolved, path, schema_source=resolved_source)
        return
    if "x-optional-required" in schema:
        raise PolicyLoadError(f"x-optional-required requires $ref in {schema_source}")
    expected = schema.get("type")
    if expected is not None:
        choices = expected if isinstance(expected, list) else [expected]
        if not choices or any(not isinstance(item, str) for item in choices):
            raise PolicyLoadError(f"invalid {schema_source}: {path}.type")
        if not any(_json_type_matches(value, item) for item in choices):
            raise PolicyLoadError(f"{path} must have JSON type {' or '.join(choices)}")
    if "const" in schema and value != schema["const"]:
        raise PolicyLoadError(f"{path} must equal the schema const")
    if "enum" in schema:
        choices = schema["enum"]
        if not isinstance(choices, list) or value not in choices:
            raise PolicyLoadError(f"{path} contains an invalid enum value")

    if isinstance(value, dict):
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        if not isinstance(properties, dict) or not isinstance(required, list):
            raise PolicyLoadError(f"invalid {schema_source}: {path} object keywords")
        missing = [name for name in required if name not in value]
        if missing:
            raise PolicyLoadError(f"{path} is missing required fields: {sorted(missing)}")
        if schema.get("additionalProperties") is False:
            unknown = set(value) - set(properties)
            if unknown:
                raise PolicyLoadError(f"{path} has unknown fields: {sorted(unknown)}")
        for name, item in value.items():
            child = properties.get(name)
            if child is not None:
                _validate_schema(item, child, f"{path}.{name}", schema_source=schema_source)

    if isinstance(value, list):
        minimum = schema.get("minItems")
        if minimum is not None and (not isinstance(minimum, int) or len(value) < minimum):
            raise PolicyLoadError(f"{path} must contain at least {minimum} items")
        if schema.get("uniqueItems") is True:
            encoded = [json.dumps(item, sort_keys=True, ensure_ascii=False) for item in value]
            if len(encoded) != len(set(encoded)):
                raise PolicyLoadError(f"{path} items must be unique")
        item_schema = schema.get("items")
        if item_schema is not None:
            for index, item in enumerate(value):
                _validate_schema(item, item_schema, f"{path}[{index}]", schema_source=schema_source)
        contains = schema.get("contains")
        if contains is not None:
            matches = 0
            for item in value:
                try:
                    _validate_schema(item, contains, path, schema_source=schema_source)
                except PolicyLoadError:
                    continue
                matches += 1
            minimum_contains = schema.get("minContains", 1)
            maximum_contains = schema.get("maxContains")
            if not isinstance(minimum_contains, int) or minimum_contains < 0:
                raise PolicyLoadError(f"invalid {schema_source}: {path}.minContains")
            if matches < minimum_contains:
                raise PolicyLoadError(f"{path} does not contain enough required values")
            if maximum_contains is not None:
                if not isinstance(maximum_contains, int) or maximum_contains < minimum_contains:
                    raise PolicyLoadError(f"invalid {schema_source}: {path}.maxContains")
                if matches > maximum_contains:
                    raise PolicyLoadError(f"{path} contains too many matching values")

    if isinstance(value, str):
        minimum = schema.get("minLength")
        if minimum is not None and len(value) < minimum:
            raise PolicyLoadError(f"{path} must contain at least {minimum} characters")
        pattern = schema.get("pattern")
        if pattern is not None and re.fullmatch(pattern, value) is None:
            raise PolicyLoadError(f"{path} does not match the required pattern")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        minimum = schema.get("minimum")
        if minimum is not None and value < minimum:
            raise PolicyLoadError(f"{path} must be >= {minimum}")


def _resolve_schema_reference(reference, schema_source):
    if not isinstance(reference, str) or "#" not in reference:
        raise PolicyLoadError(f"invalid schema reference in {schema_source}: {reference!r}")
    filename, fragment = reference.split("#", 1)
    source = pathlib.Path(schema_source).resolve()
    target_source = (source if not filename else source.parent / filename).resolve()
    trusted_paths = {pathlib.Path(item["path"]).resolve() for item in _registry_entries()}
    if target_source not in trusted_paths:
        raise PolicyLoadError(f"schema reference escapes the trusted registry: {reference}")
    try:
        target = json.loads(target_source.read_text(encoding="utf-8", errors="strict"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PolicyLoadError(f"cannot resolve policy schema reference {reference}: {exc}") from exc
    if fragment:
        if not fragment.startswith("/"):
            raise PolicyLoadError(f"invalid schema fragment in {reference}")
        for raw_segment in fragment[1:].split("/"):
            segment = raw_segment.replace("~1", "/").replace("~0", "~")
            if not isinstance(target, dict) or segment not in target:
                raise PolicyLoadError(f"unresolved schema fragment in {reference}")
            target = target[segment]
    if not isinstance(target, dict):
        raise PolicyLoadError(f"schema reference does not resolve to an object: {reference}")
    return target, str(target_source)


def _registry_entries():
    try:
        manifest = json.loads(SCHEMA_REGISTRY.read_text(encoding="utf-8", errors="strict"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PolicyLoadError(f"cannot load policy schema registry {SCHEMA_REGISTRY}: {exc}") from exc
    if not isinstance(manifest, dict) or set(manifest) != {"schema_version", "entries"}:
        raise PolicyLoadError("policy schema registry has invalid top-level fields")
    if manifest["schema_version"] != "adf/policy-schema-registry/v1":
        raise PolicyLoadError("unsupported policy schema registry version")
    raw_entries = manifest["entries"]
    if not isinstance(raw_entries, list) or not raw_entries:
        raise PolicyLoadError("policy schema registry entries must be a non-empty array")
    root = SCHEMA_ROOT.resolve()
    entries = []
    seen_versions = set()
    seen_paths = set()
    for raw in raw_entries:
        if not isinstance(raw, dict) or set(raw) != {"policy_schema_version", "path", "legacy_optional_ref", "legacy_optional_required"}:
            raise PolicyLoadError("policy schema registry entry has invalid fields")
        version = raw["policy_schema_version"]
        relative = raw["path"]
        optional = raw["legacy_optional_required"]
        optional_ref = raw["legacy_optional_ref"]
        if not isinstance(version, str) or not version or version in seen_versions:
            raise PolicyLoadError("policy schema registry versions must be unique non-empty strings")
        if not isinstance(relative, str) or not relative or pathlib.PurePath(relative).is_absolute():
            raise PolicyLoadError("policy schema registry paths must be relative strings")
        source = (root / relative).resolve()
        if source.parent != root or source in seen_paths:
            raise PolicyLoadError("policy schema registry paths must be unique files inside the schema root")
        if (
            not isinstance(optional, list)
            or any(not isinstance(item, str) or not item for item in optional)
            or len(optional) != len(set(optional))
        ):
            raise PolicyLoadError("legacy_optional_required must be a unique string array")
        if (optional and not isinstance(optional_ref, str)) or (not optional and optional_ref is not None):
            raise PolicyLoadError("legacy_optional_ref must bind exactly one approved optional list")
        entries.append({"policy_schema_version": version, "path": str(source), "legacy_optional_ref": optional_ref, "legacy_optional_required": optional})
        seen_versions.add(version)
        seen_paths.add(source)
    return entries


def _trusted_schema_entry(source):
    resolved = pathlib.Path(source).resolve()
    for entry in _registry_entries():
        if pathlib.Path(entry["path"]).resolve() == resolved:
            return entry
    raise PolicyLoadError(f"schema is not in the trusted registry: {source}")


def _schema_registry():
    registry = {}
    for entry in _registry_entries():
        source = pathlib.Path(entry["path"])
        try:
            schema = json.loads(source.read_text(encoding="utf-8", errors="strict"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise PolicyLoadError(f"cannot load policy schema {source}: {exc}") from exc
        version = entry["policy_schema_version"]
        declared = schema.get("x-policy-schema-version") if isinstance(schema, dict) else None
        if declared != version or version in registry:
            raise PolicyLoadError(f"policy schema version mismatch in {source}")
        registry[version] = (schema, source)
    return registry


def _cross_field_constraints(value):
    """Enforce relationships, never a copy of current canonical values."""

    containers = [value]
    repair = value.get("repair") if isinstance(value, dict) else None
    if isinstance(repair, dict):
        containers.append(repair)
    for container in containers:
        base = container.get("base_auto_rounds")
        optional = container.get("optional_progress_rounds")
        maximum = container.get("autonomous_max_rounds")
        if isinstance(base, int) and not isinstance(base, bool):
            if isinstance(optional, int) and not isinstance(optional, bool) and base + optional < base:
                raise PolicyLoadError("optional repair rounds cannot reduce the base budget")
            if isinstance(maximum, int) and not isinstance(maximum, bool) and maximum < base:
                raise PolicyLoadError("autonomous_max_rounds cannot be lower than base_auto_rounds")
        required_true = container.get("required_true_fields")
        required_false = container.get("required_false_fields")
        if isinstance(required_true, list) and isinstance(required_false, list):
            overlap = set(required_true) & set(required_false)
            if overlap:
                raise PolicyLoadError(f"repair required true/false fields overlap: {sorted(overlap)}")
    campaign = repair.get("campaign") if isinstance(repair, dict) else None
    scope = campaign.get("scope_manifest") if isinstance(campaign, dict) else None
    if isinstance(scope, dict) and scope.get("exact_files_field") == scope.get("path_prefixes_field"):
        raise PolicyLoadError("campaign scope field names must be distinct")


def _parse_json(text, source):
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PolicyLoadError(f"invalid policy JSON in {source}: {exc}") from exc
    validate_policy_value(value)
    return value


def validate_policy_value(value):
    """Validate an already parsed policy exactly as file loading does."""

    if not isinstance(value, dict):
        raise PolicyLoadError("policy must be a JSON object")
    version = value.get("schema_version")
    registry = _schema_registry()
    entry = registry.get(version)
    if entry is None:
        raise PolicyLoadError(f"unsupported policy schema: {version!r}")
    schema, source = entry
    _validate_schema(value, schema, schema_source=str(source))
    _cross_field_constraints(value)


def load_policy_document(path):
    source = pathlib.Path(path)
    try:
        text = source.read_text(encoding="utf-8", errors="strict")
    except (OSError, UnicodeError) as exc:
        raise PolicyLoadError(f"cannot read policy {source}: {exc}") from exc
    stripped = text.lstrip()
    if stripped.startswith("{"):
        value = _parse_json(text, source)
    else:
        match = LEGACY_POLICY_PATTERN.search(text)
        if not match:
            raise PolicyLoadError(f"legacy POLICY_JSON block missing: {source}")
        warnings.warn(
            f"Markdown POLICY_JSON is deprecated; use policy/*.json: {source}",
            LegacyPolicyWarning,
            stacklevel=2,
        )
        value = _parse_json(match.group(1), source)
    return _freeze(value)
