"""Define serializable queries and explicit property-test validation.

Parsing validates structure. Call a test's ``validate_for`` method separately to
check supplied property metadata. These models do not fetch metadata or execute
queries.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Annotated, Literal, TypeAlias, get_args
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from multiconn_archicad.models.tapir.types import (
    ElementType,
    PropertyCollectionType,
    PropertyDetails,
    PropertyValueType,
)


class _QueryModel(BaseModel):
    """Reject extra fields and preserve validated values through immutability."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class PropertyTestModel(_QueryModel, ABC):
    """Define discovery and context-validation behavior for a test family.

    Concrete models declare their operator Literal and operand fields. Pydantic
    validates those fields at construction. Each family must also explicitly
    implement ``validate_for`` to check supplied property metadata and any
    metadata-dependent operand restrictions.
    """

    @classmethod
    def operators(cls) -> tuple[str, ...]:
        """Return operator strings directly from the family's Literal field."""
        return get_args(cls.model_fields["operator"].annotation)

    @classmethod
    @abstractmethod
    def accepts(cls, details: PropertyDetails) -> bool:
        """Report whether this family supports the property's metadata type."""
        ...

    @abstractmethod
    def validate_for(self, details: PropertyDetails) -> None:
        """Check property compatibility and metadata-dependent operand rules."""
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
            raise ValueError(
                f"{cls.__name__} cannot be used with property "
                f"{details.propertyGroupName} / {details.propertyName} "
                f"({details.propertyCollectionType.value}, "
                f"{details.propertyValueType.value}, "
                f"{details.propertyMeasureType.value})"
            )


class TextTest(PropertyTestModel):
    """Describe a text comparison; matching semantics belong to the evaluator."""

    kind: Literal["text"] = "text"
    operator: Literal[
        "is",
        "is not",
        "contains",
        "does not contain",
        "starts with",
        "ends with",
    ]
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


class NumberTest(PropertyTestModel):
    """Compare scalar numbers; measured properties use implicit SI operands."""

    kind: Literal["number"] = "number"
    operator: Literal[
        "is",
        "is not",
        "is greater than",
        "is greater than or equal to",
        "is less than",
        "is less than or equal to",
    ]
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


class Negate(_QueryModel):
    """Negate a predicate; unavailable-value behavior is defined by evaluation."""

    kind: Literal["not"] = "not"
    item: Predicate


Predicate: TypeAlias = Annotated[
    PropertyPredicate | ElementTypePredicate | AllOf | AnyOf | Negate,
    Field(discriminator="kind"),
]


class Query(_QueryModel):
    """Store a versioned query tree, independently of any Archicad connection."""

    schema_version: str = "1.0"
    where: Predicate


# Resolve the recursive predicate alias after all node classes are declared.
for _model in (AllOf, AnyOf, Negate, Query):
    _model.model_rebuild()
