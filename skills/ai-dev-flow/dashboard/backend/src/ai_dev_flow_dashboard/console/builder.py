"""Single queue engine shared by the HTTP API and CLI."""

from __future__ import annotations

import datetime as dt
from typing import Any

from ai_dev_flow_dashboard.core.canonical import canonical_sha256
from ai_dev_flow_dashboard.runtime import RuntimeSessionStore


DISCLAIMER = "Project Console 是只读投影；TASK、Git、Review、UA 与 authority 仍由各自事实源决定。"
PRIORITY = {"high": 0, "medium": 1, "low": 2}


class ConsoleBuilder:
    def __init__(self, runtime_store: RuntimeSessionStore) -> None:
        self.runtime_store = runtime_store

    def build(self, published) -> dict[str, Any]:
        snapshot = published.snapshot
        tasks = {item["task_id"]: item for item in snapshot["tasks"]}
        actions_by_task: dict[str, list[dict[str, Any]]] = {}
        for action in snapshot["actions"]:
            actions_by_task.setdefault(action["task_id"], []).append(action)
        sessions = self.runtime_store.list()
        unblocks = {
            task_id: sum(
                1
                for edge in snapshot["edges"]
                if edge.get("type") == "depends_on"
                and edge.get("target_task_id") == task_id
            )
            for task_id in tasks
        }
        queues: dict[str, list[dict[str, Any]]] = {
            "active_work": [],
            "human_attention": [],
            "ready_queue": [],
            "blocked": [],
            "stale_sessions": [],
        }
        assigned: set[str] = set()

        for session in sessions:
            task = tasks.get(session.get("task_id"))
            if session["freshness"] in {"stale", "invalid"}:
                queues["stale_sessions"].append(
                    self._session_item(session, task, "stale_sessions")
                )
                continue
            if session["freshness"] == "ended":
                continue
            if task is None:
                queues["blocked"].append(
                    self._session_item(session, None, "blocked")
                )
                continue
            task_id = task["task_id"]
            actions = actions_by_task.get(task_id, [])
            if session["phase"] == "waiting_user":
                queues["human_attention"].append(
                    self._item(task, actions, session, "human_attention", ("WAITING_USER",), unblocks[task_id])
                )
            elif session["phase"] == "blocked":
                queues["blocked"].append(
                    self._item(task, actions, session, "blocked", ("RUNTIME_BLOCKED",), unblocks[task_id])
                )
            elif session["phase"] != "done":
                queues["active_work"].append(
                    self._item(task, actions, session, "active_work", ("ACTIVE_RUNTIME_SESSION",), unblocks[task_id])
                )
            assigned.add(task_id)

        for task_id, task in tasks.items():
            if task_id in assigned:
                continue
            actions = actions_by_task.get(task_id, [])
            lifecycle = task.get("lifecycle")
            reason_codes = tuple(
                code for action in actions for code in action.get("reason_codes", ())
            )
            eligibilities = {action.get("eligibility") for action in actions}
            action_kinds = {action.get("action_kind") for action in actions}
            ready_execute = lifecycle == "Ready" and any(
                action.get("action_kind") == "execute"
                and action.get("eligibility") in {"actionable", "needs_authority"}
                for action in actions
            )
            if lifecycle == "Blocked" or eligibilities & {"blocked", "unknown"}:
                queues["blocked"].append(
                    self._item(
                        task,
                        actions,
                        None,
                        "blocked",
                        reason_codes or ("TASK_BLOCKED",),
                        unblocks[task_id],
                    )
                )
            elif ready_execute:
                queues["ready_queue"].append(
                    self._item(task, actions, None, "ready_queue", reason_codes, unblocks[task_id])
                )
            elif "user_decision" in action_kinds or "needs_authority" in eligibilities:
                queues["human_attention"].append(
                    self._item(task, actions, None, "human_attention", reason_codes, unblocks[task_id])
                )
            elif lifecycle == "In Progress":
                queues["active_work"].append(
                    self._item(
                        task,
                        actions,
                        None,
                        "active_work",
                        ("TASK_IN_PROGRESS_WITHOUT_LIVE_SESSION",),
                        unblocks[task_id],
                    )
                )

        queues["human_attention"].sort(key=self._human_key)
        queues["active_work"].sort(key=self._activity_key)
        queues["ready_queue"].sort(key=self._ready_key)
        queues["blocked"].sort(key=self._activity_key)
        queues["stale_sessions"].sort(key=self._activity_key)
        candidates = [
            (self._primary_candidate_key(item), item)
            for name in ("active_work", "human_attention", "ready_queue")
            for item in queues[name]
        ]
        highest_candidates = []
        if candidates:
            highest_rank = min(rank for rank, _item in candidates)
            highest_candidates = [item for rank, item in candidates if rank == highest_rank]
        generated_at = snapshot["generated_at"]
        runtime_at = max(
            (item.get("updated_at") for item in sessions if item.get("updated_at")),
            default=None,
        )
        if runtime_at is not None:
            generated_at = max(generated_at, runtime_at)
        payload = {
            "schema_version": "adf/project-console/v1",
            "revision": "0" * 64,
            "snapshot_revision": published.revision,
            "generated_at": generated_at,
            "state": snapshot["state"],
            "freshness": {
                "task_facts_at": snapshot["generated_at"],
                "git_facts_at": snapshot["generated_at"],
                "runtime_facts_at": runtime_at,
            },
            "counts": {name: len(items) for name, items in queues.items()},
            **queues,
            "recent_changes": self._recent_changes(published, sessions),
            "ambiguity": {
                "has_unique_primary": len(highest_candidates) == 1,
                "candidate_count": len(highest_candidates),
                "message": (
                    "当前有唯一主候选"
                    if len(highest_candidates) == 1
                    else "当前没有唯一主任务"
                ),
            },
            "disclaimer": DISCLAIMER,
        }
        payload["revision"] = canonical_sha256(payload)
        return payload

    @staticmethod
    def _recent_changes(published, sessions):
        changes = [
            {
                "task_id": task_id,
                "session_id": None,
                "kind": "task_snapshot",
                "at": published.snapshot["generated_at"],
            }
            for task_id in published.changed_task_ids
        ]
        changes.extend(
            {
                "task_id": item.get("task_id"),
                "session_id": item["session_id"],
                "kind": "runtime_session",
                "at": item.get("updated_at") or published.snapshot["generated_at"],
            }
            for item in sessions
        )
        changes.sort(
            key=lambda item: (
                item["task_id"] or "",
                item["session_id"] or "",
                item["kind"],
            )
        )
        changes.sort(key=lambda item: item["at"], reverse=True)
        return changes[:20]

    def _item(self, task, actions, session, queue, why, unblocks_count=0):
        actions = list(actions or ())
        action = self._representative_action(actions)
        reasons = tuple(
            code for item in actions for code in item.get("reason_codes", ())
        )
        blocking_tasks = sorted(
            {
                task_id
                for item in actions
                for task_id in item.get("blocking_task_ids", ())
            }
        )
        return {
            "task_id": task["task_id"],
            "title": task["title"],
            "queue": queue,
            "actor": "user" if queue == "human_attention" else "agent",
            "session_id": session.get("session_id") if session else None,
            "harness_id": session.get("harness_id") if session else None,
            "phase": session.get("phase") if session else None,
            "next_step": (
                session.get("next_step")
                if session
                else self._next_step(action, queue)
            ),
            "status_summary": (
                session.get("status_summary") or self._status_summary(task, action, queue)
                if session
                else self._status_summary(task, action, queue)
            ),
            "why_now_codes": list(dict.fromkeys((*why, *reasons))),
            "blocking_task_ids": blocking_tasks,
            "unblocks_count": unblocks_count,
            "priority": task.get("priority") or "medium",
            "last_activity_at": session.get("updated_at") if session else None,
            "freshness": session.get("freshness") if session else task.get("freshness", "fresh"),
            "source_kinds": ["task", "git", *( ["runtime"] if session else [] )],
            "branch": session.get("branch") if session else None,
            "worktree": session.get("worktree") if session else None,
            "action_kind": (action or {}).get("action_kind", "none"),
            "action_eligibility": (action or {}).get("eligibility", "unknown"),
            "action_kinds": sorted(
                {item.get("action_kind", "none") for item in actions}
            ),
            "action_eligibilities": sorted(
                {item.get("eligibility", "unknown") for item in actions}
            ),
        }

    def _session_item(self, session, task, queue):
        if task is not None:
            return self._item(
                task,
                (),
                session,
                queue,
                ("STALE_RUNTIME_SESSION" if session["freshness"] == "stale" else "INVALID_RUNTIME_SESSION",),
            )
        return {
            "task_id": session.get("task_id"),
            "title": "无效或未绑定的运行时会话",
            "queue": queue,
            "actor": "agent",
            "session_id": session["session_id"],
            "harness_id": session.get("harness_id"),
            "phase": session.get("phase"),
            "next_step": "需要补充证据",
            "status_summary": session.get("status_summary") or "运行时会话无效或未绑定",
            "why_now_codes": session.get("error_codes", ["STALE_RUNTIME_SESSION"]),
            "blocking_task_ids": [],
            "unblocks_count": 0,
            "priority": "medium",
            "last_activity_at": session.get("updated_at"),
            "freshness": session["freshness"],
            "source_kinds": ["runtime"],
            "branch": session.get("branch"),
            "worktree": session.get("worktree"),
            "action_kind": "none",
            "action_eligibility": "unknown",
            "action_kinds": [],
            "action_eligibilities": [],
        }

    @staticmethod
    def _representative_action(actions):
        rank = {
            "needs_authority": 0,
            "blocked": 1,
            "unknown": 2,
            "actionable": 3,
            "not_applicable": 4,
        }
        return min(
            actions,
            key=lambda item: (
                rank.get(item.get("eligibility"), 5),
                item.get("action_kind", ""),
            ),
            default=None,
        )

    @staticmethod
    def _next_step(action, queue):
        if queue == "blocked":
            return "需要补充证据"
        if not action:
            return "核对 TASK 与运行时状态"
        return {
            "execute": "继续执行任务",
            "review": "进行独立 Review",
            "user_decision": "等待用户决定",
            "merge": "等待 merge authority",
            "release": "等待 release authority",
            "close": "等待 close authority",
        }.get(action.get("action_kind"), "核对下一步")

    @staticmethod
    def _status_summary(task, action, queue):
        if queue == "active_work":
            return "任务正在进行"
        if queue == "human_attention":
            return "任务等待用户处理"
        if queue == "ready_queue":
            return "任务已就绪，可以开始"
        if queue == "blocked":
            return "任务当前受阻"
        return str(task.get("lifecycle") or (action or {}).get("action_kind") or "状态待核对")

    @staticmethod
    def _human_key(item):
        rank = (
            0
            if item.get("phase") == "waiting_user"
            else 1
            if "user_decision" in item.get("action_kinds", ())
            else 2
        )
        return (rank, PRIORITY.get(item["priority"], 1), item["task_id"] or "")

    @staticmethod
    def _activity_key(item):
        return (
            PRIORITY.get(item["priority"], 1),
            ConsoleBuilder._descending_time(item.get("last_activity_at")),
            item.get("task_id") or "",
        )

    @staticmethod
    def _ready_key(item):
        return (
            PRIORITY.get(item["priority"], 1),
            -item.get("unblocks_count", 0),
            ConsoleBuilder._descending_time(item.get("last_activity_at")),
            item.get("task_id") or "",
        )

    @staticmethod
    def _descending_time(value):
        if not value:
            return float("inf")
        return -dt.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()

    @staticmethod
    def _primary_candidate_key(item):
        queue = item["queue"]
        priority = PRIORITY.get(item["priority"], 1)
        activity = ConsoleBuilder._descending_time(item.get("last_activity_at"))
        if queue == "active_work":
            return (0, priority, activity)
        if queue == "human_attention":
            human_rank = 0 if item.get("phase") == "waiting_user" else 1 if "user_decision" in item.get("action_kinds", ()) else 2
            return (1, human_rank, priority)
        return (2, priority, -item.get("unblocks_count", 0), activity)
