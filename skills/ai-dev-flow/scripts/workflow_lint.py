"""Read-only CLI Adapter for WorkflowContract.inspect()."""

import sys
sys.dont_write_bytecode = True

import argparse
from dataclasses import asdict
import json

from workflow_contract import DISCLAIMER, WorkflowContract


class InvocationError(Exception):
    pass


class ReadOnlyParser(argparse.ArgumentParser):
    def error(self, message):
        raise InvocationError(message)


def _diagnostic_dict(item):
    data = asdict(item)
    data["provenance"] = list(data["provenance"])
    return data


def _json_payload(report):
    projections = [asdict(item) for item in report.projections] if isinstance(report.projections, tuple) else report.projections
    return {
        "summary": asdict(report.summary),
        "diagnostics": [_diagnostic_dict(item) for item in report.diagnostics],
        "projections": projections,
        "disclaimer": report.disclaimer,
    }


def _requested_format(argv):
    values = list(sys.argv[1:] if argv is None else argv)
    if "--format" in values:
        index = values.index("--format")
        if index + 1 < len(values) and values[index + 1] == "json":
            return "json"
    return "human"


def _emit_invocation_error(message, output_format):
    if output_format == "json":
        print(json.dumps({"summary":{"errors":1,"violations":0,"warnings":0,"exit_code":2}, "diagnostics":[{"code":"E_PARSE","severity":"error","path":"","line":0,"column":0,"message":message,"suggestion":"请按 --help 中的只读调用格式重试。","provenance":[]}], "projections":"not_evaluated", "disclaimer":DISCLAIMER}, ensure_ascii=False, sort_keys=True))
    else:
        print(f"[error] E_PARSE {message}")
        print("建议：请按 --help 中的只读调用格式重试。")
        print(DISCLAIMER)


def main(argv=None):
    output_format = _requested_format(argv)
    parser = ReadOnlyParser(description="只读检查 Workflow Contract；不会修改 TASK、TASK_BOARD 或 Git。")
    parser.add_argument("target")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    try:
        args = parser.parse_args(argv)
    except InvocationError as exc:
        _emit_invocation_error(str(exc), output_format)
        return 2
    report = WorkflowContract.inspect(args.target)
    if args.format == "json":
        print(json.dumps(_json_payload(report), ensure_ascii=False, sort_keys=True))
    else:
        print(f"Workflow Contract lint: errors={report.summary.errors}, violations={report.summary.violations}, warnings={report.summary.warnings}")
        if isinstance(report.projections, tuple):
            for projection in report.projections:
                print("projection: " + json.dumps(asdict(projection), ensure_ascii=False, sort_keys=True))
        for item in report.diagnostics:
            print(f"[{item.severity}] {item.code} {item.path}:{item.line}:{item.column} {item.message}")
            print(f"  建议：{item.suggestion}")
            for provenance in item.provenance:
                print("  provenance: " + json.dumps(asdict(provenance), ensure_ascii=False, sort_keys=True))
        print(report.disclaimer)
    return report.summary.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
