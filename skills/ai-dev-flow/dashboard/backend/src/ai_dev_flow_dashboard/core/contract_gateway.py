"""Adapter around the existing public WorkflowContract facade."""

from __future__ import annotations

import importlib.util
import sys
import threading
from pathlib import Path
from types import ModuleType
from typing import Any

from .canonical import stable_text_id
from .models import (
    ContractGatewayReport,
    CoreContract,
    Diagnostic,
    FrozenProjectInput,
    Provenance,
    primitive,
)


class ContractGatewayError(RuntimeError):
    """The public Workflow Contract facade is unavailable or incompatible."""


_MODULE_LOAD_LOCK = threading.RLock()


def _provenance(item: Any) -> Provenance:
    source_type = str(getattr(item, "source_type", "canonical"))
    return Provenance(
        source_path=str(getattr(item, "path", "")),
        heading=getattr(item, "heading", None),
        field=getattr(item, "field", None),
        line=max(0, int(getattr(item, "line", 0) or 0)),
        raw_value=getattr(item, "raw_value", None),
        source_type={
            "filename": "derived",
            "heading": "canonical",
            "legacy": "legacy_inferred",
        }.get(source_type, source_type),
    )


def _diagnostic(item: Any, task_ids: tuple[str, ...]) -> Diagnostic:
    code = str(getattr(item, "code", "E_CONTRACT_GATEWAY"))
    path = str(getattr(item, "path", ""))
    line = max(0, int(getattr(item, "line", 0) or 0))
    message = str(getattr(item, "message", "Workflow Contract diagnostic"))
    return Diagnostic(
        diagnostic_id=stable_text_id("diagnostic", code, path, str(line), message),
        code=code,
        severity=str(getattr(item, "severity", "error")),
        message=message,
        task_ids=tuple(sorted(set(task_ids))),
        provenance=tuple(_provenance(prov) for prov in getattr(item, "provenance", ())),
    )


class ContractGateway:
    """Call only ``WorkflowContract.inspect(project_root)`` from the public facade."""

    def __init__(self, project_root: str | Path, skill_root: str | Path | None = None):
        self.project_root = Path(project_root).resolve()
        self.skill_root = (
            Path(skill_root).resolve()
            if skill_root is not None
            else (self.project_root / "skills" / "ai-dev-flow").resolve()
        )

    def _load_public_module(self) -> ModuleType:
        public_path = self.skill_root / "scripts" / "workflow_contract.py"
        if not public_path.is_file():
            raise ContractGatewayError(f"public Workflow Contract facade is missing: {public_path}")
        scripts_dir = str(public_path.parent)
        module_name = f"_ai_dev_flow_public_workflow_contract_{stable_text_id(str(public_path))[:16]}"
        existing = sys.modules.get(module_name)
        if existing is not None:
            return existing
        with _MODULE_LOAD_LOCK:
            existing = sys.modules.get(module_name)
            if existing is not None:
                return existing
            spec = importlib.util.spec_from_file_location(module_name, public_path)
            if spec is None or spec.loader is None:
                raise ContractGatewayError("cannot load public Workflow Contract facade")
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            added = scripts_dir not in sys.path
            if added:
                sys.path.insert(0, scripts_dir)
            private_names = ("_workflow_contract", "_task_board")
            previous_private = {
                name: sys.modules.pop(name)
                for name in private_names
                if name in sys.modules
            }
            try:
                spec.loader.exec_module(module)
            except Exception:
                sys.modules.pop(module_name, None)
                raise
            finally:
                for name in private_names:
                    sys.modules.pop(name, None)
                sys.modules.update(previous_private)
                if added:
                    sys.path.remove(scripts_dir)
        if not hasattr(module, "WorkflowContract") or not hasattr(module.WorkflowContract, "inspect"):
            raise ContractGatewayError("public module does not expose WorkflowContract.inspect")
        return module

    def inspect(self, frozen: FrozenProjectInput) -> ContractGatewayReport:
        if frozen.project_root != self.project_root:
            raise ContractGatewayError("frozen input belongs to a different project root")
        if not getattr(frozen.lease_guard, "active", False):
            raise ContractGatewayError("public Workflow Contract inspection requires an active input lease")
        module = self._load_public_module()
        report = module.WorkflowContract.inspect(
            self.project_root,
            frozen_task_texts={
                item.path: item.text
                for item in frozen.tasks
            },
        )

        raw_contracts = tuple(getattr(report, "contracts", ()))
        expected_sources = tuple(sorted(item.source_path for item in frozen.tasks))
        actual_sources = tuple(
            sorted(str(getattr(item, "source_path", "")) for item in raw_contracts)
        )
        if actual_sources != expected_sources:
            raise ContractGatewayError("public Workflow Contract report does not match frozen TASK set")
        source_to_task = {
            str(getattr(item, "source_path", "")): str(dict(getattr(item, "normalized", ())).get("task_id") or "")
            for item in raw_contracts
        }

        def related_tasks(diag: Any) -> tuple[str, ...]:
            candidates = {str(getattr(diag, "path", ""))}
            candidates.update(str(getattr(item, "path", "")) for item in getattr(diag, "provenance", ()))
            return tuple(sorted({source_to_task[path] for path in candidates if source_to_task.get(path)}))

        converted_report_diagnostics = tuple(
            _diagnostic(item, related_tasks(item)) for item in getattr(report, "diagnostics", ())
        )
        report_diag_by_signature = {
            (item.code, tuple(item.task_ids), item.message): item for item in converted_report_diagnostics
        }

        contracts: list[CoreContract] = []
        for item in raw_contracts:
            normalized = tuple((str(key), value if value is None else str(value)) for key, value in item.normalized)
            values = dict(normalized)
            task_id = str(values.get("task_id") or "")
            source_path = str(getattr(item, "source_path", ""))
            local_diagnostics = tuple(
                _diagnostic(diag, (task_id,) if task_id else ()) for diag in getattr(item, "diagnostics", ())
            )
            # Prefer richer public validation diagnostics when the signature is identical.
            local_diagnostics = tuple(
                report_diag_by_signature.get((diag.code, tuple(diag.task_ids), diag.message), diag)
                for diag in local_diagnostics
            )
            contracts.append(
                CoreContract(
                    task_id=task_id,
                    title=str(getattr(item, "title", "") or task_id),
                    source_path=source_path,
                    normalized=normalized,
                    diagnostics=local_diagnostics,
                    provenance=tuple(_provenance(prov) for prov in getattr(item, "provenance", ())),
                )
            )

        summary = getattr(report, "summary", None)
        summary_values = tuple(
            (field, int(getattr(summary, field, 0) or 0))
            for field in ("errors", "violations", "warnings", "exit_code")
        )
        return ContractGatewayReport(
            contracts=tuple(sorted(contracts, key=lambda item: (item.task_id, item.source_path))),
            diagnostics=tuple(
                sorted(
                    converted_report_diagnostics,
                    key=lambda item: (item.severity, item.code, item.diagnostic_id),
                )
            ),
            projections=primitive(getattr(report, "projections", None)),
            summary=summary_values,
            disclaimer=str(getattr(report, "disclaimer", "")),
        )
