"""Capture layer metadata independently of query predicates and tests."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class LayerAttribute:
    """Keep only the attribute metadata needed by query fields."""

    guid: UUID
    index: int
    name: str


@dataclass(frozen=True, slots=True)
class LayerCombinationData:
    """Snapshot the name and visible layer GUIDs of a saved combination."""

    name: str
    visible_layers: frozenset[UUID]
