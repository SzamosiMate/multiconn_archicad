"""Verify the uniform field API against synthetic property metadata."""

import json
from uuid import UUID

import pytest
from pydantic import ValidationError

from multiconn_archicad.models.tapir import types as tapir
from multiconn_archicad.utilities.queries import (
    AmbiguousPropertyTypeError,
    FieldInfo,
    InvalidPropertyTestError,
    NumberTest,
    PropertyInfo,
    PropertyPredicate,
    PropertyTest,
    Query,
    TextTest,
    UnsupportedPropertyTypeError,
)
from multiconn_archicad.utilities.queries import TestRegistry as Registry

pytestmark = pytest.mark.unit

PROPERTY_ID = "22222222-2222-4222-8222-222222222222"


def property_details(**changes) -> tapir.PropertyDetails:
    data = {
        "propertyId": {"guid": PROPERTY_ID},
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


@pytest.mark.parametrize(
    ("group", "name", "qualified_name"),
    [
        ("Example", "Height", "Example / Height"),
        ("", "Height", "Height"),
        ("GeneralElemProperties", "General_Opening_IDs", "GeneralElemProperties / General_Opening_IDs"),
    ],
)
def test_uniform_names_preserve_upstream_labels_and_derive_qualified_name(group, name, qualified_name):
    info = PropertyInfo(
        property_details(propertyGroupName=group, propertyName=name),
        Registry.from_union(PropertyTest),
    )

    assert isinstance(info, FieldInfo)
    assert info.name == name
    assert info.group == group
    assert info.qualified_name == qualified_name
    assert info.property_id == UUID(PROPERTY_ID)
    assert info.reference == {"kind": "property", "property_id": PROPERTY_ID}


@pytest.mark.parametrize(
    ("metadata", "data", "family"),
    [
        ({}, {"operator": "is greater than", "value": 3}, NumberTest),
        (
            {"propertyValueType": "String", "propertyMeasureType": "Default"},
            {"operator": "starts with", "value": "External"},
            TextTest,
        ),
    ],
)
def test_field_selection_exposes_operators_and_creates_tests_for_query_serialization(metadata, data, family):
    info = PropertyInfo(property_details(**metadata), Registry.from_union(PropertyTest))

    assert info.test_model is family
    assert info.operators() == family.operators()
    test = info.create_test(**data)
    assert isinstance(test, family)
    info.validate(test)

    predicate = PropertyPredicate.model_validate({**info.reference, "test": test})
    query = Query(where=predicate)
    assert Query.model_validate_json(query.model_dump_json()) == query


@pytest.mark.parametrize("measure", list(tapir.PropertyMeasureType))
def test_describe_returns_json_friendly_uniform_discovery_information(measure):
    info = PropertyInfo(property_details(propertyMeasureType=measure), Registry.from_union(PropertyTest))

    description = json.loads(json.dumps(info.describe()))

    assert description["reference"] == info.reference
    assert description["name"] == "Height"
    assert description["group"] == "Example"
    assert description["qualified_name"] == "Example / Height"
    assert description["measure_type"] == measure.value
    assert description["operators"] == list(info.operators())
    assert description["test_schema"] == info.test_schema()
    assert description["test_schema"]["properties"]["value"]["type"] == "number"


def test_metadata_and_returned_values_cannot_change_the_field_snapshot():
    details = property_details()
    info = PropertyInfo(details, Registry.from_union(PropertyTest))

    details.propertyName = "Changed"
    details.propertyValueType = tapir.PropertyValueType.STRING
    returned_details = info.details
    returned_details.propertyGroupName = "Changed"
    returned_reference = info.reference
    returned_reference["property_id"] = "changed"
    description = info.describe()
    description["test_schema"]["$defs"]["NumberOperator"]["enum"].clear()

    assert info.qualified_name == "Example / Height"
    assert info.reference["property_id"] == PROPERTY_ID
    assert info.details.propertyMeasureType == tapir.PropertyMeasureType.LENGTH
    assert info.details.propertyValueType == tapir.PropertyValueType.REAL
    assert info.test_schema()["$defs"]["NumberOperator"]["enum"]
    assert isinstance(info.create_test(operator="is", value=3), NumberTest)


def test_same_labels_do_not_merge_distinct_property_identities():
    registry = Registry.from_union(PropertyTest)
    first = PropertyInfo(property_details(), registry)
    second = PropertyInfo(property_details(propertyId={"guid": "11111111-1111-4111-8111-111111111111"}), registry)

    assert first.qualified_name == second.qualified_name
    assert first.reference != second.reference


@pytest.mark.parametrize(
    "data",
    [
        {"operator": "contains", "value": 3},
        {"operator": "is", "value": "3"},
        {"kind": "text", "operator": "is", "value": "3"},
    ],
)
def test_create_test_runs_structure_validation(data):
    info = PropertyInfo(property_details(), Registry.from_union(PropertyTest))

    with pytest.raises(ValidationError):
        info.create_test(**data)


def test_validate_rejects_tests_from_another_family():
    info = PropertyInfo(property_details(), Registry.from_union(PropertyTest))

    with pytest.raises(InvalidPropertyTestError, match="Example / Height requires NumberTest, got TextTest"):
        info.validate(TextTest(operator="is", value="3"))


class LimitedNumberTest(NumberTest):
    def validate_for(self, details: tapir.PropertyDetails) -> None:
        super().validate_for(details)
        if self.value > 10:
            raise InvalidPropertyTestError("Example operand limit is 10")


def test_create_and_validate_both_apply_family_context_rules():
    info = PropertyInfo(property_details(), Registry(LimitedNumberTest))

    assert isinstance(info.create_test(operator="is", value=10), LimitedNumberTest)
    with pytest.raises(InvalidPropertyTestError, match="operand limit"):
        info.create_test(operator="is", value=11)
    with pytest.raises(InvalidPropertyTestError, match="operand limit"):
        info.validate(LimitedNumberTest(operator="is", value=11))


def test_construction_preserves_unsupported_and_ambiguous_registry_errors():
    with pytest.raises(UnsupportedPropertyTypeError):
        PropertyInfo(property_details(propertyValueType="Boolean"), Registry.from_union(PropertyTest))
    with pytest.raises(AmbiguousPropertyTypeError):
        PropertyInfo(property_details(), Registry(NumberTest, LimitedNumberTest))
