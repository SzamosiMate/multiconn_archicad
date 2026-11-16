"""Define serializable queries, property-test validation, and value comparisons.

Parsing validates structure. Call a test's ``validate_for`` method separately to
check supplied property metadata. Families compare supplied strings; predicates
validate field references, prepare source requests and evaluate the tree against
shared execution data.
Neither performs API reads.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from enum import StrEnum
from math import isclose, isfinite
from typing import TYPE_CHECKING, Annotated, Any, ClassVar, Literal, Self, TypeAlias, assert_never, cast
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, ValidationInfo, field_validator, model_validator

from multiconn_archicad.models.tapir.types import (
    ElementType,
    PropertyCollectionType,
    PropertyDetails,
    PropertyMeasureType,
    PropertyValueType,
)
from multiconn_archicad.utilities.results.batch_results import BatchError, BatchRow, BatchSlot
from multiconn_archicad.utilities.results.property_errors import PropertyUnavailableError, PropertyUndefinedError

from .context import ContextBuilder, EvaluationContext
from .errors import InvalidPropertyTestError
from .inputs import InputAvailability
from .operators import (
    BooleanOperator,
    ClassificationOperator,
    CollectionOperator,
    EnumOperator,
    GuidOperator,
    NumberOperator,
    TextOperator,
)
from .sources import CLASSIFICATION_FIELDS, CLASSIFICATION_VALUES, PROPERTY_VALUES, TYPE_MEMBERSHIP
from .validation import FieldCheck, QueryValidationContext, QueryValidationIssue
from .versioning import QUERY_SCHEMA_VERSION

if TYPE_CHECKING:
    from .catalogue import QueryFieldCatalogue
    from .fields import ClassificationInfo


class _QueryModel(BaseModel):
    """Reject extra fields and preserve validated values through immutability."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class TestModel(_QueryModel, ABC):
    """Share immutable test structure and readable operator discovery."""

    @classmethod
    def operators(cls) -> tuple[str, ...]:
        """Return the declared operator values, if this test uses operators."""
        operator_field = cls.model_fields.get("operator")
        if operator_field is None:
            return ()
        operator_type = cast(type[StrEnum], operator_field.annotation)
        return tuple(operator.value for operator in operator_type)

    @classmethod
    def input_availability(cls, current_data: Mapping[str, JsonValue]) -> InputAvailability:
        """Describe ordinary inputs from the schema before the test is complete."""
        schema = cls.model_json_schema()
        visible = tuple(name for name in schema["properties"] if name != "kind")
        return InputAvailability(visible, frozenset(schema.get("required", ())).intersection(visible))

    @classmethod
    def resolve_input_schema(cls, schema: dict[str, Any], current_data: Mapping[str, JsonValue]) -> dict[str, Any]:
        """Resolve operator-dependent input shapes in a copied, metadata-aware schema."""
        return schema


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

    @classmethod
    def input_availability(cls, current_data: Mapping[str, JsonValue]) -> InputAvailability:
        operator = current_data.get("operator")
        if not isinstance(operator, str) or operator not in cls.operators():
            # Keep the operator editable. Strict validation reports unknown values.
            return InputAvailability(("operator",), frozenset({"operator"}))
        if ClassificationOperator(operator).requires_value:
            return InputAvailability(("operator", "value"), frozenset({"operator", "value"}))
        return InputAvailability(("operator",), frozenset({"operator"}), frozenset({"value"}))

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


class IntegerTest(PropertyTestModel):
    """Compare scalar Integer properties exactly, preserving integer precision."""

    kind: Literal["integer"] = "integer"
    operator: NumberOperator
    value: int = Field(strict=True)

    @classmethod
    def accepts(cls, details: PropertyDetails) -> bool:
        return (
            details.propertyCollectionType == PropertyCollectionType.SINGLE
            and details.propertyValueType == PropertyValueType.INTEGER
        )

    def validate_for(self, details: PropertyDetails) -> None:
        self._require_compatible_property(details)

    def evaluate(self, raw_value: str) -> BatchSlot[bool]:
        """Parse with int() and compare without float conversion or tolerance."""
        try:
            actual = int(raw_value)
        except ValueError:
            return BatchSlot.failure(f"Cannot interpret {raw_value!r} as an integer")

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


def _real_equal(actual: float, expected: float) -> bool:
    return isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-10)


def _annotate_real_unit(schema: dict[str, Any], measure: PropertyMeasureType) -> None:
    unit = {
        PropertyMeasureType.LENGTH: ("m", "metres"),
        PropertyMeasureType.AREA: ("m²", "square metres"),
        PropertyMeasureType.VOLUME: ("m³", "cubic metres"),
        PropertyMeasureType.ANGLE: ("°", "degrees"),
    }.get(measure)
    if unit is not None:
        symbol, name = unit
        schema.update({"x-unit": symbol, "description": f"Enter a value in {name} ({symbol})."})


class RealTest(PropertyTestModel):
    """Compare scalar Real properties with 1e-10 relative and absolute tolerance.

    Operands use SI units, except degrees for angles. Values within tolerance
    match equality and inclusive ordering, and fail strict ordering.
    """

    kind: Literal["real"] = "real"
    operator: NumberOperator
    value: float = Field(strict=True, allow_inf_nan=False)

    @classmethod
    def schema_for(cls, details: PropertyDetails) -> dict:
        """Annotate the operand with the query unit from its property metadata."""
        schema = super().schema_for(details)
        _annotate_real_unit(schema["properties"]["value"], details.propertyMeasureType)
        return schema

    @classmethod
    def accepts(cls, details: PropertyDetails) -> bool:
        """Accept scalar Real properties regardless of measure type."""
        return (
            details.propertyCollectionType == PropertyCollectionType.SINGLE
            and details.propertyValueType == PropertyValueType.REAL
        )

    def validate_for(self, details: PropertyDetails) -> None:
        """Require a numeric property; Pydantic already checked the finite operand."""
        self._require_compatible_property(details)

    def evaluate(self, raw_value: str) -> BatchSlot[bool]:
        """Parse a finite float and apply tolerance without rounding the value."""
        try:
            actual = float(raw_value)
        except ValueError:
            return BatchSlot.failure(f"Cannot interpret {raw_value!r} as a number")

        if not isfinite(actual):
            return BatchSlot.failure(f"Cannot interpret {raw_value!r} as a finite number")
        close = _real_equal(actual, self.value)

        match self.operator:
            case NumberOperator.IS:
                return BatchSlot.success(close)
            case NumberOperator.IS_NOT:
                return BatchSlot.success(not close)
            case NumberOperator.GREATER_THAN:
                return BatchSlot.success(actual > self.value and not close)
            case NumberOperator.GREATER_THAN_OR_EQUAL_TO:
                return BatchSlot.success(actual > self.value or close)
            case NumberOperator.LESS_THAN:
                return BatchSlot.success(actual < self.value and not close)
            case NumberOperator.LESS_THAN_OR_EQUAL_TO:
                return BatchSlot.success(actual < self.value or close)
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


def _enum_labels(details: PropertyDetails) -> tuple[str, ...]:
    return tuple(choice.enumValue.displayValue for choice in details.possibleEnumValues or ())


def _accepts_enumeration(details: PropertyDetails, collection: PropertyCollectionType) -> bool:
    labels = _enum_labels(details)
    return (
        details.propertyCollectionType == collection
        and details.propertyValueType == PropertyValueType.STRING
        and bool(labels)
        and len(set(labels)) == len(labels)
        # A flattened empty multi-enum read cannot distinguish an empty choice
        # from an empty selection. Scalar enum reads have no such ambiguity.
        and (collection != PropertyCollectionType.MULTIPLE_CHOICE_ENUMERATION or "" not in labels)
    )


def _validate_enum_values(details: PropertyDetails, values: tuple[str, ...]) -> None:
    labels = _enum_labels(details)
    for value in values:
        if value not in labels:
            raise InvalidPropertyTestError(
                f"{value!r} is not a choice of property {details.propertyGroupName} / {details.propertyName}"
            )


class EnumTest(PropertyTestModel):
    """Compare a single enum's exact display label, validated against metadata."""

    kind: Literal["enum"] = "enum"
    operator: EnumOperator
    value: str = Field(strict=True)

    @classmethod
    def accepts(cls, details: PropertyDetails) -> bool:
        return _accepts_enumeration(details, PropertyCollectionType.SINGLE_CHOICE_ENUMERATION)

    def validate_for(self, details: PropertyDetails) -> None:
        self._require_compatible_property(details)
        _validate_enum_values(details, (self.value,))

    @classmethod
    def schema_for(cls, details: PropertyDetails) -> dict:
        schema = super().schema_for(details)
        schema["properties"]["value"]["enum"] = list(_enum_labels(details))
        return schema

    def evaluate(self, raw_value: str) -> BatchSlot[bool]:
        match self.operator:
            case EnumOperator.IS:
                return BatchSlot.success(raw_value == self.value)
            case EnumOperator.IS_NOT:
                return BatchSlot.success(raw_value != self.value)
            case _:
                assert_never(self.operator)


def _collection_schema(schema: dict[str, Any]) -> None:
    item_schema = next(branch for branch in schema["properties"]["value"]["anyOf"] if branch["type"] != "array")
    schema["oneOf"] = [
        {
            "properties": {
                "operator": {"const": operator.value},
                "value": {"type": "array" if operator.requires_collection else item_schema["type"]},
            }
        }
        for operator in CollectionOperator
    ]


class _CollectionTest[ItemT](PropertyTestModel):
    """Share collection operand shapes, complete parsing, and item comparisons."""

    operator: CollectionOperator
    value: ItemT | tuple[ItemT, ...]
    model_config = ConfigDict(json_schema_extra=_collection_schema)
    _value_type: ClassVar[PropertyValueType]

    @model_validator(mode="after")
    def validate_operand(self) -> Self:
        if self.operator.requires_collection:
            if not isinstance(self.value, tuple):
                raise ValueError(f"{self.operator.value!r} requires a collection of items")
        elif isinstance(self.value, tuple):
            raise ValueError(f"{self.operator.value!r} requires one item")
        return self

    @classmethod
    def accepts(cls, details: PropertyDetails) -> bool:
        return (
            details.propertyCollectionType == PropertyCollectionType.LIST
            and details.propertyValueType == cls._value_type
        )

    def validate_for(self, details: PropertyDetails) -> None:
        self._require_compatible_property(details)

    @classmethod
    def resolve_input_schema(cls, schema: dict[str, Any], current_data: Mapping[str, JsonValue]) -> dict[str, Any]:
        operator = current_data.get("operator")
        if isinstance(operator, str) and operator in cls.operators():
            requires_collection = CollectionOperator(operator).requires_collection
            value_schema = schema["properties"]["value"]
            schema["properties"]["value"] = next(
                branch for branch in value_schema["anyOf"] if (branch["type"] == "array") == requires_collection
            )
        return schema

    @abstractmethod
    def _parse_item(self, raw_value: str) -> ItemT:
        """Convert one item, raising ValueError for an invalid returned value."""
        ...

    def _items_equal(self, actual: ItemT, expected: ItemT) -> bool:
        return actual == expected

    def _collections_equal(self, actual: tuple[ItemT, ...], expected: tuple[ItemT, ...]) -> bool:
        return len(actual) == len(expected) and all(
            self._items_equal(left, right) for left, right in zip(actual, expected, strict=True)
        )

    def evaluate(self, raw_value: str) -> BatchSlot[bool]:
        try:
            # Parse every item before comparing, including items after a match.
            actual = tuple(self._parse_item(item) for item in raw_value.split("; ")) if raw_value else ()
        except ValueError as error:
            return BatchSlot.failure(
                f"Cannot interpret {raw_value!r} as a {self._value_type.value.lower()} collection: {error}"
            )

        match self.operator:
            case CollectionOperator.IS:
                assert isinstance(self.value, tuple)
                return BatchSlot.success(self._collections_equal(actual, self.value))
            case CollectionOperator.CONTAINS | CollectionOperator.DOES_NOT_CONTAIN:
                expected = self.value
                assert not isinstance(expected, tuple)
                matched = any(self._items_equal(item, expected) for item in actual)
                return BatchSlot.success(not matched if self.operator is CollectionOperator.DOES_NOT_CONTAIN else matched)
            case _:
                assert_never(self.operator)


_StringItem = Annotated[str, Field(strict=True)]
_IntegerItem = Annotated[int, Field(strict=True)]
_RealItem = Annotated[float, Field(strict=True, allow_inf_nan=False)]


class StringListTest(_CollectionTest[_StringItem]):
    """Compare ordered string lists, using casefold for whole-item equality.

    Items must not contain semicolons. An empty read means an empty list; a
    single empty-string item cannot be distinguished by this read path.
    """

    kind: Literal["string_list"] = "string_list"
    _value_type = PropertyValueType.STRING

    def _parse_item(self, raw_value: str) -> str:
        return raw_value

    def _items_equal(self, actual: str, expected: str) -> bool:
        return actual.casefold() == expected.casefold()


class IntegerListTest(_CollectionTest[_IntegerItem]):
    """Compare ordered Integer lists exactly, without float conversion."""

    kind: Literal["integer_list"] = "integer_list"
    _value_type = PropertyValueType.INTEGER

    def _parse_item(self, raw_value: str) -> int:
        return int(raw_value)


class RealListTest(_CollectionTest[_RealItem]):
    """Compare ordered finite Real lists using the scalar Real tolerance policy.

    Operands use SI units, except degrees for angles, for every measure type.
    """

    kind: Literal["real_list"] = "real_list"
    _value_type = PropertyValueType.REAL

    @classmethod
    def schema_for(cls, details: PropertyDetails) -> dict:
        """Annotate both membership operands and whole-list operand items."""
        schema = super().schema_for(details)
        for branch in schema["properties"]["value"]["anyOf"]:
            operand = branch["items"] if branch["type"] == "array" else branch
            _annotate_real_unit(operand, details.propertyMeasureType)
        return schema

    def _parse_item(self, raw_value: str) -> float:
        value = float(raw_value)
        if not isfinite(value):
            raise ValueError("Expected a finite number")
        return value

    def _items_equal(self, actual: float, expected: float) -> bool:
        return _real_equal(actual, expected)


class MultiEnumTest(_CollectionTest[_StringItem]):
    """Compare a selection as a set, or test exact choice-label membership.

    Reads split Tapir's '; ' separator. Labels containing semicolons are outside
    this initial implementation's supported assumptions.
    """

    kind: Literal["multi_enum"] = "multi_enum"
    _value_type = PropertyValueType.STRING
    value: Annotated[str, Field(strict=True)] | Annotated[
        tuple[Annotated[str, Field(strict=True)], ...], Field(json_schema_extra={"uniqueItems": True})
    ]

    @model_validator(mode="after")
    def validate_unique_choices(self) -> Self:
        if isinstance(self.value, tuple) and len(set(self.value)) != len(self.value):
            raise ValueError("Multiple-choice enumeration operands must not repeat choices")
        return self

    @classmethod
    def accepts(cls, details: PropertyDetails) -> bool:
        return _accepts_enumeration(details, PropertyCollectionType.MULTIPLE_CHOICE_ENUMERATION)

    def validate_for(self, details: PropertyDetails) -> None:
        self._require_compatible_property(details)
        _validate_enum_values(details, (self.value,) if isinstance(self.value, str) else self.value)

    @classmethod
    def schema_for(cls, details: PropertyDetails) -> dict:
        schema = super().schema_for(details)
        for branch in schema["properties"]["value"]["anyOf"]:
            operand = branch["items"] if branch["type"] == "array" else branch
            operand["enum"] = list(_enum_labels(details))
        return schema

    def _parse_item(self, raw_value: str) -> str:
        return raw_value

    def _collections_equal(self, actual: tuple[str, ...], expected: tuple[str, ...]) -> bool:
        return set(actual) == set(expected)


class GuidTest(PropertyTestModel):
    """Compare UUID identity independently of the returned string's spelling."""

    kind: Literal["guid"] = "guid"
    operator: GuidOperator
    value: UUID

    @classmethod
    def accepts(cls, details: PropertyDetails) -> bool:
        return (
            details.propertyCollectionType == PropertyCollectionType.SINGLE
            and details.propertyValueType == PropertyValueType.GUID
        )

    def validate_for(self, details: PropertyDetails) -> None:
        self._require_compatible_property(details)

    def evaluate(self, raw_value: str) -> BatchSlot[bool]:
        try:
            actual = UUID(raw_value)
        except ValueError:
            return BatchSlot.failure(f"Cannot interpret {raw_value!r} as a GUID")
        match self.operator:
            case GuidOperator.IS:
                return BatchSlot.success(actual == self.value)
            case GuidOperator.IS_NOT:
                return BatchSlot.success(actual != self.value)
            case _:
                assert_never(self.operator)


PropertyTest: TypeAlias = Annotated[
    TextTest
    | IntegerTest
    | RealTest
    | BooleanTest
    | EnumTest
    | GuidTest
    | MultiEnumTest
    | StringListTest
    | IntegerListTest
    | RealListTest,
    Field(discriminator="kind"),
]


class PropertyPredicate(_QueryModel):
    """Apply a typed test to a property referenced by its project GUID."""

    kind: Literal["property"] = "property"
    field_id: UUID
    test: PropertyTest

    def validate_fields(
        self, context: QueryValidationContext, location: tuple[str | int, ...] = ("where",)
    ) -> tuple[QueryValidationIssue, ...]:
        """Validate this property's reference and test against captured metadata."""
        return context.check_field(FieldCheck(predicate=self, location=location))

    def candidate_types(self) -> frozenset[ElementType] | None:
        """A property comparison alone imposes no element-type restriction."""
        return None

    def field_references(self) -> tuple[Mapping[str, object], ...]:
        """Declare the property metadata needed for validation."""
        return ({"kind": self.kind, "field_id": self.field_id},)

    def prepare(self, builder: ContextBuilder, *, fields: QueryFieldCatalogue | None = None) -> None:
        """Request this property's values for the execution's candidate population."""
        builder.require(PROPERTY_VALUES, self.field_id)

    def evaluate(self, context: EvaluationContext, element_id: UUID, *, path: str = "where") -> BatchSlot[bool]:
        """Evaluate a supplied property read, retaining its GUID/path on failure."""
        value = context.data(PROPERTY_VALUES)[self.field_id].value(element_id)
        result = evaluate_property(self.test, value)
        if result.is_error:
            return BatchSlot.failure(
                BatchError.aggregate((result.error,), context=f"{path}.test (property {self.field_id})")
            )
        return result


class ClassificationPredicate(_QueryModel):
    """Test an element's assignment in one classification system."""

    kind: Literal["classification"] = "classification"
    field_id: UUID
    test: ClassificationTest

    def validate_fields(
        self, context: QueryValidationContext, location: tuple[str | int, ...] = ("where",)
    ) -> tuple[QueryValidationIssue, ...]:
        """Validate this system reference and test against its captured tree."""
        return context.check_field(FieldCheck(predicate=self, location=location))

    def candidate_types(self) -> frozenset[ElementType] | None:
        return None

    def field_references(self) -> tuple[Mapping[str, object], ...]:
        """Declare the system/tree metadata needed for validation and evaluation."""
        return ({"kind": self.kind, "field_id": self.field_id},)

    def prepare(self, builder: ContextBuilder, *, fields: QueryFieldCatalogue | None = None) -> None:
        """Request assignments and reuse a validated tree when supplied.

        Offline prepare/build callers may omit fields to let the metadata source
        load the tree. Bound execution passes its validated discovery snapshot.
        """
        builder.require(CLASSIFICATION_FIELDS, self.field_id)
        builder.require(CLASSIFICATION_VALUES, self.field_id)
        if fields is not None:
            field = fields.resolve({"kind": self.kind, "field_id": self.field_id})
            if field is None:
                raise ValueError(f"Expected validated classification metadata for system {self.field_id}")
            builder.provide(CLASSIFICATION_FIELDS, self.field_id, cast("ClassificationInfo", field))

    def evaluate(self, context: EvaluationContext, element_id: UUID, *, path: str = "where") -> BatchSlot[bool]:
        field = context.data(CLASSIFICATION_FIELDS)[self.field_id]
        value = context.data(CLASSIFICATION_VALUES)[self.field_id].value(element_id)
        result = BatchSlot.failure(value.error) if value.is_error else self.test.evaluate(value.value, field)
        if result.is_error:
            return BatchSlot.failure(
                BatchError.aggregate(
                    (result.error,),
                    context=f"{path}.test (classification system {self.field_id})",
                )
            )
        return result


class ElementTypeTest(TestModel):
    """Specify the Archicad element types accepted by a membership test."""

    kind: Literal["element_type"] = "element_type"
    types: tuple[ElementType, ...] = Field(
        min_length=1, json_schema_extra={"not": {"contains": {"const": "Unknown"}}}
    )

    @field_validator("types")
    @classmethod
    def reject_unknown_type(cls, types: tuple[ElementType, ...]) -> tuple[ElementType, ...]:
        if ElementType.UNKNOWN in types:
            raise ValueError("Unknown is a response sentinel, not a queryable element type")
        return types


class ElementTypePredicate(_QueryModel):
    """Match one or more Archicad element types."""

    kind: Literal["element_type"] = "element_type"
    test: ElementTypeTest

    def validate_fields(
        self, context: QueryValidationContext, location: tuple[str | int, ...] = ("where",)
    ) -> tuple[QueryValidationIssue, ...]:
        """Require no metadata: Pydantic already checked element-type choices."""
        return ()

    def candidate_types(self) -> frozenset[ElementType]:
        """Only the declared types can satisfy this predicate."""
        return frozenset(self.test.types)

    def field_references(self) -> tuple[Mapping[str, object], ...]:
        """Element types need no project metadata discovery."""
        return ()

    def prepare(self, builder: ContextBuilder, *, fields: QueryFieldCatalogue | None = None) -> None:
        """Request membership for this distinct set of element types."""
        builder.require(TYPE_MEMBERSHIP, self.candidate_types())

    def evaluate(self, context: EvaluationContext, element_id: UUID, *, path: str = "where") -> BatchSlot[bool]:
        """Use this predicate's supplied FilterElements membership result."""
        return BatchSlot.success(element_id in context.data(TYPE_MEMBERSHIP)[self.candidate_types()])


class AllOf(_QueryModel):
    """Require all contained predicates to match."""

    kind: Literal["all"] = "all"
    items: tuple[Predicate, ...] = Field(min_length=1)

    def validate_fields(
        self, context: QueryValidationContext, location: tuple[str | int, ...] = ("where",)
    ) -> tuple[QueryValidationIssue, ...]:
        """Collect every child's field issues in query order."""
        return tuple(
            issue
            for index, child in enumerate(self.items)
            for issue in child.validate_fields(context, (*location, "items", index))
        )

    def candidate_types(self) -> frozenset[ElementType] | None:
        """Intersect restrictions; unrestricted children add no restriction."""
        result: frozenset[ElementType] | None = None
        for child in self.items:
            types = child.candidate_types()
            if types is not None:
                result = types if result is None else result & types
        return result

    def field_references(self) -> tuple[Mapping[str, object], ...]:
        """Collect every child's metadata references, even for impossible branches."""
        return tuple(reference for child in self.items for reference in child.field_references())

    def prepare(self, builder: ContextBuilder, *, fields: QueryFieldCatalogue | None = None) -> None:
        """Collect requirements from every child, sharing the same builder."""
        for child in self.items:
            child.prepare(builder, fields=fields)

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

    def validate_fields(
        self, context: QueryValidationContext, location: tuple[str | int, ...] = ("where",)
    ) -> tuple[QueryValidationIssue, ...]:
        """Collect every child's field issues, regardless of boolean semantics."""
        return tuple(
            issue
            for index, child in enumerate(self.items)
            for issue in child.validate_fields(context, (*location, "items", index))
        )

    def candidate_types(self) -> frozenset[ElementType] | None:
        """Union restrictions; an unrestricted child makes the group unrestricted."""
        result: frozenset[ElementType] = frozenset()
        for child in self.items:
            types = child.candidate_types()
            if types is None:
                return None
            result |= types
        return result

    def field_references(self) -> tuple[Mapping[str, object], ...]:
        """Collect every child's metadata references, regardless of Boolean semantics."""
        return tuple(reference for child in self.items for reference in child.field_references())

    def prepare(self, builder: ContextBuilder, *, fields: QueryFieldCatalogue | None = None) -> None:
        """Collect requirements from every child, sharing the same builder."""
        for child in self.items:
            child.prepare(builder, fields=fields)

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

    @model_validator(mode="before")
    @classmethod
    def require_explicit_version(cls, data: Any, info: ValidationInfo) -> Any:
        """Require a version in input data when requested by the caller."""
        if (
            isinstance(info.context, Mapping)
            and info.context.get("require_schema_version")
            and isinstance(data, Mapping)
            and "schema_version" not in data
        ):
            raise ValueError("schema_version must be explicitly supplied")
        return data


# Resolve the recursive predicate alias after all node classes are declared.
for _model in (AllOf, AnyOf, Query):
    _model.model_rebuild()


def evaluate_property(test: PropertyTestModel, value: BatchSlot[str]) -> BatchSlot[bool]:
    """Interpret a success/error read slot, then delegate successful values.

    Known unavailability and undefined values are false, even for negative
    operators. Other read failures retain their original errors. Skipped slots are not
    completed reads and cannot be evaluated. The query must already have passed
    structure and metadata-context validation; no API calls are made here.
    """
    if value.is_error:
        if isinstance(value.error, (PropertyUnavailableError, PropertyUndefinedError)):
            return BatchSlot.success(False)
        return BatchSlot.failure(value.error)
    return test.evaluate(value.value)
