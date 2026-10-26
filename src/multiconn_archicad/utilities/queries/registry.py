"""Resolve property-test families from metadata without fetching project state."""

from __future__ import annotations

from inspect import isabstract
from types import UnionType
from typing import Annotated, Any, Union, get_args, get_origin

from multiconn_archicad.models.tapir.types import PropertyDetails

from .models import PropertyTestModel


class UnsupportedPropertyTypeError(ValueError):
    """No registered test family accepts a property's metadata."""


class AmbiguousPropertyTypeError(ValueError):
    """Multiple registered test families accept the same property's metadata."""


class TestRegistry:
    """Select exactly one family using each model's ``accepts`` rule.

    Prefer ``from_union(PropertyTest)`` to share the supported-family declaration
    with the query schema. The registry stores model classes, never project data.
    """

    def __init__(self, *families: type[PropertyTestModel]):
        if not families:
            raise ValueError("At least one property-test family is required")
        for family in families:
            if not isinstance(family, type) or not issubclass(family, PropertyTestModel) or isabstract(family):
                raise TypeError("Test families must be concrete PropertyTestModel subclasses")
        self._families = families

    @classmethod
    def from_union(cls, test_union: Any) -> TestRegistry:
        """Read models from a union, optionally wrapped in ``Annotated``."""
        if get_origin(test_union) is Annotated:
            test_union = get_args(test_union)[0]
        if get_origin(test_union) not in (Union, UnionType):
            raise TypeError("Expected a union of PropertyTestModel subclasses")
        return cls(*get_args(test_union))

    @property
    def families(self) -> tuple[type[PropertyTestModel], ...]:
        """Return the immutable list of registered model classes."""
        return self._families

    def resolve(self, details: PropertyDetails) -> type[PropertyTestModel]:
        """Return one compatible family, rejecting unsupported or ambiguous types."""
        matches = [family for family in self._families if family.accepts(details)]
        name = f"{details.propertyGroupName} / {details.propertyName}"
        if not matches:
            raise UnsupportedPropertyTypeError(
                f"No query test family supports property {name} "
                f"({details.propertyCollectionType.value}, "
                f"{details.propertyValueType.value}, "
                f"{details.propertyMeasureType.value})"
            )
        if len(matches) > 1:
            names = ", ".join(sorted(family.__name__ for family in matches))
            raise AmbiguousPropertyTypeError(f"Multiple query test families support property {name}: {names}")
        return matches[0]
