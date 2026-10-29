"""Check the public query serialization contract without a running Archicad."""

import json
from uuid import UUID

import pytest
from pydantic import ValidationError

from multiconn_archicad.models.tapir.types import ElementType
from multiconn_archicad.utilities.queries import (
    AllOf,
    AnyOf,
    ElementTypePredicate,
    NumberTest,
    PropertyPredicate,
    Query,
    TextTest,
)

pytestmark = pytest.mark.unit

PROPERTY_ID = "22222222-2222-4222-8222-222222222222"


def test_nested_query_round_trips_python_and_json_without_changing_the_tree():
    payload = {
        "schema_version": "1.0",
        "where": {
            "kind": "all",
            "items": [
                {"kind": "element_type", "types": ["Wall", "Slab"]},
                {
                    "kind": "any",
                    "items": [
                        {
                            "kind": "property",
                            "property_id": PROPERTY_ID,
                            "test": {"kind": "number", "operator": "is greater than", "value": 3},
                        },
                        {
                            "kind": "property",
                            "property_id": PROPERTY_ID,
                            "test": {"kind": "text", "operator": "does not contain", "value": "Internal"},
                        },
                    ],
                },
            ],
        },
    }

    query = Query.model_validate(payload)

    assert isinstance(query.where, AllOf)
    types, alternatives = query.where.items
    assert isinstance(types, ElementTypePredicate)
    assert types.types == (ElementType.WALL, ElementType.SLAB)
    assert isinstance(alternatives, AnyOf)
    number, text = alternatives.items
    assert isinstance(number, PropertyPredicate)
    assert number.property_id == UUID(PROPERTY_ID)
    assert isinstance(number.test, NumberTest)
    assert isinstance(text, PropertyPredicate)
    assert isinstance(text.test, TextTest)
    assert text.test.operator == "does not contain"
    assert query.model_dump(mode="json") == payload
    assert Query.model_validate_json(json.dumps(payload)) == query
    assert Query.model_validate_json(query.model_dump_json()) == query


def test_python_constructors_supply_discriminators_and_version_defaults():
    query = Query(
        where=AllOf(
            items=(
                ElementTypePredicate(types=(ElementType.WALL,)),
                PropertyPredicate(
                    property_id=UUID(PROPERTY_ID),
                    test=NumberTest(operator="is greater than", value=3),
                ),
            )
        )
    )

    payload = query.model_dump(mode="json")
    assert payload["schema_version"] == "1.0"
    assert payload["where"]["kind"] == "all"
    assert payload["where"]["items"][0] == {"kind": "element_type", "types": ["Wall"]}
    assert payload["where"]["items"][1]["test"] == {"kind": "number", "operator": "is greater than", "value": 3.0}


@pytest.mark.parametrize(
    "where",
    [
        {"kind": "unsupported"},
        {"types": ["Wall"]},
        {"kind": "element_type", "types": ["UnknownTool"]},
        {"kind": "element_type", "types": []},
        {"kind": "element_type", "types": ["Wall"], "extra": True},
        {"kind": "all", "items": []},
        {"kind": "any", "items": []},
        {"kind": "not", "item": {"kind": "element_type", "types": ["Wall"]}},
        {"kind": "property", "property_id": "not-a-guid", "test": {"kind": "text", "operator": "is", "value": "x"}},
        {"kind": "property", "property_id": PROPERTY_ID, "test": {"kind": "boolean", "operator": "is", "value": True}},
        {"kind": "property", "property_id": PROPERTY_ID, "test": {"kind": "length", "operator": "is", "value": 3}},
        {
            "kind": "property",
            "property_id": PROPERTY_ID,
            "test": {"kind": "number", "operator": "contains", "value": 3},
        },
        {
            "kind": "property",
            "property_id": PROPERTY_ID,
            "test": {"kind": "text", "operator": "is greater than", "value": "x"},
        },
        {
            "kind": "property",
            "property_id": PROPERTY_ID,
            "test": {"kind": "number", "operator": "is", "value": 3, "unit": "m"},
        },
        {"kind": "property", "property_id": PROPERTY_ID, "test": {"kind": "text", "operator": "eq", "value": "x"}},
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
            "items": [{"kind": "not", "item": {"kind": "element_type", "types": ["Wall"]}}],
        }
    }

    for parse, value in [(Query.model_validate, payload), (Query.model_validate_json, json.dumps(payload))]:
        with pytest.raises(ValidationError) as caught:
            parse(value)
        assert caught.value.errors()[0]["type"] == "union_tag_invalid"


def test_schema_version_is_preserved_as_a_plain_string():
    version = "1.1"
    payload = {"schema_version": version, "where": {"kind": "element_type", "types": ["Wall"]}}

    query = Query.model_validate(payload)

    assert query.schema_version == version
    assert Query.model_validate_json(query.model_dump_json()) == query


def test_query_envelope_rejects_extra_fields():
    with pytest.raises(ValidationError):
        Query.model_validate({"where": {"kind": "element_type", "types": ["Wall"]}, "limit": 10})


@pytest.mark.parametrize("value", [True, False, "3", None, float("nan"), float("inf"), -float("inf")])
def test_number_operands_reject_coercion_and_nonfinite_numbers(value):
    with pytest.raises(ValidationError):
        NumberTest(operator="is", value=value)
    with pytest.raises(ValidationError):
        NumberTest.model_validate_json(json.dumps({"operator": "is", "value": value}))


@pytest.mark.parametrize("value", [0, -2, 3, 3.5])
def test_number_operands_accept_integer_and_real_si_values(value):
    assert NumberTest(operator="is", value=value).value == value


@pytest.mark.parametrize("value", [3, True, None, b"External"])
def test_text_operands_require_strings(value):
    with pytest.raises(ValidationError):
        TextTest(operator="is", value=value)


def test_models_and_collections_preserve_validated_state():
    source_types = ["Wall"]
    node = ElementTypePredicate.model_validate({"types": source_types})
    source_items = [node]
    group = AllOf.model_validate({"items": source_items})

    source_types.append("InvalidTool")
    source_items.clear()

    assert node.types == (ElementType.WALL,)
    assert group.items == (node,)
    with pytest.raises(ValidationError, match="frozen"):
        node.types = ()
    test = NumberTest(operator="is", value=3)
    with pytest.raises(ValidationError, match="frozen"):
        test.value = float("nan")


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
    }
    assert "Negate" not in definitions
    assert definitions["AllOf"]["properties"]["items"]["items"]["discriminator"]["propertyName"] == "kind"
    assert set(definitions["PropertyPredicate"]["properties"]["test"]["discriminator"]["mapping"]) == {"text", "number"}
    assert definitions["TextTest"]["properties"]["operator"]["enum"] == [
        "is",
        "is not",
        "contains",
        "does not contain",
        "starts with",
        "ends with",
    ]
    assert definitions["NumberTest"]["properties"]["operator"]["enum"] == [
        "is",
        "is not",
        "is greater than",
        "is greater than or equal to",
        "is less than",
        "is less than or equal to",
    ]
    assert (
        definitions["NumberTest"]["properties"]["value"]["description"] == "Numeric operand; quantities use SI units."
    )
