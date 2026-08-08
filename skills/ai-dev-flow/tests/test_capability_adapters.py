import importlib.util
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[3]
SKILL_ROOT = ROOT / "skills" / "ai-dev-flow"
SCRIPT = SKILL_ROOT / "adapters" / "loader.py"
SPEC = importlib.util.spec_from_file_location("adapter_loader", SCRIPT)
adapter_loader = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter_loader)


class CapabilityAdapterTests(unittest.TestCase):
    def select(self, adapter, **kwargs):
        return adapter_loader.select_review_recipe(
            adapter,
            frozen_diff=True,
            stable_finding_ids=True,
            **kwargs,
        )

    def test_initial_adapters_are_data_only_and_select_by_capability(self):
        adapters = adapter_loader.load_adapter_directory(SKILL_ROOT / "adapters")
        by_id = {item["adapter_id"]: item for item in adapters}
        self.assertEqual(
            {"generic", "codex", "kimi-code", "opencode", "zcode"},
            set(by_id),
        )
        self.assertEqual("R2", self.select(by_id["codex"]))
        self.assertEqual("R3", self.select(by_id["kimi-code"]))
        self.assertEqual("R3", self.select(by_id["opencode"]))
        self.assertEqual("R5", self.select(by_id["generic"]))
        self.assertEqual("R5", self.select(by_id["zcode"]))

    def test_synthetic_adapter_onboards_without_core_change(self):
        core_before = (SKILL_ROOT / "policy" / "core.json").read_bytes()
        synthetic = adapter_loader.load_adapter(
            SKILL_ROOT / "tests" / "fixtures" / "adapters" / "test-harness.json"
        )
        self.assertEqual("test-harness", synthetic["adapter_id"])
        self.assertEqual("R1", self.select(synthetic))
        self.assertEqual(core_before, (SKILL_ROOT / "policy" / "core.json").read_bytes())

    def test_cross_harness_recipe_requires_explicit_authority(self):
        generic = adapter_loader.load_adapter(SKILL_ROOT / "adapters" / "generic.json")
        codex = adapter_loader.load_adapter(SKILL_ROOT / "adapters" / "codex.json")
        self.assertEqual("R5", self.select(generic))
        self.assertEqual(
            "R5",
            self.select(generic, cross_harness_authorized=True),
        )
        self.assertEqual(
            "R4",
            self.select(
                generic,
                cross_harness_authorized=True,
                external_adapter=codex,
            ),
        )

    def test_invocation_evidence_and_contradictory_capability_fail_closed(self):
        codex = adapter_loader.load_adapter(SKILL_ROOT / "adapters" / "codex.json")
        self.assertEqual("R5", adapter_loader.select_review_recipe(codex))
        self.assertEqual(
            "R5",
            adapter_loader.select_review_recipe(codex, frozen_diff=True),
        )
        contradictory = dict(codex)
        contradictory["read_files"] = False
        self.assertEqual("R5", self.select(contradictory))
        generic = adapter_loader.load_adapter(SKILL_ROOT / "adapters" / "generic.json")
        self.assertEqual(
            "R5",
            self.select(
                generic,
                cross_harness_authorized=True,
                external_adapter=contradictory,
            ),
        )

    def test_unknown_fields_and_invalid_enums_fail_closed(self):
        value = json.loads((SKILL_ROOT / "adapters" / "codex.json").read_text(encoding="utf-8"))
        cases = []
        unknown = dict(value)
        unknown["model"] = "not-a-governance-input"
        cases.append(unknown)
        invalid = dict(value)
        invalid["write_isolation"] = "best_effort"
        cases.append(invalid)
        with tempfile.TemporaryDirectory() as temp:
            for index, case in enumerate(cases):
                path = pathlib.Path(temp) / f"adapter-{index}.json"
                path.write_text(json.dumps(case), encoding="utf-8")
                with self.subTest(index=index), self.assertRaises(adapter_loader.AdapterLoadError):
                    adapter_loader.load_adapter(path)


if __name__ == "__main__":
    unittest.main()
