"""Validate complete queries against an offline property catalogue."""

import json
from pathlib import Path
from uuid import UUID

import pytest

from multiconn_archicad.models.tapir.commands import GetAllPropertiesResult
from multiconn_archicad.models.tapir.types import ElementType, PropertyDetails
from multiconn_archicad.utilities.queries import (
    AllOf,
    AmbiguousPropertyTypeError,
    AnyOf,
    ElementTypePredicate,
    InvalidPropertyTestError,
    NumberTest,
    PropertyCatalogue,
    PropertyPredicate,
    PropertyTest,
    Query,
    QueryValidationError,
    TextTest,
    validate_query,
)
from multiconn_archicad.utilities.queries import TestRegistry as Registry

pytestmark = pytest.mark.unit

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "query_property_discovery_19723.json"
ELEMENT_ID = UUID("7E221F33-829B-4FBC-A670-E74DABCE6289")
HEIGHT = UUID("02DB7087-5E1D-4AF3-AF62-4D08C1B70C3E")
POSITION = UUID("53402BE5-29D9-44A5-B6D6-4FA90938DDC9")
MISSING = UUID("00000000-0000-0000-0000-000000000000")


@pytest.fixture
def catalogue() -> PropertyCatalogue:
    metadata = GetAllPropertiesResult.model_validate_json(FIXTURE.read_text(encoding="utf-8")).properties
    return PropertyCatalogue(metadata, Registry.from_union(PropertyTest))


def property_test(property_id=HEIGHT, test=None) -> PropertyPredicate:
    return PropertyPredicate(
        property_id=property_id,
        test=NumberTest(operator="is greater than", value=3) if test is None else test,
    )


def test_valid_nested_query_and_metadata_are_not_transformed(catalogue):
    query = Query(
        where=AllOf(
            items=(
                ElementTypePredicate(types=(ElementType.WALL,)),
                property_test(),
                AnyOf(
                    items=(
                        property_test(ELEMENT_ID, TextTest(operator="does not contain", value="Temporary")),
                        property_test(test=NumberTest(operator="is greater than or equal to", value=1)),
                    )
                ),
            )
        )
    )
    original_query = query.model_dump(mode="json")
    original_metadata = catalogue.describe()

    result = validate_query(query, catalogue)

    assert result.is_valid
    assert result.issues == ()
    assert result.raise_for_errors() is None
    assert result.describe() == {"is_valid": True, "issues": []}
    assert query.model_dump(mode="json") == original_query
    assert catalogue.describe() == original_metadata


def test_collects_all_nested_issue_kinds_with_paths_and_field_context(catalogue):
    query = Query(
        where=AllOf(
            items=(
                property_test(MISSING),
                AnyOf(
                    items=(
                        property_test(test=TextTest(operator="contains", value="3")),
                        AllOf(items=(property_test(POSITION),)),
                    )
                ),
            )
        )
    )

    result = validate_query(query, catalogue)

    assert not result.is_valid
    assert [(issue.code, issue.path) for issue in result.issues] == [
        ("unknown_property", "where.items[0].property_id"),
        ("invalid_test", "where.items[1].items[0].test"),
        ("unsupported_property", "where.items[1].items[1].items[0].test"),
    ]
    missing, wrong_type, unsupported = result.issues
    assert missing.property_id == MISSING
    assert missing.name is None and missing.group is None and missing.qualified_name is None
    assert wrong_type.qualified_name == "WallProperties / Wall Height"
    assert "requires NumberTest, got TextTest" in wrong_type.message
    assert unsupported.qualified_name == "CategoryPropertyDefinitionGroup / Position"
    assert unsupported.location == ("where", "items", 1, "items", 1, "items", 0, "test")


@pytest.mark.parametrize("group", [AllOf, AnyOf])
def test_groups_check_all_branches_even_after_valid_or_invalid_siblings(catalogue, group):
    query = Query(
        where=group(
            items=(
                ElementTypePredicate(types=(ElementType.WALL,)),
                property_test(MISSING),
                property_test(test=TextTest(operator="is", value="3")),
            )
        )
    )

    result = validate_query(query, catalogue)

    assert [issue.path for issue in result.issues] == ["where.items[1].property_id", "where.items[2].test"]


def test_negative_operator_does_not_hide_context_errors(catalogue):
    query = Query(where=property_test(MISSING, TextTest(operator="is not", value="Temporary")))
    result = validate_query(query, catalogue)

    assert not result.is_valid
    assert result.issues[0].path == "where.property_id"
    assert result.issues[0].code == "unknown_property"


def test_repeated_properties_keep_an_issue_for_each_query_occurrence(catalogue):
    repeated = property_test(MISSING)
    query = Query(where=AllOf(items=(repeated, repeated)))

    result = validate_query(query, catalogue)

    assert [issue.path for issue in result.issues] == ["where.items[0].property_id", "where.items[1].property_id"]


def test_element_type_queries_need_no_property_metadata():
    empty_catalogue = PropertyCatalogue([], Registry.from_union(PropertyTest))
    query = Query(where=ElementTypePredicate(types=(ElementType.WALL,)))

    assert validate_query(query, empty_catalogue).is_valid


def test_result_and_exception_expose_complete_json_friendly_issues(catalogue):
    query = Query(where=AllOf(items=(property_test(MISSING), property_test(POSITION))))
    result = validate_query(query, catalogue)

    description = json.loads(json.dumps(result.describe()))

    assert description["is_valid"] is False
    assert len(description["issues"]) == 2
    assert description["issues"][0]["reference"] == {"kind": "property", "property_id": str(MISSING)}
    assert description["issues"][0]["location"] == ["where", "items", 0, "property_id"]
    with pytest.raises(QueryValidationError) as caught:
        result.raise_for_errors()
    assert caught.value.result is result
    assert "where.items[0].property_id" in str(caught.value)
    assert "where.items[1].test" in str(caught.value)


class LimitedNumberTest(NumberTest):
    def validate_for(self, details: PropertyDetails) -> None:
        super().validate_for(details)
        if self.value > 10:
            raise InvalidPropertyTestError("Example operand limit is 10")


def test_family_operand_rules_are_validated_at_each_occurrence(catalogue):
    limited_catalogue = PropertyCatalogue([catalogue[HEIGHT].details], Registry(LimitedNumberTest))
    query = Query(
        where=AllOf(
            items=(
                property_test(test=LimitedNumberTest(operator="is", value=5)),
                property_test(test=LimitedNumberTest(operator="is", value=11)),
            )
        )
    )

    result = validate_query(query, limited_catalogue)

    assert len(result.issues) == 1
    assert result.issues[0].code == "invalid_test"
    assert result.issues[0].path == "where.items[1].test"
    assert result.issues[0].message == "Example operand limit is 10"


@pytest.mark.parametrize(
    "error",
    [
        RuntimeError("broken validator"),
        ValueError("unexpected implementation error"),
        AmbiguousPropertyTypeError("ambiguous family"),
    ],
)
def test_unexpected_or_configuration_errors_propagate(catalogue, error):
    class BrokenNumberTest(NumberTest):
        def validate_for(self, details: PropertyDetails) -> None:
            raise error

    broken_catalogue = PropertyCatalogue([catalogue[HEIGHT].details], Registry(BrokenNumberTest))
    query = Query(where=property_test(test=BrokenNumberTest(operator="is", value=3)))

    with pytest.raises(type(error)) as caught:
        validate_query(query, broken_catalogue)
    assert caught.value is error
