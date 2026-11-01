"""Distinguish property-value conditions within ordinary batch error slots."""

from dataclasses import dataclass

from .batch_results import BatchError


@dataclass(frozen=True, slots=True)
class PropertyUndefinedError(BatchError):
    """Tapir returned the exact ``<Undefined>`` property-value sentinel."""


@dataclass(frozen=True, slots=True)
class PropertyUnavailableError(BatchError):
    """Tapir confirmed that a property is unavailable for this element."""
