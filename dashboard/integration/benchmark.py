"""Run the frozen Dashboard 500-task integration benchmark on Windows.

The runner creates an isolated temporary Git project, keeps every measured
sample, and never reads from or writes to the user's TASK source tree.
"""

from __future__ import annotations

import argparse
import ctypes
import http.client
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import winreg
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_SRC = REPO_ROOT / "dashboard" / "backend" / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from ai_dev_flow_dashboard.core import validated_canonical_bytes  # noqa: E402
from ai_dev_flow_dashboard.core.benchmark import generate_dataset  # noqa: E402
from ai_dev_flow_dashboard.snapshot import (  # noqa: E402
    PollingWatcher,
    SnapshotBuilder,
    SnapshotCoordinator,
)
from ai_dev_flow_dashboard.snapshot.performance import benchmark_summary  # noqa: E402
from ai_dev_flow_dashboard.server import DashboardApi, create_local_server  # noqa: E402
from dashboard.integration.atomic_write import atomic_replace_bytes  # noqa: E402
from dashboard.integration.process_tree import (  # noqa: E402
    process_group_options,
    terminate_process_tree,
    track_process_tree,
)


RESULT_SCHEMA = "ai-dev-flow/dashboard-benchmark-result/v1"
SUMMARY_SCHEMA = "ai-dev-flow/dashboard-benchmark-run/v1"
TASK_COUNT = 500
EDGE_COUNT = 2000
WARMUP_COUNT = 5
SAMPLE_COUNT = 30
GATES = {
    "cold_snapshot_ms": 2000.0,
    "stable_save_to_revision_ms": 1000.0,
    "api_serialize_ms": 250.0,
    "payload_bytes": 10 * 1024 * 1024,
}


class BenchmarkError(RuntimeError):
    """The benchmark setup, transport, or frozen gate failed."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00",
        "Z",
    )


def _run(
    arguments: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        arguments,
        cwd=cwd,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def _git(project: Path, *arguments: str) -> str:
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "Dashboard Benchmark",
            "GIT_AUTHOR_EMAIL": "benchmark@example.invalid",
            "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z",
            "GIT_COMMITTER_NAME": "Dashboard Benchmark",
            "GIT_COMMITTER_EMAIL": "benchmark@example.invalid",
            "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z",
            "GIT_OPTIONAL_LOCKS": "0",
        }
    )
    return _run(["git", "-C", str(project), *arguments], env=env).stdout.strip()


def _prepare_project(container: Path) -> tuple[Path, dict[str, Any]]:
    project = container / "project"
    manifest = generate_dataset(
        project,
        task_count=TASK_COUNT,
        edge_count=EDGE_COUNT,
    )
    source_scripts = REPO_ROOT / "skills" / "ai-dev-flow" / "scripts"
    target_scripts = project / "skills" / "ai-dev-flow" / "scripts"
    shutil.copytree(
        source_scripts,
        target_scripts,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    _git(project, "init", "--initial-branch=main")
    _git(project, "config", "core.autocrlf", "false")
    _git(project, "config", "user.name", "Dashboard Benchmark")
    _git(project, "config", "user.email", "benchmark@example.invalid")
    _git(project, "add", ".")
    _git(project, "commit", "-m", "benchmark fixture")
    for index in range(1, 6):
        _git(
            project,
            "worktree",
            "add",
            "-b",
            f"bench/w{index}",
            str(container / f"w{index}"),
        )
    if _git(project, "status", "--porcelain=v1"):
        raise BenchmarkError("temporary benchmark project is not clean")
    return project, manifest


def _memory_status() -> tuple[int, int]:
    class MemoryStatus(ctypes.Structure):
        _fields_ = [
            ("length", ctypes.c_ulong),
            ("memory_load", ctypes.c_ulong),
            ("total_physical", ctypes.c_ulonglong),
            ("available_physical", ctypes.c_ulonglong),
            ("total_page_file", ctypes.c_ulonglong),
            ("available_page_file", ctypes.c_ulonglong),
            ("total_virtual", ctypes.c_ulonglong),
            ("available_virtual", ctypes.c_ulonglong),
            ("available_extended_virtual", ctypes.c_ulonglong),
        ]

    status = MemoryStatus()
    status.length = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise ctypes.WinError()
    return int(status.total_physical), int(status.available_physical)


def _peak_rss_bytes(process_handle: int | None = None) -> int:
    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("page_fault_count", ctypes.c_ulong),
            ("peak_working_set_size", ctypes.c_size_t),
            ("working_set_size", ctypes.c_size_t),
            ("quota_peak_paged_pool_usage", ctypes.c_size_t),
            ("quota_paged_pool_usage", ctypes.c_size_t),
            ("quota_peak_non_paged_pool_usage", ctypes.c_size_t),
            ("quota_non_paged_pool_usage", ctypes.c_size_t),
            ("pagefile_usage", ctypes.c_size_t),
            ("peak_pagefile_usage", ctypes.c_size_t),
    ]

    counters = ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.GetCurrentProcess.argtypes = ()
    kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    psapi.GetProcessMemoryInfo.argtypes = (
        ctypes.c_void_p,
        ctypes.POINTER(ProcessMemoryCounters),
        ctypes.c_ulong,
    )
    psapi.GetProcessMemoryInfo.restype = ctypes.c_int
    handle = (
        ctypes.c_void_p(process_handle)
        if process_handle is not None
        else kernel32.GetCurrentProcess()
    )
    if not psapi.GetProcessMemoryInfo(
        handle,
        ctypes.byref(counters),
        counters.cb,
    ):
        raise ctypes.WinError()
    return int(counters.peak_working_set_size)


def _registry_cpu() -> str:
    with winreg.OpenKey(
        winreg.HKEY_LOCAL_MACHINE,
        r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
    ) as key:
        return str(winreg.QueryValueEx(key, "ProcessorNameString")[0]).strip()


def _powershell_value(script: str) -> str:
    utf8_script = (
        "$utf8=[System.Text.UTF8Encoding]::new($false);"
        "$OutputEncoding=$utf8;"
        "[Console]::OutputEncoding=$utf8;"
        + script
    )
    result = _run(
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            utf8_script,
        ]
    )
    return " ".join(line.strip() for line in result.stdout.splitlines() if line.strip())


def environment_report() -> dict[str, Any]:
    total_memory, _ = _memory_status()
    temporary_drive = Path(tempfile.gettempdir()).drive.rstrip(":")
    try:
        disk = _powershell_value(
            f"$p=Get-Partition -DriveLetter '{temporary_drive}';"
            "$d=$p | Get-Disk;"
            "$physical=Get-PhysicalDisk | "
            "Where-Object { [string]$_.DeviceId -eq [string]$d.Number } | "
            "Select-Object -First 1;"
            "if($physical){$physical.MediaType}else{'unknown'}"
        )
    except (OSError, subprocess.SubprocessError):
        disk = "unknown"
    try:
        power = _powershell_value(
            "(powercfg /getactivescheme) -join ' '"
        )
    except (OSError, subprocess.SubprocessError):
        power = "unknown"
    try:
        defender = _powershell_value(
            "$s=Get-MpComputerStatus; "
            "\"AntivirusEnabled=$($s.AntivirusEnabled);"
            "RealTimeProtectionEnabled=$($s.RealTimeProtectionEnabled)\""
        )
    except (OSError, subprocess.SubprocessError):
        defender = "unknown"
    try:
        filesystem = _powershell_value(
            f"(Get-Volume -DriveLetter '{temporary_drive}').FileSystem"
        )
    except (OSError, subprocess.SubprocessError):
        filesystem = "unknown"
    try:
        manufacturer = _powershell_value(
            "(Get-CimInstance Win32_ComputerSystem).Manufacturer"
        )
        model = _powershell_value(
            "(Get-CimInstance Win32_ComputerSystem).Model"
        )
        hypervisor = _powershell_value(
            "(Get-CimInstance Win32_ComputerSystem).HypervisorPresent"
        )
    except (OSError, subprocess.SubprocessError):
        manufacturer = model = hypervisor = "unknown"
    machine_identity = f"{manufacturer} {model}".casefold()
    virtual_markers = (
        "virtual machine",
        "virtualbox",
        "vmware",
        "kvm",
        "qemu",
        "xen",
        "parallels",
        "bochs",
        "amazon ec2",
        "compute engine",
        "google cloud",
        "openstack",
        "digitalocean",
        "azure",
    )
    physical_manufacturers = (
        "lenovo",
        "dell",
        "hewlett-packard",
        "asustek",
        "acer",
        "micro-star",
        "gigabyte",
        "framework",
    )
    if (
        manufacturer.casefold() in {"", "unknown"}
        or model.casefold() in {"", "unknown"}
    ):
        machine_classification = "unknown"
    elif any(marker in machine_identity for marker in virtual_markers):
        machine_classification = "virtual"
    elif (
        manufacturer.casefold().strip() == "hp"
        or any(
            marker in manufacturer.casefold()
            for marker in physical_manufacturers
        )
    ):
        machine_classification = "physical"
    elif (
        manufacturer.casefold() == "microsoft corporation"
        and model.casefold().startswith("surface")
    ):
        machine_classification = "physical"
    else:
        machine_classification = "unknown"
    return {
        "os": platform.platform(),
        "os_build": platform.version(),
        "architecture": platform.machine(),
        "cpu": _registry_cpu(),
        "logical_cpu_count": os.cpu_count(),
        "ram_bytes": total_memory,
        "disk_media_type": disk or "unknown",
        "python": sys.version.replace("\n", " "),
        "python_major_minor": [sys.version_info.major, sys.version_info.minor],
        "python_executable": sys.executable,
        "git": _run(["git", "--version"]).stdout.strip(),
        "power_scheme": power or "unknown",
        "defender": defender or "unknown",
        "temporary_filesystem": filesystem or "unknown",
        "temporary_volume": f"{temporary_drive}:" if temporary_drive else "unknown",
        "machine_manufacturer": manufacturer or "unknown",
        "machine_model": model or "unknown",
        "hypervisor_present": hypervisor or "unknown",
        "virtual_machine_detected": any(
            marker in machine_identity for marker in virtual_markers
        ),
        "machine_classification": machine_classification,
    }


def reference_profile_qualification(environment: dict[str, Any]) -> dict[str, Any]:
    """Evaluate the immutable DASHBOARD-001 reference-machine contract."""

    git_match = re.search(r"(\d+)\.(\d+)", str(environment.get("git", "")))
    git_version = (
        (int(git_match.group(1)), int(git_match.group(2)))
        if git_match
        else (0, 0)
    )
    power = str(environment.get("power_scheme", "")).casefold()
    defender = str(environment.get("defender", "")).casefold()
    build_numbers = tuple(
        int(item)
        for item in re.findall(r"\d+", str(environment.get("os_build", "")))
    )
    windows_build = build_numbers[2] if len(build_numbers) >= 3 else 0
    checks = {
        "windows_11_23h2_or_newer": (
            str(environment.get("os", "")).startswith("Windows-11-")
            and windows_build >= 22631
        ),
        "x64": str(environment.get("architecture", "")).casefold()
        in {"amd64", "x86_64"},
        "logical_cpu_at_least_8": int(environment.get("logical_cpu_count") or 0)
        >= 8,
        "ram_at_least_16_gib": int(environment.get("ram_bytes") or 0)
        >= 16 * 1024**3,
        "local_ntfs_ssd": (
            str(environment.get("disk_media_type", "")).casefold() == "ssd"
            and str(environment.get("temporary_filesystem", "")).casefold()
            == "ntfs"
        ),
        "python_3_11_or_3_12": tuple(
            int(item) for item in environment.get("python_major_minor", ())
        )
        in {(3, 11), (3, 12)},
        "git_at_least_2_40": git_version >= (2, 40),
        "balanced_power": (
            "381b4222-f694-41f0-9685-ff5bb260df2e" in power
            or "balanced" in power
            or "平衡" in power
        ),
        "defender_enabled": (
            "antivirusenabled=true" in defender
            and "realtimeprotectionenabled=true" in defender
        ),
        "physical_machine": environment.get("machine_classification")
        == "physical",
    }
    return {
        "profile": "DASHBOARD-001/windows-reference-v1",
        "checks": checks,
        "passed": all(checks.values()),
    }


def _child_environment() -> dict[str, str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(BACKEND_SRC)
        if not existing
        else str(BACKEND_SRC) + os.pathsep + existing
    )
    env["PYTHONUTF8"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _cold_child(project: Path) -> int:
    result = SnapshotBuilder(project).build()
    if result.snapshot["state"] != "fresh":
        raise BenchmarkError(
            f"cold snapshot is not fresh: {result.snapshot['state']}"
        )
    payload = result.payload or validated_canonical_bytes(result.snapshot)
    print(
        json.dumps(
            {
                "payload_bytes": len(payload),
                "revision": result.snapshot["revision"],
                "peak_rss_bytes": _peak_rss_bytes(),
            },
            separators=(",", ":"),
        )
    )
    return 0


def _cold_sample(project: Path) -> tuple[float, int, int]:
    started = time.perf_counter_ns()
    process = track_process_tree(subprocess.Popen(
        [
            sys.executable,
            "-B",
            "-X",
            "utf8",
            str(Path(__file__).resolve()),
            "--cold-child",
            str(project),
        ],
        cwd=REPO_ROOT,
        env=_child_environment(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        **process_group_options(),
    ))
    try:
        stdout, stderr = process.communicate(timeout=30)
    except subprocess.TimeoutExpired as exc:
        terminate_process_tree(process)
        stdout, stderr = process.communicate()
        raise BenchmarkError(
            f"cold child timed out after 30 seconds: {stderr.strip()}"
        ) from exc
    except BaseException:
        terminate_process_tree(process)
        try:
            process.communicate()
        except BaseException:
            pass
        raise
    terminate_process_tree(process)
    elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
    if process.returncode != 0:
        raise BenchmarkError(
            f"cold child failed with {process.returncode}: {stderr.strip()}"
        )
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise BenchmarkError(f"cold child returned invalid JSON: {stdout!r}") from exc
    return (
        elapsed_ms,
        int(payload["payload_bytes"]),
        int(payload["peak_rss_bytes"]),
    )


def _result(
    *,
    environment: dict[str, Any],
    dataset_manifest: dict[str, Any],
    metric: str,
    samples_ms: list[float],
    payload_bytes: int,
    peak_rss_bytes: int,
    started_at: str,
    finished_at: str,
) -> dict[str, Any]:
    summary = benchmark_summary(samples_ms)
    return {
        "schema_version": RESULT_SCHEMA,
        "environment": environment,
        "dataset_manifest": dataset_manifest,
        "metric": metric,
        "samples_ms": summary["samples_ms"],
        "p50_ms": summary["p50_ms"],
        "p95_ms": summary["p95_ms"],
        "payload_bytes": payload_bytes,
        "peak_rss_bytes": peak_rss_bytes,
        "started_at": started_at,
        "finished_at": finished_at,
    }


def cold_snapshot_result(
    project: Path,
    environment: dict[str, Any],
    dataset_manifest: dict[str, Any],
) -> dict[str, Any]:
    for _ in range(WARMUP_COUNT):
        _cold_sample(project)
    started_at = _utc_now()
    samples: list[float] = []
    payload_bytes = 0
    peak_rss = 0
    for _ in range(SAMPLE_COUNT):
        elapsed, payload_bytes, child_peak = _cold_sample(project)
        samples.append(elapsed)
        peak_rss = max(peak_rss, child_peak)
    return _result(
        environment=environment,
        dataset_manifest=dataset_manifest,
        metric="cold_snapshot_ms",
        samples_ms=samples,
        payload_bytes=payload_bytes,
        peak_rss_bytes=peak_rss,
        started_at=started_at,
        finished_at=_utc_now(),
    )


def _read_sse_event(response: http.client.HTTPResponse) -> str:
    event_id: str | None = None
    while True:
        line = response.fp.readline()
        if not line:
            raise BenchmarkError("SSE connection closed before snapshot event")
        if line.startswith(b"id: "):
            event_id = line[4:].strip().decode("ascii")
        if line in {b"\n", b"\r\n"} and event_id is not None:
            return event_id


def _wait_for_task_lifecycle(
    response: http.client.HTTPResponse,
    coordinator: SnapshotCoordinator,
    lifecycle: str,
) -> str:
    while True:
        event_revision = _read_sse_event(response)
        current = coordinator.current()
        if current is None or current.revision != event_revision:
            continue
        task = next(
            item
            for item in current.snapshot["tasks"]
            if item["task_id"] == "BENCH-0001"
        )
        if task["lifecycle"] == lifecycle:
            return event_revision


def stable_save_result(
    project: Path,
    environment: dict[str, Any],
    dataset_manifest: dict[str, Any],
) -> tuple[dict[str, Any], SnapshotCoordinator]:
    coordinator = SnapshotCoordinator(project)
    current = coordinator.refresh()
    watcher = PollingWatcher(coordinator)
    server = create_local_server(
        coordinator,
        host="127.0.0.1",
        port=0,
        heartbeat_seconds=5,
    )
    server_thread = threading.Thread(
        target=server.serve_forever,
        kwargs={"poll_interval": 0.05},
        daemon=True,
    )
    task_path = project / "docs" / "tasks" / "BENCH-0001.md"
    original: bytes | None = None
    connection: http.client.HTTPConnection | None = None
    watcher_started = False
    server_started = False
    samples: list[float] = []
    started_at = _utc_now()
    try:
        watcher.start()
        watcher_started = True
        server_thread.start()
        server_started = True
        if not watcher.wait_until_idle(5):
            raise BenchmarkError("watcher did not become idle")
        coordinator.set_server_state("ready")
        connection = http.client.HTTPConnection(
            "127.0.0.1",
            server.server_port,
            timeout=10,
        )
        connection.request(
            "GET",
            "/api/v1/events",
            headers={"Last-Event-ID": current.revision},
        )
        response = connection.getresponse()
        if response.status != 200:
            raise BenchmarkError(
                f"SSE connection returned HTTP {response.status}"
            )
        retry_line = response.fp.readline()
        if retry_line != b"retry: 2000\n":
            raise BenchmarkError(f"unexpected SSE prelude: {retry_line!r}")

        original = task_path.read_bytes()
        changed = original.replace(
            b"- `lifecycle`: `Ready`",
            b"- `lifecycle`: `Draft`",
            1,
        )
        if changed == original:
            raise BenchmarkError("benchmark task lifecycle marker is missing")
        for index in range(WARMUP_COUNT + SAMPLE_COUNT):
            before = coordinator.current()
            if before is None:
                raise BenchmarkError("coordinator has no current snapshot")
            started = atomic_replace_bytes(task_path, changed)
            event_revision = _wait_for_task_lifecycle(
                response,
                coordinator,
                "Draft",
            )
            elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
            if event_revision == before.revision:
                raise BenchmarkError("SSE did not publish a successor revision")
            if index >= WARMUP_COUNT:
                samples.append(elapsed_ms)
            if not watcher.wait_until_idle(5):
                raise BenchmarkError("watcher did not return to idle after save")

            changed_record = coordinator.current()
            if changed_record is None:
                raise BenchmarkError("changed snapshot was not published")
            atomic_replace_bytes(task_path, original)
            restored_revision = _wait_for_task_lifecycle(
                response,
                coordinator,
                "Ready",
            )
            if restored_revision == changed_record.revision:
                raise BenchmarkError("restore did not publish a successor revision")
            if not watcher.wait_until_idle(5):
                raise BenchmarkError("watcher did not return to idle after restore")
    finally:
        if connection is not None:
            connection.close()
        if watcher_started:
            watcher.stop()
        if server_started:
            server.shutdown()
        server.server_close()
        if server_started:
            server_thread.join(timeout=5)
        if original is not None and task_path.read_bytes() != original:
            atomic_replace_bytes(task_path, original)

    current = coordinator.current()
    if current is None:
        raise BenchmarkError("coordinator lost the final snapshot")
    return (
        _result(
            environment=environment,
            dataset_manifest=dataset_manifest,
            metric="stable_save_to_revision_ms",
            samples_ms=samples,
            payload_bytes=len(current.payload),
            peak_rss_bytes=_peak_rss_bytes(),
            started_at=started_at,
            finished_at=_utc_now(),
        ),
        coordinator,
    )


def api_serialize_result(
    coordinator: SnapshotCoordinator,
    environment: dict[str, Any],
    dataset_manifest: dict[str, Any],
) -> dict[str, Any]:
    current = coordinator.current()
    if current is None:
        raise BenchmarkError("coordinator has no snapshot for API serialization")
    api = DashboardApi(coordinator)

    def serialize() -> bytes:
        payload = validated_canonical_bytes(current.snapshot)
        response = api._response(
            200,
            payload,
            [("ETag", current.etag)],
            content_type="application/json; charset=utf-8",
        )
        if response.status != 200:
            raise BenchmarkError("API serialization returned a non-200 response")
        return response.body

    for _ in range(WARMUP_COUNT):
        serialize()
    started_at = _utc_now()
    samples: list[float] = []
    payload = b""
    for _ in range(SAMPLE_COUNT):
        started = time.perf_counter_ns()
        payload = serialize()
        samples.append((time.perf_counter_ns() - started) / 1_000_000)
    return _result(
        environment=environment,
        dataset_manifest=dataset_manifest,
        metric="api_serialize_ms",
        samples_ms=samples,
        payload_bytes=len(payload),
        peak_rss_bytes=_peak_rss_bytes(),
        started_at=started_at,
        finished_at=_utc_now(),
    )


def evaluate_gates(results: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = {str(result["metric"]): result for result in results}
    checks = {
        metric: float(metrics[metric]["p95_ms"]) <= limit
        for metric, limit in GATES.items()
        if metric.endswith("_ms")
    }
    payload = max(int(result["payload_bytes"]) for result in results)
    checks["payload_bytes"] = payload <= int(GATES["payload_bytes"])
    return {
        "thresholds": GATES,
        "checks": checks,
        "passed": all(checks.values()),
    }


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def run_benchmark(output_dir: Path) -> dict[str, Any]:
    environment = environment_report()
    qualification = reference_profile_qualification(environment)
    started_at = _utc_now()
    with tempfile.TemporaryDirectory(prefix="dashboard-benchmark-") as directory:
        project, manifest = _prepare_project(Path(directory))
        cold = cold_snapshot_result(project, environment, manifest)
        stable, coordinator = stable_save_result(project, environment, manifest)
        api = api_serialize_result(coordinator, environment, manifest)
        results = [cold, stable, api]
    gates = evaluate_gates(results)
    summary = {
        "schema_version": SUMMARY_SCHEMA,
        "dataset_sha256": manifest["dataset_sha256"],
        "results": results,
        "gates": gates,
        "reference_profile": qualification,
        "passed": gates["passed"] and qualification["passed"],
        "started_at": started_at,
        "finished_at": _utc_now(),
    }
    for result in results:
        _write_json(output_dir / f"{result['metric']}.json", result)
    _write_json(output_dir / "summary.json", summary)
    return summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).with_name("artifacts") / "benchmark",
    )
    parser.add_argument("--cold-child", type=Path, help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.cold_child is not None:
        return _cold_child(args.cold_child.resolve())
    if os.name != "nt":
        raise BenchmarkError("the frozen reference profile requires Windows")
    summary = run_benchmark(args.output_dir.resolve())
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
