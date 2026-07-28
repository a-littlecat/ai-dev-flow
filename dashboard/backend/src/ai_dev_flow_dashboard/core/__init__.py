"""Deterministic, read-only dashboard domain core."""

from .canonical import canonical_bytes, canonical_sha256, snapshot_revision
from .contract_gateway import ContractGateway
from .engine import DashboardCore
from .frozen_input import FrozenInputChangedError, FrozenInputLoader
from .schema_validator import ValidationError, validate_contract
from .scheduling import SchedulingParser

__all__ = [
    "ContractGateway",
    "DashboardCore",
    "FrozenInputChangedError",
    "FrozenInputLoader",
    "SchedulingParser",
    "ValidationError",
    "canonical_bytes",
    "canonical_sha256",
    "snapshot_revision",
    "validate_contract",
]
