"""Describe attribute selections independently of query predicates and tests."""

from collections.abc import Callable, Hashable, Sequence
from dataclasses import dataclass, field
from uuid import UUID

from multiconn_archicad.models.tapir.types import AttributeType


@dataclass(frozen=True, slots=True)
class LayerAttribute:
    """Keep only the attribute metadata needed by query fields."""

    guid: UUID
    index: int
    name: str


def attribute_choices(attributes: Sequence[LayerAttribute]) -> tuple[LayerAttribute, ...]:
    """Capture an unambiguous immutable attribute snapshot."""
    choices = tuple(attributes)
    if len({item.guid for item in choices}) != len(choices):
        raise ValueError("Duplicate attribute GUID in layer query metadata")
    if len({item.index for item in choices}) != len(choices):
        raise ValueError("Duplicate attribute index in layer query metadata")
    return choices


@dataclass(frozen=True, slots=True)
class LayerRequest:
    """Key one batched attribute selection and optionally supply its metadata.

    The selection key and attribute type identify the request. Callbacks and
    supplied metadata do not affect equality, so equivalent predicates share
    work even when they create different bound method objects.
    """

    attribute_type: AttributeType
    selection_key: Hashable
    select: Callable[[Sequence[LayerAttribute]], tuple[LayerAttribute, ...]] = field(compare=False, repr=False)
    attributes: tuple[LayerAttribute, ...] | None = field(default=None, compare=False, repr=False)
