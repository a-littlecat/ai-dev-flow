"""Read-only CLI Adapter for WorkflowContract.inspect()."""

import argparse
from dataclasses import asdict
import json
import pathlib

from workflow_contract import WorkflowContract


def _diagnostic_dict(item):
    data = asdict(item)
    data["provenance"] = list(data["provenance"])
    return data


def _json_payload(report):
    return {
        "summary": asdict(report.summary),
        "diagnostics": [_diagnostic_dict(item) for item in report.diagnostics],
        "projections": report.projections,
        "disclaimer": report.disclaimer,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="只读检查 Workflow Contract；不会修改 TASK、TASK_BOARD 或 Git。")
    parser.add_argument("target")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    args = parser.parse_args(argv)
    target = pathlib.Path(args.target)
    fixture_container = "tests/fixtures" in target.resolve().as_posix() and target.is_file()
    report = WorkflowContract.inspect(target, fixture_container=fixture_container)
    if args.format == "json":
        print(json.dumps(_json_payload(report), ensure_ascii=False, sort_keys=True))
    else:
        print(f"Workflow Contract lint: errors={report.summary.errors}, violations={report.summary.violations}, warnings={report.summary.warnings}")
        for item in report.diagnostics:
            print(f"[{item.severity}] {item.code} {item.path}:{item.line}:{item.column} {item.message}")
            print(f"  建议：{item.suggestion}")
        print(report.disclaimer)
    return report.summary.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
