"""Windows-safe bounded atomic replacement for integration fixtures."""

from __future__ import annotations

import os
import time
from pathlib import Path


def atomic_replace_bytes(
    path: Path,
    content: bytes,
    *,
    timeout_seconds: float = 5.0,
    retry_interval_seconds: float = 0.01,
) -> int:
    """Replace ``path`` after transient read leases, or fail at the deadline."""

    if timeout_seconds <= 0 or retry_interval_seconds <= 0:
        raise ValueError("atomic replacement retry bounds must be positive")
    temporary = path.with_name(f".{path.stem}.integration.tmp{path.suffix}")
    temporary.write_bytes(content)
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            os.replace(temporary, path)
            return time.perf_counter_ns()
        except PermissionError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(retry_interval_seconds)
