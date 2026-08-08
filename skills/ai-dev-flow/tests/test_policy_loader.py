import copy
import importlib.util
import json
import pathlib
import tempfile
import unittest
import warnings


ROOT = pathlib.Path(__file__).resolve().parents[3]
SKILL_ROOT = ROOT / "skills" / "ai-dev-flow"
SCRIPT = SKILL_ROOT / "scripts" / "policy_loader.py"

SPEC = importlib.util.spec_from_file_location("policy_loader", SCRIPT)
policy_loader = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(policy_loader)


class PolicyLoaderTests(unittest.TestCase):
    def legacy_campaign_policy(self):
        core = json.loads((SKILL_ROOT / "policy" / "core.json").read_text(encoding="utf-8"))
        campaign = json.loads(
            (SKILL_ROOT / "policy" / "repair-campaign.json").read_text(encoding="utf-8")
        )
        return {
            "schema_version": "ai-dev-flow/v0.8-policy-rc3",
            "unknown_input": "Blocked",
            "routes": copy.deepcopy(core["routes"]),
            "review": copy.deepcopy(core["review"]),
            "safety": copy.deepcopy(core["safety"]),
            "reviewer_selection": {
                "default": "same_harness_native_isolated",
                "cross_harness": "explicit_user_authority_only",
                "native_unavailable": "Blocked",
                "same_context_self_review": "Pending",
            },
            "repair": copy.deepcopy(campaign["repair"]),
        }

    def assert_policy_rejected(self, value, suffix=".json"):
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / f"policy{suffix}"
            body = json.dumps(value, ensure_ascii=False)
            if suffix == ".md":
                body = (
                    "<!-- POLICY_JSON_BEGIN -->\n```json\n"
                    + body
                    + "\n```\n<!-- POLICY_JSON_END -->\n"
                )
            path.write_text(body, encoding="utf-8")
            with self.assertRaises(policy_loader.PolicyLoadError):
                policy_loader.load_policy_document(path)

    def assert_policy_accepted(self, value, suffix=".json"):
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / f"policy{suffix}"
            body = json.dumps(value, ensure_ascii=False)
            if suffix == ".md":
                body = (
                    "<!-- POLICY_JSON_BEGIN -->\n```json\n"
                    + body
                    + "\n```\n<!-- POLICY_JSON_END -->\n"
                )
            path.write_text(body, encoding="utf-8")
            return policy_loader.load_policy_document(path)

    def test_canonical_json_documents_load_as_read_only_values(self):
        for name, schema in (
            ("core.json", "adf/policy-core/v1"),
            ("repair-basic.json", "adf/repair-basic/v1"),
            ("repair-campaign.json", "adf/repair-campaign/v1"),
        ):
            with self.subTest(name=name):
                value = policy_loader.load_policy_document(SKILL_ROOT / "policy" / name)
                self.assertEqual(value["schema_version"], schema)
                with self.assertRaises(TypeError):
                    value["schema_version"] = "changed"

    def test_unknown_top_level_field_and_invalid_utf8_fail_closed(self):
        core = json.loads((SKILL_ROOT / "policy" / "core.json").read_text(encoding="utf-8"))
        core["unexpected"] = True
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            unknown = root / "unknown.json"
            unknown.write_text(json.dumps(core), encoding="utf-8")
            invalid = root / "invalid.json"
            invalid.write_bytes(b"{\xff}")
            with self.assertRaises(policy_loader.PolicyLoadError):
                policy_loader.load_policy_document(unknown)
            with self.assertRaises(policy_loader.PolicyLoadError):
                policy_loader.load_policy_document(invalid)

    def test_legacy_markdown_is_accepted_with_deprecation_warning(self):
        legacy = self.legacy_campaign_policy()
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / "CORE.md"
            path.write_text(
                "<!-- POLICY_JSON_BEGIN -->\n```json\n"
                + json.dumps(legacy)
                + "\n```\n<!-- POLICY_JSON_END -->\n",
                encoding="utf-8",
            )
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                value = policy_loader.load_policy_document(path)
        self.assertEqual(value["schema_version"], "ai-dev-flow/v0.8-policy-rc3")
        self.assertTrue(any(issubclass(item.category, policy_loader.LegacyPolicyWarning) for item in caught))

    def test_nested_schema_type_enum_and_constraint_fail_closed(self):
        documents = {
            name: json.loads((SKILL_ROOT / "policy" / name).read_text(encoding="utf-8"))
            for name in ("core.json", "repair-basic.json", "repair-campaign.json")
        }

        def mutation(name, change):
            value = copy.deepcopy(documents[name])
            change(value)
            return name, value

        cases = (
            mutation("core.json", lambda value: value["routes"]["controlled"].update({"ua_min": "5"})),
            mutation("core.json", lambda value: value["routes"].update({"fallback": "Lite"})),
            mutation("core.json", lambda value: value["safety"].pop("missing_required_evidence")),
            mutation("core.json", lambda value: value["review"]["Tracked"].update({"extra": True})),
            mutation("repair-basic.json", lambda value: value.update({"base_auto_rounds": True})),
            mutation("repair-basic.json", lambda value: value["progress_gate"].update({"require_red_to_green": "yes"})),
            mutation("repair-basic.json", lambda value: value["progress_gate"].pop("forbid_green_to_red")),
            mutation("repair-basic.json", lambda value: value.update({"on_budget_exhausted": "Continue"})),
            mutation("repair-campaign.json", lambda value: value["repair"].update({"base_auto_rounds": "2"})),
            mutation("repair-campaign.json", lambda value: value["repair"]["history"].pop("require_history_anchor")),
            mutation("repair-campaign.json", lambda value: value["repair"]["campaign"]["profiles"]["core_product"].update({"max_consecutive_no_progress": 0})),
            mutation("repair-campaign.json", lambda value: value["repair"]["campaign"].update({"extra": False})),
            mutation("repair-campaign.json", lambda value: value["repair"].update({"mechanical_decisions": ["Continue"]})),
            mutation("repair-campaign.json", lambda value: value["repair"]["history"].update({"require_trusted_context": False})),
            mutation("repair-campaign.json", lambda value: value["repair"].update({"task_change_resets_budget": True})),
            mutation("repair-campaign.json", lambda value: value["repair"]["post_stop"]["authority_must_bind"].remove("target_finding_ids")),
            mutation("repair-campaign.json", lambda value: value["repair"]["campaign"]["authority_must_bind"].remove("task_id")),
            mutation("repair-campaign.json", lambda value: value["repair"]["campaign"]["hard_stop_flags"].remove("test_oracle_weakened")),
        )
        for name, value in cases:
            with self.subTest(policy=name, value=value):
                self.assert_policy_rejected(value)

    def test_policy_values_are_not_a_second_source_in_python(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for duplicated_value in (
            "architecture",
            "business_files_gt_3",
            "test_oracle_weakened",
            "same_harness_native_isolated",
            "max_consecutive_no_progress must be 4",
        ):
            with self.subTest(value=duplicated_value):
                self.assertNotIn(duplicated_value, source)

    def test_schema_allows_canonical_policy_values_to_evolve_within_enums(self):
        core = json.loads((SKILL_ROOT / "policy" / "core.json").read_text(encoding="utf-8"))
        campaign = json.loads(
            (SKILL_ROOT / "policy" / "repair-campaign.json").read_text(encoding="utf-8")
        )
        core["routes"]["controlled"]["risk_flags"] = ["delivery"]
        core["routes"]["controlled"]["ua_min"] = 6
        campaign["repair"]["base_auto_rounds"] = 3
        campaign["repair"]["autonomous_max_rounds"] = 4
        campaign["repair"]["campaign"]["profiles"]["core_product"]["max_consecutive_no_progress"] = 7
        self.assert_policy_accepted(core)
        self.assert_policy_accepted(campaign)

    def test_generic_cross_field_constraints_fail_closed(self):
        campaign = json.loads(
            (SKILL_ROOT / "policy" / "repair-campaign.json").read_text(encoding="utf-8")
        )
        cases = []
        lower_max = copy.deepcopy(campaign)
        lower_max["repair"]["autonomous_max_rounds"] = 1
        cases.append(lower_max)
        overlapping = copy.deepcopy(campaign)
        overlapping["repair"]["required_false_fields"] = [
            overlapping["repair"]["required_true_fields"][0]
        ]
        cases.append(overlapping)
        same_scope_fields = copy.deepcopy(campaign)
        same_scope_fields["repair"]["campaign"]["scope_manifest"]["path_prefixes_field"] = (
            same_scope_fields["repair"]["campaign"]["scope_manifest"]["exact_files_field"]
        )
        cases.append(same_scope_fields)
        for index, value in enumerate(cases):
            with self.subTest(index=index):
                self.assert_policy_rejected(value)

    def test_safety_invariants_fail_closed_for_json_markdown_and_memory(self):
        campaign = json.loads(
            (SKILL_ROOT / "policy" / "repair-campaign.json").read_text(encoding="utf-8")
        )
        mutations = (
            lambda value: value["repair"]["history"].update({"require_trusted_context": False}),
            lambda value: value["repair"]["campaign"]["hard_stop_flags"].remove("test_oracle_weakened"),
            lambda value: value["repair"]["campaign"]["authority_must_bind"].remove("task_id"),
            lambda value: value["repair"]["required_true_fields"].remove("authority_frozen"),
            lambda value: value["repair"]["required_false_fields"].remove("external_side_effect"),
        )
        for index, change in enumerate(mutations):
            value = copy.deepcopy(campaign)
            change(value)
            with self.subTest(index=index, source="json"):
                self.assert_policy_rejected(value)
            with self.subTest(index=index, source="markdown"):
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", policy_loader.LegacyPolicyWarning)
                    self.assert_policy_rejected(value, suffix=".md")
            with self.subTest(index=index, source="memory"):
                with self.assertRaises(policy_loader.PolicyLoadError):
                    policy_loader.validate_policy_value(value)

    def test_legacy_reviewer_selection_enum_fails_closed(self):
        legacy = self.legacy_campaign_policy()
        legacy["reviewer_selection"]["native_unavailable"] = "Continue"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", policy_loader.LegacyPolicyWarning)
            self.assert_policy_rejected(legacy, suffix=".md")

    def test_schema_registry_rejects_unlisted_escape_and_unknown_keywords(self):
        original_root = policy_loader.SCHEMA_ROOT
        original_registry = policy_loader.SCHEMA_REGISTRY
        try:
            with tempfile.TemporaryDirectory() as temp:
                root = pathlib.Path(temp) / "schemas"
                root.mkdir()
                schema = root / "one.json"
                schema.write_text(json.dumps({
                    "x-policy-schema-version": "test/v1",
                    "type": "object",
                    "required": ["schema_version"],
                    "properties": {"schema_version": {"const": "test/v1"}},
                    "additionalProperties": False,
                }), encoding="utf-8")
                registry = root / "registry.json"
                registry.write_text(json.dumps({
                    "schema_version": "adf/policy-schema-registry/v1",
                    "entries": [{"policy_schema_version": "test/v1", "path": "one.json", "legacy_optional_ref": None, "legacy_optional_required": []}],
                }), encoding="utf-8")
                policy_loader.SCHEMA_ROOT = root
                policy_loader.SCHEMA_REGISTRY = registry
                policy_loader.validate_policy_value({"schema_version": "test/v1"})

                unlisted = root / "unlisted.json"
                unlisted.write_text(json.dumps({"x-policy-schema-version": "evil/v1"}), encoding="utf-8")
                with self.assertRaises(policy_loader.PolicyLoadError):
                    policy_loader.validate_policy_value({"schema_version": "evil/v1"})

                escaped = pathlib.Path(temp) / "escape.json"
                escaped.write_text(schema.read_text(encoding="utf-8"), encoding="utf-8")
                registry.write_text(json.dumps({
                    "schema_version": "adf/policy-schema-registry/v1",
                    "entries": [{"policy_schema_version": "test/v1", "path": "../escape.json", "legacy_optional_ref": None, "legacy_optional_required": []}],
                }), encoding="utf-8")
                with self.assertRaises(policy_loader.PolicyLoadError):
                    policy_loader.validate_policy_value({"schema_version": "test/v1"})

                registry.write_text(json.dumps({
                    "schema_version": "adf/policy-schema-registry/v1",
                    "entries": [{"policy_schema_version": "test/v1", "path": "one.json", "legacy_optional_ref": None, "legacy_optional_required": []}],
                }), encoding="utf-8")
                malformed = json.loads(schema.read_text(encoding="utf-8"))
                malformed["unsafeCustomKeyword"] = True
                schema.write_text(json.dumps(malformed), encoding="utf-8")
                with self.assertRaises(policy_loader.PolicyLoadError):
                    policy_loader.validate_policy_value({"schema_version": "test/v1"})

                sibling = {
                    "x-policy-schema-version": "test/v1",
                    "$ref": "one.json#",
                    "required": ["silently_ignored"],
                }
                schema.write_text(json.dumps(sibling), encoding="utf-8")
                with self.assertRaises(policy_loader.PolicyLoadError):
                    policy_loader.validate_policy_value({"schema_version": "test/v1"})

                no_ref = {
                    "x-policy-schema-version": "test/v1",
                    "type": "object",
                    "x-optional-required": ["schema_version"],
                }
                schema.write_text(json.dumps(no_ref), encoding="utf-8")
                with self.assertRaises(policy_loader.PolicyLoadError):
                    policy_loader.validate_policy_value({"schema_version": "test/v1"})
        finally:
            policy_loader.SCHEMA_ROOT = original_root
            policy_loader.SCHEMA_REGISTRY = original_registry


if __name__ == "__main__":
    unittest.main()
