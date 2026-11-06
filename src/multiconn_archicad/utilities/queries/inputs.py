"""Framework-neutral input descriptions for a query test draft."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class InputAvailability:
    """Name the inputs that are visible, required, or forbidden for a draft."""

    visible: tuple[str, ...]
    required: frozenset[str]
    forbidden: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class TestInput:
    """Describe one active input using its JSON Schema fragment."""

    name: str
    schema: dict[str, Any]
    required: bool


@dataclass(frozen=True, slots=True)
class TestInputs:
    """Supply active fields and the shared definitions used by their schemas."""

    fields: tuple[TestInput, ...]
    definitions: dict[str, Any]
    forbidden_fields: frozenset[str] = frozenset()
