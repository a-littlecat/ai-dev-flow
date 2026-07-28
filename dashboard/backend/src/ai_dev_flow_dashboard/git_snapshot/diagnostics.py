"""Stable Git diagnostic construction without leaking command output."""

from __future__ import annotations

from ai_dev_flow_dashboard.core.canonical import stable_text_id
from ai_dev_flow_dashboard.core.models import Diagnostic, Provenance


def git_diagnostic(
    code: str,
    message: str,
    *,
    source_path: str = "",
    task_ids: tuple[str, ...] = (),
    severity: str = "warning",
) -> Diagnostic:
    provenance = (
        Provenance(
            source_path=source_path,
            heading=None,
            field=None,
            line=0,
            raw_value=None,
            source_type="git",
        ),
    ) if source_path else ()
    return Diagnostic(
        diagnostic_id=stable_text_id(
            "git-diagnostic",
            code,
            source_path,
            message,
            *sorted(set(task_ids)),
        ),
        code=code,
        severity=severity,
        message=message,
        task_ids=tuple(sorted(set(task_ids))),
        provenance=provenance,
    )
