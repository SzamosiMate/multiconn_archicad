"""Verify the uniform field API against synthetic property metadata."""

import json
from uuid import UUID

import pytest
from pydantic import ValidationError

from multiconn_archicad.models.tapir import types as tapir
from multiconn_archicad.utilities.queries import (
    BUILTIN_QUERY_FIELDS,
    AmbiguousPropertyTypeError,
    ElementTypeInfo,
    TYPES_ALL,
    TYPES_2D,
    TYPES_3D,
    TYPES_3D_COMPONENTS,
    TYPES_3D_WITH_COMPONENTS,
    ElementTypeTest,
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
from multiconn_archicad.utilities.queries.editing import QueryRow, QueryRows, build_query

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


def test_describes_added_scalar_inputs_from_the_registered_test_schema():
    class BoundedNumberTest(NumberTest):
        limit: float = 10

    info = PropertyInfo(property_details(), Registry(BoundedNumberTest))

    description = info.describe_test_inputs(current_data={})
    assert description is not None
    operator, value, limit = description.fields
    assert (operator.name, value.name, limit.name) == ("operator", "value", "limit")
    assert (operator.required, value.required, limit.required) == (True, True, False)
    assert description.definitions["NumberOperator"]["enum"] == list(info.operators())
    assert value.schema["type"] == "number"
    assert limit.schema["default"] == 10
    description.definitions.clear()
    value.schema.clear()

    fresh_description = info.describe_test_inputs(current_data={})
    assert fresh_description is not None
    assert fresh_description.definitions["NumberOperator"]["enum"]
    assert fresh_description.fields[1].schema["type"] == "number"


def test_builtin_element_type_choices_compile_through_the_field_description():
    field = next(field for field in BUILTIN_QUERY_FIELDS if isinstance(field, ElementTypeInfo))
    assert field.reference == {"kind": "element_type"}
    assert field.operators() == ()
    description = field.describe_test_inputs(current_data={})
    assert description is not None
    (types_input,) = description.fields
    assert types_input.name == "types"
    assert types_input.required
    assert [choice["title"] for choice in types_input.schema["oneOf"][:5]] == (
        ["All Types", "3D Types", "2D Types", "3D Component Types", "3D Types with Components"]
    )
    choice = next(choice for choice in types_input.schema["oneOf"] if choice["title"] == "Wall")
    assert choice["const"] == ["Wall"]

    data = {"types": choice["const"]}
    test = field.create_test(**data)
    assert test == ElementTypeTest(types=(tapir.ElementType.WALL,))
    row = QueryRow(predicate={**field.reference, "test": test.model_dump(mode="json")})
    result = build_query(QueryRows(rows=[row]))
    assert result.query is not None, result.issues
    assert result.query.where.candidate_types() == frozenset({tapir.ElementType.WALL})


@pytest.mark.parametrize(
    ("title", "types"),
    [
        ("All Types", TYPES_ALL),
        ("3D Types", TYPES_3D),
        ("3D Component Types", TYPES_3D_COMPONENTS),
        ("3D Types with Components", TYPES_3D_WITH_COMPONENTS),
        ("2D Types", TYPES_2D),
    ],
)
def test_element_type_presets_compile_and_save_concrete_types(title, types):
    field = ElementTypeInfo()
    description = field.describe_test_inputs(current_data={})
    (types_input,) = description.fields
    choice = next(choice for choice in types_input.schema["oneOf"] if choice["title"] == title)
    assert choice["const"] == [element_type.value for element_type in types]
    test = field.create_test(types=choice["const"])
    row = QueryRow(predicate={**field.reference, "test": test.model_dump(mode="json")})
    saved = QueryRows(rows=[row]).model_dump_json()

    restored = QueryRows.model_validate_json(saved, context={"require_schema_version": True})
    result = build_query(restored)

    assert result.query is not None, result.issues
    assert result.query.where.test.types == types
    assert result.query.where.candidate_types() == frozenset(types)
    assert "types" in restored.rows[0].predicate["test"]


def test_element_type_editor_choices_do_not_restrict_the_test_schema():
    from jsonschema import Draft202012Validator

    field = ElementTypeInfo()
    schema = field.test_schema()
    validator = Draft202012Validator(schema)
    payload = {"kind": "element_type", "types": ["Wall", "Window"]}

    assert "oneOf" not in schema["properties"]["types"]
    validator.validate(payload)
    assert field.create_test(**payload).types == (tapir.ElementType.WALL, tapir.ElementType.WINDOW)
    assert not validator.is_valid({"kind": "element_type", "types": ["NotAnElementType"]})


def test_element_type_preset_descriptions_are_independent_snapshots():
    field = ElementTypeInfo()
    first = field.describe_test_inputs(current_data={})
    choice = next(option for option in first.fields[0].schema["oneOf"] if option["title"] == "3D Types")
    choice["const"].clear()

    second = field.describe_test_inputs(current_data={})

    fresh = next(option for option in second.fields[0].schema["oneOf"] if option["title"] == "3D Types")
    assert fresh["const"] == [element_type.value for element_type in TYPES_3D]


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
    assert info.reference == {"kind": "property", "field_id": PROPERTY_ID}


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
    returned_reference["field_id"] = "changed"
    description = info.describe()
    description["test_schema"]["$defs"]["NumberOperator"]["enum"].clear()

    assert info.qualified_name == "Example / Height"
    assert info.reference["field_id"] == PROPERTY_ID
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
        PropertyInfo(property_details(propertyValueType="Guid"), Registry.from_union(PropertyTest))
    with pytest.raises(AmbiguousPropertyTypeError):
        PropertyInfo(property_details(), Registry(NumberTest, LimitedNumberTest))
