from __future__ import annotations

import copy
import hashlib
import json
import unittest

from be001.support import CONTRACTS_ROOT, task
from ai_dev_flow_dashboard.core.canonical import canonical_bytes, canonical_sha256, snapshot_revision
from ai_dev_flow_dashboard.core.models import primitive
from ai_dev_flow_dashboard.core.schema_validator import (
    ValidationError,
    validate_contract,
    validate_sse_transcript,
)


class SharedContractTests(unittest.TestCase):
    def setUp(self):
        self.fixture_root = CONTRACTS_ROOT / "fixtures" / "v1"

    def snapshot_with_edge(self, edge):
        value = json.loads((self.fixture_root / "fresh.json").read_text(encoding="utf-8"))
        value["edges"] = [edge]
        return value

    @staticmethod
    def edge(edge_type, condition, storage, display, directional):
        return {
            "edge_id": "9" * 64,
            "type": edge_type,
            "source_task_id": "SOURCE",
            "target_task_id": "TARGET",
            "condition": condition,
            "storage_direction": storage,
            "display_direction": display,
            "directional": directional,
            "origin": "canonical",
            "provenance": [],
        }

    def test_all_eight_versioned_json_fixtures_validate_twice_stably(self):
        fixtures = sorted(self.fixture_root.glob("*.json"))
        self.assertGreaterEqual(len(fixtures), 8)
        first = []
        second = []
        for path in fixtures:
            value = json.loads(path.read_text(encoding="utf-8"))
            validate_contract(value)
            first.append((path.name, hashlib.sha256(path.read_bytes()).hexdigest(), canonical_sha256(value)))
        for path in fixtures:
            value = json.loads(path.read_text(encoding="utf-8"))
            validate_contract(value)
            second.append((path.name, hashlib.sha256(path.read_bytes()).hexdigest(), canonical_sha256(value)))
        self.assertEqual(first, second)

    def test_fixture_set_covers_required_states(self):
        names = {path.stem for path in self.fixture_root.glob("*.json")}
        self.assertTrue(
            {
                "fresh",
                "stale",
                "partial",
                "parse-error",
                "dependency-cycle",
                "parallel-unknown",
                "git-degraded",
                "task-detail-error",
            }
            <= names
        )

    def test_strict_validator_rejects_missing_extra_type_and_enum(self):
        value = json.loads((self.fixture_root / "fresh.json").read_text(encoding="utf-8"))
        cases = []
        missing = copy.deepcopy(value)
        missing.pop("schema_version")
        cases.append(missing)
        extra = copy.deepcopy(value)
        extra["surprise"] = True
        cases.append(extra)
        wrong_type = copy.deepcopy(value)
        wrong_type["tasks"] = "not-an-array"
        cases.append(wrong_type)
        invalid_enum = copy.deepcopy(value)
        invalid_enum["state"] = "mostly-fresh"
        cases.append(invalid_enum)
        for candidate in cases:
            with self.subTest(candidate=candidate):
                with self.assertRaises(ValidationError):
                    validate_contract(candidate)

    def test_nested_additional_property_is_rejected(self):
        value = json.loads((self.fixture_root / "fresh.json").read_text(encoding="utf-8"))
        value["project"]["command"] = "git status"
        with self.assertRaises(ValidationError) as caught:
            validate_contract(value)
        self.assertIn("additional property command", str(caught.exception))

    def test_wire_schema_rejects_reader_not_recorded_sentinel(self):
        value = json.loads((self.fixture_root / "fresh.json").read_text(encoding="utf-8"))
        for axis in ("commit_status", "merge_status"):
            with self.subTest(axis=axis):
                candidate = copy.deepcopy(value)
                candidate["tasks"] = [primitive(task("TASK", **{axis: "Not Recorded"}))]
                with self.assertRaises(ValidationError):
                    validate_contract(candidate)

    def test_dependency_condition_binds_all_eight_axes_to_their_value_registry(self):
        registry = {
            "lifecycle": ("Draft", "Accepted"),
            "review_status": ("Pending", "Passed"),
            "ua_status": ("Pending", "Passed"),
            "acceptance_authority": ("None", "User Confirmed"),
            "commit_status": ("Uncommitted", "Committed"),
            "merge_status": ("Unmerged", "Merged"),
            "merge_authority": ("None", "User Authorized"),
            "close_authority": ("None", "Rule Authorized"),
        }
        for axis, (expected, actual) in registry.items():
            with self.subTest(axis=axis):
                condition = {
                    "axis": axis,
                    "operator": "eq",
                    "expected": expected,
                    "actual": actual,
                    "evaluation": "unsatisfied",
                }
                edge = self.edge(
                    "depends_on",
                    condition,
                    "dependent_to_prerequisite",
                    "prerequisite_to_dependent",
                    True,
                )
                validate_contract(self.snapshot_with_edge(edge))
                invalid_expected = copy.deepcopy(edge)
                invalid_expected["condition"]["expected"] = "not-a-registered-value"
                with self.assertRaises(ValidationError):
                    validate_contract(self.snapshot_with_edge(invalid_expected))
                invalid_actual = copy.deepcopy(edge)
                invalid_actual["condition"]["actual"] = "not-a-registered-value"
                with self.assertRaises(ValidationError):
                    validate_contract(self.snapshot_with_edge(invalid_actual))

    def test_relationship_type_uniquely_binds_condition_and_directions(self):
        condition = {
            "axis": "lifecycle",
            "operator": "eq",
            "expected": "Accepted",
            "actual": "Ready",
            "evaluation": "unsatisfied",
        }
        shapes = (
            (
                "depends_on",
                condition,
                "dependent_to_prerequisite",
                "prerequisite_to_dependent",
                True,
            ),
            ("parent", None, "child_to_parent", "parent_to_child", True),
            ("replaces", None, "replacement_to_replaced", "replaced_to_replacement", True),
            ("discovered_from", None, "discovered_to_origin", "origin_to_discovered", True),
            ("conflicts_with", None, "symmetric", "symmetric", False),
        )
        for shape in shapes:
            with self.subTest(edge_type=shape[0]):
                validate_contract(self.snapshot_with_edge(self.edge(*shape)))

        mixed = self.edge(
            "conflicts_with",
            None,
            "dependent_to_prerequisite",
            "prerequisite_to_dependent",
            True,
        )
        with self.assertRaises(ValidationError):
            validate_contract(self.snapshot_with_edge(mixed))
        non_null_condition = self.edge(
            "parent",
            condition,
            "child_to_parent",
            "parent_to_child",
            True,
        )
        with self.assertRaises(ValidationError):
            validate_contract(self.snapshot_with_edge(non_null_condition))

    def test_error_registry_message_and_details_shape_are_strict(self):
        value = json.loads((self.fixture_root / "task-detail-error.json").read_text(encoding="utf-8"))
        validate_contract(value)
        wrong_message = copy.deepcopy(value)
        wrong_message["error"]["message"] = "missing"
        with self.assertRaises(ValidationError):
            validate_contract(wrong_message)
        wrong_details = copy.deepcopy(value)
        wrong_details["error"]["details"]["path"] = "secret"
        with self.assertRaises(ValidationError):
            validate_contract(wrong_details)

    def test_sse_transcript_uses_lf_wire_format_and_shared_event_schema(self):
        transcript = (self.fixture_root / "events.sse").read_bytes()
        validate_sse_transcript(transcript)
        self.assertNotIn(b"\r", transcript)
        self.assertTrue(transcript.endswith(b"\x0a\x0a"))
        with self.assertRaises(ValidationError):
            validate_sse_transcript(transcript.replace(b"\x0a", b"\r\n"))
        mismatched_id = transcript.replace(b"id: " + b"f" * 64, b"id: " + b"a" * 64)
        with self.assertRaises(ValidationError) as mismatch:
            validate_sse_transcript(mismatched_id)
        self.assertIn("id must equal data.revision", str(mismatch.exception))
        with self.assertRaises(ValidationError):
            validate_sse_transcript(transcript.replace(b"event: snapshot\n", b""))
        with self.assertRaises(ValidationError):
            validate_sse_transcript(transcript.replace(b"event: snapshot\n", b"event: snapshot\ntrace: forbidden\n"))

    def test_canonical_json_is_nfc_compact_utf8_and_stable(self):
        decomposed = {"z": "e\u0301", "a": [2, 1]}
        composed = {"a": [2, 1], "z": "é"}
        self.assertEqual(canonical_bytes(decomposed), canonical_bytes(composed))
        self.assertEqual(b'{"a":[2,1],"z":"\xc3\xa9"}', canonical_bytes(decomposed))
        self.assertEqual(canonical_sha256(decomposed), canonical_sha256(composed))

    def test_generated_at_does_not_change_snapshot_revision(self):
        value = json.loads((self.fixture_root / "fresh.json").read_text(encoding="utf-8"))
        changed = copy.deepcopy(value)
        changed["generated_at"] = "2026-07-28T12:34:56.789Z"
        changed["revision"] = "f" * 64
        self.assertEqual(snapshot_revision(value), snapshot_revision(changed))
        changed["state"] = "stale"
        self.assertNotEqual(snapshot_revision(value), snapshot_revision(changed))


if __name__ == "__main__":
    unittest.main()
