"""Check test discovery and explicit context validation using offline metadata."""

import pytest

from multiconn_archicad.models.tapir import types as tapir
from multiconn_archicad.utilities.queries import (
    BooleanTest,
    InvalidPropertyTestError,
    NumberTest,
    PropertyTestModel,
    TextTest,
)
from multiconn_archicad.utilities.results.batch_results import BatchSlot

from .support import property_details

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("source", ["StaticBuiltIn", "DynamicBuiltIn", "Custom"])
@pytest.mark.parametrize(
    ("test", "metadata"),
    [
        (
            TextTest(operator="contains", value="External"),
            {"propertyValueType": "String", "propertyMeasureType": "Default"},
        ),
        (NumberTest(operator="is greater than", value=3), {}),
        (BooleanTest(operator="is", value=False), {"propertyValueType": "Boolean", "propertyMeasureType": "Default"}),
    ],
)
def test_families_accept_and_validate_builtin_and_custom_property_types(source, test, metadata):
    details = property_details(propertyType=source, **metadata)

    assert type(test).accepts(details)
    assert test.validate_for(details) is None


@pytest.mark.parametrize(
    ("family", "metadata", "value_type"),
    [
        (TextTest, {"propertyValueType": "String", "propertyMeasureType": "Default"}, "string"),
        (NumberTest, {}, "number"),
        (BooleanTest, {"propertyValueType": "Boolean", "propertyMeasureType": "Default"}, "boolean"),
    ],
)
def test_family_schema_describes_compatible_operands(family, metadata, value_type):
    schema = family.schema_for(property_details(**metadata))

    assert schema["properties"]["value"]["type"] == value_type
    operator_reference = schema["properties"]["operator"]["$ref"]
    enum_name = operator_reference.rsplit("/", 1)[1]
    assert schema["$defs"][enum_name]["enum"] == list(family.operators())


def test_new_families_must_explicitly_implement_context_validation():
    class IncompleteTest(PropertyTestModel):
        @classmethod
        def accepts(cls, details: tapir.PropertyDetails) -> bool:
            return True

        def evaluate(self, raw_value: str) -> BatchSlot[bool]:
            return BatchSlot.success(True)

    with pytest.raises(TypeError, match="validate_for"):
        IncompleteTest()


def test_new_families_must_explicitly_implement_evaluation():
    class IncompleteTest(PropertyTestModel):
        @classmethod
        def accepts(cls, details: tapir.PropertyDetails) -> bool:
            return True

        def validate_for(self, details: tapir.PropertyDetails) -> None:
            self._require_compatible_property(details)

    with pytest.raises(TypeError, match="evaluate"):
        IncompleteTest()


@pytest.mark.parametrize("measure", list(tapir.PropertyMeasureType))
def test_number_family_accepts_real_properties_across_all_measure_types(measure):
    details = property_details(propertyMeasureType=measure)
    test = NumberTest(operator="is greater than", value=3)

    assert NumberTest.accepts(details)
    test.validate_for(details)


def test_number_family_accepts_fractional_thresholds_for_integer_properties():
    details = property_details(propertyValueType="Integer", propertyMeasureType="Default")
    test = NumberTest(operator="is greater than", value=2.5)

    assert NumberTest.accepts(details)
    test.validate_for(details)


@pytest.mark.parametrize(
    ("test", "value_type"),
    [
        pytest.param(TextTest(operator="is", value="3"), "Real", id="text-on-number"),
        pytest.param(TextTest(operator="is", value="yes"), "Boolean", id="text-on-boolean"),
        pytest.param(NumberTest(operator="is", value=3), "String", id="number-on-text"),
        pytest.param(NumberTest(operator="is", value=3), "Boolean", id="number-on-boolean"),
        pytest.param(BooleanTest(operator="is", value=True), "Real", id="boolean-on-number"),
        pytest.param(BooleanTest(operator="is", value=True), "String", id="boolean-on-text"),
    ],
)
def test_scalar_fields_reject_tests_from_another_family(test, value_type):
    details = property_details(propertyValueType=value_type)

    assert not type(test).accepts(details)
    with pytest.raises(InvalidPropertyTestError, match="Example / Height"):
        test.validate_for(details)
    with pytest.raises(InvalidPropertyTestError, match="Example / Height"):
        type(test).schema_for(details)


@pytest.mark.parametrize(
    ("family", "value_type", "operand"),
    [(TextTest, "String", "A"), (NumberTest, "Real", 3), (BooleanTest, "Boolean", True)],
    ids=["text", "number", "boolean"],
)
@pytest.mark.parametrize("collection", ["Undefined", "List", "SingleChoiceEnumeration", "MultipleChoiceEnumeration"])
def test_only_scalar_single_values_are_supported(family, value_type, operand, collection):
    details = property_details(propertyValueType=value_type, propertyCollectionType=collection)

    assert not family.accepts(details)
    with pytest.raises(InvalidPropertyTestError, match="Example / Height"):
        family(operator="is", value=operand).validate_for(details)
    with pytest.raises(InvalidPropertyTestError):
        family.schema_for(details)
