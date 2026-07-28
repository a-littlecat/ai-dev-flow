from __future__ import annotations

import copy
import json
import sys
import threading
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
BACKEND_ROOT = REPO_ROOT / "dashboard" / "backend"
SRC_ROOT = BACKEND_ROOT / "src"
CONTRACTS_ROOT = REPO_ROOT / "dashboard" / "contracts"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ai_dev_flow_dashboard.core import canonical_bytes, snapshot_revision  # noqa: E402
from ai_dev_flow_dashboard.core.models import primitive  # noqa: E402
from ai_dev_flow_dashboard.snapshot import PublishedSnapshot, SnapshotCoordinator  # noqa: E402
from be001.support import task  # noqa: E402


def snapshot_with_task(task_id: str = "TEST-001", **task_overrides):
    path = CONTRACTS_ROOT / "fixtures" / "v1" / "fresh.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    node = primitive(task(task_id, **task_overrides))
    value["tasks"] = [node]
    value["summary"]["task_total"] = 1
    if node["lifecycle"]:
        value["summary"]["counts_by_lifecycle"][node["lifecycle"]] = 1
    value["generated_at"] = "2026-07-28T00:00:00.000Z"
    value["revision"] = snapshot_revision(value)
    return value


def changed_snapshot(value, **task_changes):
    result = copy.deepcopy(value)
    result["tasks"][0].update(task_changes)
    result["generated_at"] = "2026-07-28T00:00:01.000Z"
    result["revision"] = snapshot_revision(result)
    return result


def coordinator_with_snapshot(snapshot):
    coordinator = SnapshotCoordinator(REPO_ROOT)
    record = PublishedSnapshot(
        snapshot=snapshot,
        payload=canonical_bytes(snapshot),
        etag=f'"sha256-{snapshot["revision"]}"',
        previous_revision=None,
        changed_task_ids=tuple(item["task_id"] for item in snapshot["tasks"]),
    )
    with coordinator._condition:
        coordinator._current = record
        coordinator._last_refresh_at = "2026-07-28T00:00:00.000Z"
    coordinator.set_server_state("ready")
    coordinator.set_watcher_state("ready")
    return coordinator


def publish_successor(coordinator, snapshot, previous_revision, changed_ids=("TEST-001",)):
    record = PublishedSnapshot(
        snapshot=snapshot,
        payload=canonical_bytes(snapshot),
        etag=f'"sha256-{snapshot["revision"]}"',
        previous_revision=previous_revision,
        changed_task_ids=tuple(changed_ids),
    )
    with coordinator._condition:
        coordinator._current = record
        coordinator._condition.notify_all()
    return record


def run_server(server):
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return thread
