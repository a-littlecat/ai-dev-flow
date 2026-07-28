from __future__ import annotations

import ast
import sys
import unittest

from be001.support import REPO_ROOT


class ImplementationBoundaryTests(unittest.TestCase):
    def test_runtime_declares_no_third_party_dependencies(self):
        pyproject = (REPO_ROOT / "dashboard" / "backend" / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("dependencies = []", pyproject)

    def test_core_imports_are_standard_library_or_package_local(self):
        core = (
            REPO_ROOT
            / "dashboard"
            / "backend"
            / "src"
            / "ai_dev_flow_dashboard"
            / "core"
        )
        local_modules = {"ai_dev_flow_dashboard"}
        forbidden = {"git", "http", "socket", "watchdog", "requests", "flask", "fastapi"}
        for path in sorted(core.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = {alias.name.split(".", 1)[0] for alias in node.names}
                elif isinstance(node, ast.ImportFrom):
                    if node.level:
                        continue
                    names = {(node.module or "").split(".", 1)[0]}
                else:
                    continue
                for name in names:
                    self.assertNotIn(name, forbidden, f"{path.name} imports forbidden surface {name}")
                    self.assertTrue(
                        name in sys.stdlib_module_names or name in local_modules,
                        f"{path.name} imports non-standard dependency {name}",
                    )

    def test_core_does_not_expose_server_watcher_or_git_execution_modules(self):
        package = (
            REPO_ROOT
            / "dashboard"
            / "backend"
            / "src"
            / "ai_dev_flow_dashboard"
            / "core"
        )
        names = {path.stem for path in package.glob("*.py")}
        self.assertFalse(names & {"server", "http", "sse", "watcher", "git", "frontend"})


if __name__ == "__main__":
    unittest.main()
