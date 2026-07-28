from __future__ import annotations

import unittest

from be001.support import profile, task, worktree
from ai_dev_flow_dashboard.core.ownership import (
    resolve_dirty_ownership,
    resolve_dirty_ownership_for_tasks,
)


class DirtyOwnershipTests(unittest.TestCase):
    def resolve(self, left_paths, *, left_scopes=("dir:src/left space",), **overrides):
        tasks = (
            task(
                "LEFT",
                branch_hint="codex/left",
                write_scope=left_scopes,
            ),
            task(
                "RIGHT",
                branch_hint="codex/right",
                write_scope=("dir:src/right",),
            ),
        )
        profiles = {
            "LEFT": profile(
                scopes=left_scopes,
                values={"branch_hint": "codex/left"},
            ),
            "RIGHT": profile(
                scopes=("dir:src/right",),
                values={"branch_hint": "codex/right"},
            ),
        }
        left_worktree = {
            "branch": "refs/heads/codex/left",
            "dirty_state": "dirty",
            "dirty_paths": left_paths,
        }
        left_worktree.update(overrides)
        evidence = {
            "LEFT": worktree(
                "LEFT",
                **left_worktree,
            ),
            "RIGHT": worktree(
                "RIGHT",
                branch="refs/heads/codex/right",
            ),
        }
        return resolve_dirty_ownership(tasks, profiles, evidence)

    def test_unique_owned_paths_cover_unicode_spaces_casefold_rename_and_submodule(self):
        resolved = self.resolve(
            (
                "SRC/LEFT SPACE/Café.py",
                "src/left space/renamed-old.py",
                "src/left space/renamed-new.py",
                "src/left space/vendor-submodule",
            )
        )
        self.assertEqual("owned_by_task", resolved["LEFT"].dirty_ownership)
        self.assertEqual("clean", resolved["RIGHT"].dirty_ownership)

    def test_out_of_scope_and_other_task_scope_are_unowned(self):
        outside = self.resolve(("src/outside.py",))
        self.assertEqual("unowned", outside["LEFT"].dirty_ownership)
        shared = self.resolve(
            ("src/shared/file.py",),
            left_scopes=("dir:src/shared",),
        )
        tasks = (
            task("LEFT", branch_hint="codex/left", write_scope=("dir:src/shared",)),
            task("RIGHT", branch_hint="codex/right", write_scope=("file:src/shared/file.py",)),
        )
        profiles = {
            "LEFT": profile(
                scopes=("dir:src/shared",),
                values={"branch_hint": "codex/left"},
            ),
            "RIGHT": profile(
                scopes=("file:src/shared/file.py",),
                values={"branch_hint": "codex/right"},
            ),
        }
        shared = resolve_dirty_ownership(tasks, profiles, shared)
        self.assertEqual("unowned", shared["LEFT"].dirty_ownership)

    def test_invalid_path_branch_mismatch_and_duplicate_mapping_are_unknown(self):
        invalid = self.resolve(("../escape.py",))
        self.assertEqual("unknown", invalid["LEFT"].dirty_ownership)
        mismatch = self.resolve(
            ("src/left space/file.py",),
            branch="refs/heads/codex/not-left",
        )
        self.assertEqual("unknown", mismatch["LEFT"].dirty_ownership)
        duplicate = self.resolve(("src/left space/file.py",))
        duplicate["RIGHT"] = worktree(
            "RIGHT",
            root=duplicate["LEFT"].root,
            branch="refs/heads/codex/right",
        )
        tasks = (
            task("LEFT", branch_hint="codex/left", write_scope=("dir:src/left space",)),
            task("RIGHT", branch_hint="codex/right", write_scope=("dir:src/right",)),
        )
        profiles = {
            "LEFT": profile(
                scopes=("dir:src/left space",),
                values={"branch_hint": "codex/left"},
            ),
            "RIGHT": profile(
                scopes=("dir:src/right",),
                values={"branch_hint": "codex/right"},
            ),
        }
        duplicate = resolve_dirty_ownership(tasks, profiles, duplicate)
        self.assertEqual("unknown", duplicate["LEFT"].dirty_ownership)

    def test_task_node_adapter_matches_profile_resolution(self):
        resolved = self.resolve(("src/left space/file.py",))
        tasks = (
            task(
                "LEFT",
                branch_hint="codex/left",
                write_scope=("dir:src/left space",),
            ),
            task(
                "RIGHT",
                branch_hint="codex/right",
                write_scope=("dir:src/right",),
            ),
        )
        adapted = resolve_dirty_ownership_for_tasks(tasks, resolved)
        self.assertEqual("owned_by_task", adapted["LEFT"].dirty_ownership)
        self.assertEqual("clean", adapted["RIGHT"].dirty_ownership)


if __name__ == "__main__":
    unittest.main()
