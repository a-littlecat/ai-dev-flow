"""Deterministic, read-only dashboard domain core."""

from .canonical import canonical_bytes, canonical_sha256, snapshot_revision
from .contract_gateway import ContractGateway
from .engine import DashboardCore
from .frozen_input import FrozenInputChangedError, FrozenInputLoader
from .ownership import resolve_dirty_ownership_for_tasks
from .schema_validator import (
    ValidationError,
    contract_schema_digest,
    contract_schema_path,
    validate_contract,
    validated_canonical_bytes,
)
from .scheduling import SchedulingParser

__all__ = [
    "ContractGateway",
    "DashboardCore",
    "FrozenInputChangedError",
    "FrozenInputLoader",
    "SchedulingParser",
    "ValidationError",
    "contract_schema_digest",
    "contract_schema_path",
    "canonical_bytes",
    "canonical_sha256",
    "snapshot_revision",
    "resolve_dirty_ownership_for_tasks",
    "validate_contract",
    "validated_canonical_bytes",
]
