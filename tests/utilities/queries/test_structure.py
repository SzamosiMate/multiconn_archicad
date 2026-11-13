"""Executable expression shape, strict operands, immutability and JSON Schema."""

import json

import pytest
from pydantic import ValidationError

from multiconn_archicad.models.tapir.types import ElementType
from multiconn_archicad.utilities.queries import (
    AllOf,
    AnyOf,
    BooleanTest,
    ClassificationPredicate,
    ClassificationTest,
    ElementTypePredicate,
    ElementTypeTest,
    NumberTest,
    PropertyPredicate,
    Query,
    TextTest,
)

pytestmark = pytest.mark.unit

PROPERTY_ID = "22222222-2222-4222-8222-222222222222"


@pytest.mark.parametrize(
    "where",
    [
        {"kind": "unsupported"},
        {"test": {"kind": "element_type", "types": ["Wall"]}},
        {"kind": "element_type", "types": ["Wall"]},
        {"kind": "element_type", "test": {"kind": "element_type", "types": ["UnknownTool"]}},
        {"kind": "element_type", "test": {"kind": "element_type", "types": []}},
        {"kind": "element_type", "test": {"kind": "element_type", "types": ["Wall"]}, "extra": True},
        {"kind": "all", "items": []},
        {"kind": "any", "items": []},
        {"kind": "not", "item": {"kind": "element_type", "test": {"kind": "element_type", "types": ["Wall"]}}},
        {"kind": "property", "field_id": "not-a-guid", "test": {"kind": "text", "operator": "is", "value": "x"}},
        {"kind": "property", "field_id": PROPERTY_ID, "test": {"kind": "enum", "operator": "is", "value": "A"}},
        {
            "kind": "property",
            "field_id": PROPERTY_ID,
            "test": {"kind": "boolean", "operator": "contains", "value": True},
        },
        {"kind": "property", "field_id": PROPERTY_ID, "test": {"kind": "length", "operator": "is", "value": 3}},
        {
            "kind": "property",
            "field_id": PROPERTY_ID,
            "test": {"kind": "number", "operator": "contains", "value": 3},
        },
        {
            "kind": "property",
            "field_id": PROPERTY_ID,
            "test": {"kind": "text", "operator": "is greater than", "value": "x"},
        },
        {
            "kind": "property",
            "field_id": PROPERTY_ID,
            "test": {"kind": "number", "operator": "is", "value": 3, "unit": "m"},
        },
        {"kind": "property", "field_id": PROPERTY_ID, "test": {"kind": "text", "operator": "eq", "value": "x"}},
    ],
    ids=[
        "unknown-kind",
        "missing-predicate-discriminator",
        "missing-test",
        "unknown-element-type",
        "empty-type-membership",
        "extra-predicate-field",
        "empty-and",
        "empty-or",
        "general-negation",
        "malformed-field-guid",
        "unsupported-test-family",
        "text-operator-on-boolean",
        "unknown-test-family",
        "text-operator-on-number",
        "number-operator-on-text",
        "extra-test-field",
        "operator-alias",
    ],
)
def test_invalid_predicates_are_rejected_from_python_and_json(where):
    payload = {"schema_version": "1.0", "where": where}

    with pytest.raises(ValidationError):
        Query.model_validate(payload)
    with pytest.raises(ValidationError):
        Query.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize("group", ["all", "any"])
def test_general_negation_is_rejected_inside_groups(group):
    payload = {
        "where": {
            "kind": group,
            "items": [
                {"kind": "not", "item": {"kind": "element_type", "test": {"kind": "element_type", "types": ["Wall"]}}}
            ],
        }
    }

    for parse, value in [(Query.model_validate, payload), (Query.model_validate_json, json.dumps(payload))]:
        with pytest.raises(ValidationError) as caught:
            parse(value)
        assert caught.value.errors()[0]["type"] == "union_tag_invalid"


def test_query_envelope_rejects_extra_fields():
    with pytest.raises(ValidationError):
        Query.model_validate(
            {"where": {"kind": "element_type", "test": {"kind": "element_type", "types": ["Wall"]}}, "limit": 10}
        )


@pytest.mark.parametrize("value", [True, False, "3", None, float("nan"), float("inf"), -float("inf")])
def test_number_operands_reject_coercion_and_nonfinite_numbers(value):
    with pytest.raises(ValidationError):
        NumberTest(operator="is", value=value)
    with pytest.raises(ValidationError):
        NumberTest.model_validate_json(json.dumps({"operator": "is", "value": value}))


@pytest.mark.parametrize("value", [0, -2, 3, 3.5])
def test_number_operands_accept_finite_integers_and_reals(value):
    assert NumberTest(operator="is", value=value).value == value


@pytest.mark.parametrize("value", [3, True, None, b"External"])
def test_text_operands_require_strings(value):
    with pytest.raises(ValidationError):
        TextTest(operator="is", value=value)


def test_models_and_collections_preserve_validated_state():
    source_types = ["Wall"]
    node = ElementTypePredicate.model_validate({"test": {"types": source_types}})
    source_items = [node]
    group = AllOf.model_validate({"items": source_items})

    source_types.append("InvalidTool")
    source_items.clear()

    assert node.test.types == (ElementType.WALL,)
    assert group.items == (node,)


@pytest.mark.parametrize(
    ("model", "attribute"),
    [
        (Query(where=ElementTypePredicate(test=ElementTypeTest(types=("Wall",)))), "schema_version"),
        (AllOf(items=(ElementTypePredicate(test=ElementTypeTest(types=("Wall",))),)), "items"),
        (AnyOf(items=(ElementTypePredicate(test=ElementTypeTest(types=("Wall",))),)), "items"),
        (ElementTypePredicate(test=ElementTypeTest(types=("Wall",))), "test"),
        (PropertyPredicate(field_id=PROPERTY_ID, test=NumberTest(operator="is", value=3)), "field_id"),
        (ClassificationPredicate(field_id=PROPERTY_ID, test=ClassificationTest(operator="has value")), "field_id"),
        (ElementTypeTest(types=("Wall",)), "types"),
        (TextTest(operator="is", value="external"), "value"),
        (NumberTest(operator="is", value=3), "value"),
        (BooleanTest(operator="is", value=True), "value"),
        (ClassificationTest(operator="has value"), "operator"),
    ],
    ids=lambda value: type(value).__name__ if not isinstance(value, str) else value,
)
def test_executable_models_are_frozen(model, attribute):
    original = model.model_dump_json()

    with pytest.raises(ValidationError, match="frozen"):
        setattr(model, attribute, None)

    assert model.model_dump_json() == original


def test_json_tests_require_their_own_discriminator():
    payload = {
        "where": {"kind": "property", "field_id": PROPERTY_ID, "test": {"operator": "is", "value": 3}},
    }

    with pytest.raises(ValidationError, match="union_tag_not_found"):
        Query.model_validate_json(json.dumps(payload))


def test_json_schema_exposes_recursive_nodes_and_typed_operator_choices():
    schema = Query.model_json_schema()
    definitions = schema["$defs"]

    assert schema["properties"]["schema_version"]["type"] == "string"
    assert schema["properties"]["schema_version"]["default"] == "1.0"
    assert set(schema["properties"]["where"]["discriminator"]["mapping"]) == {
        "all",
        "any",
        "element_type",
        "property",
        "classification",
    }
    assert "Negate" not in definitions
    for name in ("PropertyPredicate", "ClassificationPredicate"):
        assert definitions[name]["properties"]["field_id"] == {
            "format": "uuid",
            "title": "Field Id",
            "type": "string",
        }
        assert "field_id" in definitions[name]["required"]
    assert definitions["AllOf"]["properties"]["items"]["items"]["discriminator"]["propertyName"] == "kind"
    assert set(definitions["PropertyPredicate"]["properties"]["test"]["discriminator"]["mapping"]) == {
        "text",
        "number",
        "boolean",
    }
    assert definitions["BooleanTest"]["properties"]["value"]["type"] == "boolean"
    assert definitions["BooleanOperator"]["enum"] == ["is", "is not"]
    assert definitions["TextTest"]["properties"]["operator"] == {"$ref": "#/$defs/TextOperator"}
    assert definitions["NumberTest"]["properties"]["operator"] == {"$ref": "#/$defs/NumberOperator"}
    assert definitions["TextOperator"]["enum"] == [
        "is",
        "is not",
        "contains",
        "does not contain",
        "starts with",
        "ends with",
    ]
    assert definitions["NumberOperator"]["enum"] == [
        "is",
        "is not",
        "is greater than",
        "is greater than or equal to",
        "is less than",
        "is less than or equal to",
    ]


@pytest.mark.parametrize("value", [0, 1, 0.0, 1.0, "True", "False", "true", "false", None])
def test_boolean_operands_require_actual_booleans_in_python_and_json(value):
    with pytest.raises(ValidationError):
        BooleanTest(operator="is", value=value)
    with pytest.raises(ValidationError):
        BooleanTest.model_validate_json(json.dumps({"operator": "is", "value": value}))


@pytest.mark.parametrize("value", [True, False])
def test_boolean_query_round_trip_preserves_boolean_operands(value):
    payload = {
        "schema_version": "1.0",
        "where": {
            "kind": "property",
            "field_id": PROPERTY_ID,
            "test": {"kind": "boolean", "operator": "is", "value": value},
        },
    }
    query = Query.model_validate(payload)
    assert isinstance(query.where.test, BooleanTest)
    assert query.where.test.value is value
    assert query.model_dump(mode="json") == payload
    assert Query.model_validate_json(json.dumps(payload)) == query
