"""Define serializable queries, property-test validation, and value comparisons.

Parsing validates structure. Call a test's ``validate_for`` method separately to
check supplied property metadata. Families compare supplied strings; predicates
prepare source requests and evaluate the tree against shared execution data.
Neither performs API reads.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, Literal, TypeAlias, assert_never, cast
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from multiconn_archicad.models.tapir.types import (
    ElementType,
    PropertyCollectionType,
    PropertyDetails,
    PropertyValueType,
)
from multiconn_archicad.utilities.results.batch_results import BatchError, BatchRow, BatchSlot

from .errors import InvalidPropertyTestError
from .context import ContextBuilder, EvaluationContext
from .evaluation import evaluate_property
from .operators import BooleanOperator, ClassificationOperator, NumberOperator, TextOperator
from .sources import CLASSIFICATION_FIELDS, CLASSIFICATION_VALUES, PROPERTY_VALUES, TYPE_MEMBERSHIP
from .versioning import QUERY_SCHEMA_VERSION

if TYPE_CHECKING:
    from .fields import ClassificationInfo


class _QueryModel(BaseModel):
    """Reject extra fields and preserve validated values through immutability."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class TestModel(_QueryModel, ABC):
    """Share immutable test structure and readable operator discovery."""

    @classmethod
    def operators(cls) -> tuple[str, ...]:
        """Return readable values from the test's declared operator StrEnum."""
        operator_type = cast(type[StrEnum], cls.model_fields["operator"].annotation)
        return tuple(operator.value for operator in operator_type)


class ClassificationTest(TestModel):
    """Compare a classification assignment using supplied system/tree metadata."""

    kind: Literal["classification"] = "classification"
    operator: ClassificationOperator
    model_config = ConfigDict(
        json_schema_extra={
            "oneOf": [
                {
                    "properties": {
                        "operator": {"enum": [op.value for op in ClassificationOperator if not op.requires_value]}
                    },
                    "not": {"required": ["value"]},
                },
                {
                    "properties": {
                        "operator": {"enum": [op.value for op in ClassificationOperator if op.requires_value]},
                        "value": {"type": "string", "format": "uuid"},
                    },
                    "required": ["value"],
                },
            ],
        }
    )
    value: UUID | None = Field(default=None, exclude_if=lambda value: value is None)

    @model_validator(mode="after")
    def validate_operand(self) -> ClassificationTest:
        if self.operator.requires_value:
            if self.value is None:
                raise ValueError(f"{self.operator.value!r} requires a classification item value")
        elif "value" in self.model_fields_set:
            raise ValueError(f"{self.operator.value!r} does not accept a value")
        return self

    def evaluate(self, assignment: UUID | None, field: ClassificationInfo) -> BatchSlot[bool]:
        """Include the branch root; unclassified assignments match negative tests."""
        if self.operator is ClassificationOperator.HAS_VALUE:
            return BatchSlot.success(assignment is not None)
        if self.operator is ClassificationOperator.HAS_NO_VALUE:
            return BatchSlot.success(assignment is None)

        matched = False
        try:
            match self.operator:
                case ClassificationOperator.IS | ClassificationOperator.IS_NOT:
                    matched = assignment == self.value
                case ClassificationOperator.IS_DIRECT_CHILD_OF | ClassificationOperator.IS_NOT_DIRECT_CHILD_OF:
                    matched = assignment is not None and field.item(assignment).parent_id == self.value
                case ClassificationOperator.IS_IN_BRANCH_OF | ClassificationOperator.IS_NOT_IN_BRANCH_OF:
                    current = assignment
                    while current is not None:
                        if current == self.value:
                            matched = True
                            break
                        current = field.item(current).parent_id
                case _:
                    assert_never(self.operator)
        except KeyError:
            return BatchSlot.failure(f"Classification assignment {assignment} is absent from system {field.system_id}")

        negative = self.operator in (
            ClassificationOperator.IS_NOT,
            ClassificationOperator.IS_NOT_IN_BRANCH_OF,
            ClassificationOperator.IS_NOT_DIRECT_CHILD_OF,
        )
        return BatchSlot.success(not matched if negative else matched)


class PropertyTestModel(TestModel):
    """Define discovery, validation, and comparison behavior for a test family.

    Concrete models declare their operator StrEnum and operand fields. Pydantic
    validates those fields at construction. Each family must also explicitly
    implement ``validate_for`` to check supplied property metadata and any
    metadata-dependent operand restrictions. The required ``evaluate`` method
    compares one successfully retrieved string; read conditions are handled
    separately by ``evaluate_property``.
    """

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


class BooleanTest(PropertyTestModel):
    """Compare scalar booleans returned by Tapir as True/False strings."""

    kind: Literal["boolean"] = "boolean"
    operator: BooleanOperator
    value: bool = Field(strict=True)

    @classmethod
    def accepts(cls, details: PropertyDetails) -> bool:
        """Accept single Boolean properties, both built-in and user-defined."""
        return (
            details.propertyCollectionType == PropertyCollectionType.SINGLE
            and details.propertyValueType == PropertyValueType.BOOLEAN
        )

    def validate_for(self, details: PropertyDetails) -> None:
        """Require Boolean metadata; Pydantic already checked the Boolean operand."""
        self._require_compatible_property(details)

    def evaluate(self, raw_value: str) -> BatchSlot[bool]:
        """Decode Tapir's explicit Boolean strings, retaining conversion failures."""
        match raw_value:
            case "True":
                actual = True
            case "False":
                actual = False
            case _:
                return BatchSlot.failure(f"Cannot interpret {raw_value!r} as a boolean")

        match self.operator:
            case BooleanOperator.IS:
                return BatchSlot.success(actual == self.value)
            case BooleanOperator.IS_NOT:
                return BatchSlot.success(actual != self.value)
            case _:
                assert_never(self.operator)


PropertyTest: TypeAlias = Annotated[TextTest | NumberTest | BooleanTest, Field(discriminator="kind")]


class PropertyPredicate(_QueryModel):
    """Apply a typed test to a property referenced by its project GUID."""

    kind: Literal["property"] = "property"
    property_id: UUID
    test: PropertyTest

    def candidate_types(self) -> frozenset[ElementType] | None:
        """A property comparison alone imposes no element-type restriction."""
        return None

    def prepare(self, builder: ContextBuilder) -> None:
        """Request this property's values for the execution's candidate population."""
        builder.require(PROPERTY_VALUES, self.property_id)

    def evaluate(self, context: EvaluationContext, element_id: UUID, *, path: str = "where") -> BatchSlot[bool]:
        """Evaluate a supplied property read, retaining its GUID/path on failure."""
        value = context.data(PROPERTY_VALUES)[self.property_id].value(element_id)
        result = evaluate_property(self.test, value)
        if result.is_error:
            return BatchSlot.failure(
                BatchError.aggregate((result.error,), context=f"{path}.test (property {self.property_id})")
            )
        return result


class ClassificationPredicate(_QueryModel):
    """Test an element's assignment in one classification system."""

    kind: Literal["classification"] = "classification"
    system_id: UUID
    test: ClassificationTest

    def candidate_types(self) -> frozenset[ElementType] | None:
        return None

    def prepare(self, builder: ContextBuilder) -> None:
        builder.require(CLASSIFICATION_FIELDS, self.system_id)
        builder.require(CLASSIFICATION_VALUES, self.system_id)

    def evaluate(self, context: EvaluationContext, element_id: UUID, *, path: str = "where") -> BatchSlot[bool]:
        field = context.data(CLASSIFICATION_FIELDS)[self.system_id]
        value = context.data(CLASSIFICATION_VALUES)[self.system_id].value(element_id)
        result = BatchSlot.failure(value.error) if value.is_error else self.test.evaluate(value.value, field)
        if result.is_error:
            return BatchSlot.failure(
                BatchError.aggregate(
                    (result.error,),
                    context=f"{path}.test (classification system {self.system_id})",
                )
            )
        return result


class ElementTypePredicate(_QueryModel):
    """Match one or more Archicad element types."""

    kind: Literal["element_type"] = "element_type"
    types: tuple[ElementType, ...] = Field(min_length=1)

    def candidate_types(self) -> frozenset[ElementType]:
        """Only the declared types can satisfy this predicate."""
        return frozenset(self.types)

    def prepare(self, builder: ContextBuilder) -> None:
        """Request membership for this distinct set of element types."""
        builder.require(TYPE_MEMBERSHIP, self.candidate_types())

    def evaluate(self, context: EvaluationContext, element_id: UUID, *, path: str = "where") -> BatchSlot[bool]:
        """Use this predicate's supplied FilterElements membership result."""
        return BatchSlot.success(element_id in context.data(TYPE_MEMBERSHIP)[self.candidate_types()])


class AllOf(_QueryModel):
    """Require all contained predicates to match."""

    kind: Literal["all"] = "all"
    items: tuple[Predicate, ...] = Field(min_length=1)

    def candidate_types(self) -> frozenset[ElementType] | None:
        """Intersect restrictions; unrestricted children add no restriction."""
        result: frozenset[ElementType] | None = None
        for child in self.items:
            types = child.candidate_types()
            if types is not None:
                result = types if result is None else result & types
        return result

    def prepare(self, builder: ContextBuilder) -> None:
        """Collect requirements from every child, sharing the same builder."""
        for child in self.items:
            child.prepare(builder)

    def evaluate(self, context: EvaluationContext, element_id: UUID, *, path: str = "where") -> BatchSlot[bool]:
        """Evaluate every child and AND successful values, retaining all errors."""
        children = tuple(
            child.evaluate(context, element_id, path=f"{path}.items[{index}]") for index, child in enumerate(self.items)
        )
        return BatchRow(children).aggregate(context=f"{path} (all)").map(all)


class AnyOf(_QueryModel):
    """Require at least one contained predicate to match."""

    kind: Literal["any"] = "any"
    items: tuple[Predicate, ...] = Field(min_length=1)

    def candidate_types(self) -> frozenset[ElementType] | None:
        """Union restrictions; an unrestricted child makes the group unrestricted."""
        result: frozenset[ElementType] = frozenset()
        for child in self.items:
            types = child.candidate_types()
            if types is None:
                return None
            result |= types
        return result

    def prepare(self, builder: ContextBuilder) -> None:
        """Collect requirements from every child, sharing the same builder."""
        for child in self.items:
            child.prepare(builder)

    def evaluate(self, context: EvaluationContext, element_id: UUID, *, path: str = "where") -> BatchSlot[bool]:
        """Evaluate every child and OR successful values, retaining all errors."""
        children = tuple(
            child.evaluate(context, element_id, path=f"{path}.items[{index}]") for index, child in enumerate(self.items)
        )
        return BatchRow(children).aggregate(context=f"{path} (any)").map(any)


Predicate: TypeAlias = Annotated[
    PropertyPredicate | ClassificationPredicate | ElementTypePredicate | AllOf | AnyOf,
    Field(discriminator="kind"),
]


class Query(_QueryModel):
    """Store a versioned query tree, independently of any Archicad connection."""

    schema_version: str = QUERY_SCHEMA_VERSION
    where: Predicate


# Resolve the recursive predicate alias after all node classes are declared.
for _model in (AllOf, AnyOf, Query):
    _model.model_rebuild()
