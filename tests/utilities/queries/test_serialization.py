"""Save/load query definitions and enforce documented major/minor compatibility."""

from uuid import UUID

import pytest
from pydantic import ValidationError

from multiconn_archicad.models.tapir.types import ElementType
from multiconn_archicad.utilities.queries import (
    QUERY_SCHEMA_VERSION,
    AllOf,
    AnyOf,
    BooleanOperator,
    BooleanTest,
    ElementTypePredicate,
    ElementTypeTest,
    NumberOperator,
    NumberTest,
    PropertyPredicate,
    Query,
    TextOperator,
    TextTest,
    UnsupportedQueryVersionError,
    validate_query_version,
    versioning,
)

pytestmark = pytest.mark.unit

PROPERTY_ID = "22222222-2222-4222-8222-222222222222"


def test_default_query_version_is_supported():
    query = Query.model_validate(
        {"where": {"kind": "element_type", "test": {"kind": "element_type", "types": ["Wall"]}}}
    )

    assert query.schema_version == QUERY_SCHEMA_VERSION == "1.0"
    validate_query_version(query.schema_version)


def test_persisted_queries_require_explicit_version():
    query = Query.model_validate(
        {"where": {"kind": "element_type", "test": {"kind": "element_type", "types": ["Wall"]}}}
    )
    context = {"require_schema_version": True}
    assert Query.model_validate(query.model_dump(), context=context) == query
    assert Query.model_validate_json(query.model_dump_json(), context=context) == query
    with pytest.raises(ValidationError, match="schema_version"):
        Query.model_validate(query.model_dump(exclude_defaults=True), context=context)
    with pytest.raises(ValidationError, match="schema_version"):
        Query.model_validate_json(query.model_dump_json(exclude_unset=True), context=context)
    assert (
        Query.model_validate({**query.model_dump(), "schema_version": "2.0"}, context=context).schema_version == "2.0"
    )


@pytest.mark.parametrize("requested", ["1.0", "1.3", "1.9", "1.10"])
def test_same_major_and_older_or_equal_minor_are_supported(monkeypatch, requested):
    monkeypatch.setattr(versioning, "QUERY_SCHEMA_VERSION", "1.10")

    validate_query_version(requested)


@pytest.mark.parametrize("requested", ["0.9", "1.11", "2.0"])
def test_other_majors_and_future_minors_are_rejected(monkeypatch, requested):
    monkeypatch.setattr(versioning, "QUERY_SCHEMA_VERSION", "1.10")

    with pytest.raises(UnsupportedQueryVersionError) as caught:
        validate_query_version(requested)

    assert caught.value.requested_version == requested
    assert caught.value.supported_version == "1.10"


@pytest.mark.parametrize("requested", ["", "1", "1.0.0", "1.0rc1", " 1.0", "1.0\n", "-1.0", "one.zero"])
def test_malformed_versions_are_rejected(requested):
    with pytest.raises(ValueError, match="expected 'major.minor'"):
        validate_query_version(requested)


def test_nested_query_round_trips_python_and_json_without_changing_the_tree():
    payload = {
        "schema_version": "1.0",
        "where": {
            "kind": "all",
            "items": [
                {"kind": "element_type", "test": {"kind": "element_type", "types": ["Wall", "Slab"]}},
                {
                    "kind": "any",
                    "items": [
                        {
                            "kind": "property",
                            "field_id": PROPERTY_ID,
                            "test": {"kind": "number", "operator": "is greater than", "value": 3},
                        },
                        {
                            "kind": "property",
                            "field_id": PROPERTY_ID,
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
    assert types.test.types == (ElementType.WALL, ElementType.SLAB)
    assert isinstance(alternatives, AnyOf)
    number, text = alternatives.items
    assert isinstance(number, PropertyPredicate)
    assert number.field_id == UUID(PROPERTY_ID)
    assert isinstance(number.test, NumberTest)
    assert isinstance(text, PropertyPredicate)
    assert isinstance(text.test, TextTest)
    assert text.test.operator == "does not contain"
    assert query.model_dump(mode="json") == payload
    assert Query.model_validate_json(query.model_dump_json()) == query


def test_python_constructors_supply_discriminators_and_version_defaults():
    query = Query(
        where=AllOf(
            items=(
                ElementTypePredicate(test=ElementTypeTest(types=(ElementType.WALL,))),
                PropertyPredicate(
                    field_id=UUID(PROPERTY_ID),
                    test=NumberTest(operator="is greater than", value=3),
                ),
            )
        )
    )

    payload = query.model_dump(mode="json")
    assert payload["schema_version"] == "1.0"
    assert payload["where"]["kind"] == "all"
    assert payload["where"]["items"][0] == {"kind": "element_type", "test": {"kind": "element_type", "types": ["Wall"]}}
    assert payload["where"]["items"][1]["test"] == {"kind": "number", "operator": "is greater than", "value": 3.0}


def test_schema_version_is_preserved_as_a_plain_string():
    version = "1.1"
    payload = {
        "schema_version": version,
        "where": {"kind": "element_type", "test": {"kind": "element_type", "types": ["Wall"]}},
    }

    query = Query.model_validate(payload)

    assert query.schema_version == version
    assert Query.model_validate_json(query.model_dump_json()) == query


@pytest.mark.parametrize(
    ("family", "operator", "value"),
    [
        (TextTest, TextOperator.CONTAINS, "External"),
        (NumberTest, NumberOperator.GREATER_THAN, 3),
        (BooleanTest, BooleanOperator.IS_NOT, False),
    ],
)
def test_operator_enums_are_stored_as_members_and_serialized_as_readable_values(family, operator, value):
    test = family(operator=operator, value=value)
    parsed = family.model_validate({"operator": operator.value, "value": value})

    assert parsed.operator is operator
    assert test == parsed
    assert test.model_dump(mode="json")["operator"] == operator.value
    assert family.model_validate_json(test.model_dump_json()).operator is operator
