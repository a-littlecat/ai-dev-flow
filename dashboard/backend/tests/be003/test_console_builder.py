from __future__ import annotations

import copy
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

from ai_dev_flow_dashboard.console import ConsoleBuilder
from ai_dev_flow_dashboard.core.actions import ActionEngine
from ai_dev_flow_dashboard.core.models import primitive
from ai_dev_flow_dashboard.core.schema_validator import validate_contract
from ai_dev_flow_dashboard.runtime import RuntimeSessionError, RuntimeSessionStore
from be002 import support


class Clock:
    def __init__(self):
        self.value = dt.datetime(2026, 8, 8, 12, 0, tzinfo=dt.timezone.utc)

    def __call__(self):
        return self.value


class ConsoleBuilderTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.project = root / "project"
        (self.project / "docs" / "tasks").mkdir(parents=True)
        self.clock = Clock()
        self.store = RuntimeSessionStore(
            self.project,
            runtime_root=root / "runtime",
            now=self.clock,
        )

    def tearDown(self):
        self.temporary.cleanup()

    def published(self, snapshot):
        return support.coordinator_with_snapshot(snapshot).current()

    def test_live_waiting_blocked_and_stale_sessions_are_separate(self):
        snapshot = support.snapshot_with_task()
        self.store.start(
            session_id="live",
            task_id="TEST-001",
            harness_id="codex",
            phase="validating",
            next_step="tests",
            status_summary="正在验证 Console",
        )
        console = ConsoleBuilder(self.store).build(self.published(snapshot))
        validate_contract(console)
        self.assertEqual(["TEST-001"], [item["task_id"] for item in console["active_work"]])
        self.assertEqual("正在验证 Console", console["active_work"][0]["status_summary"])
        self.assertEqual(["task", "runtime"], console["active_work"][0]["source_kinds"])
        self.store.wait("live", "user check")
        console = ConsoleBuilder(self.store).build(self.published(snapshot))
        self.assertEqual(1, console["counts"]["human_attention"])
        self.store.update("live", phase="blocked", next_step="need evidence")
        console = ConsoleBuilder(self.store).build(self.published(snapshot))
        self.assertEqual(1, console["counts"]["blocked"])
        self.store.update("live", phase="implementing")
        self.clock.value += dt.timedelta(seconds=181)
        console = ConsoleBuilder(self.store).build(self.published(snapshot))
        self.assertEqual(0, console["counts"]["active_work"])
        self.assertEqual(1, console["counts"]["stale_sessions"])

    def test_inconsistent_done_record_is_invalid_and_ready_task_stays_visible(self):
        snapshot = support.snapshot_with_task(lifecycle="Ready")
        node = support.task("TEST-001", lifecycle="Ready")
        snapshot["actions"] = list(primitive(ActionEngine().recommend((node,), (), ())))
        self.store.start(
            session_id="inconsistent-done",
            task_id="TEST-001",
            harness_id="codex",
            phase="implementing",
            next_step="work",
        )
        path = self.store.sessions_dir / "inconsistent-done.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["phase"] = "done"
        path.write_text(json.dumps(payload), encoding="utf-8")

        console = ConsoleBuilder(self.store).build(self.published(snapshot))

        self.assertEqual(1, console["counts"]["stale_sessions"])
        self.assertEqual(1, console["counts"]["ready_queue"])
        self.assertEqual("TEST-001", console["ready_queue"][0]["task_id"])
        with self.assertRaisesRegex(RuntimeSessionError, "terminal state is inconsistent"):
            self.store.heartbeat("inconsistent-done")

    def test_builder_defense_does_not_assign_live_done_session(self):
        snapshot = support.snapshot_with_task(lifecycle="Ready")
        node = support.task("TEST-001", lifecycle="Ready")
        snapshot["actions"] = list(primitive(ActionEngine().recommend((node,), (), ())))
        session = self.store.start(
            session_id="defensive-done",
            task_id="TEST-001",
            harness_id="codex",
            phase="implementing",
            next_step="work",
        )
        with unittest.mock.patch.object(
            self.store,
            "list",
            return_value=[{**session, "phase": "done", "freshness": "live"}],
        ):
            console = ConsoleBuilder(self.store).build(self.published(snapshot))

        self.assertEqual(1, console["counts"]["stale_sessions"])
        self.assertEqual(1, console["counts"]["ready_queue"])

    def test_task_only_active_ready_blocked_sorting_and_ambiguity(self):
        snapshot = support.snapshot_with_task(lifecycle="In Progress", priority="low")
        node = support.task("TEST-001", lifecycle="In Progress", priority="low")
        snapshot["actions"] = list(primitive(ActionEngine().recommend((node,), (), ())))
        active = ConsoleBuilder(self.store).build(self.published(snapshot))
        self.assertEqual("continue", active["active_work"][0]["action_kind"])
        self.assertEqual("needs_authority", active["active_work"][0]["action_eligibility"])
        self.assertEqual(0, active["counts"]["human_attention"])
        self.assertIn(
            "TASK_IN_PROGRESS_WITHOUT_LIVE_SESSION",
            active["active_work"][0]["why_now_codes"],
        )
        self.assertEqual("任务正在进行", active["active_work"][0]["status_summary"])
        base = copy.deepcopy(snapshot["tasks"][0])
        high = {**base, "task_id": "READY-HIGH", "title": "high", "lifecycle": "Ready", "priority": "high"}
        low = {**base, "task_id": "READY-LOW", "title": "low", "lifecycle": "Ready", "priority": "low"}
        snapshot["tasks"] = [low, high]
        snapshot["actions"] = [
            {
                "action_id": f"A-{task['task_id']}",
                "task_id": task["task_id"],
                "action_kind": "execute",
                "eligibility": "actionable",
                "reason_codes": ["DEPENDENCIES_SATISFIED"],
                "blocking_task_ids": [],
                "blocking_condition_ids": [],
                "related_diagnostic_ids": [],
                "required_authority": "execution",
                "authority_state": "present",
                "evidence": [],
            }
            for task in (low, high)
        ]
        ready = ConsoleBuilder(self.store).build(self.published(snapshot))
        self.assertEqual(["READY-HIGH", "READY-LOW"], [item["task_id"] for item in ready["ready_queue"]])
        self.assertTrue(ready["ready_ambiguity"]["has_unique_primary"])
        self.assertEqual(1, ready["ready_ambiguity"]["candidate_count"])
        snapshot["tasks"][0]["priority"] = "high"
        tied = ConsoleBuilder(self.store).build(self.published(snapshot))
        self.assertFalse(tied["ready_ambiguity"]["has_unique_primary"])
        self.assertEqual(2, tied["ready_ambiguity"]["candidate_count"])
        snapshot["tasks"][0]["lifecycle"] = "Blocked"
        snapshot["actions"][0]["action_kind"] = "none"
        snapshot["actions"][0]["eligibility"] = "unknown"
        blocked = ConsoleBuilder(self.store).build(self.published(snapshot))
        self.assertEqual("READY-LOW", blocked["blocked"][0]["task_id"])

    def test_ready_queue_prefers_downstream_unblocking_and_authority_is_human_attention(self):
        snapshot = support.snapshot_with_task()
        base = copy.deepcopy(snapshot["tasks"][0])
        task_a = {**base, "task_id": "READY-A", "title": "a", "lifecycle": "Ready", "priority": "medium"}
        task_b = {**base, "task_id": "READY-B", "title": "b", "lifecycle": "Ready", "priority": "medium"}
        snapshot["tasks"] = [task_a, task_b]
        snapshot["edges"] = [
            {"type": "depends_on", "source_task_id": "DOWN-1", "target_task_id": "READY-B"},
            {"type": "depends_on", "source_task_id": "DOWN-2", "target_task_id": "READY-B"},
        ]
        snapshot["actions"] = [
            {
                "task_id": "READY-A",
                "action_kind": "execute",
                "eligibility": "actionable",
                "reason_codes": [],
                "blocking_task_ids": [],
            },
            {
                "task_id": "READY-B",
                "action_kind": "execute",
                "eligibility": "actionable",
                "reason_codes": [],
                "blocking_task_ids": [],
            },
        ]
        result = ConsoleBuilder(self.store).build(self.published(snapshot))
        self.assertEqual(["READY-B", "READY-A"], [item["task_id"] for item in result["ready_queue"]])
        snapshot["tasks"] = [{**task_a, "lifecycle": "Review"}]
        snapshot["edges"] = []
        snapshot["actions"] = [
            {
                "task_id": "READY-A",
                "action_kind": "merge",
                "eligibility": "needs_authority",
                "reason_codes": ["MERGE_AUTHORITY_MISSING"],
                "blocking_task_ids": [],
            }
        ]
        result = ConsoleBuilder(self.store).build(self.published(snapshot))
        self.assertEqual("READY-A", result["human_attention"][0]["task_id"])

    def test_multiple_actions_are_preserved_and_blocked_wins_over_ready(self):
        snapshot = support.snapshot_with_task(lifecycle="Ready")
        snapshot["actions"] = [
            {
                "task_id": "TEST-001",
                "action_kind": "execute",
                "eligibility": "actionable",
                "reason_codes": ["DEPENDENCIES_SATISFIED"],
                "blocking_task_ids": [],
            },
            {
                "task_id": "TEST-001",
                "action_kind": "review",
                "eligibility": "blocked",
                "reason_codes": ["REVIEW_INPUT_BLOCKED"],
                "blocking_task_ids": ["BASE-001"],
            },
        ]
        result = ConsoleBuilder(self.store).build(self.published(snapshot))
        self.assertEqual(0, result["counts"]["ready_queue"])
        item = result["blocked"][0]
        self.assertEqual(["execute", "review"], item["action_kinds"])
        self.assertEqual(["actionable", "blocked"], item["action_eligibilities"])
        self.assertEqual(["BASE-001"], item["blocking_task_ids"])

    def test_real_action_engine_output_uses_formal_eligibility_values(self):
        snapshot = support.snapshot_with_task(lifecycle="Ready")
        node = support.task("TEST-001", lifecycle="Ready")
        recommendations = ActionEngine().recommend((node,), (), ())
        snapshot["actions"] = list(primitive(recommendations))
        result = ConsoleBuilder(self.store).build(self.published(snapshot))
        item = result["ready_queue"][0]
        self.assertEqual("needs_authority", item["action_eligibility"])
        self.assertEqual(["needs_authority"], item["action_eligibilities"])
        self.assertEqual("execute", item["action_kind"])
        self.assertEqual(0, result["counts"]["human_attention"])
        self.assertEqual("可以作为下一项开始", item["status_summary"])
        self.assertEqual("尚未授权自动执行", item["next_step"])
        self.assertEqual(["task"], item["source_kinds"])

    def test_ready_ambiguity_ignores_active_work_in_real_action_chain(self):
        snapshot = support.snapshot_with_task(
            task_id="ACTIVE-001", lifecycle="In Progress", priority="high"
        )
        base = copy.deepcopy(snapshot["tasks"][0])
        ready_a = {**base, "task_id": "READY-A", "title": "a", "lifecycle": "Ready"}
        ready_b = {**base, "task_id": "READY-B", "title": "b", "lifecycle": "Ready"}
        snapshot["tasks"].extend((ready_a, ready_b))
        nodes = (
            support.task("ACTIVE-001", lifecycle="In Progress", priority="high"),
            support.task("READY-A", lifecycle="Ready", priority="high"),
            support.task("READY-B", lifecycle="Ready", priority="high"),
        )
        snapshot["actions"] = list(primitive(ActionEngine().recommend(nodes, (), ())))
        self.store.start(
            session_id="active-real-chain",
            task_id="ACTIVE-001",
            harness_id="codex",
            phase="implementing",
            next_step="work",
        )

        result = ConsoleBuilder(self.store).build(self.published(snapshot))

        self.assertEqual(1, result["counts"]["active_work"])
        self.assertEqual(2, result["counts"]["ready_queue"])
        self.assertFalse(result["ready_ambiguity"]["has_unique_primary"])
        self.assertEqual(2, result["ready_ambiguity"]["candidate_count"])

    def test_ready_ambiguity_is_empty_when_only_active_work_exists(self):
        snapshot = support.snapshot_with_task(lifecycle="In Progress", priority="high")
        node = support.task("TEST-001", lifecycle="In Progress", priority="high")
        snapshot["actions"] = list(primitive(ActionEngine().recommend((node,), (), ())))
        self.store.start(
            session_id="active-only-real-chain",
            task_id="TEST-001",
            harness_id="codex",
            phase="implementing",
            next_step="work",
        )

        result = ConsoleBuilder(self.store).build(self.published(snapshot))

        self.assertEqual(1, result["counts"]["active_work"])
        self.assertEqual(0, result["counts"]["ready_queue"])
        self.assertFalse(result["ready_ambiguity"]["has_unique_primary"])
        self.assertEqual(0, result["ready_ambiguity"]["candidate_count"])

    def test_active_work_same_priority_sorts_by_recent_activity_descending(self):
        snapshot = support.snapshot_with_task(lifecycle="In Progress", priority="medium")
        second = {**copy.deepcopy(snapshot["tasks"][0]), "task_id": "TEST-002", "title": "second"}
        snapshot["tasks"].append(second)
        self.store.start(session_id="older", task_id="TEST-001", harness_id="codex", phase="implementing", next_step="work")
        self.clock.value += dt.timedelta(seconds=1)
        self.store.start(session_id="newer", task_id="TEST-002", harness_id="codex", phase="implementing", next_step="work")
        result = ConsoleBuilder(self.store).build(self.published(snapshot))
        self.assertEqual(["TEST-002", "TEST-001"], [item["task_id"] for item in result["active_work"]])

    def test_unknown_live_session_is_visible_as_blocked(self):
        self.store.start(
            session_id="unknown-task",
            task_id="MISSING-001",
            harness_id="codex",
            phase="implementing",
            next_step="work",
        )
        result = ConsoleBuilder(self.store).build(
            self.published(support.snapshot_with_task())
        )
        self.assertEqual("unknown-task", result["blocked"][0]["session_id"])

    def test_console_contains_allowlisted_fields_only_and_revision_is_stable(self):
        snapshot = support.snapshot_with_task()
        console_a = ConsoleBuilder(self.store).build(self.published(snapshot))
        console_b = ConsoleBuilder(self.store).build(self.published(snapshot))
        self.assertEqual(console_a["revision"], console_b["revision"])
        serialized = str(console_a).casefold()
        for forbidden in ("prompt", "token", "secret", "stdout", "environment", "shell"):
            self.assertNotIn(forbidden, serialized)

    def test_source_kinds_include_git_only_when_git_provenance_participates(self):
        snapshot = support.snapshot_with_task(lifecycle="Ready")
        snapshot["tasks"][0]["provenance"] = [
            {
                "source_path": ".git/HEAD",
                "heading": None,
                "field": "lifecycle",
                "line": 1,
                "raw_value": "Ready",
                "source_type": "git",
            }
        ]
        node = support.task("TEST-001", lifecycle="Ready")
        snapshot["actions"] = list(primitive(ActionEngine().recommend((node,), (), ())))

        item = ConsoleBuilder(self.store).build(self.published(snapshot))["ready_queue"][0]

        self.assertEqual(["task", "git"], item["source_kinds"])

    def test_snapshot_changes_are_included_without_runtime_sessions(self):
        snapshot = support.snapshot_with_task()
        console = ConsoleBuilder(self.store).build(self.published(snapshot))
        self.assertIsNone(console["freshness"]["runtime_facts_at"])
        self.assertEqual(
            {
                "task_id": "TEST-001",
                "session_id": None,
                "kind": "task_snapshot",
                "at": snapshot["generated_at"],
            },
            console["recent_changes"][0],
        )
        validate_contract(console)


if __name__ == "__main__":
    unittest.main()
