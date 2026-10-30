"""Define serializable queries, property-test validation, and value comparisons.

Parsing validates structure. Call a test's ``validate_for`` method separately to
check supplied property metadata. Families evaluate supplied value strings; these
models do not fetch metadata or execute query trees.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Annotated, Literal, TypeAlias, assert_never, cast
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from multiconn_archicad.models.tapir.types import (
    ElementType,
    PropertyCollectionType,
    PropertyDetails,
    PropertyValueType,
)
from multiconn_archicad.utilities.results.batch_results import BatchSlot

from .errors import InvalidPropertyTestError
from .operators import NumberOperator, TextOperator


class _QueryModel(BaseModel):
    """Reject extra fields and preserve validated values through immutability."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class PropertyTestModel(_QueryModel, ABC):
    """Define discovery, validation, and comparison behavior for a test family.

    Concrete models declare their operator StrEnum and operand fields. Pydantic
    validates those fields at construction. Each family must also explicitly
    implement ``validate_for`` to check supplied property metadata and any
    metadata-dependent operand restrictions. The required ``evaluate`` method
    compares one successfully retrieved string; read conditions are handled
    separately by ``evaluate_property``.
    """

    @classmethod
    def operators(cls) -> tuple[str, ...]:
        """Return readable values from the family's declared operator StrEnum."""
        operator_type = cast(type[StrEnum], cls.model_fields["operator"].annotation)
        return tuple(operator.value for operator in operator_type)

    @classmethod
    @abstractmethod
    def accepts(cls, details: PropertyDetails) -> bool:
        """Report whether this family supports the property's metadata type."""
        ...

    @abstractmethod
    def validate_for(self, details: PropertyDetails) -> None:
        """Check context, raising InvalidPropertyTestError for expected failures."""
        ...

    @abstractmethod
    def evaluate(self, raw_value: str) -> BatchSlot[bool]:
        """Compare a retrieved value, retaining expected conversion failures."""
        ...

    @classmethod
    def schema_for(cls, details: PropertyDetails) -> dict:
        """Describe a compatible test; families can add metadata-based choices."""
        cls._require_compatible_property(details)
        return cls.model_json_schema()

    @classmethod
    def _require_compatible_property(cls, details: PropertyDetails) -> None:
        """Reuse the family's discovery rule when validating a selected test."""
        if not cls.accepts(details):
            raise InvalidPropertyTestError(
                f"{cls.__name__} cannot be used with property "
                f"{details.propertyGroupName} / {details.propertyName} "
                f"({details.propertyCollectionType.value}, "
                f"{details.propertyValueType.value}, "
                f"{details.propertyMeasureType.value})"
            )


class TextTest(PropertyTestModel):
    """Describe a case-insensitive text comparison with significant whitespace."""

    kind: Literal["text"] = "text"
    operator: TextOperator
    value: str = Field(strict=True)

    @classmethod
    def accepts(cls, details: PropertyDetails) -> bool:
        """Accept single string properties, excluding lists and enumerations."""
        return (
            details.propertyCollectionType == PropertyCollectionType.SINGLE
            and details.propertyValueType == PropertyValueType.STRING
        )

    def validate_for(self, details: PropertyDetails) -> None:
        """Require a single string property; Pydantic already checked the operand."""
        self._require_compatible_property(details)

    def evaluate(self, raw_value: str) -> BatchSlot[bool]:
        """Compare without case sensitivity, preserving whitespace."""
        actual = raw_value.casefold()
        expected = self.value.casefold()
        match self.operator:
            case TextOperator.IS:
                return BatchSlot.success(actual == expected)
            case TextOperator.IS_NOT:
                return BatchSlot.success(actual != expected)
            case TextOperator.CONTAINS:
                return BatchSlot.success(expected in actual)
            case TextOperator.DOES_NOT_CONTAIN:
                return BatchSlot.success(expected not in actual)
            case TextOperator.STARTS_WITH:
                return BatchSlot.success(actual.startswith(expected))
            case TextOperator.ENDS_WITH:
                return BatchSlot.success(actual.endswith(expected))
            case _:
                assert_never(self.operator)


class NumberTest(PropertyTestModel):
    """Compare scalar numbers without tolerance; measured operands use SI."""

    kind: Literal["number"] = "number"
    operator: NumberOperator
    value: float = Field(strict=True, allow_inf_nan=False, description="Numeric operand; quantities use SI units.")

    @classmethod
    def accepts(cls, details: PropertyDetails) -> bool:
        """Accept scalar integer and real properties regardless of measure type."""
        return details.propertyCollectionType == PropertyCollectionType.SINGLE and details.propertyValueType in (
            PropertyValueType.INTEGER,
            PropertyValueType.REAL,
        )

    def validate_for(self, details: PropertyDetails) -> None:
        """Require a numeric property; Pydantic already checked the finite operand."""
        self._require_compatible_property(details)

    def evaluate(self, raw_value: str) -> BatchSlot[bool]:
        """Apply float() directly, without unit conversion, rounding, or tolerance."""
        try:
            actual = float(raw_value)
        except ValueError:
            return BatchSlot.failure(f"Cannot interpret {raw_value!r} as a number")

        match self.operator:
            case NumberOperator.IS:
                return BatchSlot.success(actual == self.value)
            case NumberOperator.IS_NOT:
                return BatchSlot.success(actual != self.value)
            case NumberOperator.GREATER_THAN:
                return BatchSlot.success(actual > self.value)
            case NumberOperator.GREATER_THAN_OR_EQUAL_TO:
                return BatchSlot.success(actual >= self.value)
            case NumberOperator.LESS_THAN:
                return BatchSlot.success(actual < self.value)
            case NumberOperator.LESS_THAN_OR_EQUAL_TO:
                return BatchSlot.success(actual <= self.value)
            case _:
                assert_never(self.operator)


PropertyTest: TypeAlias = Annotated[TextTest | NumberTest, Field(discriminator="kind")]


class PropertyPredicate(_QueryModel):
    """Apply a typed test to a property referenced by its project GUID."""

    kind: Literal["property"] = "property"
    property_id: UUID
    test: PropertyTest


class ElementTypePredicate(_QueryModel):
    """Match one or more Archicad element types."""

    kind: Literal["element_type"] = "element_type"
    types: tuple[ElementType, ...] = Field(min_length=1)


class AllOf(_QueryModel):
    """Require all contained predicates to match."""

    kind: Literal["all"] = "all"
    items: tuple[Predicate, ...] = Field(min_length=1)


class AnyOf(_QueryModel):
    """Require at least one contained predicate to match."""

    kind: Literal["any"] = "any"
    items: tuple[Predicate, ...] = Field(min_length=1)


Predicate: TypeAlias = Annotated[
    PropertyPredicate | ElementTypePredicate | AllOf | AnyOf,
    Field(discriminator="kind"),
]


class Query(_QueryModel):
    """Store a versioned query tree, independently of any Archicad connection."""

    schema_version: str = "1.0"
    where: Predicate


# Resolve the recursive predicate alias after all node classes are declared.
for _model in (AllOf, AnyOf, Query):
    _model.model_rebuild()
