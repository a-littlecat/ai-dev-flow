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
            mutation("core.json", lambda value: value["safety"].update({"delivery_requires_controlled": False})),
            mutation("repair-basic.json", lambda value: value.update({"base_auto_rounds": True})),
            mutation("repair-basic.json", lambda value: value["progress_gate"].update({"require_red_to_green": "yes"})),
            mutation("repair-basic.json", lambda value: value["progress_gate"].pop("forbid_green_to_red")),
            mutation("repair-basic.json", lambda value: value.update({"on_budget_exhausted": "Continue"})),
            mutation("repair-basic.json", lambda value: value.update({"independent_review_after_patch": False})),
            mutation("repair-campaign.json", lambda value: value["repair"].update({"base_auto_rounds": "2"})),
            mutation("repair-campaign.json", lambda value: value["repair"]["history"].pop("require_history_anchor")),
            mutation("repair-campaign.json", lambda value: value["repair"]["campaign"]["profiles"]["core_product"].update({"max_consecutive_no_progress": 0})),
            mutation("repair-campaign.json", lambda value: value["repair"]["campaign"].update({"extra": False})),
            mutation("repair-campaign.json", lambda value: value["repair"].update({"mechanical_decisions": ["Continue"]})),
        )
        for name, value in cases:
            with self.subTest(policy=name, value=value):
                self.assert_policy_rejected(value)

    def test_security_critical_mutations_fail_for_json_and_legacy_markdown(self):
        campaign = json.loads(
            (SKILL_ROOT / "policy" / "repair-campaign.json").read_text(encoding="utf-8")
        )
        mutations = (
            lambda value: value["repair"]["post_stop"]["authority_must_bind"].pop(),
            lambda value: value["repair"]["campaign"]["authority_must_bind"].pop(),
            lambda value: value["repair"]["campaign"]["hard_stop_flags"].remove("test_oracle_weakened"),
            lambda value: value["repair"]["history"].update({"require_trusted_context": False}),
            lambda value: value["repair"]["history"].update({"require_independent_review_receipt_after_each_attempt": False}),
            lambda value: value["repair"].update({"task_change_resets_budget": True}),
            lambda value: value["repair"]["campaign"].update({"task_change_resets_streak": True}),
            lambda value: value["repair"]["campaign"].update({"model_change_resets_streak": True}),
            lambda value: value["repair"]["campaign"].update({"chain_change_resets_streak": True}),
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", policy_loader.LegacyPolicyWarning)
            for index, change in enumerate(mutations):
                direct = copy.deepcopy(campaign)
                legacy = self.legacy_campaign_policy()
                change(direct)
                change(legacy)
                with self.subTest(index=index, source="json"):
                    self.assert_policy_rejected(direct)
                with self.subTest(index=index, source="legacy"):
                    self.assert_policy_rejected(legacy, suffix=".md")

    def test_legacy_reviewer_selection_enum_fails_closed(self):
        legacy = self.legacy_campaign_policy()
        legacy["reviewer_selection"]["native_unavailable"] = "Continue"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", policy_loader.LegacyPolicyWarning)
            self.assert_policy_rejected(legacy, suffix=".md")


if __name__ == "__main__":
    unittest.main()
