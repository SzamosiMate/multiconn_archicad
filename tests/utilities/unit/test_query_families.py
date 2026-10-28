"""Check test discovery and explicit context validation using offline metadata."""

import pytest

from multiconn_archicad.models.tapir import types as tapir
from multiconn_archicad.utilities.queries import InvalidPropertyTestError, NumberTest, PropertyTestModel, TextTest

pytestmark = pytest.mark.unit


def property_details(**changes) -> tapir.PropertyDetails:
    """Build synthetic metadata independently of any open Archicad project."""
    data = {
        "propertyId": {"guid": "22222222-2222-4222-8222-222222222222"},
        "propertyType": "Custom",
        "propertyGroupName": "Example",
        "propertyName": "Height",
        "propertyCollectionType": "Single",
        "propertyValueType": "Real",
        "propertyMeasureType": "Length",
        "propertyIsEditable": True,
        "isExpressionBased": False,
    }
    data.update(changes)
    return tapir.PropertyDetails.model_validate(data)


@pytest.mark.parametrize("source", ["StaticBuiltIn", "DynamicBuiltIn", "Custom"])
@pytest.mark.parametrize(
    ("test", "metadata"),
    [
        (
            TextTest(operator="contains", value="External"),
            {"propertyValueType": "String", "propertyMeasureType": "Default"},
        ),
        (NumberTest(operator="is greater than", value=3), {}),
    ],
)
def test_families_accept_and_validate_builtin_and_custom_property_types(source, test, metadata):
    details = property_details(propertyType=source, **metadata)

    assert type(test).accepts(details)
    assert test.validate_for(details) is None


@pytest.mark.parametrize(
    ("test", "metadata"),
    [
        (TextTest(operator="is", value="3"), {}),
        (
            TextTest(operator="is", value="A"),
            {"propertyValueType": "String", "propertyCollectionType": "SingleChoiceEnumeration"},
        ),
        (TextTest(operator="contains", value="A"), {"propertyValueType": "String", "propertyCollectionType": "List"}),
        (NumberTest(operator="is", value=3), {"propertyValueType": "String"}),
        (NumberTest(operator="is", value=3), {"propertyValueType": "Boolean"}),
        (NumberTest(operator="is", value=3), {"propertyValueType": "Guid"}),
        (NumberTest(operator="is", value=3), {"propertyCollectionType": "List"}),
        (NumberTest(operator="is", value=3), {"propertyCollectionType": "SingleChoiceEnumeration"}),
    ],
)
def test_context_validation_rejects_incompatible_metadata_after_structure_validation(test, metadata):
    details = property_details(**metadata)

    assert not type(test).accepts(details)
    with pytest.raises(InvalidPropertyTestError, match=f"{type(test).__name__}.*Example / Height"):
        test.validate_for(details)
    with pytest.raises(InvalidPropertyTestError, match="Example / Height"):
        type(test).schema_for(details)


def test_families_expose_readable_operators_directly():
    assert TextTest.operators() == ("is", "is not", "contains", "does not contain", "starts with", "ends with")
    assert NumberTest.operators() == (
        "is",
        "is not",
        "is greater than",
        "is greater than or equal to",
        "is less than",
        "is less than or equal to",
    )


@pytest.mark.parametrize(
    ("family", "metadata", "value_type"),
    [
        (TextTest, {"propertyValueType": "String", "propertyMeasureType": "Default"}, "string"),
        (NumberTest, {}, "number"),
    ],
)
def test_family_schema_describes_compatible_operands(family, metadata, value_type):
    schema = family.schema_for(property_details(**metadata))

    assert schema["properties"]["value"]["type"] == value_type
    assert schema["properties"]["operator"]["enum"] == list(family.operators())


def test_new_families_must_explicitly_implement_context_validation():
    class IncompleteTest(PropertyTestModel):
        @classmethod
        def accepts(cls, details: tapir.PropertyDetails) -> bool:
            return True

    with pytest.raises(TypeError, match="validate_for"):
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


@pytest.mark.parametrize("collection", ["Undefined", "List", "SingleChoiceEnumeration", "MultipleChoiceEnumeration"])
def test_number_family_rejects_numeric_collections_and_enum_choices(collection):
    details = property_details(propertyCollectionType=collection)

    assert not NumberTest.accepts(details)
    with pytest.raises(InvalidPropertyTestError):
        NumberTest(operator="is", value=3).validate_for(details)
