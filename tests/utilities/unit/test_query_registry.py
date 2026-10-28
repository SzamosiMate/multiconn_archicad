"""Verify family dispatch and static extension without Archicad access."""

from typing import Annotated, Literal, Union

import pytest
from pydantic import Field, TypeAdapter

from multiconn_archicad.models.tapir import types as tapir
from multiconn_archicad.utilities.queries import (
    AmbiguousPropertyTypeError,
    NumberTest,
    PropertyTest,
    PropertyTestModel,
    TextTest,
    UnsupportedPropertyTypeError,
)
from multiconn_archicad.utilities.queries import TestRegistry as Registry

pytestmark = pytest.mark.unit


def property_details(**changes) -> tapir.PropertyDetails:
    data = {
        "propertyId": {"guid": "22222222-2222-4222-8222-222222222222"},
        "propertyType": "Custom",
        "propertyGroupName": "Example",
        "propertyName": "Value",
        "propertyCollectionType": "Single",
        "propertyValueType": "Real",
        "propertyMeasureType": "Default",
        "propertyIsEditable": True,
        "isExpressionBased": False,
    }
    data.update(changes)
    return tapir.PropertyDetails.model_validate(data)


@pytest.mark.parametrize("test_union", [PropertyTest, TextTest | NumberTest, Union[TextTest, NumberTest]])
def test_registry_reads_families_from_annotated_and_plain_unions(test_union):
    registry = Registry.from_union(test_union)

    assert registry.families == (TextTest, NumberTest)
    assert registry.resolve(property_details()) is NumberTest
    assert registry.resolve(property_details(propertyValueType="String")) is TextTest


@pytest.mark.parametrize("test_union", [TextTest | NumberTest, NumberTest | TextTest])
def test_family_selection_is_independent_of_union_order(test_union):
    registry = Registry.from_union(test_union)

    assert registry.resolve(property_details(propertyValueType="Integer")) is NumberTest
    assert registry.resolve(property_details(propertyMeasureType="Area")) is NumberTest
    assert registry.resolve(property_details(propertyValueType="String")) is TextTest


@pytest.mark.parametrize(
    "metadata",
    [
        {"propertyValueType": "Boolean"},
        {"propertyCollectionType": "List"},
        {"propertyCollectionType": "SingleChoiceEnumeration", "propertyValueType": "String"},
    ],
)
def test_unsupported_types_produce_a_distinct_contextual_error(metadata):
    registry = Registry.from_union(PropertyTest)

    with pytest.raises(UnsupportedPropertyTypeError, match="Example / Value"):
        registry.resolve(property_details(**metadata))


class OtherNumberTest(NumberTest):
    kind: Literal["other_number"] = "other_number"


@pytest.mark.parametrize("test_union", [NumberTest | OtherNumberTest, OtherNumberTest | NumberTest])
def test_overlapping_families_are_rejected_regardless_of_registration_order(test_union):
    registry = Registry.from_union(test_union)

    with pytest.raises(AmbiguousPropertyTypeError, match="Example / Value: NumberTest, OtherNumberTest"):
        registry.resolve(property_details())


class BooleanTest(PropertyTestModel):
    """A third family used only to demonstrate extension in this test."""

    kind: Literal["boolean"] = "boolean"
    operator: Literal["is", "is not"]
    value: bool = Field(strict=True)

    @classmethod
    def accepts(cls, details: tapir.PropertyDetails) -> bool:
        return (
            details.propertyCollectionType == tapir.PropertyCollectionType.SINGLE
            and details.propertyValueType == tapir.PropertyValueType.BOOLEAN
        )

    def validate_for(self, details: tapir.PropertyDetails) -> None:
        self._require_compatible_property(details)


def test_adding_a_family_requires_only_its_class_and_the_shared_union():
    extended_tests = Annotated[TextTest | NumberTest | BooleanTest, Field(discriminator="kind")]
    registry = Registry.from_union(extended_tests)
    adapter = TypeAdapter(extended_tests)
    details = property_details(propertyValueType="Boolean")

    test = adapter.validate_json('{"kind": "boolean", "operator": "is", "value": true}')

    assert registry.resolve(details) is BooleanTest
    assert isinstance(test, BooleanTest)
    test.validate_for(details)
    assert "boolean" in adapter.json_schema()["discriminator"]["mapping"]
    with pytest.raises(UnsupportedPropertyTypeError):
        Registry.from_union(PropertyTest).resolve(details)


@pytest.mark.parametrize(
    "invalid",
    [
        str,
        TextTest,
        TextTest | str,
        Annotated[TextTest | str, Field(discriminator="kind")],
        PropertyTestModel | TextTest,
        tuple[TextTest, NumberTest],
    ],
)
def test_registry_requires_a_union_of_test_models(invalid):
    with pytest.raises(TypeError, match="PropertyTestModel"):
        Registry.from_union(invalid)


def test_registry_rejects_empty_and_abstract_family_registrations():
    with pytest.raises(ValueError, match="At least one"):
        Registry()
    with pytest.raises(TypeError, match="concrete"):
        Registry(PropertyTestModel)
